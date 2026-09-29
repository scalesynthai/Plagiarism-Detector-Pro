export interface PlagiarismResult {
    overall_similarity: number;
    raw_similarity: number;
    body_similarity: number;
    bibliography_similarity: number;
    quotation_similarity: number;
    scored_word_count: number;
    excluded_word_count: number;
    normalized_text: string;
    matched_spans: Array<{start: number; end: number; token_start: number; token_end: number; source_name: string; matched_text: string}>;
    scoring: {method: string; minimum_match_words: number; exclude_quotes: boolean; exclude_bibliography: boolean; citations_excluded: boolean; source_percentages_overlap: boolean; offset_unit: string; limitations: string};
    safeassign_risk: "Low Risk" | "Medium Risk" | "High Risk";
    status_class: string;
    total_words: number;
    flagged_word_count: number;
    highest_matching_source?: string | null;
    highest_similarity: number;
    sources_breakdown: Array<{
        filename: string;
        similarity: number;
        source_type: string;
        badge: string;
    }>;
    highlighted_sentences: Array<{
        text: string;
        is_plagiarized: boolean;
        similarity: number;
        source?: string | null;
        matched_source_sentence?: string | null;
        has_citation: boolean;
    }>;
    ai_analysis?: {
        pattern_score: number;
        ai_probability: number;
        burstiness: number;
        ai_risk_level: string;
        flagged_markers_count: number;
        reliability: "insufficient" | "limited" | "standard";
        pattern_version: string;
        categories: WritingPatternCategory[];
        top_signals: Array<{id: string; label: string; score: number; evidence_count: number; recommendation: string}>;
        style_metrics: WritingStyleMetrics;
        provenance_flags: Array<{text: string; start: number; end: number; kind: string}>;
        provenance_flags_count: number;
        provenance_note: string;
    };
    evidence_analysis?: EvidenceAnalysis;
    check_summary?: CheckSummary;
    student_coach?: {
        unsupported_claims: Array<{
            sentence: string;
            claim_marker: string;
            recommendation: string;
        }>;
        unsupported_claims_count: number;
        tone_suggestions: Array<{
            matched_term: string;
            context_snippet: string;
            scholarly_replacements: string[];
            tip: string;
        }>;
        tone_suggestions_count: number;
        thesis_evaluation: {
            score: number;
            word_count: number;
            has_hypothesis: boolean;
            has_method: boolean;
            has_significance: boolean;
            feedback: string[];
        };
    };
}

export function scan(textOrFilePath: string, options?: {
    server?: string;
    sourcesDir?: string;
    includeWeb?: boolean;
    excludeQuotes?: boolean;
    excludeBibliography?: boolean;
    privateDraft?: boolean;
}): Promise<PlagiarismResult>;

export class PlagiarismChecker {
    constructor(sourcesDir?: string);
    analyze(text: string, options?: any): PlagiarismResult;
}

export class AIDetector {
    static analyze(text: string, context?: {unsupported_claims?: Array<{sentence: string}>}): {
        pattern_score: number;
        ai_probability: number;
        burstiness: number;
        ai_risk_level: string;
        flagged_markers_count: number;
        reliability: "insufficient" | "limited" | "standard";
        categories: WritingPatternCategory[];
        style_metrics: WritingStyleMetrics;
        provenance_flags: Array<{text: string; start: number; end: number; kind: string}>;
        provenance_flags_count: number;
        provenance_note: string;
    };
}

export interface WritingPatternCategory {
    id: string;
    label: string;
    score: number;
    max_score: 3;
    evidence_count: number;
    evidence: Array<{text: string; start: number; end: number; kind: string; suggestion?: string | null}>;
    metrics: Record<string, unknown>;
    recommendation: string;
}

export interface WritingStyleMetrics {
    word_count: number;
    sentence_count: number;
    paragraph_count: number;
    em_dash_count: number;
    em_dashes_per_300_words: number;
    hedge_count: number;
    transition_count: number;
}

export interface EvidenceAnalysis {
    evidence_score: number | null;
    band: string;
    claim_count: number;
    cited_claims_count: number;
    unsupported_claims_count: number;
    claim_citation_coverage_pct: number | null;
    citation_count: number;
    citation_link_rate_pct: number | null;
    source_quality_score: number | null;
    limitation: string;
}

export class AcademicParaphraser {
    static synthesizeSentence(sentence: string, sourceName?: string, sourceTitle?: string): {
        original_sentence: string;
        source_attribution: string;
        suggestions: Array<{ style: string; text: string; description: string; }>;
    };
}

export class AcademicStudentCoach {
    static scanClaims(text: string): Array<{ sentence: string; claim_marker: string; has_citation: boolean; citation: string | null; start: number; end: number; recommendation: string; }>;
    static scanUnsupportedClaims(text: string): Array<{ sentence: string; claim_marker: string; recommendation: string; }>;
    static analyzeToneAndVocabulary(text: string): Array<{ matched_term: string; context_snippet: string; scholarly_replacements: string[]; tip: string; }>;
    static alphabetizeAndFormatReferences(referencesText: string): { sorted_references: string[]; count: number; formatted_text: string; issues: string[]; };
    static evaluateThesisAbstract(text: string): { score: number; word_count: number; has_hypothesis: boolean; has_method: boolean; has_significance: boolean; feedback: string[]; };
}

export class EvidenceAnalyzer {
    static analyze(claims?: any[], citationAnalysis?: any, sources?: any[]): EvidenceAnalysis;
}

export interface CheckFix {
    priority: "critical" | "high" | "moderate";
    kind: "provenance" | "writing_pattern" | "citation";
    message: string;
    category?: string;
    evidence_count?: number;
    examples?: string[];
}

export interface CheckSummary {
    verdict: "clear" | "needs_review" | "insufficient_text";
    summary: string;
    pattern_score: number;
    provenance_flags_count: number;
    evidence_score: number | null;
    reasons: string[];
    top_fixes: CheckFix[];
    disclaimer: string;
}

/** Combines ai_analysis + evidence_analysis into one verdict. Adds no new detection. */
export function buildCheckSummary(aiAnalysis: any, evidenceAnalysis: any): CheckSummary;

export interface CleanupEdit {
    index: number;
    start: number;
    end: number;
    original: string;
    replacement: string;
    category: "predictability";
}

export class WritingCleanup {
    /** Deterministic, offline predictable-vocabulary swap suggestions. Never rewrites text itself. */
    static suggestEdits(text: string): CleanupEdit[];
    /** Applies the given edits (absolute offsets into `text`) with a minimal a/an fix-up. */
    static applyEdits(text: string, edits: CleanupEdit[]): string;
}

export class DocumentExtractor {
    static extractFromFile(filePath: string): string;
}

export class CitationGenerator {
    static resolveCitation(query: string): Promise<{
        title: string;
        authors: string[];
        journal: string;
        year: number;
        doi?: string | null;
        bibtex: string;
        apa: string;
        mla: string;
        ieee: string;
    }>;
}

export class DraftComparator {
    static compare(draft1: string, draft2: string): {
        draft_v1_words: number;
        draft_v2_words: number;
        words_delta: number;
        similarity_percentage: number;
        revision_percentage: number;
        unchanged_count: number;
        added_count: number;
        total_sentences_v2: number;
        sentence_breakdown: any[];
    };
}
