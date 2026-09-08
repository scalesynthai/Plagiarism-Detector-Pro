---
name: plagiarism-detector
description: Enterprise Academic Originality, SafeAssign Plagiarism, AI Content Detector, Citation Generator, and Student Writing Coach. Use to audit documents, detect uncredited overlap, rephrase overlapping sentences with citations, evaluate thesis statements, and auto-format bibliographies.
---

# Plagiarism Detector Pro (Claude & Codex Skill)

This skill provides direct access to the **ScaleSynthAI Plagiarism Detector Pro** engine for verifying academic originality, detecting AI-generated prose, checking for unverified empirical claims, generating citations, and restructuring text with academic integrity.

## Available MCP & CLI Tools

### 1. `plag_scan_text` / `plag scan <text>`
Scans an essay, manuscript, or paragraph for:
- SafeAssign Similarity Index (%)
- Statistical AI-content likelihood (%)
- Syntax burstiness & perplexity variance
- Contiguous matched phrases vs. institutional and global repositories

### 2. `plag_scan_file` / `plag scan <file_path>`
Ingests and scans `.docx`, `.pdf`, `.tex`, `.ipynb`, `.md`, and `.txt` files directly from disk.

### 3. `plag_paraphrase` / `plag paraphrase "<sentence>" --source "<title>"`
Synthesizes and restructures overlapping passages into 3 distinct scholarly formulations:
1. **Active Inversion** with formal author attribution clause
2. **Methodological Synthesis** (APA 7th / IEEE standard)
3. **High-Density Conceptual Restructuring** prioritizing empirical findings over source syntax

### 4. `plag_academic_coach` / `plag coach <text>`
Performs a 3-point academic integrity audit:
- **Unsupported Claim Finder**: Flags empirical/statistical assertions (*"studies show"*, *"85% of"*) lacking in-text citations.
- **Scholarly Tone Booster**: Identifies colloquial phrasing (*"a lot of"*, *"basically"*, *"big impact"*) and offers 1-click formal alternatives.
- **Thesis Statement & Abstract Evaluator**: Scores opening abstracts (`/100`) on hypothesis clarity, methodology, and significance.

### 5. `plag_generate_citation` / `plag cite <query>`
Resolves any **DOI** (e.g., `10.1145/3318464.3389700`), **arXiv ID** (e.g., `1706.03762`), or **Paper Title** into copy-ready:
- BibTeX (`@article{...}`)
- APA 7th Edition
- MLA 9th Edition
- IEEE Format

### 6. `plag_alphabetize_references` / `plag alphabetize <file_or_text>`
Alphabetizes unorganized bibliographies by primary author last name, validates publication years, and checks for DOI/URL links.

### 7. `plag_compare_drafts` / `plag diff <draft1> <draft2>`
Calculates revision delta percentages, newly added sections, and retained phrasing between Draft 1 and Draft 2.

---

## Claude Desktop Configuration (`claude_desktop_config.json`)

To enable Plagiarism Detector Pro natively in Claude Desktop, add this entry to `~/Library/Application Support/Claude/claude_desktop_config.json` (Mac) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

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

Or when running from local clone:
```json
{
  "mcpServers": {
    "plagiarism-detector-pro": {
      "command": "node",
      "args": ["/Users/subbataniparti/Documents/Git/Plagiarism-Detector/bin/mcp-server.js"]
    }
  }
}
```

---

## OpenAI Codex / Cursor / Terminal CLI Usage

```bash
# Global installation via NPM
npm install -g plagiarism-detector-pro

# Scan an essay
plag scan thesis_draft.md

# Scan with cloud hybrid global database
plag scan research.docx --server https://plag.subba.dev

# Restructure an uncredited sentence
plag paraphrase "Deep neural networks learn representations from massive text corpora." --source "Vaswani2017"

# Resolve a DOI to BibTeX and APA
plag cite 10.1038/s41586-020-2649-2

# Format messy references
plag alphabetize my_bibliography.txt
```
