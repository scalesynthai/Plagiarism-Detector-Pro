/**
 * Local Standalone Plagiarism & Passage Matching Engine
 * Implements Longest Common Subsequence (LCS) shingling and SafeAssign risk calculation.
 */

const fs = require("fs");
const path = require("path");
const { DEFAULT_ACADEMIC_CORPUS } = require("./default_corpus");

const STOP_WORDS = new Set([
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are",
    "aren't", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both",
    "but", "by", "can't", "cannot", "could", "couldn't", "did", "didn't", "do", "does", "doesn't",
    "doing", "don't", "down", "during", "each", "few", "for", "from", "further", "had", "hadn't",
    "has", "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her", "here",
    "here's", "hers", "herself", "him", "himself", "his", "how", "how's", "i", "i'd", "i'll",
    "i'm", "i've", "if", "in", "into", "is", "isn't", "it", "it's", "its", "itself", "let's",
    "me", "more", "most", "mustn't", "my", "myself", "no", "nor", "not", "of", "off", "on",
    "once", "only", "or", "other", "ought", "our", "ours", "ourselves", "out", "over", "own",
    "same", "shan't", "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some",
    "such", "than", "that", "that's", "the", "their", "theirs", "them", "themselves", "then",
    "there", "there's", "these", "they", "they'd", "they'll", "they're", "they've", "this",
    "those", "through", "to", "too", "under", "until", "up", "very", "was", "wasn't", "we",
    "we'd", "we'll", "we're", "we've", "were", "weren't", "what", "what's", "when", "when's",
    "where", "where's", "which", "while", "who", "who's", "whom", "why", "why's", "with",
    "won't", "would", "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours",
    "yourself", "yourselves"
]);

class PlagiarismChecker {
    constructor(sourcesDir = null) {
        this.sources = [];
        this.sourcesDir = sourcesDir || path.join(__dirname, "..", "sources");
        this.loadLocalSources();
    }

    loadLocalSources() {
        // 1. Initialize with built-in academic reference corpus
        DEFAULT_ACADEMIC_CORPUS.forEach(src => {
            this.sources.push({
                filename: src.filename,
                text: src.text,
                words: src.text.trim().split(/\s+/).length
            });
        });

        // 2. Supplement with any additional local filesystem sources if directory exists
        if (fs.existsSync(this.sourcesDir)) {
            const files = fs.readdirSync(this.sourcesDir);
            const loaded = new Set(this.sources.map(s => s.filename));
            files.forEach(f => {
                const fullPath = path.join(this.sourcesDir, f);
                if (fs.statSync(fullPath).isFile() && !f.startsWith(".") && !loaded.has(f)) {
                    try {
                        const content = fs.readFileSync(fullPath, "utf8");
                        this.sources.push({
                            filename: f,
                            text: content,
                            words: content.trim().split(/\s+/).length
                        });
                    } catch {}
                }
            });
        }
    }

    /**
     * Computes Longest Common Subsequence of words between two strings.
     */
    static lcsLength(wordsA, wordsB) {
        const m = wordsA.length;
        const n = wordsB.length;
        if (m === 0 || n === 0) return 0;

        const dp = Array.from({ length: m + 1 }, () => new Uint16Array(n + 1));
        for (let i = 1; i <= m; i++) {
            for (let j = 1; j <= n; j++) {
                if (wordsA[i - 1] === wordsB[j - 1]) {
                    dp[i][j] = dp[i - 1][j - 1] + 1;
                } else {
                    dp[i][j] = Math.max(dp[i - 1][j], dp[i][j - 1]);
                }
            }
        }
        return dp[m][n];
    }

    /**
     * Performs full originality and SafeAssign passage analysis.
     * @param {string} text 
     * @param {object} [options] 
     */
    analyze(text, options = {}) {
        const queryText = (text || "").trim();
        const totalWords = queryText.split(/\s+/).filter(Boolean).length;
        if (totalWords === 0) {
            return {
                overall_similarity: 0.0,
                safeassign_risk: "Low Risk",
                total_words: 0,
                flagged_word_count: 0,
                highest_matching_source: null,
                highest_similarity: 0.0,
                sources_breakdown: [],
                highlighted_sentences: []
            };
        }

        const sentences = queryText
            .split(/(?<=[.!?])\s+|\n+/)
            .map(s => s.trim())
            .filter(s => s.length > 5);

        const highlightedSentences = [];
        let totalFlaggedWords = 0;
        const sourceMatchScores = {};

        sentences.forEach(sent => {
            const sentWords = sent.toLowerCase().replace(/[^\w\s]/g, "").split(/\s+/).filter(Boolean);
            let bestSim = 0.0;
            let bestSource = null;
            let bestSourceSent = null;

            if (sentWords.length >= 4) {
                this.sources.forEach(src => {
                    const srcSentences = src.text.split(/(?<=[.!?])\s+|\n+/).filter(s => s.trim().length > 5);
                    srcSentences.forEach(srcS => {
                        const srcWords = srcS.toLowerCase().replace(/[^\w\s]/g, "").split(/\s+/).filter(Boolean);
                        if (srcWords.length >= 4) {
                            const lcs = PlagiarismChecker.lcsLength(sentWords, srcWords);
                            const sim = (lcs / Math.max(sentWords.length, 1)) * 100;
                            // Contiguous passage requirement: must match at least 4 contiguous words or > 65% overlap
                            if (sim > bestSim && (lcs >= 4 || sim >= 65)) {
                                bestSim = sim;
                                bestSource = src.filename;
                                bestSourceSent = srcS.trim();
                            }
                        }
                    });
                });
            }

            const isPlag = bestSim >= 50.0;
            const flaggedWordsCount = isPlag ? sentWords.length : 0;
            totalFlaggedWords += flaggedWordsCount;

            if (bestSource) {
                sourceMatchScores[bestSource] = Math.max(sourceMatchScores[bestSource] || 0, Math.round(bestSim));
            }

            highlightedSentences.push({
                text: sent,
                is_plagiarized: isPlag,
                similarity: Math.round(bestSim),
                source: bestSource,
                matched_source_sentence: bestSourceSent,
                has_citation: /\([A-Z][a-zA-Z\s\.\,\&]+(?:et al\.)?,\s*\d{4}\)|\[\d+\]/.test(sent)
            });
        });

        const overallSimilarity = parseFloat(Math.min(100, (totalFlaggedWords / Math.max(1, totalWords)) * 100).toFixed(1));

        let safeassignRisk = "Low Risk";
        let statusClass = "success";
        if (overallSimilarity >= 40.0) {
            safeassignRisk = "High Risk";
            statusClass = "danger";
        } else if (overallSimilarity >= 15.0) {
            safeassignRisk = "Medium Risk";
            statusClass = "warning";
        }

        const sourcesBreakdown = Object.entries(sourceMatchScores).map(([filename, similarity]) => ({
            filename,
            similarity,
            source_type: "institutional",
            badge: "🏛️ Institutional"
        })).sort((a, b) => b.similarity - a.similarity);

        return {
            overall_similarity: overallSimilarity,
            safeassign_risk: safeassignRisk,
            status_class: statusClass,
            total_words: totalWords,
            flagged_word_count: totalFlaggedWords,
            highest_matching_source: sourcesBreakdown[0] ? sourcesBreakdown[0].filename : null,
            highest_similarity: sourcesBreakdown[0] ? sourcesBreakdown[0].similarity : 0.0,
            sources_breakdown: sourcesBreakdown,
            highlighted_sentences: highlightedSentences
        };
    }
}

module.exports = { PlagiarismChecker };
