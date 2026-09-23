/** Exact lexical passage coverage. Does not establish plagiarism or authorship. */
const COMMON = new Set('a an the and or but if then of in on at to for from by with as is are was were be been this that these those it its we our they their'.split(' '));
const { citations } = require('./diagnostics');
function tokens(text) {
    return Array.from(text.matchAll(/[\p{L}\p{N}_]+/gu), m => ({ word: m[0].toLowerCase(), start: m.index, end: m.index + m[0].length }));
}
function intersection(a, b) { return new Set([...a].filter(i => b.has(i))); }
function percent(a, b) { return b.size ? Math.round(10000 * a.size / b.size) / 100 : 0; }
function sentenceRanges(text) {
    let start = 0;
    const ranges = [];
    for (const m of text.matchAll(/(?<=[.!?])\s+|\n\s*\n/g)) {
        if (text.slice(Math.max(start, m.index - 6), m.index).toLowerCase().endsWith('et al.')) continue;
        if (text.slice(start, m.index).trim()) ranges.push([start, m.index]);
        start = m.index + m[0].length;
    }
    if (text.slice(start).trim()) ranges.push([start, text.length]);
    return ranges;
}
function matchDocument(text, sources, options = {}) {
    const query = tokens(text), n = query.length;
    const seed = (ts, i) => ts.slice(i, i + 4).map(t => t.word).join('\u0000');
    const wanted = new Set();
    for (let i = 0; i <= n - 4; i++) {
        if (query.slice(i, i + 4).filter(t => !COMMON.has(t.word)).length >= 2) wanted.add(seed(query, i));
    }
    const index = new Map(), sourceTokens = sources.map(s => tokens(s.text));
    sourceTokens.forEach((ts, key) => {
        for (let j = 0; j <= ts.length - 4; j++) {
            const s = seed(ts, j);
            if (wanted.has(s)) {
                if (!index.has(s)) index.set(s, []);
                index.get(s).push([key, j]);
            }
        }
    });
    const quoteRanges = Array.from(text.matchAll(/"[^"\n]+"|“[^”]+”|«[^»]+»/g), m => [m.index, m.index + m[0].length]);
    const header = /^\s*(?:#+\s*|\d+\.\s*)?(?:references|bibliography|works cited|reference list)\s*:?[ \t]*$/im.exec(text);
    const bibStart = header ? header.index : text.length;
    const all = new Set(query.map((_, i) => i));
    const quoted = new Set([...all].filter(i => quoteRanges.some(([a, b]) => query[i].start >= a && query[i].end <= b)));
    const bib = new Set([...all].filter(i => query[i].start >= bibStart));
    const excluded = new Set([...(options.excludeQuotes ? quoted : []), ...(options.excludeBibliography ? bib : [])]);
    const eligible = new Set([...all].filter(i => !excluded.has(i)));
    const body = new Set([...all].filter(i => !bib.has(i)));
    const rawBySource = new Map(), evidence = new Map();
    for (let i = 0; i <= n - 4; i++) {
        const bestBySource = new Map();
        for (const [key, j] of index.get(seed(query, i)) || []) {
            const st = sourceTokens[key];
            let left=i, sl=j, right=i+4, sr=j+4;
            while(left>0 && sl>0 && query[left-1].word===st[sl-1].word) { left--; sl--; }
            while(right<n && sr<st.length && query[right].word===st[sr].word) {right++;sr++;}
            const candidate = { length:right-left, left, right, sourceLeft:sl };
            if (!bestBySource.has(key) || candidate.length > bestBySource.get(key).length) bestBySource.set(key,candidate);
        }
        for (const [key, candidate] of bestBySource) {
            if (!rawBySource.has(key)) { rawBySource.set(key, new Set()); evidence.set(key, new Map()); }
            const hits = rawBySource.get(key), ev = evidence.get(key);
            const {left,right,sourceLeft} = candidate;
            for(let k=left;k<right;k++) {
                hits.add(k);
                if(!ev.has(k)) ev.set(k,sourceLeft+k-left);
            }
        }
    }
    const raw = new Set([...rawBySource.values()].flatMap(s => [...s]));
    const matched = intersection(raw, eligible), perSource = new Map();
    const passages = [];
    for (const [key, ids] of rawBySource) {
        const hits = intersection(ids, eligible); perSource.set(key, hits);
        const runs = [], ev = evidence.get(key), ts = sourceTokens[key];
        for (const i of [...hits].sort((a,b) => a-b)) {
            const run = runs[runs.length-1];
            if (run && i === run[run.length-1]+1 && ev.get(i) === ev.get(run[run.length-1])+1) run.push(i);
            else runs.push([i]);
        }
        for (const run of runs) {
            const first = run[0], last = run[run.length-1], start = query[first].start, end = query[last].end;
            const sa = ts[ev.get(first)].start, sb = ts[ev.get(last)].end;
            passages.push({ start, end, token_start: first, token_end: last+1, word_count: run.length,
                text: text.slice(start,end), source_key: String(key), source_name: sources[key].filename,
                source_start: sa, source_end: sb, matched_text: sources[key].text.slice(sa,sb) });
        }
    }
    const highlighted = sentenceRanges(text).map(([start,end]) => {
        const ids = new Set([...all].filter(i => query[i].start >= start && query[i].end <= end));
        const hits = intersection(matched, ids);
        const candidates = [...perSource].map(([key, set]) => [intersection(set, ids).size, key]).filter(([count])=>count)
            .sort((a,b)=>b[0]-a[0] || sources[a[1]].filename.localeCompare(sources[b[1]].filename));
        const key = candidates.length ? candidates[0][1] : null, source = sources[key] || {};
        const spans = passages.filter(p => p.start < end && p.end > start), best = spans.find(p=>p.source_key===String(key));
        const cite = citations(text.slice(start,end));
        return { text: text.slice(start,end), start, end, is_plagiarized: !!hits.size,
            similarity: percent(hits, intersection(ids, eligible)), matched_word_count: hits.size,
            has_citation: !!cite.length, citation: cite[0] || null, is_quoted: !!intersection(ids, quoted).size,
            source: source.filename || null, url: source.url || null, badge: source.badge || 'Institutional',
            matched_source_sentence: best ? best.matched_text : null, matched_spans: spans };
    });
    const breakdown = [...perSource].filter(([,ids])=>ids.size).map(([key,ids])=>({
        filename: sources[key].filename, similarity: percent(ids,eligible), common_words_count: ids.size,
        source_word_count: sourceTokens[key].length,
        matched_sentences_count: highlighted.filter(row => row.matched_spans.some(span => span.source_key === String(key))).length,
        max_passage_similarity: 100,
        source_type: sources[key].source_type || 'institutional',
        badge: sources[key].badge || 'Institutional',
        url: sources[key].url || null,
    })).sort((a,b)=>b.similarity-a.similarity || a.filename.localeCompare(b.filename));
    const diffs = highlighted.filter(r=>r.is_plagiarized).map(r=>({student_sentence:r.text, matched_sentence:r.matched_source_sentence,
        source_name:r.source, source_url:r.url, badge:r.badge, similarity:r.similarity,
        is_quoted:r.is_quoted, has_citation:r.has_citation, citation:r.citation, matched_spans:r.matched_spans}));
    return { overall_similarity:percent(matched,eligible), raw_similarity:percent(raw,all), body_similarity:percent(intersection(raw,body),body),
        bibliography_similarity:percent(intersection(raw,bib),bib), quotation_similarity:percent(intersection(raw,quoted),quoted),
        total_words:n, scored_word_count:eligible.size, flagged_word_count:matched.size, raw_matched_word_count:raw.size,
        excluded_word_count:excluded.size, bibliography_word_count:bib.size, quotation_word_count:quoted.size,
        matched_spans:passages, highlighted_sentences:highlighted, diff_matches:diffs, sources_breakdown:breakdown,
        total_sentences:highlighted.length, plagiarized_sentences_count:diffs.length, quotes_count:quoteRanges.length,
        highest_matching_source:breakdown[0]?.filename || null, highest_matching_url:breakdown[0]?.url || null,
        highest_similarity:breakdown[0]?.similarity || 0,
        scoring:{method:'exact-word-spans-v1',minimum_match_words:4,exclude_quotes:!!options.excludeQuotes,
            exclude_bibliography:!!options.excludeBibliography,citations_excluded:false,source_percentages_overlap:true,
            offset_text:'normalized_text',offset_unit:'utf16_code_units',
            limitations:'Measures lexical overlap in retrieved sources; semantic paraphrases may be missed.'}, normalized_text:text };
}
module.exports = { matchDocument, sentenceRanges };
