# Human-writing calibration corpus

A small, guaranteed-human text sample used to check the writing-pattern
score's false-positive rate, following the methodology the MIT-licensed
`avoid-ai-writing` project documents for its own threshold (calibrating
against a corpus of confirmed human writing, then reporting how many of
those documents an unchanged detector would flag). See
[THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md).

## What's in it, and why

- **`emerson_essays_1841.json`** — 10 excerpts (~150-500 words each) from
  Ralph Waldo Emerson's *Essays: First Series* (1841), via
  [Project Gutenberg #2944](https://www.gutenberg.org/ebooks/2944). Public
  domain everywhere; author died in 1882.
- **`arxiv_abstracts_pre2022.json`** — 11 full abstracts of well-known
  papers, all posted to arXiv before ChatGPT existed (Nov 2022), covering
  ML, NLP, and particle physics. Fetched from each paper's public `arxiv.org/abs/`
  page; exact IDs and titles are the JSON keys.

Both sets were chosen because their **publication date makes LLM
involvement impossible** — a stronger guarantee than "this looks human,"
which is exactly the problem with the AI-writing-detection literature
itself (see `humanize`'s README on Wikipedia's AI-contamination concerns
for *current* text). The two sets also give two very different
registers: 19th-century literary essay prose, and terse contemporary
academic abstracts, which is close to (if not identical to) the
register a student's writing sample is likely to be compared against.

## Known limitation

**N = 21 documents.** `avoid-ai-writing`'s own calibration corpus has 376.
This corpus is real and honestly sourced, but far smaller — treat the
percentiles in `../threshold_calibration.md` as a sanity check that
validates the existing thresholds don't obviously misfire, not as a
statistically tight bound. Expanding this corpus (more registers, more
documents per register, ideally contributed by real student writing with
permission) would make any future threshold change trustworthy in a way
this sample alone cannot.

## Reproducing or extending it

```bash
python3 benchmarks/calibrate_thresholds.py
```

Add more `{"id": text}` entries to either JSON file, or add a new JSON
file and register it in `calibrate_thresholds.py`, to grow the corpus.
Keep every addition to a **pre-November-2022** source, or another source
with an equally strong human-authorship guarantee, so the corpus keeps
meaning what it claims to mean.
