<div align="center">

# ⚡ Plagiarism Detector Pro

**The Open-Source Enterprise Academic Originality, SafeAssign Plagiarism, AI-Content Detector & Student Writing Coach.**

*Available as an Interactive Web Dashboard, 100% Offline CLI, NPM Package, and Native Claude/Codex MCP Server.*

[![CI](https://github.com/ScaleSynthAI/Plagiarism-Detector-Pro/actions/workflows/ci.yml/badge.svg)](https://github.com/ScaleSynthAI/Plagiarism-Detector-Pro/actions/workflows/ci.yml)
[![npm version](https://img.shields.io/npm/v/plagiarism-detector-pro.svg?style=for-the-badge&logo=npm&color=CB3837)](https://www.npmjs.com/package/plagiarism-detector-pro)
[![Live Demo](https://img.shields.io/badge/Live%20Demo-plag.subba.dev-blueviolet?style=for-the-badge&logo=google-chrome&logoColor=white)](https://plag.subba.dev)
[![Node.js](https://img.shields.io/badge/Node.js-18%2B-green?style=for-the-badge&logo=node.js&logoColor=white)](https://nodejs.org/)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)](Dockerfile)
[![MCP Compatible](https://img.shields.io/badge/MCP-Compatible-orange?style=for-the-badge&logo=anthropic)](skills/plagiarism-detector/SKILL.md)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)

[🚀 Live Demo](https://plag.subba.dev) • [📦 NPM & Standalone CLI](#-npm-package--standalone-cli-100-offline) • [🤖 Claude & Codex MCP Setup](#-claude-desktop-claude-code--codex-mcp-integration) • [🌐 Run Web Server](#-running-as-a-web-server) • [🎓 Key Features](#-key-features) • [📡 REST API](#-rest-api-reference)

---

</div>

## 🌟 Why Plagiarism Detector Pro?

Most open-source plagiarism checkers rely on basic string searching or single-word keyword matching, causing massive **false-positive keyword collisions** (e.g. flagging common nouns like *"diamonds"*, *"seaborn"*, or *"price"*). 

**Plagiarism Detector Pro** solves this by implementing **Longest Common Subsequence (LCS) contiguous passage matching** alongside **Statistical AI Perplexity & Burstiness Forensics** to deliver true university-grade parity with **Blackboard SafeAssign** and **Turnitin**.

```
┌──────────────────────────────────────────────────────────────────────────────────┐
│                             PLAGIARISM DETECTOR PRO                              │
├─────────────────────────┬──────────────────────────────┬─────────────────────────┤
│   🌐 Web Application    │    📦 Standalone CLI & NPM   │   🤖 Claude & Codex MCP │
│  • Interactive split-UI │  • 100% offline local engine │  • Native JSON-RPC MCP  │
│  • Batch ZIP gradebook  │  • Zero server dependency    │  • 1-click citation bot │
│  • PDF / Cert export    │  • Fast terminal feedback    │  • Real-time coach tool │
└─────────────────────────┴──────────────────────────────┴─────────────────────────┘
```

---

## 📦 NPM Package & Standalone CLI (100% Offline)

The CLI and NPM package operate **completely offline and standalone** with built-in embedded benchmark corpora. **Zero Python or web server required!**

### 1. Installation

```bash
# Global installation
npm install -g plagiarism-detector-pro

# Or run instantly with npx (no install needed)
npx plagiarism-detector-pro --help
```

### 2. CLI Command Suite

```bash
# 🔍 1. Scan a document for SafeAssign Plagiarism & AI Content
plag scan thesis_draft.md
plag scan essay.docx --verbose   # Shows side-by-side matching passages
plag scan paper.tex --json       # Outputs machine-readable JSON

# 🧑‍🎓 2. Student Writing & Integrity Coach
# Scans unsupported empirical claims, formal vocabulary boosts, and thesis strength
plag coach manuscript.docx

# 🔬 3. PhD Research & Conference Double-Blind Pre-Flight Auditor
# Audits anonymity compliance, isolates LaTeX math, and profiles section cadence
plag audit neurips_paper.pdf

# ✍️ 4. Smart Academic Paraphraser & Attribution Helper
# Generates 3 academic restructuring options (Active Inversion, Methodological, Conceptual)
plag paraphrase "Deep neural networks learn rich representations from massive text corpora." --source "Vaswani2017"

# 📚 5. Instant DOI, arXiv & Scientific Citation Generator
# Resolves DOIs/arXiv IDs into copy-ready BibTeX, APA 7th, MLA 9th, and IEEE
plag cite 10.1038/s41586-020-2649-2
plag cite 1706.03762

# 🔤 6. Reference List Alphabetizer & Clean Formatter
# Auto-sorts unorganized bibliographies by primary author, validates years & DOIs
plag alphabetize unorganized_references.txt

# 📑 7. Draft-to-Draft Revision Comparator
# Evaluates revision percentage, newly added sections, and retained text between drafts
plag diff draft_v1.txt draft_v2.txt

# 📦 8. Class Gradebook Batch Processor
# Ingests an entire folder of student assignments and prints an aggregated gradebook table
plag batch ./student_submissions/

# 📜 9. Verifiable Student Authorship Certificate
# Generates a cryptographic SHA-256 verified academic honor certificate
plag certificate essay.md --name "Jane Doe" --title "Deep Learning Study"

# 🤖 10. Start Model Context Protocol (MCP) Server for Claude & Codex
plag mcp
```

---

## 🤖 Claude Desktop, Claude Code & Codex MCP Integration

Plagiarism Detector Pro implements the **Model Context Protocol (MCP)**, allowing **Claude Desktop**, **Claude Code**, **OpenAI Codex**, **Antigravity**, and **Cursor** to natively audit originality, verify citations, and restructure text.

### Claude Desktop Setup

Add this configuration to your Claude Desktop config file:
- **macOS:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows:** `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "plagiarism-detector-pro": {
      "command": "npx",
      "args": ["-y", "plagiarism-detector-pro", "mcp"]
    }
  }
}
```

### Claude Code CLI Setup
```bash
claude mcp add plagiarism-detector-pro npx -y plagiarism-detector-pro mcp
```

### Available MCP Tools for AI Assistants:

| Tool Name | Parameters | Purpose |
| :--- | :--- | :--- |
| `plag_scan_text` | `text`, `exclude_quotes` | Scans text for plagiarism %, SafeAssign risk tier, and AI probability |
| `plag_scan_file` | `file_path`, `exclude_quotes` | Ingests `.docx`, `.pdf`, `.tex`, `.ipynb`, `.md`, or `.txt` from disk |
| `plag_academic_coach` | `text` | Scans unsupported claims, tone booster formal synonyms, and thesis score |
| `plag_paraphrase` | `sentence`, `source_title` | Restructures overlapping text into 3 scholarly formulations with attribution |
| `plag_generate_citation`| `query` | Resolves DOI / arXiv / Paper Title to BibTeX, APA, MLA, and IEEE |
| `plag_alphabetize_references`| `references_text` | Auto-sorts and validates reference lists alphabetically |
| `plag_compare_drafts` | `draft_v1`, `draft_v2` | Computes draft continuity %, added content %, and word delta |

---

## 🌐 Running as a Web Server

If you wish to host your own web platform instance with the interactive dashboard, PDF report generator, and class gradebook:

### Option A: Docker Compose (Recommended)
```bash
# 1. Clone repository
git clone https://github.com/scalesynthai/Plagiarism-Detector-Pro.git
cd Plagiarism-Detector-Pro

# 2. Start container
docker compose up -d --build
```
Open **`http://localhost:5001`** in your browser.

### Option B: Local Python Setup
```bash
# 1. Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate   # On Windows: venv\Scripts\activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch development server
python app.py
```

### Environment Configuration (`.env`)
```ini
FLASK_ENV=production
SECRET_KEY=your-secure-random-secret-key
ADMIN_PIN=2026           # PIN required for institutional document deletion
PORT=5001
MAX_CONTENT_LENGTH=52428800 # 50MB max file upload size
```

---

## 🎓 Key Features & Capabilities

### 1. 🛡️ Student "Private Draft Shield"
- **No Self-Plagiarism Guarantee**: Allows students to check drafts against 250M+ publications and university databases **without storing the manuscript into institutional archives**, preventing self-plagiarism flags upon final Canvas/Turnitin submission.

### 2. 🧑‍🎓 Student Academic Writing & Integrity Coach
- **🔍 Unsupported Claim Finder**: Detects empirical and statistical assertions (*"studies show"*, *"85% of"*, *"research demonstrates"*) lacking a parenthetical citation, with a 1-click `(Author, Year)` citation placeholder.
- **✍️ Scholarly Tone Booster**: Identifies conversational phrases (*"a lot of"*, *"basically"*, *"big impact"*) and provides instant formal replacements (*numerous*, *fundamentally*, *significant effect*).
- **🎯 Thesis Statement & Abstract Evaluator**: Evaluates scientific completeness (Hypothesis, Methodology, Significance) with a `/100` score and actionable recommendations.

### 3. 🔬 PhD Research & Conference Pre-Flight Auditor
- **🔒 Double-Blind Anonymity Compliance**: Detects self-identifying author references or unblinded repository links before conference submission (NeurIPS, ICML, ICLR, IEEE).
- **📐 Mathematical & LaTeX Isolation**: Isolates LaTeX equations (`$...$`, `\begin{equation}`) and code cells from false similarity flags.

### 4. ↔️ Interactive Side-by-Side Split Diff Comparison
- Clicking any highlighted sentence opens a split-screen viewer comparing the student submission on the left with the verbatim original source on the right.

### 5. 🤖 AI-Generated Content & LLM Detection Layer
- Computes **Syntactic Burstiness** and **Lexical Entropy** to classify:
  - 🟢 **Human-Written** ($< 25\%$)
  - 🟡 **Mixed / AI-Assisted** ($25\% - 65\%$)
  - 🔴 **Likely AI-Generated** ($> 65\%$)

### 6. 📦 Whole-Class Batch Submissions Gradebook
- Upload a `.zip` archive or multiple files to scan all submissions concurrently and produce an aggregated **Instructor Gradebook Table**.

---

## 📡 REST API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/check` | Scan text (`query`) or document (`file`) for originality and AI content |
| `POST` | `/check/batch` | Scan whole-class `.zip` archive or multiple files |
| `POST` | `/check/compare-drafts` | Compare Draft v1 vs Draft v2 revision deltas |
| `POST` | `/api/paraphrase` | Generate 3 academic restructurings for a sentence |
| `POST` | `/api/cite` | Auto-generate BibTeX, APA, MLA, and IEEE citations |
| `POST` | `/api/student-coach/tone-and-claims` | Scan unsupported claims and formal tone boosts |
| `POST` | `/api/student-coach/alphabetize-references` | Alphabetize and validate reference list |
| `POST` | `/api/student-coach/evaluate-thesis` | Evaluate opening abstract / thesis statement |
| `POST` | `/reports/certificate` | Generate verifiable Student Certificate of Academic Authorship |
| `GET` | `/sources` | List institutional repository documents |
| `POST` | `/sources/upload` | Add new document to institutional repository |
| `DELETE` | `/sources/<filename>` | Delete document from institutional repository (Requires Admin PIN) |
| `GET` | `/docs` | Interactive Swagger UI API playground |

---

## 🧪 Testing & Quality Assurance

Plagiarism Detector Pro includes comprehensive test suites across both Python and Node.js:

```bash
# Run Node.js & CLI test suite (12 tests)
npm test

# Run Python & Web test suite (28 tests)
pytest tests/ -v
# Or: ./venv/bin/python -m unittest discover tests -v

# Run all test suites
make test
```

---

## 🤝 Contributing & Security

Contributions are warmly welcomed! Please read our [**Contributing Guide**](CONTRIBUTING.md) and [**Code of Conduct**](CODE_OF_CONDUCT.md) before submitting pull requests.

If you discover a security vulnerability, please consult our [**Security Policy**](SECURITY.md) or report it privately to **`security@subba.dev`**.

---

## 📄 License

This project is open-source software licensed under the [**MIT License**](LICENSE).

---

<div align="center">
  <sub>Engineered by <a href="https://github.com/ScaleSynthAI">ScaleSynthAI</a> • Maintained for Scholars, Students, and Researchers Worldwide.</sub>
</div>
