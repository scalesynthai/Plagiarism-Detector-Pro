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

## Compatibility fields

`ai_probability` and `human_probability` remain in API and npm CLI output for
backward compatibility. They mirror the uncalibrated pattern score and its
complement and must not be described as calibrated probabilities.
