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

class WritingCleanup {
    /** Deterministic edit-eligible predictable-vocabulary findings for `text`. */
    static suggestEdits(text) {
        const analysis = AIDetector.analyze(String(text || ''));
        const predictability = (analysis.categories || []).find(row => row.id === 'predictability');
        const edits = [];
        for (const row of (predictability && predictability.evidence) || []) {
            const suggestion = row.suggestion;
            if (!suggestion || suggestion.startsWith('(')) continue;
            edits.push({ start: row.start, end: row.end, original: row.text, replacement: suggestion, category: 'predictability' });
        }
        edits.sort((a, b) => a.start - b.start);
        edits.forEach((edit, index) => { edit.index = index; });
        return edits;
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
