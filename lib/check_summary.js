/**
 * Combine the existing pattern-score, provenance, and evidence-integrity
 * signals into one verdict and a prioritized fix list. Adds no new
 * detection: it only reads the already-computed ai_analysis and
 * evidence_analysis objects and orders what they found.
 */
function buildCheckSummary(aiAnalysis = {}, evidenceAnalysis = {}) {
    aiAnalysis = aiAnalysis || {};
    evidenceAnalysis = evidenceAnalysis || {};

    const patternScore = aiAnalysis.pattern_score ?? 0;
    const provenanceCount = aiAnalysis.provenance_flags_count || 0;
    const evidenceScore = evidenceAnalysis.evidence_score;
    const reliability = aiAnalysis.reliability || "standard";

    let verdict;
    let reasons = [];
    if (reliability === "insufficient") {
        verdict = "insufficient_text";
        reasons = [`Fewer than ${aiAnalysis.minimum_reliable_words || 120} words; signals are not reliable yet.`];
    } else {
        if (provenanceCount > 0) reasons.push(`${provenanceCount} AI-tool copy-paste artifact(s) found`);
        if (patternScore >= 65) reasons.push(`writing-pattern score is High (${patternScore}/100)`);
        if (evidenceScore != null && evidenceScore < 60) reasons.push(`evidence integrity is ${evidenceAnalysis.band || "low"} (${evidenceScore}/100)`);
        verdict = reasons.length ? "needs_review" : "clear";
    }

    const fixes = [];

    (aiAnalysis.provenance_flags || []).slice(0, 3).forEach(flag => {
        fixes.push({
            priority: "critical",
            kind: "provenance",
            message: `Remove ${flag.kind}: ${JSON.stringify(flag.text)} before submission.`
        });
    });

    for (const signal of (aiAnalysis.top_signals || [])) {
        if (fixes.length >= 3) break;
        fixes.push({
            priority: (signal.score || 0) >= 2 ? "high" : "moderate",
            kind: "writing_pattern",
            category: signal.label,
            message: signal.recommendation || "",
            evidence_count: signal.evidence_count || 0
        });
    }

    const unsupportedCount = evidenceAnalysis.unsupported_claims_count || 0;
    if (unsupportedCount && fixes.length < 3) {
        const examples = (evidenceAnalysis.claim_pairs || [])
            .filter(row => !row.has_citation)
            .slice(0, 3)
            .map(row => (row.sentence || "").slice(0, 160));
        fixes.push({
            priority: "high",
            kind: "citation",
            message: `${unsupportedCount} claim(s) need a citation.`,
            examples
        });
    }

    const summary = verdict === "insufficient_text"
        ? "Insufficient text for a reliable review."
        : verdict === "needs_review"
            ? "Needs review before submission."
            : "No high-confidence issues found in the signals this tool checks.";

    return {
        verdict,
        summary,
        pattern_score: patternScore,
        provenance_flags_count: provenanceCount,
        evidence_score: evidenceScore ?? null,
        reasons,
        top_fixes: fixes.slice(0, 3),
        disclaimer: "This combines existing pattern-score, provenance, and evidence-integrity signals into one verdict. It is not a plagiarism or AI-authorship determination; institutional review still governs."
    };
}

module.exports = { buildCheckSummary };
