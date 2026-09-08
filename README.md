<div align="center">

# ⚡ Plagiarism Detector Pro

**An Enterprise & University-Grade Academic Originality, SafeAssign Plagiarism, and AI-Content Detection Platform.**

[![CI](https://github.com/ScaleSynthAI/Plagiarism-Detector-Pro/actions/workflows/ci.yml/badge.svg)](https://github.com/ScaleSynthAI/Plagiarism-Detector-Pro/actions/workflows/ci.yml)
[![Live Demo](https://img.shields.io/badge/Live%20Demo-plag.subba.dev-blueviolet?style=for-the-badge&logo=google-chrome&logoColor=white)](https://plag.subba.dev)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.1%2B-black?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
[![Security Policy](https://img.shields.io/badge/Security-Policy-red?style=for-the-badge&logo=github)](SECURITY.md)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=for-the-badge)](CONTRIBUTING.md)

[🚀 Live Platform](https://plag.subba.dev) • [Features](#-key-features) • [Architecture](#-project-architecture) • [Getting Started](#-getting-started) • [API Documentation](#-rest-api-reference) • [Contributing](#-contributing) • [Security](#-security-policy)

---

</div>

## 🌟 Overview

**Plagiarism Detector Pro** is an open-source academic originality platform engineered to match and exceed the detection standards of **Blackboard SafeAssign** and **Turnitin**.

It evaluates student manuscripts, scientific papers, and professional essays across dual analytical dimensions:
1. **SafeAssign Plagiarism Index (%)**: Evaluated against live web sources, Wikipedia, arXiv, 250M+ OpenAlex/CrossRef scholarly publications, and local institutional repositories.
2. **AI-Generated Content Likelihood (%)**: Evaluates statistical perplexity, burstiness, syntax variance, and lexical entropy to detect machine-generated and LLM-assisted text.

---

## 🚀 Key Features

### 1. 🛡️ Student "Private Draft Shield" & Honor Protection
- **No Self-Plagiarism Guarantee**: Scans student drafts against 250M+ publications and university databases **without storing or caching the student's manuscript** in institutional repositories, ensuring zero false-positive matches when submitting to Canvas or Turnitin.

### 2. 📜 Verifiable Student Certificate of Academic Authorship
- Generates a certificate of authenticity with SHA-256 integrity hash, SafeAssign index, AI likelihood forensics, verified citation count, and honor pledge signature block.

### 3. 💡 Smart Citation Generator & Paraphrase Coach
- 1-click **APA 7th**, **MLA 9th**, and **IEEE** citation generation with instant clipboard copy.
- Actionable sentence-level synthesis and attribution guidance to help students ethically rewrite and quote referenced material.

### 4. 🤖 AI-Generated Content & LLM Detection Layer
- Evaluates **Burstiness** (sentence length and syntactic variance) and **Lexical Entropy**.
- Identifies machine-generated text patterns with classification:
  - 🟢 **Human-Written Content** ($< 25\%$)
  - 🟡 **Mixed / AI-Assisted Content** ($25\% - 65\%$)
  - 🔴 **Likely AI-Generated Content** ($> 65\%$)

### 5. 🛡️ Adversarial Obfuscation & Homoglyph Defense
- Detects invisible zero-width characters (`\u200B`, `\uFEFF`) and Cyrillic/Greek homoglyphs inserted to evade detection algorithms, while calculating Flesch Reading Ease & Grade Level.

### 6. ↔️ Interactive Side-by-Side Split Diff Comparison
- Clicking any flagged sentence opens a split-screen modal displaying the student's submission on the left and the verbatim matched publication on the right with synchronized highlight alignment.

### 7. 📄 Exportable Academic PDF Originality Reports
- Formal, printable academic reports complete with SafeAssign score gauges, AI probability indexes, color-annotated manuscripts, and source appendix citations.

### 8. 📦 Bulk & Batch Submissions Processor (.ZIP / Multi-File)
- Ingests class ZIP archives or multiple documents simultaneously with an aggregated **Class Gradebook Table**.

---

## 📁 Project Architecture

```
Plagiarism-Detector/
├── app.py                      # Application factory, routes, and error handlers
├── config.py                   # Centralized configuration (Dev, Test, Prod)
├── wsgi.py                     # Production WSGI entrypoint (Gunicorn / uWSGI)
├── plag.py                     # Backward-compatible entrypoint shim
├── requirements.txt            # Production dependencies
├── Dockerfile                  # Containerized deployment spec
├── docker-compose.yml          # Multi-container orchestration
├── Makefile                    # Developer automation commands
│
├── core/                       # Core analytical & detection engines
│   ├── checker.py              # Master SafeAssign originality engine
│   ├── ai_detector.py          # Statistical AI & LLM likelihood analyzer
│   ├── phd_auditor.py          # PhD conference pre-flight & double-blind anonymity auditor
│   ├── sanitizer.py            # Homoglyph, zero-width evasion defense & readability
│   ├── citation_validator.py   # APA/MLA/IEEE in-text citation & bib validator
│   ├── vector_engine.py        # Dense semantic vector indexing
│   ├── batch_processor.py      # Multi-file & ZIP batch processor
│   ├── report_generator.py     # Printable academic PDF/HTML & certificate generator
│   ├── extractor.py            # Text parser for .tex, .bib, .ipynb, .docx, .pdf, .txt
│   └── web_searcher.py         # Real-time Wikipedia, arXiv, CrossRef, OpenAlex & Semantic Scholar search
│
├── sources/                    # Institutional reference repository
├── static/                     # Frontend styles and interactive UI scripts
├── templates/                  # Jinja2 dashboard templates
└── tests/                      # Automated unit and integration test suite
```

---

## 💻 Getting Started

### Prerequisites
- **Python 3.10+**
- **Git**
- Optional: **Docker** & **Docker Compose**

### 1. Installation

```bash
git clone https://github.com/ScaleSynthAI/Plagiarism-Detector-Pro.git
cd Plagiarism-Detector-Pro

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Running Locally

```bash
python app.py
# Or with Makefile
make dev
```
> Open **`http://127.0.0.1:5001`** in your browser.

### 3. Running with Production WSGI (Gunicorn)

```bash
gunicorn wsgi:app -b 0.0.0.0:5001 --workers 4 --timeout 60
# Or with Makefile
make start
```

### 4. Running with Docker Compose

```bash
docker compose up --build -d
```

---

## 🧪 Automated Testing

We maintain rigorous test coverage across all core modules:

```bash
# Run unit tests
python -m unittest discover tests -v

# Or using Makefile
make test
```

---

## 📡 REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/` | Main academic dashboard |
| `POST` | `/check` | Scan text (`query`) or document (`file`) with Private Draft Shield |
| `POST` | `/check/batch` | Scan `.zip` archive or multiple files (Class Gradebook) |
| `POST` | `/reports/html` | Generate printable academic PDF report |
| `POST` | `/reports/certificate` | Generate verifiable Student Certificate of Academic Authorship |
| `GET` | `/docs` | Interactive Swagger UI API playground |
| `GET` | `/api/spec.json` | OpenAPI 3.0 specification JSON |
| `GET` | `/sources` | List all institutional repository documents |
| `POST` | `/sources/upload` | Add new document to institutional repository |
| `DELETE` | `/sources/<filename>` | Delete document from institutional repository |

---

## 🤝 Contributing

Contributions make the open-source community an incredible place to learn, inspire, and create. Any contributions you make are **greatly appreciated**!

Please see our [**Contributing Guide**](CONTRIBUTING.md) for detailed instructions on:
- Setting up your local development environment
- Submitting Bug Reports and Feature Requests
- Coding standards and test requirements
- Conventional Commits and Pull Request workflows

All contributors are expected to adhere to our [**Code of Conduct**](CODE_OF_CONDUCT.md).

### Quick Contribution Steps:
1. Fork the Project (`https://github.com/ScaleSynthAI/Plagiarism-Detector-Pro/fork`)
2. Create your Feature Branch (`git checkout -b feat/amazing-feature`)
3. Commit your Changes (`git commit -m 'feat: add amazing feature'`)
4. Ensure all tests pass (`make test`)
5. Push to the Branch (`git push origin feat/amazing-feature`)
6. Open a Pull Request on GitHub

---

## 🛡️ Security Policy

We take the security of Plagiarism Detector Pro seriously. If you discover a vulnerability, please report it privately via **`security@subba.dev`** or consult our [**Security Policy**](SECURITY.md) for supported versions and our coordinated disclosure timeline.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🌐 Acknowledgements & Links

- **Live Deployment**: [plag.subba.dev](https://plag.subba.dev)
- **GitHub Repository**: [ScaleSynthAI/Plagiarism-Detector-Pro](https://github.com/ScaleSynthAI/Plagiarism-Detector-Pro)
- **Issues & Support**: [GitHub Issues](https://github.com/ScaleSynthAI/Plagiarism-Detector-Pro/issues)
- **Security Inquiries**: [security@subba.dev](mailto:security@subba.dev)

