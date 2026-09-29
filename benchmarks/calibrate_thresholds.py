#!/usr/bin/env python3
"""Checks the writing-pattern score's false-positive rate against a small,
guaranteed-human corpus (see human_corpus/README.md) and reports what the
current pattern_score band thresholds (Elevated >= 25, High >= 65) would
flag. This validates or challenges the existing thresholds; it does not
change them automatically. See docs/AI_SCORING.md and
benchmarks/threshold_calibration.md.

Usage: python3 benchmarks/calibrate_thresholds.py
"""

import json
import statistics
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from core.ai_detector import AIDetector  # noqa: E402

CORPUS_DIR = ROOT / "benchmarks" / "human_corpus"
ELEVATED_THRESHOLD = 25
HIGH_THRESHOLD = 65


def load_corpus():
    docs = []
    with open(CORPUS_DIR / "emerson_essays_1841.json", encoding="utf-8") as f:
        for title, text in json.load(f).items():
            docs.append({"id": f"emerson:{title}", "register": "19th-century essay", "text": text})
    with open(CORPUS_DIR / "arxiv_abstracts_pre2022.json", encoding="utf-8") as f:
        for title, text in json.load(f).items():
            docs.append({"id": f"arxiv:{title}", "register": "academic abstract (pre-2022)", "text": text})
    return docs


def main():
    docs = load_corpus()
    rows = []
    for doc in docs:
        result = AIDetector.analyze(doc["text"])
        rows.append({
            "id": doc["id"],
            "register": doc["register"],
            "word_count": result["style_metrics"]["word_count"],
            "reliability": result["reliability"],
            "pattern_score": result["pattern_score"],
            "risk_level": result["ai_risk_level"],
            "category_scores": {c["id"]: c["score"] for c in result["categories"]},
        })
    rows.sort(key=lambda r: r["pattern_score"])

    print(f"{'id':60} {'words':>6} {'rel':>10} {'score':>7}")
    for r in rows:
        print(f"{r['id']:60} {r['word_count']:6d} {r['reliability']:>10} {r['pattern_score']:7.1f}")

    scores = [r["pattern_score"] for r in rows]
    print(f"\nN = {len(scores)}")
    print(f"mean = {statistics.mean(scores):.2f}, median = {statistics.median(scores):.2f}, "
          f"stdev = {statistics.pstdev(scores):.2f}, max = {max(scores):.1f}")
    sorted_scores = sorted(scores)
    for pct in (75, 90, 95, 100):
        idx = min(len(scores) - 1, int(round(pct / 100 * (len(scores) - 1))))
        print(f"p{pct}: {sorted_scores[idx]:.1f}")

    elevated = sum(1 for s in scores if s >= ELEVATED_THRESHOLD)
    high = sum(1 for s in scores if s >= HIGH_THRESHOLD)
    print(f"\nAt current thresholds ({ELEVATED_THRESHOLD}/{HIGH_THRESHOLD}): "
          f"{elevated}/{len(scores)} scored Elevated+, {high}/{len(scores)} scored High")

    fired = Counter()
    for r in rows:
        for cat, score in r["category_scores"].items():
            if score > 0:
                fired[cat] += 1
    print(f"\nCategories that fired on at least one human document: {dict(fired)}")


if __name__ == "__main__":
    main()
