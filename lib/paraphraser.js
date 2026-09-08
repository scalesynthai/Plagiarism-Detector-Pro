/**
 * Academic Paraphraser & Synthesis Engine
 * Provides 1-click academic restructuring and formal attribution formulations.
 */

const TRANSITIONS = [
    "Specifically, empirical investigations indicate that",
    "Notably, prior research demonstrates that",
    "Furthermore, contemporary findings substantiate that",
    "In this context, domain literature reveals that",
    "As rigorously observed in experimental trials,"
];

const VERBS = [
    [/\bdemonstrates\b/gi, "establishes"],
    [/\bshows\b/gi, "substantiates"],
    [/\bproves\b/gi, "validates"],
    [/\banalyzes\b/gi, "evaluates"],
    [/\bpredicts\b/gi, "estimates"],
    [/\bexplains\b/gi, "elucidates"],
    [/\buses\b/gi, "utilizes"],
    [/\bfinds\b/gi, "uncovers"],
    [/\bhelps\b/gi, "facilitates"]
];

class AcademicParaphraser {
    /**
     * Synthesizes and paraphrases an overlapping sentence into 3 distinct academic options.
     * @param {string} sentence 
     * @param {string} [sourceName] 
     * @param {string} [sourceTitle] 
     */
    static synthesizeSentence(sentence, sourceName = null, sourceTitle = null) {
        const cleanS = (sentence || "").trim().replace(/[.!?]+$/, "");
        if (!cleanS) {
            return { original_sentence: "", suggestions: [] };
        }

        const words = cleanS.split(/\s+/);
        const citeKey = (sourceTitle || sourceName || "Cited Publication").replace(/\.[^/.]+$/, "");
        const transition = TRANSITIONS[Math.abs(cleanS.length) % TRANSITIONS.length];

        let restructuredV1 = cleanS;
        for (const [pattern, replacement] of VERBS) {
            if (pattern.test(restructuredV1)) {
                restructuredV1 = restructuredV1.replace(pattern, replacement);
                break;
            }
        }

        // 1. Active Inversion with Direct Attribution
        const opt1 = `According to ${citeKey}, ${restructuredV1.charAt(0).toLowerCase() + restructuredV1.slice(1)}.`;

        // 2. Passive Methodological Synthesis
        const opt2 = `${transition} ${cleanS.charAt(0).toLowerCase() + cleanS.slice(1)} (${citeKey}, 2024).`;

        // 3. High-Density Conceptual Restructuring
        let opt3 = "";
        if (words.length > 7) {
            const splitIdx = Math.floor(words.length / 2);
            const firstHalf = words.slice(0, splitIdx).join(" ");
            const secondHalf = words.slice(splitIdx).join(" ");
            opt3 = `Regarding ${secondHalf.toLowerCase()}, ${firstHalf.charAt(0).toLowerCase() + firstHalf.slice(1)} as established in recent literature [${citeKey}].`;
        } else {
            opt3 = `Evidence presented in ${citeKey} reinforces that ${cleanS.toLowerCase()}.`;
        }

        return {
            original_sentence: sentence,
            source_attribution: citeKey,
            suggestions: [
                {
                    style: "Active Attribution (APA/MLA)",
                    text: opt1,
                    description: "Explicit attribution clause framing the author's primary assertion."
                },
                {
                    style: "Methodological Synthesis (Scholarly Formal)",
                    text: opt2,
                    description: "Passive voice synthesis contextualizing findings into academic consensus."
                },
                {
                    style: "Conceptual Restructuring (High-Density)",
                    text: opt3,
                    description: "Inverted focus prioritizing empirical implications over source phrasing."
                }
            ]
        };
    }
}

module.exports = { AcademicParaphraser };
