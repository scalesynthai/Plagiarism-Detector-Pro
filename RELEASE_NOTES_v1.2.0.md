# Plagiarism Detector Pro v1.2.0

**Note:** this version was committed and tagged retroactively. It was never published to npm as `1.2.0` — v1.3.0 (which fully includes everything below, plus the writing-cleanup tool) shipped first and is the current live version. This release exists so the git/GitHub history has no gap; if you need this exact version's code without v1.3.0's additions, install from the `v1.2.0` tag directly rather than from npm.

## CLI fix tips and word-level suggestions

- `plag scan` now prints a "Top Fixes" section by default: the highest-scoring writing-pattern categories with their recommendation and quoted evidence, and the unsupported-claim sentences needing a citation. Previously the CLI only showed counts; the full explanation existed only in the web app.
- Added a `suggestion` field to flagged predictable-vocabulary evidence (e.g. `"leverage" -> "use"`), taken from `avoid-ai-writing`'s and `humanize`'s own published before/after word tables. Shown to the reviewer, not an automated rewrite; no document text is rewritten by this version. Surfaced in the CLI and the web app's evidence list.
- Corrected the `THIRD_PARTY_NOTICES.md` credit for `hyperresearch`: the earlier wording ("claim-to-citation pairing and renormalized scoring") overstated the connection to that project, which is a web-research agent, not a citation-scoring library. Replaced with an accurate, narrower credit and documented the real gap between what's credited and what's implemented.

**Full Changelog**: https://github.com/scalesynthai/Plagiarism-Detector-Pro/compare/v1.1.0...v1.2.0
