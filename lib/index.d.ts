export interface PlagiarismResult {
    overall_similarity: number;
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
        ai_probability: number;
        burstiness: number;
        ai_risk_level: string;
        flagged_markers_count: number;
    };
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
    privateDraft?: boolean;
}): Promise<PlagiarismResult>;

export class PlagiarismChecker {
    constructor(sourcesDir?: string);
    analyze(text: string, options?: any): PlagiarismResult;
}

export class AIDetector {
    static analyze(text: string): {
        ai_probability: number;
        burstiness: number;
        ai_risk_level: string;
        flagged_markers_count: number;
    };
}

export class AcademicParaphraser {
    static synthesizeSentence(sentence: string, sourceName?: string, sourceTitle?: string): {
        original_sentence: string;
        source_attribution: string;
        suggestions: Array<{ style: string; text: string; description: string; }>;
    };
}

export class AcademicStudentCoach {
    static scanUnsupportedClaims(text: string): Array<{ sentence: string; claim_marker: string; recommendation: string; }>;
    static analyzeToneAndVocabulary(text: string): Array<{ matched_term: string; context_snippet: string; scholarly_replacements: string[]; tip: string; }>;
    static alphabetizeAndFormatReferences(referencesText: string): { sorted_references: string[]; count: number; formatted_text: string; issues: string[]; };
    static evaluateThesisAbstract(text: string): { score: number; word_count: number; has_hypothesis: boolean; has_method: boolean; has_significance: boolean; feedback: string[]; };
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
