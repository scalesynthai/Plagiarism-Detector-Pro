# Plagiarism Detector Pro v1.4.0

## One combined pre-submission verdict (`plag check`)

- Added `plag check <file|text>` (CLI, `--json` supported) and a `check_summary` field on every `/check` response and `scan()`/`analyze()` result: a single `clear` / `needs_review` / `insufficient_text` verdict with the top 3 fixes, built entirely from the existing `pattern_score`, `provenance_flags`, and `evidence_score` signals.
- This adds no new detection. `core/check_summary.py` / `lib/check_summary.js` only prioritize and summarize what `ai_detector` and `evidence_analyzer` already compute, so you get one answer instead of three separate outputs to reconcile before deciding whether a draft is ready.
- Provenance flags (literal AI-tool copy-paste artifacts) always rank first in `top_fixes` since they're the most concrete, checkable issue; the highest-scoring writing-pattern categories and uncited claims fill the remaining slots.

## Fixed a stale version badge on the live website

- The web app's header badge was hardcoded to `v1.0.4` and had been stale since v1.0.5 shipped three releases ago; `pyproject.toml` independently said `2.1.0` and was never read by anything. Three disconnected version numbers for one product.
- `app.py` now reads the version from `package.json` once at startup and injects it into every template and the OpenAPI spec, so this can't go stale again. Added a regression test that fails if the rendered page, the OpenAPI spec, and `package.json` ever disagree.

**Full Changelog**: https://github.com/scalesynthai/Plagiarism-Detector-Pro/compare/v1.3.0...v1.4.0
