# Third-party notices

Plagiarism Detector Pro includes concepts and selectively adapted,
dependency-free implementations from the following MIT-licensed projects:

## Avoid AI Writing

- Project: https://github.com/conorbronsdon/avoid-ai-writing
- Copyright (c) 2026 Conor Bronsdon
- License: MIT

The writing-pattern engine draws on its categorized pattern detection,
length-normalized review model, visible evidence, and explicit false-positive
boundaries. Em-dash use is reported as style guidance and is not decisive
authorship evidence. `provenance_flags` (unfilled template placeholders,
chatbot citation markup, AI-tool URL tracking parameters) is adapted directly
from its documented "AI-tool fingerprint" pattern category and is reported
separately from the pattern score because these are literal, checkable
artifacts rather than style inference.

## Humanize

- Project: https://github.com/harshaneel/humanize
- Copyright (c) 2026 Harshaneel Gokhale
- License: MIT

The nine-category review layout draws on its research-backed AI-check signal
groups: predictable vocabulary, burstiness, hedging, structure, specificity,
transitions, punctuation, register, and rhetorical scaffolding. Its documented
em-dash rate ("roughly 3-5x above human baseline... hard limit: one per 300
words") is the source of this project's own em-dash review threshold.

## Avoid AI Writing and Humanize (word-suggestion tables)

The `suggestion` field attached to flagged predictable-vocabulary evidence
(for example "leverage" -> "use") is taken directly from the before/after
word-replacement tables both projects publish in their own READMEs
(avoid-ai-writing's "Language Patterns" table; humanize's Lever 1 word list).
`core/writing_cleanup.py` / `lib/writing_cleanup.js` can mechanically apply
this same fixed lookup table when the writer opts in and reviews each change
(`plag cleanup --apply`; the web app's "Suggested cleanup" panel) -- a plain
find-and-replace over an already-fixed word list, not text generation. Neither
upstream project's own rewrite/humanization skill (the part of their own
tooling built with an LLM to help arbitrary text evade AI detectors, including
third-party ones) is used here; that is a different purpose than this
project's, and was deliberately left out. See docs/AI_SCORING.md for the exact
boundary of what the cleanup tool does and does not do.

## HyperResearch

- Project: https://github.com/jordan-gibbs/hyperresearch
- Copyright (c) 2026 Jordan Gibbs
- License: MIT

**Correction (this notice previously overstated this credit).** HyperResearch
is a multi-agent deep-research harness (web crawling, a persistent source
vault, adversarial critics) and does not implement or document a
"claim-to-citation pairing" technique as such; an earlier version of this
notice described one anyway. The one specific, comparable idea this project's
`evidence_analysis.source_quality` heuristic takes from HyperResearch's design
is the general principle that source quality should be scored by source type
rather than treated uniformly. HyperResearch computes this from live citation
authority and retraction status (OpenAlex/Crossref lookups); this project's
`SOURCE_TIERS` is a static, offline heuristic by source-type string and does
not check retraction status or citation counts — a real gap, not yet closed,
between what is credited here and what is implemented.

Each upstream project is provided under the MIT License. The full permission
notice for each project is reproduced below:

> Permission is hereby granted, free of charge, to any person obtaining a copy
> of this software and associated documentation files (the "Software"), to deal
> in the Software without restriction, including without limitation the rights
> to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
> copies of the Software, and to permit persons to whom the Software is
> furnished to do so, subject to the following conditions:
>
> The above copyright notice and this permission notice shall be included in all
> copies or substantial portions of the Software.
>
> THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
> IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
> FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
> AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
> LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
> OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
> SOFTWARE.
