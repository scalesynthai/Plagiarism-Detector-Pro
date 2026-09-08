# Changelog

All notable changes to **Plagiarism Detector Pro** are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
