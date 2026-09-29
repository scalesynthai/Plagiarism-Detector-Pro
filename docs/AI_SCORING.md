# Explainable writing-pattern scoring

The writing-pattern score is a review aid, not a probability that AI wrote a
document. It scores nine visible signal groups from 0 to 3 and normalizes the
sum to 100:

1. Predictable vocabulary
2. Sentence rhythm
3. Hedge density
4. Formulaic structure
5. Specificity and grounding
6. Transition fingerprint
7. Punctuation fingerprint
8. Assistant-style register
9. Rhetorical scaffolding

Every non-zero category includes the phrases or sentence spans that caused the
finding and a focused revision suggestion. Samples under 120 words are marked
as limited because document-level rhythm and structure need enough text.

## Word-level suggestions

Each flagged predictable-vocabulary phrase (`categories[].evidence[].suggestion`
where `id` is `predictability`) carries a plain-language replacement, e.g.
`"leverage" -> "use"`. This is a suggestion for the person reviewing the text
to consider, not an automated rewrite: the tool never rewrites a document's
prose, and the suggestion table is a small, fixed lookup, not a text-generation
step. Shown in the CLI's "Top Fixes" section and the web app's evidence list.
Sourced from `avoid-ai-writing`'s and `humanize`'s own published word tables;
see THIRD_PARTY_NOTICES.md for the boundary on what was and was not adapted
from those two projects.

## Em dashes

The analyzer reports both the count and the number of em dashes per 300 words.
More than one per 300 words is highlighted for review. An em dash alone cannot
produce a high score or establish authorship. This preserves the professor's
useful style feedback without converting one punctuation choice into an
academic-integrity accusation.

## AI-tool copy-paste artifacts

Separate from the nine scored categories, the analyzer checks for a small set of
literal artifacts of copying an AI assistant's output: an unfilled template
placeholder (`[Your Name]`, `2025-XX-XX`), leftover chatbot citation markup
(`citeturn0search0`, `contentReference[oaicite:0]`), or an AI-tool tracking
parameter in a URL (`utm_source=chatgpt.com`). These are checkable facts, not
style inference, so they are reported as `provenance_flags` and are never added
to `pattern_score`. Pattern set adapted from the MIT-licensed `avoid-ai-writing`
project's documented tells; see THIRD_PARTY_NOTICES.md. A zero count means none
of these specific artifacts were found, not that the document is human-written.

## Evidence integrity

The evidence score is separate from the writing-pattern score. It combines the
available components and renormalizes their weights:

- recognized empirical claims with same-sentence citations: 50%
- in-text citations linked to bibliography entries: 30%
- source-type quality heuristic: 20%

Missing components do not become zero. Citation syntax and bibliography links
do not prove that a source exists or supports the sentence, so the report tells
the writer to verify each important claim against the cited source.

## Threshold calibration

The Elevated (≥25) and High (≥65) `pattern_score` bands were checked against
a small, guaranteed-human corpus (documents that predate LLMs entirely, so
authorship is not in question) and produced zero false positives. This
validates the existing thresholds; the corpus is too small (21 documents)
to justify tightening them further. See
[benchmarks/threshold_calibration.md](../benchmarks/threshold_calibration.md)
for the corpus, methodology, and full results, adapted from `avoid-ai-writing`'s
documented approach to its own threshold.

## Compatibility fields

`ai_probability` and `human_probability` remain in API and npm CLI output for
backward compatibility. They mirror the uncalibrated pattern score and its
complement and must not be described as calibrated probabilities.
