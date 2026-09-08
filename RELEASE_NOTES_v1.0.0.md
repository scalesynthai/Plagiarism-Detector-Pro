# Plagiarism Detector Pro v1.0.0 — Enterprise Academic Originality & Student Productivity Suite

ScaleSynthAI is proud to announce the **v1.0.0** release of **Plagiarism Detector Pro**, an enterprise-grade academic originality, AI content verification, and student writing coach platform.

---

## 🌟 Major Highlights & Core Features

### 1. Dual Plagiarism & AI-Generated Content Engine
- **SafeAssign Plagiarism Index (%)**: Evaluates sentence containment, matched word volume, and document vector similarity.
- **Zero False-Positive Noun Collision Defense**: Uses Longest Common Subsequence (LCS) and contiguous phrase overlap to prevent false flags on common keywords (e.g. *diamonds*, *seaborn*, *price*).
- **Statistical AI & LLM Likelihood Engine**: Computes sentence length **Burstiness**, **Lexical Entropy**, and transitional cadence to detect ChatGPT, Claude, Gemini, and synthetic prose.

### 2. Student Academic Writing & Integrity Coach
- **🔍 Unsupported Claim & Citation Finder**: Automatically flags empirical/statistical assertions (*"studies show"*, *"85% of"*, *"research demonstrates"*) lacking a parenthetical citation, with a **1-click "+ Copy (Author, Year)"** helper.
- **✍️ Scholarly Tone & Vocabulary Booster**: Highlights conversational phrases (*"a lot of"*, *"basically"*, *"big impact"*) and provides clickable formal replacements (*numerous*, *fundamentally*, *significant effect*).
- **🔤 Reference List Alphabetizer & Formatter**: Auto-sorts unorganized bibliographies alphabetically by primary author last name, validates publication years, checks DOIs, and copies with proper hanging indents.
- **🎯 Thesis Statement & Abstract Evaluator**: Scores opening paragraphs (`/100`) based on hypothesis clarity, empirical methodology, and scholarly significance.
- **🎯 Assignment Word-Budget & Sweet-Spot Tracker**: Live word counter with target presets (500 to 5,000 words or custom) and visual progress feedback.

### 3. PhD Research & Conference Double-Blind Auditor
- **🔒 Double-Blind Anonymity Compliance**: Automatically detects self-identifying author references or unblinded repository links before conference submission (NeurIPS, ICML, ICLR, IEEE).
- **📐 Mathematical & LaTeX Isolation**: Isolates LaTeX equations (`$...$`, `\begin{equation}`) and code cells from false similarity flags.

### 4. Interactive Full-Text Manuscript Inspector & Split Diff Viewer
- Click any sentence to inspect synchronized side-by-side matches against the original reference text.
- 1-click **Academic Paraphrasing & Synthesis Assistant** with citation injectors (APA 7th, MLA 9th, IEEE).

### 5. Multi-Format Parsing & Batch Processing
- Ingests **Microsoft Word (.docx)**, **Adobe PDF (.pdf)**, **LaTeX (.tex)**, **Jupyter Notebooks (.ipynb)**, **Markdown (.md)**, and **Plain Text (.txt)**.
- **Class Gradebook Batch Processing**: Ingests whole-class `.zip` archives or multiple documents, generating an aggregated gradebook.

### 6. Real-Time Global Internet & Scholarly Database Search
- Live queries against **Wikipedia**, **arXiv Preprints**, **OpenAlex**, **CrossRef**, and an **Institutional Reference Corpus** protected by Admin Security PIN.

### 7. Executive Light Academic Paper Theme (Default)
- High-contrast, clean academic styling with seamless dark mode toggling.

---

## 🧪 Verification & Quality Standards
- **28 Automated Unit & Integration Tests**: Complete test coverage across extraction, vector similarity, citation validation, AI heuristics, and student coach APIs.
- **Production Container Ready**: Optimized Docker image with non-root security, healthchecks, and Docker Compose configuration.

---

## 🚀 Quick Start
```bash
# Clone repository
git clone https://github.com/scalesynthai/Plagiarism-Detector-Pro.git
cd Plagiarism-Detector-Pro

# Launch with Docker Compose
docker compose up -d --build
```
Access at `http://localhost:5001`.
