# Changelog

All notable changes to **Plagiarism Detector Pro** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [v1.1.0] - 2026-09-29

### Explainable writing-pattern scoring

- Replaced the single AI-probability estimate with a nine-signal `pattern_score` (0-100), adapted from the MIT-licensed `avoid-ai-writing` and `humanize` projects. Every non-zero category quotes the exact phrases or sentence spans behind it and includes a focused revision suggestion. See [docs/AI_SCORING.md](docs/AI_SCORING.md) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
- Em dashes are now reported as an exact count and a rate per 300 words, with each instance located in the text. An em dash alone can no longer produce a high score or imply authorship, addressing the common false signal that punctuation choice alone proves AI use.
- Added a separate evidence-integrity score, adapted from the MIT-licensed `hyperresearch` project. It pairs recognized empirical claims with same-sentence citations, links in-text citations to bibliography entries, and factors in source-type quality, renormalizing when a component is unavailable rather than scoring it as zero.
- `ai_probability` and `human_probability` remain in the Python API and npm CLI/MCP output as compatibility aliases for `pattern_score`; they are documented as uncalibrated heuristic mirrors, not calibrated probabilities.
- The web dashboard, PDF/HTML reports, advisory certificates, and batch gradebook all display the new score consistently. Python and Node implementations are verified to score identically on the same input.
- Added `provenance_flags`: a separate, high-precision check for literal AI-tool copy-paste artifacts (unfilled template placeholders, leftover chatbot citation markup, AI-tool URL tracking parameters), adapted from `avoid-ai-writing`'s documented "AI-tool fingerprint" category. Never folded into `pattern_score`. Surfaced in the CLI, web app, and HTML report.
- Checked the Elevated/High `pattern_score` thresholds against a small, guaranteed-human corpus (21 documents, all predating LLMs entirely) and confirmed zero false positives; thresholds were not changed. See [benchmarks/threshold_calibration.md](benchmarks/threshold_calibration.md).

---

## [v1.0.5] - 2026-09-25

### Local document formats

- The Node CLI, library, and MCP server now read `.docx` and text-based `.pdf` files directly, with no new dependencies.
- PDF extraction handles compressed streams, object streams, CID fonts with ToUnicode maps, and kerned text. Scanned/image-only and encrypted PDFs are rejected with a clear error rather than scanned as empty text.

---

## [v1.0.4] - 2026-09-23

### Matching accuracy and diagnostic reliability

- Replaced sentence-level similarity estimates with deterministic exact-word-span coverage in both Python and Node.
- Prevented duplicated and overlapping sources from inflating the overall matched-word count.
- Added independent quotation and bibliography exclusions while keeping citations in the similarity calculation.
- Added raw, body, bibliography, quotation, and selected-score disclosures with exact matched offsets.
- Improved APA/IEEE citation recognition, thesis-section selection, front-matter anonymity screening, and distributed web-query sampling.
- Reframed AI-related output as an uncalibrated writing-pattern heuristic rather than an authorship determination.
- Added a fixed 25-case accuracy benchmark, Python/Node parity checks, challenge cases, and CI enforcement.
- Hardened generated reports, external source links, advisory summaries, and CLI/MCP descriptions against misleading claims.

The benchmark is a regression fixture set rather than evidence of real-world accuracy or equivalence to proprietary services. See `benchmarks/README.md` in the repository for results and limitations.

---

## [v1.0.0] - 2026-09-08

### 🌟 Initial Major Release — Enterprise Academic Originality & SafeAssign Suite

This release transforms the legacy single-file script into an enterprise-grade, full-featured academic originality, SafeAssign plagiarism, and AI-content detection platform.

---

### 🚀 What's New & Why It's Better

#### 1. Dual-Engine Originality Assessment (Plagiarism + AI Detection)
- **Traditional Checkers**: Only check for direct string matches against static text files.
- **Plagiarism Detector Pro**:
  - **SafeAssign Plagiarism Index (%)**: Evaluates sentence containment, matched word volume, and document vector similarity.
  - **Statistical AI & LLM Likelihood (%)**: Computes sentence length **Burstiness**, **Lexical Entropy**, and transitional smoothness to detect ChatGPT, Claude, and Gemini generated prose.

#### 2. Real-Time Global Internet & Scholarly Repository Crawler
- **Traditional Checkers**: Only compare against a single local `.txt` file.
- **Plagiarism Detector Pro**: Queries live internet sources on-the-fly:
  - 🌐 **Live Wikipedia**: Real-time article extracts and citations.
  - 🎓 **arXiv Open Access**: Preprints, academic papers, and abstracts.
  - 📚 **OpenAlex & CrossRef**: 250M+ scientific journal papers and publications.
  - 🏛️ **Institutional Corpus**: Dynamic local repository with instant UI/API upload and deletion.

#### 3. University SafeAssign & Turnitin Multi-Layer Scoring
- Implements **Longest Common Subsequence (LCS)**, **Sliding 3-Gram & 5-Gram Shingling**, and **Stopword-Weighted TF-IDF Cosine Similarity**.
- Categorizes submissions into standard academic risk tiers:
  - 🟢 **Low Risk (< 15%)**
  - 🟡 **Medium Risk (15% - 40%)**
  - 🔴 **High Risk (> 40%)**

#### 4. Interactive Side-by-Side Split Diff Comparison
- Clicking any flagged red sentence opens a synchronized dual-viewer displaying the student submission on the left and the verbatim original reference text on the right.

#### 5. Citation & Bibliography Integrity Validator
- Automatically parses in-text citations (**APA**, **MLA**, **IEEE**, **Chicago**) and cross-references them with the **References / Bibliography** section.
- Legitimate cited quotes can be excluded from the uncredited plagiarism index.

#### 6. Multi-Format Document Ingestion & Batch ZIP Processing
- Parses `.docx` (Microsoft Word), `.pdf` (Adobe PDF), `.txt` (Plain Text), and `.md` (Markdown).
- **Batch Processing**: Ingests whole-class `.zip` archives or multiple files, producing an interactive **Instructor Gradebook Table**.

#### 7. Exportable Academic PDF Reports
- One-click export of formal, printable academic originality reports.

#### 8. Cloud & Container Deployment (Komodo Ready)
- Production-ready `Dockerfile`, `docker-compose.yml`, multi-worker Gunicorn WSGI server, healthcheck endpoints, and GitHub Actions CI workflow for Python 3.10 through 3.13.

---

### 📁 Technical Architecture
- **Application Factory Pattern**: `create_app()` in `app.py` with modular configuration in `config.py`.
- **Decoupled Service Layer**:
  - `core/checker.py`: Similarity calculations & SafeAssign rubric
  - `core/ai_detector.py`: Statistical AI & LLM likelihood engine
  - `core/citation_validator.py`: APA/MLA/IEEE in-text citation validator
  - `core/vector_engine.py`: Dense semantic vector indexing
  - `core/batch_processor.py`: Multi-file & ZIP archive processor
  - `core/report_generator.py`: Academic PDF & printable HTML builder
  - `core/extractor.py`: Multi-format text extractor
  - `core/web_searcher.py`: Real-time academic & web searcher
- **Automated Tests**: Complete test suite in `tests/test_app.py` with 10 passing unit & integration tests.
