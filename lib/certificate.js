/**
 * Advisory analysis-summary generator with a reproducibility hash.
 */

const crypto = require("crypto");

class CertificateGenerator {
    /**
     * Generates an advisory, unsigned summary of supplied analysis results.
     */
    static generate({
        studentName = "Academic Scholar",
        paperTitle = "Academic Manuscript",
        plagiarismScore = 0.0,
        aiScore = 0.0,
        wordCount = 0,
        safeassignRisk = "Low Risk",
        text = ""
    }) {
        const timestamp = new Date().toISOString();
        const hashInput = JSON.stringify({ studentName, paperTitle, plagiarismScore, aiScore, wordCount, text });
        const digest = crypto.createHash("sha256").update(hashInput).digest("hex");
        const certificateId = "ANALYSIS-" + digest.slice(0, 16).toUpperCase();

        const asciiBox = `
╔════════════════════════════════════════════════════════════════════════════════╗
║                    PRE-SUBMISSION ANALYSIS SUMMARY                             ║
║                         ScaleSynthAI Diagnostics                               ║
╠════════════════════════════════════════════════════════════════════════════════╣
║ Analysis ID:      ${certificateId.padEnd(59)}║
║ Issue Date:       ${timestamp.padEnd(59)}║
║ Student Name:     ${studentName.padEnd(59)}║
║ Manuscript:       ${paperTitle.padEnd(59)}║
╠════════════════════════════════════════════════════════════════════════════════╣
║ AUTOMATED SCREENING METRICS:                                                   ║
║   • Selected Similarity:            ${(plagiarismScore.toFixed(1) + "% (" + safeassignRisk + ")").padEnd(42)}║
║   • AI-Pattern Heuristic:           ${(aiScore.toFixed(1) + "%").padEnd(42)}║
║   • Manuscript Word Count:         ${(wordCount.toLocaleString() + " words").padEnd(42)}║
║   • Assessment Status:             ADVISORY ONLY; AUTHORSHIP NOT VERIFIED       ║
╠════════════════════════════════════════════════════════════════════════════════╣
║ ADVISORY DISCLAIMER:                                                          ║
║ This unsigned summary reports automated lexical and writing-pattern metrics.   ║
║ It does not certify originality, authorship, citation validity, or compliance. ║
╚════════════════════════════════════════════════════════════════════════════════╝
`;

        return {
            certificate_id: certificateId,
            student_name: studentName,
            paper_title: paperTitle,
            timestamp,
            plagiarism_score: plagiarismScore,
            ai_probability: aiScore,
            safeassign_risk: safeassignRisk,
            word_count: wordCount,
            sha256_hash: digest,
            disclaimer: "This unsigned summary reports automated lexical and writing-pattern metrics. It does not certify originality, authorship, citation validity, or institutional compliance.",
            ascii_certificate: asciiBox.trim()
        };
    }
}

module.exports = { CertificateGenerator };
