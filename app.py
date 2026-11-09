import json
import logging
import os
import io
import hmac
import base64
import hashlib
import re
import unicodedata
import sqlite3
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from flask import Flask, request, render_template, jsonify, send_file, make_response, url_for as flask_url_for
from werkzeug.utils import secure_filename
from werkzeug.exceptions import HTTPException, BadRequest

from config import Config, DevelopmentConfig
from core.limits import validate_text
from core.public_errors import public_message
from core.checker import PlagiarismChecker
from core.extractor import extract_text_from_file, extract_document, is_allowed_file
from core.batch_processor import BatchProcessor
from core.report_generator import ReportGenerator
from core.paraphraser import AcademicParaphraser
from core.citation_generator import CitationGenerator
from core.diff_comparator import DraftComparator
from core.student_coach import AcademicStudentCoach
from core.writing_cleanup import WritingCleanup
from core.site_analytics import SiteAnalytics
from core.vector_engine import VectorSearchEngine

# Configure standard logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] in %(module)s: %(message)s"
)
logger = logging.getLogger(__name__)


def _read_app_version(default: str = "0.0.0") -> str:
    """Single source of truth for the version shown in the UI, reports, and
    OpenAPI spec: package.json's "version", the number that actually gets
    bumped and released (see CHANGELOG.md). Falls back to `default` rather
    than raising, so a missing/unreadable file never breaks the app itself
    -- only the version badge, which is cosmetic.
    """
    try:
        package_json = Path(__file__).resolve().parent / "package.json"
        return json.loads(package_json.read_text(encoding="utf-8")).get("version", default)
    except (OSError, ValueError):
        logger.warning("Could not read version from package.json; using default %s", default)
        return default


APP_VERSION = _read_app_version()

APP_CSP = (
    "default-src 'self'; script-src 'self'; "
    "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
    "font-src https://fonts.gstatic.com; img-src 'self' data:; connect-src 'self'; "
    "object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'"
)
# Swagger UI is loaded from a CDN (pinned version) and needs inline bootstrap script/styles.
SWAGGER_UI_VERSION = "5.17.14"
DOCS_CSP = (
    "default-src 'self'; script-src 'unsafe-inline' https://unpkg.com; "
    "style-src 'unsafe-inline' https://unpkg.com; img-src 'self' data: https:; "
    "connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
)


def create_app(config_class: type = Config) -> Flask:
    """Application factory for Plagiarism Detector Pro."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    @app.before_request
    def validate_request():
        if request.is_json:
            # MCP endpoint handles its own JSON validation (supports batch arrays)
            if request.path.startswith("/mcp"):
                return
            data = request.get_json()
            if not isinstance(data, dict):
                raise BadRequest("JSON body must be an object.")
            text_fields = ("query", "sentence", "text", "references", "draft_v1",
                           "draft_v2", "student_name", "paper_title", "source_name", "source_title",
                           "email", "company")
            for field in text_fields:
                if field in data and not isinstance(data[field], str):
                    if field in ("source_name", "source_title") and data[field] is None:
                        continue
                    raise BadRequest(f"{field} must be a string.")
                if isinstance(data.get(field), str):
                    try:
                        validate_text(data[field])
                    except ValueError as e:
                        raise BadRequest(public_message(e))
            for field in ("include_web", "exclude_quotes", "private_draft", "exclude_bibliography"):
                if field in data and not isinstance(data[field], bool):
                    raise BadRequest(f"{field} must be a boolean.")
            if "consent" in data and not isinstance(data["consent"], bool):
                raise BadRequest("consent must be a boolean.")
            if "protected_terms" in data:
                terms = data["protected_terms"]
                if (not isinstance(terms, list) or len(terms) > 50
                        or any(not isinstance(term, str) or len(term) > 120 for term in terms)):
                    raise BadRequest("protected_terms must be a list of up to 50 short strings.")
            if "accept" in data:
                accepted = data["accept"]
                if not isinstance(accepted, list) or any(not isinstance(index, int) or index < 0 for index in accepted):
                    raise BadRequest("accept must be a list of non-negative edit indices.")
        if (request.path == "/sources/upload"
                or (request.method == "DELETE" and request.path.startswith("/sources/"))
                or request.path.startswith("/api/admin/")):
            expected = app.config.get("ADMIN_PIN", "")
            provided = request.headers.get("X-Admin-PIN", "")
            if not expected or not hmac.compare_digest(provided.encode(), str(expected).encode()):
                return jsonify({"error": "Invalid or missing Admin PIN. Corpus changes are forbidden."}), 403

    # Cache busting for static assets: automatically appends timestamp query parameter
    @app.context_processor
    def inject_asset_version():
        def dated_url_for(endpoint, **values):
            if endpoint == 'static':
                filename = values.get('filename', None)
                if filename:
                    file_path = os.path.join(app.root_path, 'static', filename)
                    if os.path.isfile(file_path):
                        values['v'] = int(os.stat(file_path).st_mtime)
            return flask_url_for(endpoint, **values)
        try:
            current_visitor_stats = analytics.summary(30)
        except (NameError, OSError, sqlite3.Error):
            current_visitor_stats = {"page_views": 0, "all_time_page_views": 0, "days": 30}
        return dict(url_for=dated_url_for, app_version=APP_VERSION, visitor_stats=current_visitor_stats)

    # Cache control headers to prevent stale reverse proxy / CDN / browser caching
    @app.after_request
    def set_cache_headers(response):
        if request.path.startswith('/static/'):
            # Static assets with ?v= query can be cached with revalidation
            response.headers['Cache-Control'] = 'public, max-age=3600, must-revalidate'
        elif request.path == '/' or request.path.endswith('.html'):
            # Main HTML document should always revalidate so fresh CSS/JS URLs are picked up instantly
            response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response.headers['Pragma'] = 'no-cache'
            response.headers['Expires'] = '0'
        if not request.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers.setdefault(
            "Content-Security-Policy",
            DOCS_CSP if request.path == "/docs" else APP_CSP,
        )
        return response

    # Ensure sources directory exists
    os.makedirs(app.config["SOURCES_DIR"], exist_ok=True)

    # Initialize checker service
    checker = PlagiarismChecker(
        sources_dir=app.config["SOURCES_DIR"],
        search_timeout=app.config["WEB_SEARCH_TIMEOUT"]
    )
    batch_processor = BatchProcessor(checker)
    report_generator = ReportGenerator()
    analytics = SiteAnalytics(app.config["ANALYTICS_DB_PATH"])

    app.checker = checker
    app.batch_processor = batch_processor
    app.report_generator = report_generator
    app.analytics = analytics

    # Register error handlers
    register_error_handlers(app)

    # Routes
    @app.route("/", methods=["GET"])
    def index():
        """Renders the main plagiarism detector dashboard."""
        sources = checker.list_sources()
        try:
            analytics.record_page_view("/")
            visitor_stats = analytics.summary(30)
        except (OSError, sqlite3.Error):
            logger.exception("Site analytics storage is unavailable")
            visitor_stats = {"page_views": 0, "all_time_page_views": 0, "days": 30}
        return render_template("index.html", sources_count=len(sources), sources=sources, visitor_stats=visitor_stats)

    @app.route("/api/analytics/summary", methods=["GET"])
    def analytics_summary():
        """Return aggregate page-view counts. No visitor identity is exposed."""
        return jsonify(analytics.summary(30)), 200

    @app.route("/api/visitors/email", methods=["POST"])
    def visitor_email():
        """Store an explicitly consented release-update email address."""
        data = request.get_json() or {}
        # Quietly accept bot-filled honeypots without retaining their input.
        if data.get("company"):
            return jsonify({"message": "Thanks. You're on the update list."}), 200
        if data.get("consent") is not True:
            return jsonify({"error": "Please consent to receiving project updates."}), 400
        try:
            analytics.subscribe(data.get("email"))
        except ValueError as error:
            return jsonify({"error": public_message(error)}), 400
        return jsonify({"message": "Thanks. You're on the update list."}), 200

    @app.route("/api/admin/subscribers", methods=["GET"])
    def admin_subscribers():
        """List consented email signups for the authenticated site administrator."""
        subscribers = analytics.subscribers()
        return jsonify({"count": len(subscribers), "subscribers": subscribers}), 200

    @app.route("/", methods=["POST"])
    def legacy_form_submit():
        """Handles legacy form post submissions."""
        query_text = ""
        if "file" in request.files and request.files["file"].filename:
            uploaded_file = request.files["file"]
            if is_allowed_file(uploaded_file.filename):
                try:
                    query_text = extract_text_from_file(uploaded_file)
                except Exception as e:
                    logger.error("File extraction error: %s", e)
                    return render_template("index.html", error="The file could not be read. Check the format and try again.", sources_count=len(checker.sources))
        else:
            query_text = request.form.get("query", "")

        if not query_text.strip():
            return render_template("index.html", error="Please enter valid text.", sources_count=len(checker.sources))

        result = checker.analyze(query_text, include_web_sources=True)
        sources = checker.list_sources()
        return render_template("index.html", result=result, query_text=query_text, sources_count=len(sources), sources=sources)

    @app.route("/check", methods=["POST"])
    def check_plagiarism():
        """
        API endpoint to scan text or uploaded document for plagiarism,
        AI content, and citation integrity.
        """
        query_text = ""
        include_web = True
        exclude_quotes = False
        private_draft = True
        exclude_bibliography = False
        document_context = None
        style_profile = "academic_report"

        if "file" in request.files and request.files["file"].filename:
            file_obj = request.files["file"]
            if not is_allowed_file(file_obj.filename):
                return jsonify({
                    "error": "Unsupported file format. Please upload .docx, .pdf, .txt, or .md."
                }), 400
            try:
                document_context = extract_document(file_obj)
                query_text = document_context["analysis_text"]
            except Exception as e:
                logger.error("Failed to extract file text: %s", e)
                return jsonify({"error": "Failed to extract document text. Check that the file is a valid, unencrypted document."}), 400
            include_web = request.form.get("include_web", "true").lower() in ("true", "1", "yes")
            exclude_quotes = request.form.get("exclude_quotes", "false").lower() in ("true", "1", "yes")
            private_draft = request.form.get("private_draft", "true").lower() in ("true", "1", "yes")
            exclude_bibliography = request.form.get("exclude_bibliography", "false").lower() in ("true", "1", "yes")
            style_profile = request.form.get("style_profile", "academic_report")
        elif request.is_json:
            data = request.get_json() or {}
            query_text = data.get("query", "")
            include_web = bool(data.get("include_web", True))
            exclude_quotes = bool(data.get("exclude_quotes", False))
            private_draft = bool(data.get("private_draft", True))
            exclude_bibliography = data.get("exclude_bibliography", False)
            style_profile = data.get("style_profile", "academic_report")
        else:
            query_text = request.form.get("query", "")
            include_web = request.form.get("include_web", "true").lower() in ("true", "1", "yes")
            exclude_quotes = request.form.get("exclude_quotes", "false").lower() in ("true", "1", "yes")
            private_draft = request.form.get("private_draft", "true").lower() in ("true", "1", "yes")
            exclude_bibliography = request.form.get("exclude_bibliography", "false").lower() in ("true", "1", "yes")
            style_profile = request.form.get("style_profile", "academic_report")

        if not query_text or not query_text.strip():
            if document_context and document_context.get("extraction_status") == "empty_requires_ocr":
                return jsonify({"error": "No extractable PDF text was found; OCR is required.", "document_metadata": document_context}), 422
            return jsonify({"error": "No text or document provided for analysis."}), 400

        try:
            logger.info("Executing similarity and writing-style scan (Words: %d, Include Web: %s, Exclude Quotes: %s, Private Draft: %s)",
                        len(query_text.split()), include_web, exclude_quotes, private_draft)
            analysis = checker.analyze(
                query_text,
                include_web_sources=include_web,
                exclude_quotes=exclude_quotes,
                private_draft=private_draft,
                exclude_bibliography=exclude_bibliography,
                document_context=document_context,
                style_profile=style_profile,
            )

            # Add Student Writing & Academic Integrity Coach Insights
            claim_analysis = analysis.get("claim_analysis") or AcademicStudentCoach.scan_claims(query_text)
            unsupported_claims = [claim for claim in claim_analysis if not claim.get("has_citation")]
            tone_suggestions = AcademicStudentCoach.analyze_tone_and_vocabulary(query_text)
            thesis_eval = AcademicStudentCoach.evaluate_thesis_abstract(query_text)
            analysis["student_coach"] = {
                "unsupported_claims": unsupported_claims,
                "unsupported_claims_count": len(unsupported_claims),
                "claims": claim_analysis,
                "claims_count": len(claim_analysis),
                "cited_claims_count": sum(1 for claim in claim_analysis if claim.get("has_citation")),
                "tone_suggestions": tone_suggestions,
                "tone_suggestions_count": len(tone_suggestions),
                "thesis_evaluation": thesis_eval
            }

            return jsonify(analysis), 200
        except ValueError as e:
            return jsonify({"error": public_message(e)}), 400
        except Exception as e:
            logger.exception("Internal analysis error: %s", e)
            return jsonify({"error": "Unable to complete the request. See server logs for details."}), 500

    @app.route("/check/batch", methods=["POST"])
    def check_batch_submissions():
        """
        Processes bulk submissions via ZIP file archive or multiple uploaded files.
        """
        include_web = request.form.get("include_web", "true").lower() in ("true", "1", "yes")
        exclude_quotes = request.form.get("exclude_quotes", "false").lower() in ("true", "1", "yes")

        exclude_bibliography = request.form.get("exclude_bibliography", "false").lower() in ("true", "1", "yes")

        uploaded_files = request.files.getlist("files") or request.files.getlist("file")
        if not uploaded_files or not uploaded_files[0].filename:
            return jsonify({"error": "No files or ZIP archive provided."}), 400

        first_file = uploaded_files[0]
        if first_file.filename.lower().endswith('.zip'):
            try:
                batch_result = batch_processor.process_zip_archive(
                    first_file.stream, include_web=include_web, exclude_quotes=exclude_quotes, exclude_bibliography=exclude_bibliography
                )
                return jsonify(batch_result), 200
            except (ValueError, zipfile.BadZipFile) as e:
                return jsonify({"error": public_message(e)}), 400
            except Exception as e:
                logger.exception("Failed to process ZIP archive: %s", e)
                return jsonify({"error": "Unable to complete the request. See server logs for details."}), 500

        # Multiple individual files
        file_tuples = []
        for f in uploaded_files:
            if f.filename and is_allowed_file(f.filename):
                file_tuples.append((secure_filename(f.filename), io.BytesIO(f.read())))

        if not file_tuples:
            return jsonify({"error": "No supported document files found in upload."}), 400

        try:
            batch_result = batch_processor.process_multiple_files(
                file_tuples, include_web=include_web, exclude_quotes=exclude_quotes, exclude_bibliography=exclude_bibliography
            )
            return jsonify(batch_result), 200
        except ValueError as e:
            return jsonify({"error": public_message(e)}), 400
        except Exception as e:
            logger.exception("Batch processing error: %s", e)
            return jsonify({"error": "Unable to complete the request. See server logs for details."}), 500

    @app.route("/reports/html", methods=["POST"])
    def generate_report():
        """Generates a printable HTML/PDF-ready academic report."""
        data = request.get_json() or {}
        try:
            html_content = report_generator.generate_html_report(data)
        except ValueError as e:
            raise BadRequest(public_message(e))
        response = make_response(html_content)
        response.headers["Content-Type"] = "text/html"
        return response

    @app.route("/reports/certificate", methods=["POST"])
    def generate_certificate():
        """Generates an unsigned advisory summary of supplied analysis data."""
        payload = request.get_json() or {}
        data = payload.get("data", payload)
        student_name = payload.get("student_name", "Student / Author")
        paper_title = payload.get("paper_title", "Academic Manuscript")
        try:
            html_content = report_generator.generate_student_certificate(
                data, student_name=student_name, paper_title=paper_title
            )
        except ValueError as e:
            raise BadRequest(public_message(e))
        response = make_response(html_content)
        response.headers["Content-Type"] = "text/html"
        return response

    @app.route("/api/spec.json", methods=["GET"])
    def openapi_spec():
        """Returns the OpenAPI 3.0 specification for Plagiarism Detector Pro."""
        return jsonify({
            "openapi": "3.0.3",
            "info": {
                "title": "Plagiarism Detector Pro API",
                "version": APP_VERSION,
                "description": "Academic text-similarity, citation, and writing-pattern analysis REST API."
            },
            "servers": [
                {"url": "https://plag.subba.dev", "description": "Production Server"},
                {"url": "http://127.0.0.1:5001", "description": "Local Development"}
            ],
            "paths": {
                "/check": {
                    "post": {
                        "summary": "Scan text or an uploaded document for lexical overlap and writing-pattern signals",
                        "responses": {"200": {"description": "Analysis result."}}
                    }
                },
                "/check/batch": {
                    "post": {
                        "summary": "Bulk class assignment scanner (.ZIP or multi-file)",
                        "responses": {"200": {"description": "Gradebook result."}}
                    }
                },
                "/reports/html": {
                    "post": {
                        "summary": "Generate printable academic report HTML",
                        "responses": {"200": {"description": "Report HTML."}}
                    }
                },
                "/reports/certificate": {
                    "post": {
                        "summary": "Generate an unsigned advisory analysis summary",
                        "responses": {"200": {"description": "Advisory summary HTML."}}
                    }
                },
                "/sources": {
                    "get": {"summary": "List all institutional corpus documents"},
                    "post": {"summary": "Upload document to institutional repository"}
                }
            }
        })

    @app.route("/docs", methods=["GET"])
    def swagger_ui():
        """Renders interactive Swagger UI documentation."""
        return """<!DOCTYPE html>
<html>
<head>
    <title>Plagiarism Detector Pro - API Documentation</title>
    <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@{v}/swagger-ui.css" />
    <style>body { margin: 0; background: #0f172a; } .swagger-ui { filter: invert(88%) hue-rotate(180deg); }</style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@{v}/swagger-ui-bundle.js"></script>
    <script>
        window.onload = () => {
            SwaggerUIBundle({
                url: '/api/spec.json',
                dom_id: '#swagger-ui',
                deepLinking: true,
                presets: [SwaggerUIBundle.presets.apis],
                layout: "BaseLayout"
            });
        };
    </script>
</body>
</html>""".replace("{v}", SWAGGER_UI_VERSION)

    @app.route("/sources", methods=["GET"])
    def get_sources():
        """Returns metadata for all indexed reference sources."""
        sources = checker.list_sources()
        return jsonify({"sources": sources, "total": len(sources)}), 200

    @app.route("/sources/upload", methods=["POST"])
    def upload_source():
        """Uploads a new reference document to the institutional corpus."""
        if "file" not in request.files:
            return jsonify({"error": "No file uploaded."}), 400

        file_obj = request.files["file"]
        if not file_obj or not file_obj.filename:
            return jsonify({"error": "No file selected."}), 400

        if not is_allowed_file(file_obj.filename):
            return jsonify({"error": "Unsupported file type for reference database."}), 400

        safe_name = secure_filename(file_obj.filename)
        try:
            source_data = checker.add_source(safe_name, file_obj)
            logger.info("Added new source to database: %s", safe_name)
            return jsonify({
                "success": True,
                "filename": safe_name,
                "word_count": source_data.get("word_count", 0)
            }), 201
        except FileExistsError:
            return jsonify({"error": "A reference source with this name already exists."}), 400
        except ValueError as e:
            return jsonify({"error": public_message(e)}), 400
        except Exception as e:
            logger.exception("Failed to add reference source: %s", e)
            return jsonify({"error": "Unable to complete the request. See server logs for details."}), 500

    @app.route("/sources/<filename>", methods=["DELETE"])
    def delete_source(filename: str):
        """Deletes a reference document from the corpus with Admin PIN verification."""
        safe_name = secure_filename(filename)
        deleted = checker.delete_source(safe_name)
        if deleted:
            logger.info("Deleted source from database with valid PIN: %s", safe_name)
            return jsonify({"success": True, "filename": safe_name}), 200
        return jsonify({"error": "Source file not found or could not be deleted."}), 404

    @app.route("/api/paraphrase", methods=["POST"])
    def paraphrase_sentence():
        """Generates ethical scholarly paraphrasing and synthesis alternatives for flagged text."""
        data = request.get_json(silent=True) or {}
        sentence = data.get("sentence", "").strip()
        if not sentence:
            return jsonify({"error": "No sentence provided for paraphrasing."}), 400

        source_name = data.get("source_name")
        source_title = data.get("source_title")
        res = AcademicParaphraser.synthesize_sentence(sentence, source_name, source_title)
        return jsonify(res), 200

    @app.route("/api/cite", methods=["POST"])
    def generate_citation():
        """Generates APA, MLA, IEEE, Chicago, and BibTeX citations from DOI, arXiv, or title."""
        data = request.get_json(silent=True) or {}
        query = data.get("query", "").strip()
        if not query:
            return jsonify({"error": "Please provide a DOI, arXiv link, or paper title."}), 400

        res = CitationGenerator.generate_from_identifier(query)
        return jsonify(res), 200

    @app.route("/check/compare-drafts", methods=["POST"])
    def compare_drafts():
        """Quantifies revisions, text additions, and originality delta between Draft v1 and Draft v2."""
        data = request.get_json(silent=True) or {}
        draft_v1 = data.get("draft_v1", "").strip()
        draft_v2 = data.get("draft_v2", "").strip()

        if not draft_v1 or not draft_v2:
            return jsonify({"error": "Please provide both Draft 1 and Draft 2 texts for comparison."}), 400

        res = DraftComparator.compare_drafts(draft_v1, draft_v2)
        return jsonify(res), 200

    @app.route("/api/student-coach/tone-and-claims", methods=["POST"])
    def analyze_tone_and_claims():
        """Scans input text for conversational tone and unsupported empirical assertions."""
        data = request.get_json(silent=True) or {}
        text = data.get("text", "").strip()
        if not text:
            return jsonify({"error": "No text provided for coach analysis."}), 400

        unsupported = AcademicStudentCoach.scan_unsupported_claims(text)
        tone_items = AcademicStudentCoach.analyze_tone_and_vocabulary(text)
        return jsonify({
            "unsupported_claims": unsupported,
            "unsupported_claims_count": len(unsupported),
            "tone_suggestions": tone_items,
            "tone_suggestions_count": len(tone_items)
        }), 200

    @app.route("/api/student-coach/alphabetize-references", methods=["POST"])
    def alphabetize_references():
        """Sorts bibliography list alphabetically, checks publication years and missing DOIs."""
        data = request.get_json(silent=True) or {}
        references = data.get("references", "").strip()
        if not references:
            return jsonify({"error": "Please provide bibliography references text."}), 400

        res = AcademicStudentCoach.alphabetize_and_format_references(references)
        return jsonify(res), 200

    @app.route("/api/student-coach/evaluate-thesis", methods=["POST"])
    def evaluate_thesis():
        """Evaluates abstract/thesis opening for scientific hypothesis, methodology, and significance."""
        data = request.get_json(silent=True) or {}
        text = data.get("text", "").strip()
        if not text:
            return jsonify({"error": "No text provided for thesis evaluation."}), 400

        res = AcademicStudentCoach.evaluate_thesis_abstract(text)
        return jsonify(res), 200

    @app.route("/api/writing-cleanup", methods=["POST"])
    def suggest_writing_cleanup():
        """Deterministic, offline predictable-vocabulary swap suggestions.

        Never rewrites anything itself: returns the edit-eligible findings for
        the client to display, and separately accepts which indices to apply.
        """
        data = request.get_json(silent=True) or {}
        text = data.get("text", "")
        if not text or not text.strip():
            return jsonify({"error": "No text provided for cleanup."}), 400

        protected_terms = data.get("protected_terms") or []
        length_mode = data.get("length_mode", "no_increase")
        try:
            review = WritingCleanup.review(text, protected_terms, length_mode)
        except ValueError as error:
            return jsonify({"error": str(error)}), 400
        return jsonify(review), 200

    @app.route("/api/writing-cleanup/apply", methods=["POST"])
    def apply_writing_cleanup():
        """Applies only the caller-selected subset of freshly recomputed edits.

        The edit content (start/end/replacement) is always re-derived from
        `text` on the server; the client can only choose which indices to
        include, never supply arbitrary replacement text.
        """
        data = request.get_json(silent=True) or {}
        text = data.get("text", "")
        if not text or not text.strip():
            return jsonify({"error": "No text provided for cleanup."}), 400
        accept = data.get("accept")
        if accept is not None and (
            not isinstance(accept, list) or not all(isinstance(i, int) and not isinstance(i, bool) for i in accept)
        ):
            return jsonify({"error": "accept must be a list of integer edit indices."}), 400
        protected_terms = data.get("protected_terms") or []
        length_mode = data.get("length_mode", "no_increase")
        try:
            review = WritingCleanup.review(text, protected_terms, length_mode)
        except ValueError as error:
            return jsonify({"error": str(error)}), 400
        all_edits = review["edits"]
        accepted = set(accept or [])
        selected = all_edits if accept is None else [e for e in all_edits if e["index"] in accepted]
        cleaned_text = WritingCleanup.apply_edits(text, selected)

        def revision_metrics(value):
            analysis = checker.analyze(
                value, include_web_sources=False, private_draft=True,
                exclude_quotes=False, exclude_bibliography=False,
            )
            citations = analysis.get("citation_analysis") or {}
            style = analysis.get("style_review") or {}
            readability = analysis.get("readability") or {}
            return {
                "word_count": len(value.split()),
                "local_similarity": analysis.get("overall_similarity", 0),
                "style_pattern_index": style.get("style_pattern_index"),
                "citations_detected": citations.get("citation_count", len(citations.get("citations", []))),
                "reading_grade": readability.get("fk_grade_level", readability.get("grade_level")),
            }

        before = revision_metrics(text)
        after = revision_metrics(cleaned_text)
        return jsonify({
            "cleaned_text": cleaned_text,
            "applied_count": len(selected),
            "excluded_count": review["excluded_count"],
            "applied_edits": selected,
            "before": before,
            "after": after,
            "word_delta": after["word_count"] - before["word_count"],
            "comparison_note": "Similarity is rescored against the local corpus only; run a full scan for external-source coverage.",
        }), 200

    # ── MCP (Model Context Protocol) HTTP endpoint ───────────────────────────
    # Implements stateless Streamable HTTP transport (MCP 2025-03-26+) so Claude Web,
    # Claude Desktop, Cursor, and any MCP-aware client can call plag tools
    # directly at https://plag.subba.dev/mcp
    # Auth: Bearer token via Authorization or X-Api-Key header.
    # Set MCP_API_KEY env var on the server. Leave blank to disable auth.

    _MCP_PROTOCOL_VERSIONS = ("2025-06-18", "2025-03-26")
    _MCP_DEFAULT_PROTOCOL_VERSION = "2025-03-26"

    _MCP_SCAN_OPTIONS = {
        "references_text": {"type": "string", "description": "Reference list used for citation linkage but excluded from similarity scoring."},
        "include_web": {"type": "boolean", "description": "Send search queries to configured external sources; default false."},
        "genre": {"type": "string", "enum": ["academic_report", "business_report", "general_essay", "technical_documentation"]},
        "detail_level": {"type": "string", "enum": ["summary", "standard", "full"], "description": "Defaults to summary."},
        "page": {"type": "integer", "minimum": 1},
        "page_size": {"type": "integer", "minimum": 1, "maximum": 50},
        "fields": {"type": "array", "items": {"type": "string"}, "description": "Optional top-level result fields."},
        "minimum_match_words": {"type": "integer", "minimum": 4, "maximum": 50},
        "whitelist_terms": {"type": "array", "items": {"type": "string"}},
        "reference_sources": {"type": "array", "items": {"type": "object"}, "description": "Cited sources as {title,text}; compared without persisting them."},
        "export_report": {"type": "boolean", "description": "Include a dated Markdown report."},
    }

    _MCP_TOOLS = [
        {
            "name": "plag_scan_text",
            "description": "Measures lexical overlap against configured sources and reports an uncalibrated writing-pattern score, evidence integrity, and student-coaching signals.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text":                 {"type": "string",  "description": "The academic text or essay to scan."},
                    "exclude_bibliography": {"type": "boolean", "description": "Exclude the References section from scoring."},
                    "exclude_quotes":       {"type": "boolean", "description": "Exclude only quoted text from similarity scoring."},
                    "include_web":          {"type": "boolean", "description": "Include web search results (default false)."},
                    **_MCP_SCAN_OPTIONS,
                },
                "required": ["text"],
            },
        },
        {
            "name": "plag_scan_document",
            "description": "Scans an uploaded DOCX or text-based PDF. Content is base64 encoded; title-page, table, code, and appendix blocks can be excluded.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "filename": {"type": "string", "description": "Filename ending in .docx or .pdf."},
                    "content_base64": {"type": "string", "description": "Base64-encoded document bytes."},
                    "skip_title_page": {"type": "boolean", "description": "Default true."},
                    "skip_tables": {"type": "boolean", "description": "Default true."},
                    "skip_code": {"type": "boolean", "description": "Default true."},
                    "skip_appendix": {"type": "boolean", "description": "Default true."},
                    **_MCP_SCAN_OPTIONS,
                },
                "required": ["filename", "content_base64"],
            },
        },
        {
            "name": "plag_attribution_coach",
            "description": "Explains whether a passage should be quoted, cited, or restated through the student's own analysis. It does not rewrite text to lower a score.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "sentence":     {"type": "string", "description": "The sentence to restructure."},
                    "source_title": {"type": "string", "description": "Author or publication that should receive attribution."},
                },
                "required": ["sentence"],
            },
        },
        {
            "name": "plag_academic_coach",
            "description": "Scans an essay for unsupported empirical claims, conversational phrases with scholarly alternatives, and thesis strength (0–100).",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Manuscript text or excerpt to evaluate."},
                },
                "required": ["text"],
            },
        },
        {
            "name": "plag_generate_citation",
            "description": "Generates BibTeX, APA 7th, MLA 9th, and IEEE citations from a DOI, arXiv ID, or paper title.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "DOI (e.g. 10.1145/...), arXiv ID (e.g. 1706.03762), or Paper Title."},
                },
                "required": ["query"],
            },
        },
        {
            "name": "plag_alphabetize_references",
            "description": "Alphabetizes an unorganized bibliography by primary author last name, validates publication years, and checks for DOIs.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "references_text": {"type": "string", "description": "Raw bibliography or list of references (one per line)."},
                },
                "required": ["references_text"],
            },
        },
        {
            "name": "plag_compare_drafts",
            "description": "Compares Draft 1 against Draft 2 to calculate revision delta percentages, newly added sections, and retained phrasing.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "draft_v1": {"type": "string", "description": "Original draft text."},
                    "draft_v2": {"type": "string", "description": "Revised draft text."},
                },
                "required": ["draft_v1", "draft_v2"],
            },
        },
    ]

    def _mcp_mixed_script_findings(text):
        findings = []
        for match in re.finditer(r"\b[^\W\d_]+\b", text, re.UNICODE):
            word = match.group(0)
            has_latin = any("LATIN" in unicodedata.name(ch, "") for ch in word)
            foreign = [ch for ch in word if any(script in unicodedata.name(ch, "") for script in ("GREEK", "CYRILLIC"))]
            if has_latin and foreign:
                findings.append({"word": word, "offset": match.start(), "characters": foreign})
        return findings

    def _mcp_document_text(document, args):
        kept, skipped = [], {"title_page": 0, "tables": 0, "code": 0, "appendix": 0, "references": 0}
        in_appendix = False
        found_body_heading = document.get("source_format") == "pdf"
        for block in document.get("blocks", []):
            value = block.get("text", "")
            kind = block.get("type", "paragraph")
            if re.match(r"^\s*(?:appendix|appendices)\b", value, re.I):
                in_appendix = True
            if kind == "heading" and re.match(r"^\s*(?:abstract|introduction|background|methods?)\b", value, re.I):
                found_body_heading = True
            reason = None
            if args.get("skip_title_page", True) and ((block.get("page") == 1) or (document.get("source_format") == "docx" and not found_body_heading)):
                reason = "title_page"
            elif args.get("skip_tables", True) and kind == "table_cell":
                reason = "tables"
            elif args.get("skip_code", True) and kind == "code":
                reason = "code"
            elif args.get("skip_appendix", True) and in_appendix:
                reason = "appendix"
            elif kind == "reference":
                reason = "references"
            if reason:
                skipped[reason] += 1
            else:
                kept.append(value)
        return "\n\n".join(kept).strip(), skipped

    def _mcp_checker_with_sources(reference_sources):
        if not reference_sources:
            return checker
        isolated = PlagiarismChecker(None, search_timeout=app.config.get("WEB_SEARCH_TIMEOUT", 4))
        isolated.sources = {key: dict(value) for key, value in checker.sources.items()}
        for index, source in enumerate(reference_sources[:20]):
            title, text = source.get("title", ""), source.get("text", "")
            validate_text(text)
            if not title.strip() or not text.strip():
                raise ValueError("Each reference source requires non-empty title and text")
            words = isolated.tokenize(text)
            key = f"cited_{index}"
            isolated.sources[key] = {"filename": title[:160], "filepath": None, "text": text, "words": words,
                "word_count": len(words), "sentences": isolated.split_into_sentences(text), "tf": isolated.compute_tf(words),
                "source_type": "user_cited_source", "badge": "User-provided cited source", "url": None}
        return isolated

    def _mcp_compact_result(analysis, scanned_text, args, extraction=None):
        minimum = args.get("minimum_match_words", 4)
        whitelist = {item.casefold() for item in args.get("whitelist_terms", []) if item.strip()}
        rows = []
        for row in analysis.get("highlighted_sentences", []):
            if not row.get("is_plagiarized"):
                continue
            words = re.findall(r"\b\w+\b", row.get("text", ""))
            if len(words) < minimum or (whitelist and all(word.casefold() in whitelist for word in words)):
                continue
            item = {key: row.get(key) for key in ("text", "source", "similarity", "url") if row.get(key) is not None}
            value = row.get("text", "")
            quoted = bool(row.get("is_quoted") or re.search(r"[\"“”]", value))
            cited = bool(row.get("has_citation") or re.search(r"\([^)]*\d{4}[^)]*\)", value))
            item["attribution_status"] = ("properly_attributed" if quoted and cited else
                "citation_present_review_wording" if cited else "quote_needs_citation" if quoted else "attribution_not_detected")
            rows.append(item)
        page, size = args.get("page", 1), args.get("page_size", 10)
        start = (page - 1) * size
        citations = analysis.get("citation_analysis") or {}
        style = analysis.get("style_review") or {}
        ai = analysis.get("ai_analysis") or {}
        mixed = _mcp_mixed_script_findings(scanned_text)
        cited_source_review = []
        if args.get("reference_sources"):
            engine = VectorSearchEngine()
            body_sentences = checker.split_into_sentences(scanned_text)[:50]
            body_vectors = [(sentence, engine.encode(sentence)) for sentence in body_sentences]
            for source in args["reference_sources"][:20]:
                source_sentences = checker.split_into_sentences(source.get("text", ""))[:100]
                source_vectors = [(sentence, engine.encode(sentence)) for sentence in source_sentences]
                best = None
                for body_sentence, body_vector in body_vectors:
                    for source_sentence, source_vector in source_vectors:
                        similarity = engine.cosine_distance(body_vector, source_vector)
                        if best is None or similarity > best["similarity"]:
                            best = {"similarity": similarity, "draft_passage": body_sentence[:500], "source_passage": source_sentence[:500]}
                cited_source_review.append({"title": source.get("title"), "closest_passage": best,
                    "method": "experimental hashed unigram/bigram cosine; review manually and do not treat as proof of paraphrase"})
        result = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "summary": {"engine_similarity_percent": analysis.get("overall_similarity", 0), "matched_words": analysis.get("matching_words_count", 0),
                "eligible_words": analysis.get("total_words", 0), "similarity_band": analysis.get("safeassign_risk"),
                "citations_detected": citations.get("in_text_citations_count", 0), "unlinked_citations": citations.get("unlinked_citations_count", 0)},
            "writing_patterns": {"profile": style.get("profile", args.get("genre", "academic_report")),
                "reliability": ai.get("reliability", "unknown"), "confidence": "limited" if ai.get("reliability") != "standard" else "review multiple categories",
                "categories": style.get("category_breakdown", []), "note": "Review category evidence; no authorship or AI probability is reported."},
            "matches": {"page": page, "page_size": size, "total": len(rows), "items": rows[start:start + size]},
            "homoglyph_review": {"mixed_script_words": mixed, "count": len(mixed), "note": "Standalone Greek/math symbols are not flagged."},
            "cited_source_review": cited_source_review,
            "transparency": {"scanned_sha256": hashlib.sha256(scanned_text.encode()).hexdigest(), "characters_scanned": len(scanned_text),
                "words_scanned": len(scanned_text.split()), "sources_searched": [row.get("filename") for row in analysis.get("sources_breakdown", [])],
                "scanned_text_start": scanned_text[:500], "scanned_text_end": scanned_text[-500:] if len(scanned_text) > 500 else "",
                "web_search_enabled": bool(args.get("include_web", False)),
                "external_data": "Search excerpts may leave the server when web search is enabled; document text remains local otherwise.",
                "matching": {"engine_minimum_match_words": 4, "reported_minimum_match_words": minimum, "whitelist_terms": sorted(whitelist),
                    "method": "exact lexical overlap plus an experimental cited-source passage comparison when source text is supplied"}},
        }
        if extraction:
            result["document"] = extraction
        if args.get("detail_level", "summary") in {"standard", "full"}:
            result["citation_review"] = citations
            result["evidence_review"] = analysis.get("evidence_analysis")
            result["writing_patterns"]["experimental_index"] = style.get("style_pattern_index")
        if args.get("detail_level") == "full":
            result["full_analysis"] = analysis
        if args.get("export_report"):
            result["report_markdown"] = f"# MCP Academic Review\n\nGenerated: {result['generated_at']}\n\nEngine similarity: {result['summary']['engine_similarity_percent']}%\n\nCitations: {result['summary']['citations_detected']} detected; {result['summary']['unlinked_citations']} unlinked.\n\nChecks: lexical overlap, citation linkage, mixed-script review, writing-pattern categories.\n"
        fields = args.get("fields")
        return {key: result[key] for key in fields if key in result} if fields else result

    def _mcp_run_tool(name: str, args: dict) -> dict:
        """Execute a named MCP tool synchronously and return its result dict."""
        tool = next((t for t in _MCP_TOOLS if t["name"] == name), None)
        if tool is None:
            raise ValueError(f"Unknown tool: {name}")
        if not isinstance(args, dict):
            raise ValueError("Arguments must be an object")
        for key in tool["inputSchema"].get("required", []):
            if not isinstance(args.get(key), str) or not args[key].strip():
                raise ValueError(f"'{key}' must be a non-empty string")
        for key, value in args.items():
            schema = tool["inputSchema"]["properties"].get(key)
            if schema is None:
                raise ValueError(f"Unknown argument: {key}")
            expected = schema["type"]
            if expected == "string" and not isinstance(value, str):
                raise ValueError(f"'{key}' must be a string")
            if expected == "boolean" and not isinstance(value, bool):
                raise ValueError(f"'{key}' must be a boolean")
            if expected == "integer" and (not isinstance(value, int) or isinstance(value, bool)):
                raise ValueError(f"'{key}' must be an integer")
            if expected == "array" and not isinstance(value, list):
                raise ValueError(f"'{key}' must be an array")
            if "enum" in schema and value not in schema["enum"]:
                raise ValueError(f"'{key}' has an unsupported value")
            if expected == "integer" and not schema.get("minimum", value) <= value <= schema.get("maximum", value):
                raise ValueError(f"'{key}' is outside the supported range")
            if expected == "array" and len(value) > (20 if key == "reference_sources" else 100):
                raise ValueError(f"'{key}' contains too many items")
        for key, value in args.items():
            if isinstance(value, str):
                if key == "content_base64":
                    if len(value) > 12 * 1024 * 1024:
                        raise ValueError("content_base64 exceeds the document upload limit")
                else:
                    validate_text(value)

        if name == "plag_scan_text":
            body_text = args["text"]
            references = args.get("references_text", "").strip()
            analysis_text = body_text + ("\n\nReferences\n" + references if references else "")
            scan_checker = _mcp_checker_with_sources(args.get("reference_sources"))
            analysis = scan_checker.analyze(
                analysis_text,
                include_web_sources=args.get("include_web", False),
                exclude_quotes=args.get("exclude_quotes", False),
                exclude_bibliography=bool(references) or args.get("exclude_bibliography", False),
                private_draft=True,
                style_profile=args.get("genre", "academic_report"),
            )
            # Attach student coach (mirrors /check route)
            claim_analysis    = analysis.get("claim_analysis") or AcademicStudentCoach.scan_claims(args["text"])
            unsupported_claims = [c for c in claim_analysis if not c.get("has_citation")]
            tone_suggestions = AcademicStudentCoach.analyze_tone_and_vocabulary(args["text"])
            analysis["student_coach"] = {
                "unsupported_claims":       unsupported_claims,
                "unsupported_claims_count": len(unsupported_claims),
                "claims":                   claim_analysis,
                "claims_count":             len(claim_analysis),
                "cited_claims_count":       sum(1 for c in claim_analysis if c.get("has_citation")),
                "tone_suggestions":         tone_suggestions,
                "tone_suggestions_count":   len(tone_suggestions),
                "thesis_evaluation":        AcademicStudentCoach.evaluate_thesis_abstract(args["text"]),
            }
            return _mcp_compact_result(analysis, body_text, args)

        if name == "plag_scan_document":
            filename = args["filename"]
            if Path(filename).suffix.lower() not in {".docx", ".pdf"}:
                raise ValueError("MCP document scans accept .docx or .pdf files")
            try:
                raw = base64.b64decode(args["content_base64"], validate=True)
            except (ValueError, TypeError) as exc:
                raise ValueError("content_base64 must be valid base64") from exc
            document = extract_document(io.BytesIO(raw), filename)
            body_text, skipped = _mcp_document_text(document, args)
            if not body_text:
                raise ValueError("No scannable body text remained after section exclusions")
            references = args.get("references_text", "").strip()
            analysis_text = body_text + ("\n\nReferences\n" + references if references else "")
            scan_checker = _mcp_checker_with_sources(args.get("reference_sources"))
            analysis = scan_checker.analyze(analysis_text, include_web_sources=args.get("include_web", False),
                exclude_bibliography=bool(references), private_draft=True,
                style_profile=args.get("genre", "technical_documentation"))
            extraction = {"filename": filename, "format": document.get("source_format"),
                "blocks_extracted": len(document.get("blocks", [])), "blocks_skipped": skipped,
                "warnings": document.get("warnings", []), "scanned_text_preview": body_text[:500]}
            return _mcp_compact_result(analysis, body_text, args, extraction)

        if name == "plag_attribution_coach":
            source = args.get("source_title") or "the source"
            return {"passage": args["sentence"], "source": source,
                    "guidance": ["Use quotation marks and a citation if retaining distinctive wording.",
                                 "Cite the source when summarizing its finding.",
                                 "Restate the idea through your own analysis and explain why it supports your argument."],
                    "note": "This tool does not generate detector-avoidance rewrites."}

        if name == "plag_academic_coach":
            claims = AcademicStudentCoach.scan_unsupported_claims(args["text"])
            tone   = AcademicStudentCoach.analyze_tone_and_vocabulary(args["text"])
            thesis = AcademicStudentCoach.evaluate_thesis_abstract(args["text"])
            return {
                "unsupported_claims":       claims,
                "unsupported_claims_count": len(claims),
                "tone_suggestions":         tone,
                "tone_suggestions_count":   len(tone),
                "thesis_evaluation":        thesis,
            }

        if name == "plag_generate_citation":
            return CitationGenerator.generate_from_identifier(args["query"])

        if name == "plag_alphabetize_references":
            return AcademicStudentCoach.alphabetize_and_format_references(args["references_text"])

        if name == "plag_compare_drafts":
            return DraftComparator.compare_drafts(args["draft_v1"], args["draft_v2"])

        raise ValueError(f"No handler for tool: {name}")

    def _mcp_route_rpc(payload):
        """Route a single JSON-RPC 2.0 request and return the response dict."""
        if (not isinstance(payload, dict) or payload.get("jsonrpc") != "2.0"
                or not isinstance(payload.get("method"), str)):
            return {"jsonrpc": "2.0", "id": None,
                    "error": {"code": -32600, "message": "Invalid Request"}}

        # JSON-RPC notifications never receive a response.
        if "id" not in payload:
            return None

        rpc_id = payload.get("id")
        method = payload.get("method", "")
        params = payload.get("params") or {}
        if not isinstance(params, dict):
            return {"jsonrpc": "2.0", "id": rpc_id,
                    "error": {"code": -32602, "message": "Invalid params"}}

        if method == "initialize":
            requested_version = params.get("protocolVersion")
            protocol_version = (requested_version if requested_version in _MCP_PROTOCOL_VERSIONS
                                else _MCP_DEFAULT_PROTOCOL_VERSION)
            return {"jsonrpc": "2.0", "id": rpc_id, "result": {
                "protocolVersion": protocol_version,
                "serverInfo":      {"name": "plagiarism-detector-pro-mcp", "version": APP_VERSION},
                "capabilities":    {"tools": {}},
            }}

        if method == "ping":
            return {"jsonrpc": "2.0", "id": rpc_id, "result": {}}

        if method == "tools/list":
            return {"jsonrpc": "2.0", "id": rpc_id, "result": {"tools": _MCP_TOOLS}}

        if method == "tools/call":
            tool_name = params.get("name", "")
            tool_args = params.get("arguments") or {}
            try:
                result = _mcp_run_tool(tool_name, tool_args)
                return {"jsonrpc": "2.0", "id": rpc_id, "result": {
                    "content": [{"type": "text", "text": json.dumps(result)}]
                }}
            except ValueError as exc:
                return {"jsonrpc": "2.0", "id": rpc_id, "result": {
                    "isError": True,
                    "content": [{"type": "text", "text": f"Invalid tool arguments: {public_message(exc, 'Check the tool name and arguments.')}"}],
                }}
            except Exception:  # noqa: BLE001
                logger.exception("MCP tool call failed: %s", tool_name)
                return {"jsonrpc": "2.0", "id": rpc_id, "result": {
                    "isError": True,
                    "content": [{"type": "text", "text": "The tool call could not be processed."}],
                }}

        return {"jsonrpc": "2.0", "id": rpc_id,
                "error": {"code": -32601, "message": "Method not found"}}

    @app.route("/mcp", methods=["GET", "POST", "OPTIONS"])
    @app.route("/mcp/", methods=["GET", "POST", "OPTIONS"])
    @app.route("/mcp/health", methods=["GET", "OPTIONS"])
    def mcp_endpoint():
        """
        Stateless MCP Streamable HTTP endpoint (spec 2025-03-26).
        GET  /mcp  → 405 (stateless servers do not open an SSE stream)
        GET  /mcp/health → public server info
        POST /mcp  → JSON-RPC 2.0 (single or batch), requires Bearer token auth
        """
        # CORS preflight
        if request.method == "OPTIONS":
            resp = make_response("", 204)
            resp.headers["Access-Control-Allow-Origin"]  = "*"
            resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
            req_headers = request.headers.get("Access-Control-Request-Headers", "Content-Type, Authorization, X-Api-Key, Mcp-Session-Id, mcp-protocol-version, *")
            resp.headers["Access-Control-Allow-Headers"] = req_headers
            resp.headers["Access-Control-Expose-Headers"] = "*"
            resp.headers["Access-Control-Max-Age"]       = "86400"
            return resp

        def _mcp_json(data, status=200):
            resp = jsonify(data)
            resp.status_code = status
            resp.headers["Access-Control-Allow-Origin"] = "*"
            resp.headers["Access-Control-Expose-Headers"] = "*"
            return resp

        def _mcp_accepted():
            resp = make_response("", 202)
            resp.headers["Access-Control-Allow-Origin"] = "*"
            resp.headers["Access-Control-Expose-Headers"] = "*"
            return resp

        # Keep ordinary health JSON off the transport URL. Streamable HTTP
        # clients interpret GET /mcp as a request for a standalone SSE stream.
        if request.method == "GET":
            if request.path.rstrip("/") == "/mcp":
                resp = _mcp_json({"error": "Method not allowed",
                                  "hint": "Use POST for MCP requests or GET /mcp/health for status."}, 405)
                resp.headers["Allow"] = "POST, OPTIONS"
                return resp
            base_url = request.base_url
            if base_url.startswith("http://"):
                base_url = "https://" + base_url[7:]
            return _mcp_json({
                "status":    "ok",
                "server":    "plagiarism-detector-pro-mcp",
                "version":   APP_VERSION,
                "url":       base_url.removesuffix("/health"),
                "tools":     len(_MCP_TOOLS),
                "transport": "streamable-http",
                "spec":      _MCP_DEFAULT_PROTOCOL_VERSION,
                "supported_protocol_versions": list(_MCP_PROTOCOL_VERSIONS),
            })

        # POST /mcp — authenticate when MCP_API_KEY is set
        mcp_key = str(app.config.get("MCP_API_KEY") or "").strip("'\" \t\r\n")
        if mcp_key:
            auth_header = (request.headers.get("Authorization") or "").strip()
            api_key_hdr = (request.headers.get("X-Api-Key") or "").strip()
            query_key   = (request.args.get("key") or request.args.get("api_key") or request.args.get("token") or request.args.get("apiKey") or "").strip()

            provided = ""
            if auth_header:
                if auth_header.lower().startswith("bearer "):
                    provided = auth_header[7:].strip()
                else:
                    provided = auth_header
            elif api_key_hdr:
                provided = api_key_hdr
            elif query_key:
                provided = query_key

            if not provided or not hmac.compare_digest(provided.encode("utf-8"), mcp_key.encode("utf-8")):
                # This server uses a fixed request header, not OAuth. Returning
                # WWW-Authenticate: Bearer makes Claude attempt OAuth client
                # registration against an authorization service that does not exist.
                return _mcp_json({"error": "Forbidden",
                                  "hint": "Pass the configured key in the X-Api-Key request header."}, 403)

        body = request.get_json(force=True, silent=True)
        if body is None:
            return _mcp_json({"jsonrpc": "2.0", "id": None,
                               "error": {"code": -32700, "message": "Parse error"}}, 400)

        # Batch or single JSON-RPC request
        if isinstance(body, list):
            if not body:
                return _mcp_json({"jsonrpc": "2.0", "id": None,
                                  "error": {"code": -32600, "message": "Invalid Request"}}, 400)
            responses = [response for item in body if (response := _mcp_route_rpc(item)) is not None]
            return _mcp_json(responses) if responses else _mcp_accepted()

        response = _mcp_route_rpc(body)
        return _mcp_json(response) if response is not None else _mcp_accepted()

    # ── End MCP block ─────────────────────────────────────────────────────────

    return app


def register_error_handlers(app: Flask):
    """Registers standard HTTP error handlers."""
    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify({"error": error.description}), error.code

    @app.errorhandler(413)
    def request_entity_too_large(error):
        return jsonify({"error": f"Request exceeds the configured {app.config['MAX_CONTENT_LENGTH']} byte limit."}), 413

    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith("/sources") or request.path.startswith("/check") or request.path.startswith("/reports") or request.path.startswith("/mcp"):
            return jsonify({"error": "Resource not found."}), 404
        return render_template("index.html", error="Page not found."), 404

    @app.errorhandler(500)
    def internal_server_error(error):
        logger.error("Internal Server Error: %s", error)
        if request.is_json or request.path.startswith("/check") or request.path.startswith("/sources"):
            return jsonify({"error": "Internal server error occurred."}), 500
        return render_template("index.html", error="An internal error occurred."), 500


# Application instance for development execution
app = create_app()

if __name__ == "__main__":
    port = app.config["PORT"]
    host = app.config["HOST"]
    logger.info("Starting Plagiarism Detector Pro at http://%s:%d", host, port)
    app.run(debug=app.config["DEBUG"], host=host, port=port)
