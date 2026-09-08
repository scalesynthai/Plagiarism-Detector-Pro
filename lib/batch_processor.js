/**
 * Standalone Class Gradebook & Multi-File Batch Processor
 */

const fs = require("fs");
const path = require("path");
const { PlagiarismChecker } = require("./checker");
const { AIDetector } = require("./ai_detector");
const { DocumentExtractor } = require("./extractor");

class BatchProcessor {
    /**
     * Processes multiple files or directory paths and generates a consolidated gradebook.
     * @param {string[]|string} targetPaths 
     */
    static processBatch(targetPaths) {
        let fileList = [];
        const targets = Array.isArray(targetPaths) ? targetPaths : [targetPaths];

        targets.forEach(target => {
            if (fs.existsSync(target)) {
                const stat = fs.statSync(target);
                if (stat.isDirectory()) {
                    const files = fs.readdirSync(target);
                    files.forEach(f => {
                        const full = path.join(target, f);
                        if (fs.statSync(full).isFile() && !f.startsWith(".")) {
                            fileList.push(full);
                        }
                    });
                } else {
                    fileList.push(target);
                }
            }
        });

        if (fileList.length === 0) {
            return {
                total_submissions: 0,
                average_plagiarism: 0.0,
                average_ai_probability: 0.0,
                high_risk_count: 0,
                gradebook: []
            };
        }

        const checker = new PlagiarismChecker();
        const gradebook = [];
        let totalPlag = 0;
        let totalAi = 0;
        let highRiskCount = 0;

        fileList.forEach(filePath => {
            try {
                const text = DocumentExtractor.extractFromFile(filePath);
                const plagRes = checker.analyze(text);
                const aiRes = AIDetector.analyze(text);

                totalPlag += plagRes.overall_similarity;
                totalAi += aiRes.ai_probability;

                if (plagRes.safeassign_risk === "High Risk" || aiRes.ai_probability >= 65) {
                    highRiskCount++;
                }

                gradebook.push({
                    file_path: filePath,
                    student_or_filename: path.basename(filePath),
                    word_count: plagRes.total_words,
                    plagiarism_score: plagRes.overall_similarity,
                    ai_probability: aiRes.ai_probability,
                    safeassign_risk: plagRes.safeassign_risk,
                    ai_risk_level: aiRes.ai_risk_level
                });
            } catch (err) {
                gradebook.push({
                    file_path: filePath,
                    student_or_filename: path.basename(filePath),
                    error: err.message,
                    safeassign_risk: "Error"
                });
            }
        });

        const totalSubs = gradebook.length;

        return {
            total_submissions: totalSubs,
            average_plagiarism: parseFloat((totalPlag / Math.max(1, totalSubs)).toFixed(1)),
            average_ai_probability: parseFloat((totalAi / Math.max(1, totalSubs)).toFixed(1)),
            high_risk_count: highRiskCount,
            gradebook
        };
    }
}

module.exports = { BatchProcessor };
