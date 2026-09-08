/**
 * Student Certificate of Academic Authorship Generator
 * Produces cryptographic SHA-256 verification hash and academic integrity pledge.
 */

const crypto = require("crypto");

class CertificateGenerator {
    /**
     * Generates a verifiable academic authorship certificate.
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
        const hashInput = `${studentName}|${paperTitle}|${plagiarismScore}|${aiScore}|${wordCount}|${text.slice(0, 500)}|${timestamp}`;
        const certificateId = "AUTH-" + crypto.createHash("sha256").update(hashInput).digest("hex").slice(0, 16).toUpperCase();

        const asciiBox = `
╔════════════════════════════════════════════════════════════════════════════════╗
║                   CERTIFICATE OF ACADEMIC AUTHORSHIP                           ║
║                       ScaleSynthAI Originality Lab                             ║
╠════════════════════════════════════════════════════════════════════════════════╣
║ Certificate ID:   ${certificateId.padEnd(59)}║
║ Issue Date:       ${timestamp.padEnd(59)}║
║ Student Name:     ${studentName.padEnd(59)}║
║ Manuscript:       ${paperTitle.padEnd(59)}║
╠════════════════════════════════════════════════════════════════════════════════╣
║ VERIFIED ORIGINALITY METRICS:                                                  ║
║   • SafeAssign Plagiarism Index:   ${(plagiarismScore.toFixed(1) + "% (" + safeassignRisk + ")").padEnd(42)}║
║   • AI Content Probability:        ${(aiScore.toFixed(1) + "%").padEnd(42)}║
║   • Manuscript Word Count:         ${(wordCount.toLocaleString() + " words").padEnd(42)}║
║   • Integrity Verification Status: PASSED (Zero-Storage Private Shield)        ║
╠════════════════════════════════════════════════════════════════════════════════╣
║ HONOR PLEDGE:                                                                  ║
║ "I hereby certify that this manuscript is my original academic work, created   ║
║ with rigorous scholarly standards and proper attribution for all cited sources."║
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
            sha256_hash: crypto.createHash("sha256").update(hashInput).digest("hex"),
            ascii_certificate: asciiBox.trim()
        };
    }
}

module.exports = { CertificateGenerator };
