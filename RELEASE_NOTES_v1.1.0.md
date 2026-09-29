# Plagiarism Detector Pro v1.1.0

Version 1.1.0 replaces the single AI-probability estimate with an explainable, evidence-quoted writing-pattern review, integrating ideas from three MIT-licensed projects (see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)).

## Explainable writing-pattern scoring

- A nine-signal `pattern_score` (0-100), adapted from `avoid-ai-writing` and `humanize`. Every non-zero category quotes the exact phrases or sentence spans behind it and includes a focused revision suggestion. See [docs/AI_SCORING.md](docs/AI_SCORING.md).
- Em dashes are reported as an exact count and a rate per 300 words, with each instance located in the text. An em dash alone can no longer produce a high score or imply authorship — the common false signal that punctuation choice alone proves AI use.
- A separate evidence-integrity score, adapted from `hyperresearch`. Pairs recognized empirical claims with same-sentence citations, links in-text citations to bibliography entries, and factors in source-type quality, renormalizing when a component is unavailable rather than scoring it as zero.
- `ai_probability` / `human_probability` remain as documented compatibility aliases for `pattern_score` in the Python API and npm CLI/MCP output — uncalibrated heuristic mirrors, not calibrated probabilities.
- The web dashboard, PDF/HTML reports, advisory certificates, and batch gradebook all display the new score consistently. Python and Node score identically on the same input.

## New: AI-tool copy-paste artifacts

`provenance_flags` separately checks for literal artifacts of copying an AI assistant's output — unfilled template placeholders, leftover chatbot citation markup, AI-tool URL tracking parameters — adapted from `avoid-ai-writing`'s "AI-tool fingerprint" category. Never folded into `pattern_score`, since these are checkable facts rather than style inference.

## Threshold validation

Checked the Elevated/High `pattern_score` bands against a small, guaranteed-human corpus (21 documents, all predating LLMs entirely) and confirmed zero false positives. Thresholds were not changed — the corpus validates them without being large enough to justify loosening them. See [benchmarks/threshold_calibration.md](benchmarks/threshold_calibration.md).

**Full Changelog**: https://github.com/scalesynthai/Plagiarism-Detector-Pro/compare/v1.0.5...v1.1.0
