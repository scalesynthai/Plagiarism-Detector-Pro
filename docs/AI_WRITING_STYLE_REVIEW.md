# AI Writing Style Review

The review is an evidence browser for writing and formatting patterns. It is
not an authorship classifier. The initial English ruleset is experimental and
unvalidated because this repository does not bundle an authorized,
genre-balanced corpus of human-written and AI-assisted documents.

The evolving reference was reviewed on **2026-10-03**:
[Wikipedia:Signs of AI writing](https://en.wikipedia.org/wiki/Wikipedia:Signs_of_AI_writing).
That page describes observed Wikipedia patterns and explicitly warns that they
can occur in human writing. Project-authored rules and thresholds are labeled
as project heuristics in `config/writing_style_rules.v1.json`.

## Architecture

- `core/extractor.py` creates typed blocks for uploaded files, including block
  IDs, page numbers where PDF extraction provides them, DOCX run-format spans,
  extraction warnings, and a normalized-to-original character map.
- `config/writing_style_rules.v1.json` stores rule metadata, patterns,
  thresholds, exclusions, caps, source, review date, and enabled state.
- `core/style_review.py` emits typed findings, normalized frequencies,
  category caps, coverage warnings, and the optional style-pattern index.
- `core/citation_quality.py` checks local URL, DOI, ISBN, reference-link, and
  duplication issues separately from style and plagiarism.
- The report UI filters finding-level passages by category and shows exclusions.

Quoted passages, references, code, and supplied template blocks remain
inspectable but are excluded from the default index. Em dashes are counted as
U+2014 separately from en dashes and hyphen-minus characters. Smart quotes and
apostrophes receive zero default score.

## Scoring

The index is omitted below 120 eligible words. Each rule must meet its configured
occurrence and per-1,000-word threshold before contributing. Evidence-strength
points are capped by category, overlapping matches from the same rule and span
are deduplicated, and em-dash contribution is capped at four points. A stronger
review recommendation requires findings across at least three categories.

Compatibility API fields named `ai_probability` remain for older clients, but
the web interface uses the style-pattern index and never presents it as an AI
percentage or misconduct decision.

## Coverage matrix

| Reference category | Coverage |
|---|---|
| Significance, legacy, broader trends | Implemented heuristic check |
| Canned notability and media coverage | Requires human review |
| Superficial analysis and trailing participles | Implemented heuristic check |
| Promotional language | Implemented deterministic check |
| Vague associations | Implemented heuristic check |
| Vague attribution and consensus | Implemented heuristic check |
| Generic challenge/future endings | Implemented heuristic check |
| Awards and recognition sections | Requires human review |
| Starter vocabulary density | Implemented deterministic check |
| Avoidance of basic copulatives | Requires human review |
| Negative parallelism | Implemented deterministic check |
| Wikipedia-list proper nouns | Not applicable to uploaded documents |
| Rule of three | Implemented heuristic check |
| Heading hierarchy, boldface, emoji, Markdown, separators | Implemented deterministic checks when extraction supports formatting |
| Unusual table purpose | Requires human review |
| Em dash, en dash, hyphen-minus, smart punctuation | Implemented deterministic checks; smart punctuation scores zero |
| Assistant offers, cutoff statements, placeholders | Implemented deterministic checks |
| Internal citation/rendering tokens | Implemented deterministic checks |
| URL, DOI, ISBN, citation/reference linkage | Implemented local deterministic checks |
| DOI/URL availability and metadata | Optional external verification; disabled by default |
| Whether evidence supports a claim | Requires human review |
| Comment, edit-summary, account-history behavior | Not applicable to uploaded documents |
| Bias and semantic conclusions | Requires human review or optional authorized external verification |

## Remaining gaps

PDF formatting is limited to text and page locations; scanned PDFs require OCR.
DOCX has no stable page numbers without rendering. Table purpose, conclusion
restatement, factual claim support, and semantic associations remain human
review tasks. English is the only supported language. Reviewer dismissals are
session-local UI state until the project adds an authenticated review database.

