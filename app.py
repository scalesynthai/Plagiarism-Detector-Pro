import logging
import os
import io
from typing import Optional
from flask import Flask, request, render_template, jsonify, send_file, make_response, url_for as flask_url_for
from werkzeug.utils import secure_filename
from werkzeug.exceptions import HTTPException

from config import Config, DevelopmentConfig
from core.checker import PlagiarismChecker
from core.extractor import extract_text_from_file, is_allowed_file
from core.batch_processor import BatchProcessor
from core.report_generator import ReportGenerator
from core.paraphraser import AcademicParaphraser
from core.citation_generator import CitationGenerator
from core.diff_comparator import DraftComparator
from core.student_coach import AcademicStudentCoach

# Configure standard logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] in %(module)s: %(message)s"
)
logger = logging.getLogger(__name__)


def create_app(config_class: type = DevelopmentConfig) -> Flask:
    """Application factory for Plagiarism Detector Pro."""
    app = Flask(__name__)
    app.config.from_object(config_class)

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
        return dict(url_for=dated_url_for)

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

    app.checker = checker
    app.batch_processor = batch_processor
    app.report_generator = report_generator

    # Register error handlers
    register_error_handlers(app)

    # Routes
    @app.route("/", methods=["GET"])
    def index():
        """Renders the main plagiarism detector dashboard."""
        sources = checker.list_sources()
        return render_template("index.html", sources_count=len(sources), sources=sources)

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
                    return render_template("index.html", error=f"File error: {e}", sources_count=len(checker.sources))
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

        if "file" in request.files and request.files["file"].filename:
            file_obj = request.files["file"]
            if not is_allowed_file(file_obj.filename):
                return jsonify({
                    "error": "Unsupported file format. Please upload .docx, .pdf, .txt, or .md."
                }), 400
            try:
                query_text = extract_text_from_file(file_obj)
            except Exception as e:
                logger.error("Failed to extract file text: %s", e)
                return jsonify({"error": f"Failed to extract document text: {str(e)}"}), 400
            include_web = request.form.get("include_web", "true").lower() in ("true", "1", "yes")
            exclude_quotes = request.form.get("exclude_quotes", "false").lower() in ("true", "1", "yes")
            private_draft = request.form.get("private_draft", "true").lower() in ("true", "1", "yes")
        elif request.is_json:
            data = request.get_json() or {}
            query_text = data.get("query", "")
            include_web = bool(data.get("include_web", True))
            exclude_quotes = bool(data.get("exclude_quotes", False))
            private_draft = bool(data.get("private_draft", True))
        else:
            query_text = request.form.get("query", "")
            include_web = request.form.get("include_web", "true").lower() in ("true", "1", "yes")
            exclude_quotes = request.form.get("exclude_quotes", "false").lower() in ("true", "1", "yes")
            private_draft = request.form.get("private_draft", "true").lower() in ("true", "1", "yes")

        if not query_text or not query_text.strip():
            return jsonify({"error": "No text or document provided for analysis."}), 400

        try:
            logger.info("Executing plagiarism & AI scan (Words: %d, Include Web: %s, Exclude Quotes: %s, Private Draft: %s)",
                        len(query_text.split()), include_web, exclude_quotes, private_draft)
            analysis = checker.analyze(
                query_text,
                include_web_sources=include_web,
                exclude_quotes=exclude_quotes,
                private_draft=private_draft
            )

            # Add Student Writing & Academic Integrity Coach Insights
            unsupported_claims = AcademicStudentCoach.scan_unsupported_claims(query_text)
            tone_suggestions = AcademicStudentCoach.analyze_tone_and_vocabulary(query_text)
            thesis_eval = AcademicStudentCoach.evaluate_thesis_abstract(query_text)
            analysis["student_coach"] = {
                "unsupported_claims": unsupported_claims,
                "unsupported_claims_count": len(unsupported_claims),
                "tone_suggestions": tone_suggestions,
                "tone_suggestions_count": len(tone_suggestions),
                "thesis_evaluation": thesis_eval
            }

            return jsonify(analysis), 200
        except Exception as e:
            logger.exception("Internal analysis error: %s", e)
            return jsonify({"error": f"Internal scan error: {str(e)}"}), 500

    @app.route("/check/batch", methods=["POST"])
    def check_batch_submissions():
        """
        Processes bulk submissions via ZIP file archive or multiple uploaded files.
        """
        include_web = request.form.get("include_web", "true").lower() in ("true", "1", "yes")
        exclude_quotes = request.form.get("exclude_quotes", "false").lower() in ("true", "1", "yes")

        uploaded_files = request.files.getlist("files") or request.files.getlist("file")
        if not uploaded_files or not uploaded_files[0].filename:
            return jsonify({"error": "No files or ZIP archive provided."}), 400

        first_file = uploaded_files[0]
        if first_file.filename.lower().endswith('.zip'):
            try:
                batch_result = batch_processor.process_zip_archive(
                    first_file.stream, include_web=include_web, exclude_quotes=exclude_quotes
                )
                return jsonify(batch_result), 200
            except Exception as e:
                logger.exception("Failed to process ZIP archive: %s", e)
                return jsonify({"error": f"Failed to process ZIP archive: {str(e)}"}), 500

        # Multiple individual files
        file_tuples = []
        for f in uploaded_files:
            if f.filename and is_allowed_file(f.filename):
                file_tuples.append((secure_filename(f.filename), io.BytesIO(f.read())))

        if not file_tuples:
            return jsonify({"error": "No supported document files found in upload."}), 400

        try:
            batch_result = batch_processor.process_multiple_files(
                file_tuples, include_web=include_web, exclude_quotes=exclude_quotes
            )
            return jsonify(batch_result), 200
        except Exception as e:
            logger.exception("Batch processing error: %s", e)
            return jsonify({"error": f"Batch processing failed: {str(e)}"}), 500

    @app.route("/reports/html", methods=["POST"])
    def generate_report():
        """Generates a printable HTML/PDF-ready academic report."""
        data = request.get_json() or {}
        html_content = report_generator.generate_html_report(data)
        response = make_response(html_content)
        response.headers["Content-Type"] = "text/html"
        return response

    @app.route("/reports/certificate", methods=["POST"])
    def generate_certificate():
        """Generates a formal Student Certificate of Academic Originality & Authorship."""
        payload = request.get_json() or {}
        data = payload.get("data", payload)
        student_name = payload.get("student_name", "Student / Author")
        paper_title = payload.get("paper_title", "Academic Manuscript")
        html_content = report_generator.generate_student_certificate(
            data, student_name=student_name, paper_title=paper_title
        )
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
                "version": "2.1.0",
                "description": "Enterprise & University-Grade Academic Originality, SafeAssign Plagiarism, and AI Content Forensics REST API."
            },
            "servers": [
                {"url": "https://plag.subba.dev", "description": "Production Server"},
                {"url": "http://127.0.0.1:5001", "description": "Local Development"}
            ],
            "paths": {
                "/check": {
                    "post": {
                        "summary": "Scan text or uploaded document for plagiarism & AI",
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
                        "summary": "Generate Student Certificate of Academic Originality",
                        "responses": {"200": {"description": "Certificate HTML."}}
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
    <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css" />
    <style>body { margin: 0; background: #0f172a; } .swagger-ui { filter: invert(88%) hue-rotate(180deg); }</style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
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
</html>"""

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
        except Exception as e:
            logger.exception("Failed to add reference source: %s", e)
            return jsonify({"error": f"Failed to save source: {str(e)}"}), 500

    @app.route("/sources/<filename>", methods=["DELETE"])
    def delete_source(filename: str):
        """Deletes a reference document from the corpus with Admin PIN verification."""
        provided_pin = request.headers.get("X-Admin-PIN") or request.args.get("pin")
        expected_pin = app.config.get("ADMIN_PIN", "1234")

        if not provided_pin or str(provided_pin).strip() != str(expected_pin).strip():
            logger.warning("Unauthorized deletion attempt for '%s' (Invalid Admin PIN)", filename)
            return jsonify({
                "error": "Unauthorized: Invalid or missing Admin PIN. Deletion forbidden."
            }), 403

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

    return app


def register_error_handlers(app: Flask):
    """Registers standard HTTP error handlers."""
    @app.errorhandler(413)
    def request_entity_too_large(error):
        return jsonify({"error": "File size exceeds the 32MB limit."}), 413

    @app.errorhandler(404)
    def not_found(error):
        if request.path.startswith("/sources") or request.path.startswith("/check") or request.path.startswith("/reports"):
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
