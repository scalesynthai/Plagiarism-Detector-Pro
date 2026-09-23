# Plagiarism Detector Pro v1.0.4

Version 1.0.4 improves matching accuracy, makes score accounting explicit, and fixes several diagnostic errors.

## Matching and scoring

- Exact contiguous word spans now determine similarity in both the Python and Node engines.
- Each query word contributes at most once to the overall score, even when sources overlap or are duplicated.
- Repeated phrases within a source use the longest matching context.
- Quoted text and bibliography sections can be excluded independently. Citations remain included.
- Results expose selected, raw, body, bibliography, and quotation scores, eligible-word counts, and matched offsets.

## Diagnostic fixes

- APA `et al.`, multi-citation parentheses, narrative citations, and IEEE citations are recognized more reliably.
- Thesis analysis skips title and author front matter and stops before later manuscript sections.
- Anonymity screening checks bylines, affiliations, and email addresses in front matter and reports its limited scope.
- Writing-pattern scores are identified as uncalibrated heuristics rather than proof of AI or human authorship.

## Verification

- Added 25 fixed offline fixtures with token precision, recall, F1, false-positive rate, passage recall, and score MAE.
- Python and Node coverage must agree in CI.
- Challenge cases document known failures involving synonym paraphrases, fragments shorter than four words, unavailable sources, and generic boilerplate.

This release measures lexical overlap only in configured or retrieved sources. It does not reproduce SafeAssign or Turnitin corpora or scoring.
