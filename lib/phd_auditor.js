/**
 * PhD & Conference Pre-Flight Auditor (Node.js Standalone Engine)
 * - Double-Blind Anonymity Compliance (NeurIPS, ICML, ICLR, IEEE)
 * - LaTeX & Math Environment Isolation
 * - Section Cadence & Structure Profiling
 */

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
                is_anonymity_compliant: true,
                anonymity_count: 0,
                anonymity_violations: [],
                conference_readiness_score: 100,
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

        // Count isolated LaTeX formulas
        const inlineMath = (text.match(/\$[^$]+\$/g) || []).length;
        const blockMath = (text.match(/\\begin\{equation\}[\s\S]*?\\end\{equation\}|\$\$[\s\S]*?\$\$/g) || []).length;
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
            anonymity_violations: violations,
            conference_readiness_score: readinessScore,
            latex_equations_isolated: totalLatex,
            sections_breakdown: sectionsBreakdown
        };
    }
}

module.exports = { PhdResearchAuditor };
