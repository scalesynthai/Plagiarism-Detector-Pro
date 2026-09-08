# Contributing to Plagiarism Detector Pro

First off, thank you for considering contributing to **Plagiarism Detector Pro**! 🎉

We welcome contributions from everyone—whether you're fixing a bug, designing new academic originality algorithms, optimizing statistical AI detection layers, improving documentation, or creating new integrations.

---

## 📖 Project Description

**Plagiarism Detector Pro** is an open-source, university-grade academic originality and AI-generated content detection platform designed to match and exceed the capabilities of tools like Blackboard SafeAssign and Turnitin.

Key analytical layers include:
- **SafeAssign Multi-Source Comparison Engine**: Sentence-level n-gram tokenization, Rabin-Karp hashing, and cosine similarity across local institutional archives and live scholarly web sources (arXiv, Wikipedia, CrossRef, OpenAlex).
- **Statistical AI & LLM Likelihood Engine**: Burstiness, syntactic perplexity variance, and lexical entropy analyzers.
- **Side-by-Side Interactive Diff Modal**: Granular highlighted text matching between student submissions and identified source publications.
- **Citation & Bibliography Integrity Validator**: In-text extraction and validation against formatted bibliographies for APA, MLA, IEEE, and Chicago styles.
- **Class Batch & Gradebook Processor**: Parallel analysis of multi-file or `.zip` submissions producing an exportable class similarity overview.
- **Academic PDF Report Generator**: Printable, formatted originality transcripts.

---

## 📋 Table of Contents

1. [Code of Conduct](#-code-of-conduct)
2. [Security Policy](#-security-policy)
3. [How Can I Contribute?](#-how-can-i-contribute)
   - [Reporting Bugs](#reporting-bugs)
   - [Suggesting Enhancements](#suggesting-enhancements)
   - [Submitting Pull Requests](#submitting-pull-requests)
4. [Local Development Setup](#-local-development-setup)
5. [Running Tests](#-running-tests)
6. [Git & Commit Guidelines](#-git--commit-guidelines)
7. [Pull Request Checklist](#-pull-request-checklist)

---

## 📜 Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this standard of friendly, respectful, and inclusive collaboration. Please report unacceptable behavior to `maintainers@subba.dev`.

---

## 🛡️ Security Policy

If you discover a potential security vulnerability, **please do not disclose it publicly in an open GitHub issue**. Instead, follow our responsible disclosure process outlined in our [Security Policy](SECURITY.md) or email **`security@subba.dev`**.

---

## 🛠️ How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing [GitHub Issues](https://github.com/ScaleSynthAI/Plagiarism-Detector-Pro/issues) to ensure the defect hasn't already been reported.

When creating a bug report using our [Bug Report Template](.github/ISSUE_TEMPLATE/bug_report.yml), please include:
- A clear, descriptive title.
- Steps to reproduce the issue.
- Expected behavior vs. actual behavior.
- Python version, operating system, and browser details.
- Error traceback logs or screenshots if applicable.

### Suggesting Enhancements

Feature requests and algorithmic improvements are welcome! Please open an issue using our [Feature Request Template](.github/ISSUE_TEMPLATE/feature_request.yml) with:
- A concise title explaining the proposed feature.
- Academic motivation / user story (why this feature helps educators, researchers, or students).
- Proposed implementation details, algorithmic design, or API signatures.

---

## 💻 Local Development Setup

### 1. Fork and Clone the Repository

```bash
git clone https://github.com/<your-username>/Plagiarism-Detector-Pro.git
cd Plagiarism-Detector-Pro
```

### 2. Set Up a Virtual Environment

```bash
# Using Python 3.10+
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Run the Development Server

```bash
python app.py
# Or using the Makefile:
make dev
```
Navigate to `http://127.0.0.1:5001` in your browser.

---

## 🧪 Running Tests

Ensure all automated tests pass before committing code:

```bash
# Run unit tests via unittest
python -m unittest discover tests -v

# Or using Makefile
make test
```

If you are adding new features (e.g. citation styles, vector indexing algorithms, or file parsers), please include corresponding unit test cases in `tests/test_app.py`.

---

## 📝 Git & Commit Guidelines

We follow [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` A new feature (e.g., `feat(core): add Chicago style citation support`)
- `fix:` A bug fix (e.g., `fix(batch): handle SpooledTemporaryFile stream buffer`)
- `docs:` Documentation updates (e.g., `docs: update API reference`)
- `refactor:` Code changes that neither fix a bug nor add a feature
- `test:` Adding or refactoring automated tests
- `chore:` Maintenance tasks, dependency updates, CI/CD workflows

### Recommended Workflow:

1. Create a descriptive feature branch:
   ```bash
   git checkout -b feat/your-feature-name
   ```
2. Implement your changes and verify with test suite:
   ```bash
   make test
   ```
3. Commit with Conventional Commits:
   ```bash
   git commit -m "feat(ai-detector): add ngram burstiness analysis"
   ```
4. Push to your fork:
   ```bash
   git push origin feat/your-feature-name
   ```
5. Open a Pull Request on GitHub targeting `main`.

---

## ✅ Pull Request Checklist

Before submitting your PR, please verify:

- [ ] All existing and new unit tests pass (`make test`).
- [ ] Code follows PEP 8 conventions and project structure.
- [ ] Any new API endpoints or core modules are documented in `README.md`.
- [ ] Commit messages follow Conventional Commits format.
- [ ] Your PR targets the `main` branch.

---

## 🌟 Thank You!

Your contributions make open-source academic integrity tools accessible and robust for universities, educators, and researchers worldwide.
