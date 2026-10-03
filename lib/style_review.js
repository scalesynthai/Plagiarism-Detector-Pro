/** Versioned, evidence-first writing-style review for the offline npm CLI. */
const fs = require('fs');
const path = require('path');

const RULES_PATH = path.join(__dirname, '..', 'config', 'writing_style_rules.v1.json');
const registry = JSON.parse(fs.readFileSync(RULES_PATH, 'utf8'));
const wordCount = text => (String(text || '').match(/[A-Za-z0-9]+(?:['’][A-Za-z]+)?/g) || []).length;

function blocks(text) {
    const rows = [];
    const regex = /\S(?:.*?\S)?(?=\n\s*\n|$)/gs;
    let match;
    while ((match = regex.exec(text)) !== null) {
        const type = /^\s*[>"“]/.test(match[0]) ? 'quotation' : /^\s*(?:references|works cited|bibliography)\b/i.test(match[0]) ? 'reference' : 'paragraph';
        rows.push({ id: `block-${rows.length + 1}`, type, text: match[0], start_offset: match.index, page: null });
    }
    return rows.length ? rows : [{ id: 'block-1', type: 'paragraph', text, start_offset: 0, page: null }];
}

class WritingStyleReviewer {
    static analyze(input, options = {}) {
        const text = String(input || '');
        const documentBlocks = blocks(text);
        const eligibleWords = documentBlocks.filter(row => !['quotation', 'reference', 'code', 'template'].includes(row.type)).reduce((sum, row) => sum + wordCount(row.text), 0);
        const findings = [];
        const ruleMetrics = {};
        const categoryPoints = new Map();
        const categoryCaps = new Map();
        const strength = { weak: 2, moderate: 5, stronger: 8 };
        for (const rule of registry.rules.filter(row => row.enabled)) {
            const matches = [];
            const seen = new Set();
            for (const block of documentBlocks.filter(row => rule.applicable_block_types.includes(row.type))) {
                for (const source of rule.patterns) {
                    if (source.length > 300) throw new Error(`Unsafe oversized rule pattern: ${rule.id}`);
                    const regex = new RegExp(`(^|[^A-Za-z0-9_])(${source})(?![A-Za-z0-9_])`, 'gi');
                    let match;
                    while ((match = regex.exec(block.text)) !== null) {
                        const lead = match[1].length;
                        const start = match.index + lead;
                        const end = start + match[2].length;
                        const key = `${block.id}:${start}:${end}`;
                        if (!seen.has(key)) { seen.add(key); matches.push({ block, start, end, value: match[2] }); }
                        if (!match[0].length) regex.lastIndex += 1;
                    }
                }
            }
            matches.sort((a, b) => a.block.id.localeCompare(b.block.id) || a.start - b.start || (a.end - a.start) - (b.end - b.start));
            const deduped = [];
            for (const row of matches) {
                const previous = deduped[deduped.length - 1];
                if (previous && previous.block.id === row.block.id && row.start < previous.end) {
                    if (row.end - row.start < previous.end - previous.start) deduped[deduped.length - 1] = row;
                } else deduped.push(row);
            }
            matches.splice(0, matches.length, ...deduped);
            const eligible = matches.filter(row => !['quotation', 'reference', 'code', 'template'].includes(row.block.type));
            const frequency = eligible.length / Math.max(1, eligibleWords) * 1000;
            const threshold = eligible.length >= rule.minimum_occurrences && frequency >= rule.frequency_per_1000;
            ruleMetrics[rule.id] = { count: matches.length, eligible_count: eligible.length, per_1000_eligible_words: +frequency.toFixed(2), affected_blocks: new Set(matches.map(row => row.block.id)).size, local_concentration: Math.max(0, ...documentBlocks.map(block => eligible.filter(row => row.block.id === block.id).length)), threshold_met: threshold };
            const cap = Number(rule.category_contribution_cap);
            categoryCaps.set(rule.category, Math.max(categoryCaps.get(rule.category) || 0, cap));
            if (threshold) categoryPoints.set(rule.category, (categoryPoints.get(rule.category) || 0) + strength[rule.evidence_strength] * Math.min(2, eligible.length / Math.max(1, rule.minimum_occurrences)));
            for (const row of matches) {
                const excludedType = ['quotation', 'reference', 'code', 'template'].includes(row.block.type);
                findings.push({ id: `finding-${rule.id}-${row.block.id}-${row.start}`, rule_id: rule.id, category: rule.category, evidence_strength: rule.evidence_strength, detector_type: rule.detector_type, block_id: row.block.id, page: null, start_offset: row.block.start_offset + row.start, end_offset: row.block.start_offset + row.end, matched_text: row.value, explanation: rule.description, context: row.block.text.slice(Math.max(0, row.start - 90), row.end + 90), excluded_from_score: excludedType || !threshold, exclusion_reason: excludedType ? `${row.block.type} blocks are excluded from the default index.` : !threshold ? 'Reported below the configured repetition or frequency threshold.' : null });
            }
        }
        const emDashCount = (text.match(/—/g) || []).length;
        const enDashCount = (text.match(/–/g) || []).length;
        const hyphenCount = (text.match(/-/g) || []).length;
        const emRate = emDashCount / Math.max(1, eligibleWords) * 1000;
        categoryCaps.set('punctuation', 4);
        categoryPoints.set('punctuation', Math.min(4, Math.max(0, emRate - 2) * .25));
        const breakdown = [...categoryCaps].map(([category, cap]) => ({ category, points: +Math.min(cap, categoryPoints.get(category) || 0).toFixed(1), cap, finding_count: findings.filter(row => row.category === category && !row.excluded_from_score).length })).sort((a, b) => a.category.localeCompare(b.category));
        const total = breakdown.reduce((sum, row) => sum + row.points, 0);
        const maximum = breakdown.reduce((sum, row) => sum + row.cap, 0) || 1;
        const styleIndex = eligibleWords >= registry.minimum_eligible_words ? +(total / maximum * 100).toFixed(1) : null;
        const asciiLetters = [...text].filter(char => /[A-Za-z]/.test(char)).length;
        const allLetters = [...text].filter(char => /\p{L}/u.test(char)).length;
        const ratio = asciiLetters / Math.max(1, allLetters);
        return {
            feature_name: 'AI Writing Style Review', ruleset_version: registry.ruleset_version, ruleset_status: registry.status,
            source_review_date: registry.review_date, analysis_timestamp: new Date().toISOString(), profile: options.profile || registry.default_profile,
            extraction_status: 'text_input', extraction_warnings: ratio < .85 ? ['English rules have limited coverage for this document; the absence of findings is not a clean result.'] : [],
            language_coverage: { language: ratio >= .85 ? 'en' : 'unknown', english_character_ratio: +ratio.toFixed(3), coverage: ratio >= .85 ? 'standard' : 'limited' },
            eligible_word_count: eligibleWords, excluded_word_count: documentBlocks.filter(row => ['quotation', 'reference', 'code', 'template'].includes(row.type)).reduce((sum, row) => sum + wordCount(row.text), 0),
            style_pattern_index: styleIndex, numeric_index_enabled: true, category_breakdown: breakdown, rule_metrics: ruleMetrics,
            punctuation_metrics: { em_dash_count: emDashCount, en_dash_count: enDashCount, hyphen_minus_count: hyphenCount, em_dashes_per_1000_eligible_words: +emRate.toFixed(2), smart_quote_or_apostrophe_count: (text.match(/[“”‘’]/g) || []).length },
            findings: findings.sort((a, b) => a.start_offset - b.start_offset), finding_count: findings.length, scored_finding_count: findings.filter(row => !row.excluded_from_score).length,
            recommendation: styleIndex == null ? 'Insufficient text for a document-level index.' : 'Review multiple independent categories and their passages.',
            disclaimer: 'These findings identify writing patterns that can occur in both human and AI-assisted text. They do not establish authorship.',
            validation: 'No authorized genre-balanced human/AI evaluation corpus is bundled; this ruleset is unvalidated and its thresholds are experimental.'
        };
    }
}

module.exports = { WritingStyleReviewer };
