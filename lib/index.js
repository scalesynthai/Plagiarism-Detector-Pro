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
const { EvidenceAnalyzer } = require("./evidence_analyzer");
const { WritingStyleReviewer } = require("./style_review");
const { WritingCleanup } = require("./writing_cleanup");
const { buildCheckSummary } = require("./check_summary");

/**
 * High-level lexical-overlap and academic-diagnostics function (100% offline standalone).
 */
async function scan(textOrFilePath, options = {}) {
    if (typeof textOrFilePath !== "string" || !textOrFilePath.trim()) {
        throw new TypeError("Text or a document path is required.");
    }
    let content = textOrFilePath;
    const isFile = require("fs").existsSync(textOrFilePath);

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

    // 2. Text-similarity engine
    const checker = new PlagiarismChecker(options.sourcesDir);
    const originality = checker.analyze(cleanText, options);

    // 3. Pair empirical claims with recognized citations.
    const claims = AcademicStudentCoach.scanClaims(cleanText);
    const unsupportedClaims = claims.filter(claim => !claim.has_citation);

    // 4. Explainable writing-pattern review
    const aiAnalysis = AIDetector.analyze(cleanText, { unsupported_claims: unsupportedClaims });
    const styleReview = WritingStyleReviewer.analyze(cleanText, { profile: options.styleProfile || 'academic_report' });

    // 5. Student Coach
    const toneSuggestions = AcademicStudentCoach.analyzeToneAndVocabulary(cleanText);
    const thesisEvaluation = AcademicStudentCoach.evaluateThesisAbstract(cleanText);

    // 6. Structural evidence profile
    const citationCount = require('./diagnostics').citations(cleanText).length;
    const evidenceAnalysis = EvidenceAnalyzer.analyze(
        claims,
        { in_text_citations_count: citationCount },
        originality.sources_breakdown || []
    );

    // 7. PhD Conference & Anonymity Auditor
    const phdAudit = PhdResearchAuditor.auditManuscript(cleanText);

    return {
        ...originality,
        ai_analysis: aiAnalysis,
        style_review: styleReview,
        evidence_analysis: evidenceAnalysis,
        check_summary: buildCheckSummary(aiAnalysis, evidenceAnalysis),
        readability: readability,
        obfuscation_info: sanitization,
        phd_audit: phdAudit,
        student_coach: {
            unsupported_claims: unsupportedClaims,
            unsupported_claims_count: unsupportedClaims.length,
            claims,
            claims_count: claims.length,
            cited_claims_count: claims.filter(claim => claim.has_citation).length,
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
    PlagiarismApiClient,
    EvidenceAnalyzer,
    WritingStyleReviewer,
    WritingCleanup,
    buildCheckSummary
};
