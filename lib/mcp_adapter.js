"use strict";

const crypto = require("node:crypto");
const path = require("node:path");
const { DocumentExtractor } = require("./extractor");

const scanOptionProperties = {
    references_text: { type: "string", description: "Reference list used for citation linkage but excluded from similarity scoring." },
    genre: { type: "string", enum: ["academic_report", "business_report", "general_essay", "technical_documentation"] },
    detail_level: { type: "string", enum: ["summary", "standard", "full"] },
    page: { type: "integer", minimum: 1 },
    page_size: { type: "integer", minimum: 1, maximum: 50 },
    fields: { type: "array", items: { type: "string" } },
    minimum_match_words: { type: "integer", minimum: 4, maximum: 50 },
    whitelist_terms: { type: "array", items: { type: "string" } },
    reference_sources: { type: "array", items: { type: "object" }, description: "Cited sources as {title,text}." },
    export_report: { type: "boolean" },
};

function prepareText(body, args) {
    const references = String(args.references_text || "").trim();
    return { body, analysisText: body + (references ? `\n\nReferences\n${references}` : ""), references };
}

function filterSections(text, args) {
    let value = text;
    const skipped = { title_page: 0, tables: 0, code: 0, appendix: 0 };
    if (args.skip_code !== false) {
        value = value.replace(/```[\s\S]*?```/g, () => { skipped.code++; return ""; });
    }
    if (args.skip_appendix !== false) {
        value = value.replace(/(?:^|\n)\s*(?:appendix|appendices)\b[\s\S]*$/i, () => { skipped.appendix++; return ""; });
    }
    if (args.skip_title_page !== false) {
        const parts = value.split(/\n\s*\n/);
        const body = parts.findIndex(part => /^\s*(?:abstract|introduction|background|methods?)\b/i.test(part));
        if (body > 0) { skipped.title_page = body; value = parts.slice(body).join("\n\n"); }
    }
    return { text: value.trim(), skipped };
}

function prepareDocument(filename, buffer, args) {
    const extension = path.extname(filename).toLowerCase();
    if (![".docx", ".pdf"].includes(extension)) throw new Error("MCP document scans accept .docx or .pdf files");
    if (!Buffer.isBuffer(buffer) || buffer.length === 0 || buffer.length > 8 * 1024 * 1024) throw new Error("Document must be between 1 byte and 8 MB");
    const extracted = extension === ".docx" ? DocumentExtractor.extractFromDocx(buffer) : DocumentExtractor.extractFromPdf(buffer);
    const filtered = filterSections(extracted, args);
    return { ...prepareText(filtered.text, args), extraction: { filename, format: extension.slice(1), blocks_skipped: filtered.skipped, scanned_text_preview: filtered.text.slice(0, 500) } };
}

function mixedScriptWords(text) {
    const findings = [];
    for (const match of text.matchAll(/\p{L}+/gu)) {
        const word = match[0];
        if (/\p{Script=Latin}/u.test(word) && /[\p{Script=Greek}\p{Script=Cyrillic}]/u.test(word)) {
            findings.push({ word, offset: match.index });
        }
    }
    return findings;
}

function citedSourceReview(text, sources = []) {
    const words = value => new Set(String(value).toLowerCase().match(/[a-z0-9]+/g) || []);
    const sentences = value => String(value).split(/(?<=[.!?])\s+|\n\s*\n/).filter(item => item.trim().split(/\s+/).length >= 4);
    return sources.slice(0, 20).map(source => {
        let best = null;
        for (const draft of sentences(text).slice(0, 50)) for (const cited of sentences(source.text).slice(0, 100)) {
            const a = words(draft), b = words(cited), shared = [...a].filter(word => b.has(word)).length;
            const score = a.size && b.size ? +(200 * shared / (a.size + b.size)).toFixed(1) : 0;
            if (!best || score > best.similarity) best = { similarity: score, draft_passage: draft.slice(0, 500), source_passage: cited.slice(0, 500) };
        }
        return { title: source.title, closest_passage: best,
            method: "experimental token-set similarity; review manually and do not treat as proof of paraphrase" };
    });
}

function compactResult(analysis, scannedText, args, extraction = null) {
    const minimum = args.minimum_match_words || 4;
    const whitelist = new Set((args.whitelist_terms || []).map(value => String(value).toLowerCase()));
    const matches = (analysis.highlighted_sentences || []).filter(row => row.is_plagiarized)
        .filter(row => (row.matched_word_count || String(row.text || "").split(/\s+/).length) >= minimum)
        .filter(row => !whitelist.size || !String(row.text || "").split(/\s+/).every(word => whitelist.has(word.toLowerCase())))
        .map(row => ({ text: row.text, source: row.source, similarity: row.similarity,
            attribution_status: row.is_quoted && row.has_citation ? "properly_attributed" : row.has_citation ? "citation_present_review_wording" : row.is_quoted ? "quote_needs_citation" : "attribution_not_detected" }));
    const page = args.page || 1, size = Math.min(50, args.page_size || 10), start = (page - 1) * size;
    const claims = analysis.student_coach?.claims || [];
    const result = {
        generated_at: new Date().toISOString(),
        summary: { engine_similarity_percent: analysis.overall_similarity || 0, matched_words: analysis.flagged_word_count || 0,
            eligible_words: analysis.scored_word_count || analysis.total_words || 0, similarity_band: analysis.safeassign_risk,
            citations_detected: claims.filter(item => item.has_citation).length },
        writing_patterns: { profile: analysis.style_review?.profile || args.genre || "academic_report",
            reliability: analysis.ai_analysis?.reliability || "unknown", confidence: analysis.ai_analysis?.reliability === "standard" ? "review multiple categories" : "limited",
            categories: analysis.style_review?.category_breakdown || [], note: "Review category evidence; no authorship or AI probability is reported." },
        matches: { page, page_size: size, total: matches.length, items: matches.slice(start, start + size) },
        homoglyph_review: { mixed_script_words: mixedScriptWords(scannedText), note: "Standalone Greek/math symbols are not flagged." },
        cited_source_review: citedSourceReview(scannedText, args.reference_sources || []),
        transparency: { scanned_sha256: crypto.createHash("sha256").update(scannedText).digest("hex"), characters_scanned: scannedText.length,
            words_scanned: scannedText.trim().split(/\s+/).filter(Boolean).length,
            scanned_text_start: scannedText.slice(0, 500), scanned_text_end: scannedText.length > 500 ? scannedText.slice(-500) : "",
            sources_searched: (analysis.sources_breakdown || []).map(row => row.filename), web_search_enabled: false,
            external_data: "The standalone MCP server performs this scan locally.",
            matching: { engine_minimum_match_words: 4, reported_minimum_match_words: minimum, whitelist_terms: [...whitelist],
                method: "exact lexical overlap plus an experimental cited-source passage comparison when source text is supplied" } }
    };
    if (extraction) result.document = extraction;
    if (["standard", "full"].includes(args.detail_level)) {
        result.evidence_review = analysis.evidence_analysis;
        result.writing_patterns.experimental_index = analysis.style_review?.style_pattern_index;
    }
    if (args.detail_level === "full") result.full_analysis = analysis;
    if (args.export_report) result.report_markdown = `# MCP Academic Review\n\nGenerated: ${result.generated_at}\n\nEngine similarity: ${result.summary.engine_similarity_percent}%\n`;
    return Array.isArray(args.fields) ? Object.fromEntries(args.fields.filter(key => key in result).map(key => [key, result[key]])) : result;
}

function attributionCoach(sentence, sourceTitle) {
    return { passage: sentence, source: sourceTitle || "the source", guidance: [
        "Use quotation marks and a citation if retaining distinctive wording.",
        "Cite the source when summarizing its finding.",
        "Restate the idea through your own analysis and explain why it supports your argument."
    ], note: "This tool does not generate detector-avoidance rewrites." };
}

module.exports = { scanOptionProperties, prepareText, prepareDocument, compactResult, attributionCoach };
