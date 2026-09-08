/**
 * Student Academic Writing & Integrity Coach
 * - Unsupported Claim Scanner & Citation Finder
 * - Scholarly Tone & Formal Vocabulary Booster
 * - Reference List Alphabetizer & Formatter
 * - Thesis Statement & Abstract Strength Evaluator
 */

const INFORMAL_TERMS = {
    "a lot of": ["a substantial proportion of", "numerous", "an extensive quantity of"],
    "basically": ["fundamentally", "primarily", "essentially"],
    "get rid of": ["eliminate", "mitigate", "eradicate"],
    "big impact": ["significant effect", "substantial influence", "pronounced outcome"],
    "good results": ["statistically significant outcomes", "favorable empirical metrics", "robust performance"],
    "talk about": ["discuss", "examine", "articulate", "analyze"],
    "shows clearly": ["substantiates", "empirically illustrates", "demonstrates"],
    "really important": ["paramount", "critical", "pivotal", "of foundational importance"],
    "things": ["factors", "variables", "phenomena", "elements", "mechanisms"],
    "kind of": ["moderately", "partially", "to a certain degree"],
    "sort of": ["qualitatively similar to", "resembling"],
    "a bunch of": ["a cluster of", "an array of", "a multiplicity of"],
    "cannot be denied": ["evidence indicates", "literature demonstrates"],
    "everyone knows": ["it is widely recognized in scholarly consensus that"],
    "deal with": ["address", "manage", "intervene upon"],
    "find out": ["ascertain", "determine", "uncover"],
    "make sure": ["ensure", "verify", "ascertain"],
    "looked at": ["investigated", "evaluated", "scrutinized"]
};

const CLAIM_MARKERS = [
    /\b(?:studies|research|scholars|scientists|experts|investigators|literature)\s+(?:show|shows|prove|proves|suggest|suggests|state|states|found|demonstrate|demonstrates)\b/i,
    /\b(?:it is (?:proven|established|known|evident|widely accepted|acknowledged))\b/i,
    /\b(?:\d+%\s+of|\d+\s+percent\s+of)\b/i,
    /\b(?:according to recent (?:findings|reports|data|surveys))\b/i,
    /\b(?:has been shown to (?:cause|reduce|increase|improve|lead to))\b/i
];

const CITATION_REGEX = /\((?:[A-Z][a-zA-Z\s\.\,\&]+(?:et al\.)?,\s*\d{4}[a-z]?(?:;\s*[A-Z][a-zA-Z\s\.\,\&]+(?:et al\.)?,\s*\d{4}[a-z]?)*|\d{4})\)|\[\d+\]/;

class AcademicStudentCoach {
    /**
     * Flags empirical or statistical assertions lacking parenthetical or numeric citations.
     * @param {string} text 
     * @returns {Array<{sentence: string, claim_marker: string, recommendation: string}>}
     */
    static scanUnsupportedClaims(text) {
        if (!text) return [];
        const sentences = text
            .split(/(?<=[.!?])\s+|\n+/)
            .map(s => s.trim())
            .filter(s => s.length > 20);

        const unsupported = [];

        for (const s of sentences) {
            const hasCite = CITATION_REGEX.test(s);
            if (hasCite) continue;

            for (const marker of CLAIM_MARKERS) {
                const match = s.match(marker);
                if (match) {
                    unsupported.append ? null : unsupported.push({
                        sentence: s,
                        claim_marker: match[0],
                        recommendation: `Sentence contains empirical assertion ('${match[0]}') without a cited authority. Insert (Author, Year) or numeric reference.`
                    });
                    break;
                }
            }
        }

        return unsupported;
    }

    /**
     * Identifies conversational words and suggests scholarly alternatives.
     * @param {string} text 
     */
    static analyzeToneAndVocabulary(text) {
        if (!text) return [];
        const suggestions = [];

        for (const [phrase, replacements] of Object.entries(INFORMAL_TERMS)) {
            const regex = new RegExp(`\\b${phrase}\\b`, "gi");
            let match;
            while ((match = regex.exec(text)) !== null) {
                const start = Math.max(0, match.index - 25);
                const end = Math.min(text.length, match.index + match[0].length + 25);
                const snippet = "..." + text.slice(start, end).replace(/\n/g, " ") + "...";

                suggestions.push({
                    matched_term: match[0],
                    context_snippet: snippet,
                    scholarly_replacements: replacements,
                    tip: `Replace conversational phrase '${match[0]}' with scholarly formal vocabulary.`
                });
            }
        }

        return suggestions.slice(0, 15);
    }

    /**
     * Sorts bibliography entries alphabetically by primary author last name,
     * validates year formatting, and identifies missing DOIs.
     * @param {string} referencesText 
     */
    static alphabetizeAndFormatReferences(referencesText) {
        if (!referencesText) {
            return { sorted_references: [], count: 0, issues: [] };
        }

        const lines = referencesText
            .split("\n")
            .map(l => l.trim())
            .filter(l => l.length > 10);

        if (lines.length === 0) {
            return { sorted_references: [], count: 0, issues: [] };
        }

        const parsedEntries = [];
        const issues = [];

        lines.forEach((line, idx) => {
            const cleanLine = line.replace(/^(\[\d+\]|\d+[\.\)]\s*)/, "").trim();
            const authorMatch = cleanLine.match(/^([A-Z][a-zA-Z\-\'\`]+)/);
            const sortKey = authorMatch ? authorMatch[1].toLowerCase() : cleanLine.toLowerCase();

            const hasYear = /\b(19\d\d|20\d\d)\b/.test(cleanLine);
            if (!hasYear) {
                issues.push(`Entry #${idx + 1} ('${cleanLine.slice(0, 40)}...'): Missing publication year.`);
            }

            const hasDoi = /(10\.\d{4,9}\/|doi\.org|http)/i.test(cleanLine);

            parsedEntries.push({
                original: line,
                cleaned: cleanLine,
                sortKey,
                hasYear,
                hasDoi
            });
        });

        parsedEntries.sort((a, b) => a.sortKey.localeCompare(b.sortKey));
        const sortedRefs = parsedEntries.map(e => e.cleaned);

        return {
            sorted_references: sortedRefs,
            count: sortedRefs.length,
            formatted_text: sortedRefs.join("\n\n"),
            issues
        };
    }

    /**
     * Evaluates opening abstract/thesis for scientific completeness.
     * @param {string} text 
     */
    static evaluateThesisAbstract(text) {
        if (!text) {
            return { score: 0, word_count: 0, has_hypothesis: false, has_method: false, has_significance: false, feedback: ["No text provided."] };
        }

        const firstPara = text.includes("\n\n") ? text.split("\n\n")[0] : text.slice(0, 1000);
        const words = firstPara.trim().split(/\s+/);
        const wordCount = words.length;

        const hasHypothesis = /\b(hypothesize|argue|propose|demonstrate|investigate|examine|aims to|objective)\b/i.test(firstPara);
        const hasMethod = /\b(using|method|methodology|dataset|experiment|analyzed|evaluated|simulation|framework)\b/i.test(firstPara);
        const hasSignificance = /\b(crucial|significance|implication|contributes|advance|fundamental|impact)\b/i.test(firstPara);

        let score = 40;
        if (hasHypothesis) score += 25;
        if (hasMethod) score += 20;
        if (hasSignificance) score += 15;

        const feedback = [];
        if (!hasHypothesis) {
            feedback.push("State your central thesis, hypothesis, or research question explicitly.");
        }
        if (!hasMethod) {
            feedback.push("Specify the analytical methodology, empirical dataset, or experimental approach used.");
        }
        if (!hasSignificance) {
            feedback.push("Highlight the broader academic significance or practical implications of your findings.");
        }

        return {
            score: Math.min(100, score),
            word_count: wordCount,
            has_hypothesis: hasHypothesis,
            has_method: hasMethod,
            has_significance: hasSignificance,
            feedback: feedback.length > 0 ? feedback : ["Opening paragraph possesses clear thesis framing and methodology context."]
        };
    }
}

module.exports = { AcademicStudentCoach };
