/**
 * Deterministic, offline, reviewable word-swap cleanup.
 *
 * Not a rewrite engine. Only ever applies the exact predictable-vocabulary
 * substitutions already surfaced as `suggestion` on writing-pattern evidence
 * (see lib/ai_detector.js and THIRD_PARTY_NOTICES.md) -- a plain word or
 * short phrase in, a plain word or short phrase out, nothing regenerated or
 * paraphrased. Phrases needing editorial judgment (a parenthetical
 * instruction rather than a replacement) are never auto-applied.
 *
 * No network access, no external model, and no attempt to change how a
 * third-party AI detector scores the result.
 */

const { AIDetector } = require('./ai_detector');

const ARTICLE_RE = /\b([Aa]n?)\s+$/;
const PROTECTED_PATTERNS = [
    ['quotation', /["“][^"”\n]{1,2000}["”]/g],
    ['inline code', /`[^`\n]+`|```[\s\S]*?```/g],
    ['URL or DOI', /https?:\/\/\S+|\bdoi:\s*10\.\d{4,9}\/\S+|\b10\.\d{4,9}\/\S+/gi],
    ['LaTeX command or equation', /\\(?:cite|ref|eqref|url|doi)\{[^}]+\}|\$[^$\n]+\$/g],
    ['citation', /\([^()\n]{0,100}\b(?:19|20)\d{2}[a-z]?[^()\n]{0,100}\)|\[\d+(?:\s*[-,]\s*\d+)*\]/gi]
];
const LENGTH_MODES = new Set(['any', 'same', 'no_increase', 'shorter']);

class WritingCleanup {
    static candidateEdits(text) {
        const analysis = AIDetector.analyze(String(text || ''));
        const predictability = (analysis.categories || []).find(row => row.id === 'predictability');
        const edits = [];
        for (const row of (predictability && predictability.evidence) || []) {
            const suggestion = row.suggestion;
            if (!suggestion || suggestion.startsWith('(')) continue;
            edits.push({ start: row.start, end: row.end, original: row.text, replacement: suggestion, category: 'predictability' });
        }
        edits.sort((a, b) => a.start - b.start);
        return edits;
    }

    static protectedSpans(text, protectedTerms = []) {
        const spans = [];
        for (const [reason, pattern] of PROTECTED_PATTERNS) {
            pattern.lastIndex = 0;
            for (const match of text.matchAll(pattern)) spans.push([match.index, match.index + match[0].length, reason]);
        }
        const referenceHeading = /^\s*(references|bibliography|works cited)\s*$/im.exec(text);
        if (referenceHeading) spans.push([referenceHeading.index, text.length, 'reference section']);
        for (const rawTerm of protectedTerms || []) {
            const term = String(rawTerm || '').trim();
            if (!term) continue;
            const escaped = term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            const pattern = new RegExp(`(^|\\W)(${escaped})(?!\\w)`, 'gi');
            for (const match of text.matchAll(pattern)) {
                const start = match.index + match[1].length;
                spans.push([start, start + match[2].length, `protected term: ${term}`]);
            }
        }
        return spans.sort((a, b) => a[0] - b[0]);
    }

    static review(text, options = {}) {
        text = String(text || '');
        const protectedTerms = options.protectedTerms || options.protected_terms || [];
        const lengthMode = options.lengthMode || options.length_mode || 'any';
        if (!LENGTH_MODES.has(lengthMode)) throw new Error('length_mode must be any, same, no_increase, or shorter.');
        const spans = this.protectedSpans(text, protectedTerms);
        const edits = [];
        const excludedEdits = [];
        for (const edit of this.candidateEdits(text)) {
            const overlap = spans.find(([start, end]) => edit.start < end && edit.end > start);
            const originalWords = (edit.original.match(/\b\w+\b/g) || []).length;
            const replacementWords = (edit.replacement.match(/\b\w+\b/g) || []).length;
            edit.word_delta = replacementWords - originalWords;
            let allowed = lengthMode === 'any' ||
                (lengthMode === 'same' && replacementWords === originalWords) ||
                (lengthMode === 'no_increase' && replacementWords <= originalWords) ||
                (lengthMode === 'shorter' && replacementWords < originalWords);
            if (overlap || !allowed) {
                edit.excluded_reason = overlap ? overlap[2] : `excluded by ${lengthMode} length mode`;
                excludedEdits.push(edit);
            } else {
                edits.push(edit);
            }
        }
        edits.forEach((edit, index) => { edit.index = index; });
        return { edits, excluded_edits: excludedEdits, edits_count: edits.length, excluded_count: excludedEdits.length, length_mode: lengthMode, protected_terms: protectedTerms };
    }

    /** Deterministic edit-eligible predictable-vocabulary findings for `text`. */
    static suggestEdits(text, options = {}) {
        return this.review(text, options).edits;
    }

    /** Apply non-overlapping edits (absolute offsets into `text`) and return the result. */
    static applyEdits(text, edits) {
        if (!edits || !edits.length) return text;

        const kept = [];
        for (const edit of [...edits].sort((a, b) => a.start - b.start)) {
            if (kept.length && edit.start < kept[kept.length - 1].end) continue;
            kept.push(edit);
        }

        const resolved = kept.map(edit => {
            let { start, end, replacement } = edit;
            const match = ARTICLE_RE.exec(text.slice(0, start));
            if (match && replacement && /[a-zA-Z]/.test(replacement[0])) {
                const needsAn = 'aeiouAEIOU'.includes(replacement[0]) && 'aeiou'.includes(replacement[0].toLowerCase());
                const hasAn = match[1].toLowerCase() === 'an';
                if (needsAn !== hasAn) {
                    const wasCapitalized = match[1][0] === 'A';
                    const fixedArticle = needsAn ? (wasCapitalized ? 'An' : 'an') : (wasCapitalized ? 'A' : 'a');
                    const articleStart = match.index;
                    const articleEnd = match.index + match[1].length;
                    const gap = text.slice(articleEnd, start);
                    replacement = fixedArticle + gap + replacement;
                    start = articleStart;
                }
            }
            return { start, end, replacement };
        });

        let out = text;
        for (const { start, end, replacement } of [...resolved].sort((a, b) => b.start - a.start)) {
            out = out.slice(0, start) + replacement + out.slice(end);
        }
        return out;
    }
}

module.exports = { WritingCleanup };
