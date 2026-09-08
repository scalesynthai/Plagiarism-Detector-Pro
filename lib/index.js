const { PlagiarismChecker } = require("./checker");
const { AIDetector } = require("./ai_detector");
const { AcademicParaphraser } = require("./paraphraser");
const { AcademicStudentCoach } = require("./student_coach");
const { DocumentExtractor } = require("./extractor");
const { CitationGenerator } = require("./citation_generator");
const { DraftComparator } = require("./comparator");
const { PlagiarismApiClient } = require("./api_client");

/**
 * High-level originality and academic analysis function.
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

    const checker = new PlagiarismChecker(options.sourcesDir);
    const originality = checker.analyze(content, options);
    const aiAnalysis = AIDetector.analyze(content);
    const unsupportedClaims = AcademicStudentCoach.scanUnsupportedClaims(content);
    const toneSuggestions = AcademicStudentCoach.analyzeToneAndVocabulary(content);
    const thesisEvaluation = AcademicStudentCoach.evaluateThesisAbstract(content);

    return {
        ...originality,
        ai_analysis: aiAnalysis,
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
    DocumentExtractor,
    CitationGenerator,
    DraftComparator,
    PlagiarismApiClient
};
