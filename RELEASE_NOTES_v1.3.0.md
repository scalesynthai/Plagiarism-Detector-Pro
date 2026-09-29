# Plagiarism Detector Pro v1.3.0

This release covers everything since v1.1.0. v1.2.0 was committed and documented but never tagged or published — this release supersedes it, so nothing from it is missing here.

## Deterministic, offline writing cleanup (new)

- `core/writing_cleanup.py` / `lib/writing_cleanup.js` (`WritingCleanup`) mechanically applies the exact predictable-vocabulary word-swap suggestions the writing-pattern score already shows. Not a rewrite engine: only unambiguous 1:1 word/phrase swaps are auto-appliable — a parenthetical judgment-call suggestion like "cut the phrase" is never auto-applied. A minimal a/an fix-up runs on the word before an edit (`"a pivotal role"` → `"an important role"`).
- `plag cleanup <file|text>` CLI command lists proposed edits; `--apply` (optionally `--output <path>`) applies them.
- Web app: a "Suggested cleanup" panel — one checkbox per edit, apply, copy result. New `POST /api/writing-cleanup` and `POST /api/writing-cleanup/apply`; the apply endpoint always re-derives edit content from the submitted text server-side and only accepts which indices to apply, never client-supplied replacement text.
- No network access, no external model, and deliberately no attempt to change how any third-party AI detector (GPTZero, Turnitin, Pangram) scores the result. See [docs/AI_SCORING.md](docs/AI_SCORING.md) and [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md) for the boundary.

## CLI fix tips

- `plag scan` now prints a "Top Fixes" section by default: the highest-scoring writing-pattern categories with their recommendation and quoted evidence, and the unsupported-claim sentences needing a citation. Previously the CLI only showed counts.
- Flagged predictable-vocabulary evidence carries a `suggestion` (e.g. `"leverage" -> "use"`), taken from `avoid-ai-writing`'s and `humanize`'s own published before/after word tables. Shown in the CLI and the web app's evidence list.

## Licensing correction

Corrected the `THIRD_PARTY_NOTICES.md` credit for `hyperresearch`: the earlier wording overstated the connection to that project, which is a research-agent harness, not a citation-scoring library. Replaced with an accurate, narrower credit and documented the real gap between what's credited and what's implemented.

**Full Changelog**: https://github.com/scalesynthai/Plagiarism-Detector-Pro/compare/v1.1.0...v1.3.0
