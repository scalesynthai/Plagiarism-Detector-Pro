/**
 * PhD & Conference Pre-Flight Auditor (Node.js Standalone Engine)
 * - Double-Blind Anonymity Compliance (NeurIPS, ICML, ICLR, IEEE)
 * - LaTeX & Math Environment Isolation
 * - Section Cadence & Structure Profiling
 */

/** Counts $...$ spans (non-empty, no inner $) in linear time. */
function countInlineMath(text) {
    let count = 0, pos = 0;
    for (;;) {
        const start = text.indexOf("$", pos);
        if (start === -1) break;
        const end = text.indexOf("$", start + 1);
        if (end === -1) break;
        if (end > start + 1) { count++; pos = end + 1; } else pos = start + 1;
    }
    return count;
}

/** Counts \\begin{equation}...\\end{equation} and $$...$$ spans (leftmost-first) in linear time. */
function countBlockMath(text) {
    const kinds = [{ open: "\\begin{equation}", close: "\\end{equation}", live: true }, { open: "$$", close: "$$", live: true }];
    let count = 0, pos = 0;
    for (;;) {
        let best = null, bestAt = -1;
        for (const kind of kinds) {
            if (!kind.live) continue;
            const at = text.indexOf(kind.open, pos);
            if (at === -1) { kind.live = false; continue; }
            if (best === null || at < bestAt) { best = kind; bestAt = at; }
        }
        if (best === null) break;
        const end = text.indexOf(best.close, bestAt + best.open.length);
        if (end === -1) { best.live = false; continue; }
        count++;
        pos = end + best.close.length;
    }
    return count;
}

const ANONYMITY_PATTERNS = [
    /\b(?:in\s+our\s+previous\s+work|in\s+our\s+prior\s+study|our\s+earlier\s+paper)\s*\[?\d*\]?/gi,
    /\b(?:we\s+previously\s+demonstrated|we\s+have\s+previously\s+shown)\b/gi,
    /\b(?:https?:\/\/github\.com\/[a-zA-Z0-9_\-\.]+)/gi,
    /\b(?:acknowledgments|acknowledgements)\b[\s\S]{0,300}\b(?:funded\s+by|grant\s+number|supported\s+by)\b/gi
];

class PhdResearchAuditor {
    /**
     * Audits text for conference readiness, double-blind compliance, and structural cadence.
     * @param {string} text 
     */
    static auditManuscript(text) {
        if (!text) {
            return {
                is_anonymity_compliant: null,
                anonymity_status: "insufficient_text",
                anonymity_count: 0,
                anonymity_violations: [],
                conference_readiness_score: 0,
                latex_equations_isolated: 0,
                sections_breakdown: []
            };
        }

        const violations = [];
        ANONYMITY_PATTERNS.forEach(pattern => {
            const matches = text.match(pattern);
            if (matches) {
                matches.forEach(m => {
                    if (m.startsWith("http") && (m.includes("anonymous") || m.includes("blind"))) return;
                    violations.push(`Potential unblinded reference detected: "${m.trim().slice(0, 60)}"`);
                });
            }
        });

        const front = require('./diagnostics').frontMatter(text);
        const frontPatterns = [
            /\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b/g,
            /\b(?:Department of|University of|School of|College of|Institute of)\b[^\n.!?]{0,120}/g,
            /^[ \t]*(?:By\s+|Author:\s*)[A-Z][a-z]+(?:[ \t]+[A-Z][a-z]+){1,3}\s*$/gm,
        ];
        for (const pattern of frontPatterns) {
            for (const match of front.matchAll(pattern)) violations.push(`Possible identifying front matter: ${match[0]}`);
        }

        // Count isolated LaTeX formulas
        const inlineMath = countInlineMath(text);
        const blockMath = countBlockMath(text);
        const totalLatex = inlineMath + blockMath;

        // Sections analysis
        const paragraphs = text.split(/\n\s*\n/).filter(p => p.trim().length > 30);
        const sectionsBreakdown = paragraphs.slice(0, 6).map((p, idx) => {
            const words = p.trim().split(/\s+/).length;
            const sents = p.split(/(?<=[.!?])\s+/).length || 1;
            const avgLen = parseFloat((words / sents).toFixed(1));
            let cadence = "Balanced Scholarly";
            if (avgLen > 28) cadence = "High-Density Academic";
            else if (avgLen < 14) cadence = "Concise Empirical";

            const headingMatch = p.match(/^(?:#+\s*|[0-9]+\.\s+)?([A-Z][a-zA-Z\s]{2,30})/);
            const heading = headingMatch ? headingMatch[1].trim() : `Section ${idx + 1}`;

            return {
                heading,
                word_count: words,
                avg_sentence_len: avgLen,
                cadence_profile: cadence
            };
        });

        const isCompliant = violations.length === 0;
        let readinessScore = 100;
        if (!isCompliant) readinessScore -= Math.min(40, violations.length * 15);

        return {
            is_anonymity_compliant: isCompliant,
            anonymity_count: violations.length,
            anonymity_status: violations.length ? "potential_identifiers_found" : "no_identifiers_detected",
            assessment_scope: "Pattern-based screening; does not certify anonymity or conference readiness.",
            anonymity_violations: violations,
            conference_readiness_score: readinessScore,
            latex_equations_isolated: totalLatex,
            sections_breakdown: sectionsBreakdown
        };
    }
}

module.exports = { PhdResearchAuditor };
