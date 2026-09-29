"""Combine the existing pattern-score, provenance, and evidence-integrity
signals into one verdict and a prioritized fix list.

This adds no new detection: it only reads the already-computed ai_analysis
and evidence_analysis dicts and orders what they found. Kept separate from
ai_detector.py and evidence_analyzer.py so each signal module stays focused
on its own detection logic.
"""

from typing import Any, Dict, List


def build_check_summary(ai_analysis: Dict[str, Any], evidence_analysis: Dict[str, Any]) -> Dict[str, Any]:
    ai_analysis = ai_analysis or {}
    evidence_analysis = evidence_analysis or {}

    pattern_score = ai_analysis.get("pattern_score", 0.0)
    provenance_count = ai_analysis.get("provenance_flags_count", 0)
    evidence_score = evidence_analysis.get("evidence_score")
    reliability = ai_analysis.get("reliability", "standard")

    if reliability == "insufficient":
        verdict = "insufficient_text"
        reasons: List[str] = [f"Fewer than {ai_analysis.get('minimum_reliable_words', 120)} words; signals are not reliable yet."]
    else:
        reasons = []
        if provenance_count > 0:
            reasons.append(f"{provenance_count} AI-tool copy-paste artifact(s) found")
        if pattern_score >= 65:
            reasons.append(f"writing-pattern score is High ({pattern_score}/100)")
        if evidence_score is not None and evidence_score < 60:
            reasons.append(f"evidence integrity is {evidence_analysis.get('band', 'low')} ({evidence_score}/100)")
        verdict = "needs_review" if reasons else "clear"

    fixes: List[Dict[str, Any]] = []

    for flag in ai_analysis.get("provenance_flags", [])[:3]:
        fixes.append({
            "priority": "critical",
            "kind": "provenance",
            "message": f"Remove {flag.get('kind')}: {flag.get('text')!r} before submission.",
        })

    for signal in ai_analysis.get("top_signals", []):
        if len(fixes) >= 3:
            break
        fixes.append({
            "priority": "high" if signal.get("score", 0) >= 2 else "moderate",
            "kind": "writing_pattern",
            "category": signal.get("label"),
            "message": signal.get("recommendation", ""),
            "evidence_count": signal.get("evidence_count", 0),
        })

    unsupported_count = evidence_analysis.get("unsupported_claims_count") or 0
    if unsupported_count and len(fixes) < 3:
        unsupported_sentences = [
            row.get("sentence", "")[:160]
            for row in evidence_analysis.get("claim_pairs", [])
            if not row.get("has_citation")
        ][:3]
        fixes.append({
            "priority": "high",
            "kind": "citation",
            "message": f"{unsupported_count} claim(s) need a citation.",
            "examples": unsupported_sentences,
        })

    if verdict == "insufficient_text":
        summary = "Insufficient text for a reliable review."
    elif verdict == "needs_review":
        summary = "Needs review before submission."
    else:
        summary = "No high-confidence issues found in the signals this tool checks."

    return {
        "verdict": verdict,
        "summary": summary,
        "pattern_score": pattern_score,
        "provenance_flags_count": provenance_count,
        "evidence_score": evidence_score,
        "reasons": reasons,
        "top_fixes": fixes[:3],
        "disclaimer": (
            "This combines existing pattern-score, provenance, and evidence-integrity "
            "signals into one verdict. It is not a plagiarism or AI-authorship determination; "
            "institutional review still governs."
        ),
    }
