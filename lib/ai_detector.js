/**
 * Explainable deterministic writing-pattern analysis.
 * Signal design adapted from MIT-licensed avoid-ai-writing and humanize;
 * see THIRD_PARTY_NOTICES.md. This is not an authorship detector.
 */

const MARKERS = [
    'delve', 'delve into', 'tapestry', 'testament to', 'pivotal role',
    'seamless integration', 'holistic approach', 'multifaceted',
    'in the realm of', 'the landscape of', 'a myriad of', 'a plethora of',
    'it is important to note', 'it is worth noting', 'plays a crucial role',
    'foster innovation', 'game changer', 'vibrant tapestry', 'leverage',
    'utilize', 'robust', 'comprehensive', 'streamline'
];

const META = [
    ['predictability', 'Predictable vocabulary', 'Replace stock wording with the precise term your subject requires.'],
    ['burstiness', 'Sentence rhythm', 'Vary sentence length only where it improves emphasis and readability.'],
    ['hedging', 'Hedge density', 'Keep uncertainty that is academically justified; remove reflexive softening.'],
    ['structure', 'Formulaic structure', 'Lead with the actual claim and remove repeated setup or summary frames.'],
    ['specificity', 'Specificity and grounding', 'Attach concrete evidence and a citation to factual or empirical claims.'],
    ['transitions', 'Transition fingerprint', 'Use transitions only when the logical relationship is not already clear.'],
    ['punctuation', 'Punctuation fingerprint', 'Replace unnecessary em dashes with periods, commas, or a direct sentence.'],
    ['register', 'Assistant-style register', 'Remove chatbot framing and keep the voice appropriate for the assignment.'],
    ['rhetoric', 'Rhetorical scaffolding', 'State the conclusion directly instead of announcing or staging it.']
];

function words(text) {
    return (String(text || '').toLowerCase().match(/[a-z0-9]+(?:['’][a-z]+)?/g) || []);
}

function sentences(text) {
    const rows = [];
    const regex = /[^.!?\n]+(?:[.!?]+|(?=\n|$))/g;
    let match;
    while ((match = regex.exec(text)) !== null) {
        const leading = match[0].length - match[0].trimStart().length;
        const value = match[0].trim();
        if (value.length >= 4) rows.push({ start: match.index + leading, end: match.index + match[0].trimEnd().length, text: value });
    }
    return rows;
}

function evidence(text, regex, kind) {
    const flags = regex.flags.includes('g') ? regex.flags : `${regex.flags}g`;
    const matcher = new RegExp(regex.source, flags);
    const out = [];
    let match;
    while ((match = matcher.exec(text)) !== null) {
        out.push({ text: match[0].trim(), start: match.index, end: match.index + match[0].length, kind });
        if (!match[0].length) matcher.lastIndex += 1;
    }
    return out;
}

function dedupe(rows) {
    const seen = new Set();
    return rows.sort((a, b) => a.start - b.start || a.end - b.end).filter(row => {
        const key = `${row.start}:${row.end}:${row.kind}`;
        if (seen.has(key)) return false;
        seen.add(key);
        return true;
    });
}

function scoreCount(count, moderate = 2, strong = 4) {
    if (count <= 0) return 0;
    if (count >= strong) return 3;
    if (count >= moderate) return 2;
    return 1;
}

// Literal artifacts of copying an AI assistant's output, rather than style inference.
// Adapted from the MIT-licensed avoid-ai-writing project's documented "unfilled
// placeholder" / "chatbot citation markup" / "AI-tool URL parameter" tells;
// see THIRD_PARTY_NOTICES.md.
const PROVENANCE_PATTERNS = [
    ['unfilled template placeholder', /\[(?:your name|insert (?:source|citation|name|date|link|here|[a-z]{3,20})|company name|client name|date here|placeholder|todo|tbd)\]|\b(?:19|20)\d{2}-xx-xx\b|\bxx[/-]xx[/-](?:19|20)\d{2}\b/gi],
    ['AI-assistant citation markup', /\bciteturn\d+search\d+\b|\boai_citation\b|contentreference\[oaicite:\d+\](?:\{index=\d+\})?/gi],
    ['AI-tool tracking link', /utm_source=(?:chatgpt|copilot|perplexity|openai|claude|gemini|bard)(?:\.\w+)*/gi]
];

function provenanceEvidence(text) {
    const rows = [];
    PROVENANCE_PATTERNS.forEach(([kind, regex]) => { rows.push(...evidence(text, regex, kind)); });
    return dedupe(rows);
}

function category(id, score, rows, metrics = {}) {
    const [, label, recommendation] = META.find(([key]) => key === id);
    return { id, label, score: Math.max(0, Math.min(3, Math.trunc(score))), max_score: 3, evidence: rows.slice(0, 12), evidence_count: rows.length, metrics, recommendation };
}

class AIDetector {
    static analyze(input, context = {}) {
        const text = String(input || '');
        const tokenList = words(text);
        const sentenceRows = sentences(text);
        const sentenceList = sentenceRows.map(row => row.text);
        const wordCount = tokenList.length;
        if (!wordCount || !sentenceList.length) return AIDetector.empty(wordCount);

        const lengths = sentenceList.map(sentence => words(sentence).length);
        const mean = lengths.reduce((sum, value) => sum + value, 0) / lengths.length;
        const variance = lengths.reduce((sum, value) => sum + Math.pow(value - mean, 2), 0) / Math.max(1, lengths.length);
        const burstiness = mean ? Math.min(100, Math.sqrt(variance) / mean * 100) : 0;

        let vocabularyEvidence = [];
        for (const phrase of [...MARKERS].sort((a, b) => b.length - a.length)) {
            const escaped = phrase.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            vocabularyEvidence.push(...evidence(text, new RegExp(`\\b${escaped}\\b`, 'gi'), 'stock vocabulary'));
        }
        vocabularyEvidence = dedupe(vocabularyEvidence);
        const distinctMarkers = new Set(vocabularyEvidence.map(row => row.text.toLowerCase())).size;

        const rhythmEvidence = [];
        let clusteredRuns = 0;
        for (let i = 0; i <= lengths.length - 3; i += 1) {
            const window = lengths.slice(i, i + 3);
            if (Math.max(...window) - Math.min(...window) <= 5 && Math.min(...window) >= 8) {
                clusteredRuns += 1;
                rhythmEvidence.push({ text: `Sentence lengths ${window.join(', ')}`, start: sentenceRows[i].start, end: sentenceRows[i + 2].end, kind: 'uniform sentence run' });
            }
        }
        let rhythmScore = 0;
        if (lengths.length >= 5) {
            rhythmScore = burstiness < 18 || clusteredRuns >= 3 ? 3 : burstiness < 27 || clusteredRuns >= 2 ? 2 : burstiness < 35 || clusteredRuns === 1 ? 1 : 0;
        }

        const hedgeRegex = /\b(?:often|generally|typically|arguably|potentially|perhaps|possibly|in many cases|it can be argued|one might consider|results may vary|it is (?:important|worthwhile) to (?:note|mention)|may (?:help|lead|result|suggest|indicate))\b/gi;
        const hedgeEvidence = evidence(text, hedgeRegex, 'hedge');
        const hedgeRate = hedgeEvidence.length / Math.max(1, wordCount) * 100;
        const hedgeScore = hedgeRate >= 3 ? 3 : hedgeRate >= 1.5 ? 2 : hedgeEvidence.length ? 1 : 0;

        let structureEvidence = [];
        const structurePatterns = [
            ['formulaic introduction', /\b(?:in this (?:paper|article|section),? (?:we|i) will|this (?:paper|article) (?:aims to|explores|examines))\b/gi],
            ['negative parallelism', /\b(?:it(?:'s| is) not|not just)\b[^.!?]{2,100}\b(?:it(?:'s| is)|but)\b/gi],
            ['announcement framing', /\b(?:the key (?:insight|point|lesson) is|what (?:surprised|changed|worked|clicked)[^.!?]{0,40} was)\b/gi],
            ['generic conclusion', /\b(?:the future looks bright|only time will tell|in conclusion|to summarize|in summary)\b/gi],
            ['stock significance frame', /\b(?:is|are) (?:a testament to|pivotal to|crucial to)\b/gi]
        ];
        structurePatterns.forEach(([kind, regex]) => { structureEvidence.push(...evidence(text, regex, kind)); });
        const bulletCount = (text.match(/^\s*(?:[-*•]|\d+[.)])\s+/gm) || []).length;
        if (bulletCount >= 5) structureEvidence.push({ text: `${bulletCount} list items`, start: 0, end: 0, kind: 'list-heavy structure' });
        structureEvidence = dedupe(structureEvidence);

        const citationRegex = /\((?:[A-Z][\w'’–-]+(?:\s+(?:et\s+al\.|&\s*[A-Z][\w'’–-]+))?,\s*(?:19|20)\d{2}[a-z]?|(?:19|20)\d{2})[^)]*\)|\[\d+(?:\s*[-–,]\s*\d+)*\]/i;
        const anchorRegex = /\b(?:19|20)\d{2}\b|\b\d+(?:\.\d+)?%\b|\b\d+(?:,\d{3})+(?:\.\d+)?\b|\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}\b/;
        const vagueRegex = /\b(?:(?:studies|research|experts|scholars|scientists)\s+(?:show|shows|suggest|suggests|indicate|indicates|found)|(?:many|most|numerous)\s+(?:organizations|people|researchers|students|companies|teams)|(?:significant|notable|substantial)\s+(?:improvement|progress|impact|effect|increase|decrease)s?|it (?:is|has been) (?:widely )?(?:known|accepted|established|shown))\b/i;
        const specificityEvidence = sentenceRows.filter(row => vagueRegex.test(row.text) && !citationRegex.test(row.text) && !anchorRegex.test(row.text)).map(row => ({ text: row.text.slice(0, 220), start: row.start, end: row.end, kind: 'unanchored claim' }));
        for (const row of context.unsupported_claims || []) {
            const sentence = String(row.sentence || '').trim();
            if (sentence && !specificityEvidence.some(item => item.text === sentence)) {
                const start = Math.max(0, text.indexOf(sentence));
                specificityEvidence.push({ text: sentence.slice(0, 220), start, end: start + sentence.length, kind: 'claim without recognized citation' });
            }
        }

        const transitionRegex = /^(?:furthermore|moreover|additionally),|\b(?:this highlights|this underscores|this demonstrates)\s+the\s+importance\s+of\b|\bas previously mentioned\b|\bin addition to the above\b|\bit goes without saying\b|\bneedless to say\b|\b(?:in conclusion|to summarize|in summary),?\b/gim;
        const transitionEvidence = evidence(text, transitionRegex, 'formulaic transition');

        const emDashEvidence = evidence(text, /—|\s--\s/g, 'em dash');
        const emDashRate = emDashEvidence.length / Math.max(1, wordCount) * 300;
        const wrappedRows = evidence(text, /—[^—\n]{2,100}—/g, 'wrapped em-dash aside');
        const colonRows = evidence(text, /\b(?:the (?:problem|answer|reason|rule|point)|what matters)\s*:/gi, 'announcement colon');
        const punctuationEvidence = dedupe([...emDashEvidence, ...wrappedRows, ...colonRows]);
        const punctuationScore = !punctuationEvidence.length ? 0 : wrappedRows.length || emDashRate > 3 || colonRows.length >= 2 ? 2 : 1;

        let registerEvidence = [];
        [['assistant opener', /^\s*(?:certainly|absolutely|great question)[!,.]/i], ['assistant closer', /\b(?:i hope this helps|let me know if you have any questions|feel free to reach out)\b/gi], ['reasoning narration', /\b(?:let me think step by step|let'?s break this down|breaking this down)\b/gi]].forEach(([kind, regex]) => { registerEvidence.push(...evidence(text, regex, kind)); });

        let rhetoricEvidence = [];
        [['not-X-but-Y frame', /\bnot\s+(?:just\s+)?[^,.;]{2,70}(?:,|—|–)\s*(?:but\s+)?[^.!?]{2,90}/gi], ['performed discovery', /\b(?:turns out|what i (?:didn'?t expect|realized|found) was|the thing i realized was)\b/gi], ['mini-aphorism', /\bthat(?:'s| is) (?:the (?:real|actual|whole) (?:work|cost|point|thing)|what changed|what matters)\b/gi], ['comparative framing', /\bmore\s+[\w-]+\s+than\s+[\w-]+\b/gi], ['significance flourish', /\b(?:a testament to|pivotal role|vibrant tapestry)\b/gi]].forEach(([kind, regex]) => { rhetoricEvidence.push(...evidence(text, regex, kind)); });
        rhetoricEvidence = dedupe(rhetoricEvidence);

        const provenanceFlags = provenanceEvidence(text);

        const categories = [
            category('predictability', scoreCount(distinctMarkers, 2, 5), vocabularyEvidence, { distinct_markers: distinctMarkers }),
            category('burstiness', rhythmScore, rhythmEvidence, { sentence_lengths: lengths, coefficient_of_variation_pct: +burstiness.toFixed(2) }),
            category('hedging', hedgeScore, hedgeEvidence, { per_100_words: +hedgeRate.toFixed(2) }),
            category('structure', scoreCount(structureEvidence.length, 2, 4), structureEvidence, { bullet_items: bulletCount }),
            category('specificity', scoreCount(specificityEvidence.length, 2, 4), specificityEvidence),
            category('transitions', scoreCount(transitionEvidence.length, 2, 4), transitionEvidence),
            category('punctuation', punctuationScore, punctuationEvidence, { em_dash_count: emDashEvidence.length, em_dashes_per_300_words: +emDashRate.toFixed(2), wrapped_em_dash: wrappedRows.length > 0, announcement_colons: colonRows.length }),
            category('register', registerEvidence.length >= 2 ? 3 : registerEvidence.length ? 2 : 0, registerEvidence),
            category('rhetoric', scoreCount(rhetoricEvidence.length, 2, 4), rhetoricEvidence)
        ];

        const points = categories.reduce((sum, row) => sum + row.score, 0);
        const patternScore = +(points / 27 * 100).toFixed(1);
        const risk = patternScore < 25 ? 'Low Pattern Score' : patternScore < 65 ? 'Elevated Pattern Score' : 'High Pattern Score';
        const status = patternScore < 25 ? 'success' : patternScore < 65 ? 'warning' : 'danger';
        const topSignals = categories.filter(row => row.score > 0).sort((a, b) => b.score - a.score || b.evidence_count - a.evidence_count).slice(0, 4).map(({ id, label, score, evidence_count, recommendation }) => ({ id, label, score, evidence_count, recommendation }));
        const flagged = sentenceRows.map(row => {
            const reasons = [...new Set(categories.flatMap(cat => cat.evidence.filter(item => item.end > item.start && item.start < row.end && item.end > row.start).map(() => cat.label)))];
            return reasons.length ? { sentence: row.text, start: row.start, end: row.end, word_count: words(row.text).length, is_ai_typical: true, has_llm_markers: true, reasons } : null;
        }).filter(Boolean);

        const markerCount = vocabularyEvidence.length + transitionEvidence.length;
        return {
            pattern_score: patternScore, ai_probability: patternScore, human_probability: +(100 - patternScore).toFixed(1),
            ai_risk_level: risk, status_class: status,
            verdict_description: patternScore < 25 ? 'Few configured writing patterns were detected.' : patternScore < 65 ? 'Several writing patterns merit manual review.' : 'Many configured writing patterns were detected; this does not establish authorship.',
            reliability: wordCount < 120 ? 'limited' : 'standard', minimum_reliable_words: 120, pattern_version: '2.1.0',
            categories, top_signals: topSignals,
            provenance_flags: provenanceFlags.slice(0, 20),
            provenance_flags_count: provenanceFlags.length,
            provenance_note: "These are literal artifacts of copying an AI assistant's output (an unfilled template placeholder, leftover chatbot citation markup, or an AI-tool tracking link), not stylistic inference. Each flag is a specific, checkable fact and is not folded into the pattern score above.",
            style_metrics: { word_count: wordCount, sentence_count: sentenceList.length, paragraph_count: text.split(/\n\s*\n/).filter(p => p.trim()).length, em_dash_count: emDashEvidence.length, em_dashes_per_300_words: +emDashRate.toFixed(2), hedge_count: hedgeEvidence.length, transition_count: transitionEvidence.length },
            burstiness: +burstiness.toFixed(2), lexical_diversity: +(new Set(tokenList).size / wordCount * 100).toFixed(2),
            ai_marker_count: markerCount, flagged_markers_count: markerCount, total_sentences: sentenceList.length,
            flagged_ai_sentences_count: flagged.length, flagged_sentences: flagged, flagged_ai_sentences: flagged,
            assessment_scope: 'Deterministic writing-pattern review; not evidence of AI or human authorship.',
            score_explanation: `${points} of 27 category points, normalized to 100. Short samples under 120 words have limited reliability.`,
            legacy_field_note: 'ai_probability and human_probability are compatibility fields; they are complementary heuristic scores, not calibrated probabilities.'
        };
    }

    static empty(wordCount = 0) {
        return {
            pattern_score: 0, ai_probability: 0, human_probability: 100,
            ai_risk_level: 'Insufficient Text', status_class: 'warning', reliability: 'insufficient',
            minimum_reliable_words: 120, pattern_version: '2.1.0', categories: META.map(([id]) => category(id, 0, [])), top_signals: [],
            provenance_flags: [], provenance_flags_count: 0,
            provenance_note: "These are literal artifacts of copying an AI assistant's output, not stylistic inference. Not folded into the pattern score above.",
            style_metrics: { word_count: wordCount, sentence_count: 0, paragraph_count: 0, em_dash_count: 0, em_dashes_per_300_words: 0, hedge_count: 0, transition_count: 0 },
            burstiness: 50, lexical_diversity: 0, ai_marker_count: 0, flagged_markers_count: 0,
            flagged_ai_sentences_count: 0, flagged_sentences: [], flagged_ai_sentences: [],
            assessment_scope: 'Deterministic writing-pattern review; not evidence of AI or human authorship.',
            score_explanation: 'At least 120 words are recommended for a stable document-level review.'
        };
    }
}

module.exports = { AIDetector };
