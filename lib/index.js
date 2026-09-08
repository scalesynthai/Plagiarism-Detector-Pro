const { PlagiarismChecker } = require("./checker");
const { AIDetector } = require("./ai_detector");
const { AcademicParaphraser } = require("./paraphraser");
const { AcademicStudentCoach } = require("./student_coach");
const { PhdResearchAuditor } = require("./phd_auditor");
const { TextSanitizer } = require("./sanitizer");
const { DocumentExtractor } = require("./extractor");
const { CitationGenerator } = require("./citation_generator");
const { DraftComparator } = require("./comparator");
const { CertificateGenerator } = require("./certificate");
const { BatchProcessor } = require("./batch_processor");
const { PlagiarismApiClient } = require("./api_client");

/**
 * High-level originality, AI detection, and academic analysis function (100% Offline Standalone).
 */
async function scan(textOrFilePath, options = {}) {
    let content = textOrFilePath;
    const isFile = typeof textOrFilePath === "string" && (
        textOrFilePath.endsWith(".txt") ||
        textOrFilePath.endsWith(".md") ||
        textOrFilePath.endsWith(".tex") ||
        textOrFilePath.endsWith(".ipynb") ||
        textOrFilePath.endsWith(".json")
    );

    if (isFile) {
        content = DocumentExtractor.extractFromFile(textOrFilePath);
    }

    if (options.server) {
        const client = new PlagiarismApiClient(options.server);
        return await client.scanText(content, options);
    }

    // 1. Sanitization & Homoglyph check
    const sanitization = TextSanitizer.sanitizeAndAudit(content);
    const cleanText = sanitization.clean_text;
    const readability = TextSanitizer.computeReadability(cleanText);

    // 2. SafeAssign Plagiarism Engine
    const checker = new PlagiarismChecker(options.sourcesDir);
    const originality = checker.analyze(cleanText, options);

    // 3. Statistical AI Engine
    const aiAnalysis = AIDetector.analyze(cleanText);

    // 4. Student Coach
    const unsupportedClaims = AcademicStudentCoach.scanUnsupportedClaims(cleanText);
    const toneSuggestions = AcademicStudentCoach.analyzeToneAndVocabulary(cleanText);
    const thesisEvaluation = AcademicStudentCoach.evaluateThesisAbstract(cleanText);

    // 5. PhD Conference & Anonymity Auditor
    const phdAudit = PhdResearchAuditor.auditManuscript(cleanText);

    return {
        ...originality,
        ai_analysis: aiAnalysis,
        readability: readability,
        obfuscation_info: sanitization,
        phd_audit: phdAudit,
        student_coach: {
            unsupported_claims: unsupportedClaims,
            unsupported_claims_count: unsupportedClaims.length,
            tone_suggestions: toneSuggestions,
            tone_suggestions_count: toneSuggestions.length,
            thesis_evaluation: thesisEvaluation
        }
    };
}

module.exports = {
    scan,
    PlagiarismChecker,
    AIDetector,
    AcademicParaphraser,
    AcademicStudentCoach,
    PhdResearchAuditor,
    TextSanitizer,
    DocumentExtractor,
    CitationGenerator,
    DraftComparator,
    CertificateGenerator,
    BatchProcessor,
    PlagiarismApiClient
};
