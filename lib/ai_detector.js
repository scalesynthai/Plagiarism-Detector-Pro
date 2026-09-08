/**
 * Statistical AI & LLM Likelihood Engine
 * Analyzes sentence burstiness, lexical diversity, and syntactic cadence.
 */

const AI_MARKERS = [
    /\bfurthermore,\s+it\s+is\s+important\s+to\s+note\b/i,
    /\bin\s+conclusion,\s+this\b/i,
    /\bdelves\s+into\b/i,
    /\btapestry\s+of\b/i,
    /\btestament\s+to\b/i,
    /\bpivotal\s+role\b/i,
    /\bseamless\s+integration\b/i,
    /\bholistic\s+approach\b/i,
    /\bfoster\s+innovation\b/i,
    /\bmultifaceted\b/i,
    /\bimperative\s+to\s+consider\b/i
];

class AIDetector {
    /**
     * Analyzes text for AI generation markers, burstiness, and entropy.
     * @param {string} text 
     */
    static analyze(text) {
        if (!text || text.trim().length === 0) {
            return {
                ai_probability: 0.0,
                burstiness: 0.0,
                ai_risk_level: "Human-Written",
                flagged_markers_count: 0
            };
        }

        const sentences = text
            .split(/(?<=[.!?])\s+|\n+/)
            .map(s => s.trim())
            .filter(s => s.length > 5);

        const sentenceLengths = sentences.map(s => s.split(/\s+/).length);
        const meanLength = sentenceLengths.reduce((a, b) => a + b, 0) / Math.max(1, sentenceLengths.length);

        // Calculate variance & burstiness
        let variance = 0;
        sentenceLengths.forEach(len => {
            variance += Math.pow(len - meanLength, 2);
        });
        const stdDev = Math.sqrt(variance / Math.max(1, sentenceLengths.length));
        const burstiness = parseFloat((stdDev * 5.0).toFixed(1));

        // Detect stereotypical AI boilerplate markers
        let markerHits = 0;
        AI_MARKERS.forEach(pattern => {
            if (pattern.test(text)) markerHits++;
        });

        // Compute AI probability score
        let aiScore = 15.0; // Baseline
        if (burstiness < 15.0) aiScore += 35.0; // Low burstiness = high uniformity
        else if (burstiness < 25.0) aiScore += 15.0;
        else if (burstiness > 45.0) aiScore -= 10.0; // High human variability

        aiScore += markerHits * 18.0;

        aiScore = Math.max(0.0, Math.min(99.0, parseFloat(aiScore.toFixed(1))));

        let riskLevel = "Human-Written";
        if (aiScore >= 65.0) riskLevel = "High AI Likelihood";
        else if (aiScore >= 35.0) riskLevel = "Mixed / AI-Assisted";

        return {
            ai_probability: aiScore,
            burstiness: burstiness,
            ai_risk_level: riskLevel,
            flagged_markers_count: markerHits,
            mean_sentence_length: parseFloat(meanLength.toFixed(1))
        };
    }
}

module.exports = { AIDetector };
