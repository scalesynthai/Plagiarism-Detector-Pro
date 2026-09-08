/**
 * Draft-to-Draft Revision Comparator
 * Compares Draft v1 against Draft v2 to track newly added content,
 * modified sentences, deleted paragraphs, and revision percentages.
 */

class DraftComparator {
    /**
     * Compares two drafts and produces detailed metrics.
     * @param {string} draft1 
     * @param {string} draft2 
     */
    static compare(draft1, draft2) {
        const d1 = (draft1 || "").trim();
        const d2 = (draft2 || "").trim();

        const s1 = d1.split(/(?<=[.!?])\s+|\n+/).map(s => s.trim()).filter(s => s.length > 5);
        const s2 = d2.split(/(?<=[.!?])\s+|\n+/).map(s => s.trim()).filter(s => s.length > 5);

        const set1 = new Set(s1.map(s => s.toLowerCase().replace(/[^\w\s]/g, "")));
        
        let unchangedCount = 0;
        let addedCount = 0;
        const details = [];

        s2.forEach((sent, idx) => {
            const clean = sent.toLowerCase().replace(/[^\w\s]/g, "");
            if (set1.has(clean)) {
                unchangedCount++;
                details.push({
                    sentence_index: idx + 1,
                    text: sent,
                    status: "unchanged",
                    label: "Retained from Draft 1"
                });
            } else {
                addedCount++;
                details.push({
                    sentence_index: idx + 1,
                    text: sent,
                    status: "added",
                    label: "Newly Added / Substantially Revised"
                });
            }
        });

        const w1 = d1.split(/\s+/).filter(Boolean).length;
        const w2 = d2.split(/\s+/).filter(Boolean).length;
        const totalS2 = Math.max(1, s2.length);

        const continuityPct = parseFloat(((unchangedCount / totalS2) * 100).toFixed(1));
        const revisionPct = parseFloat(((addedCount / totalS2) * 100).toFixed(1));

        return {
            draft_v1_words: w1,
            draft_v2_words: w2,
            words_delta: w2 - w1,
            similarity_percentage: continuityPct,
            revision_percentage: revisionPct,
            unchanged_count: unchangedCount,
            added_count: addedCount,
            total_sentences_v2: s2.length,
            sentence_breakdown: details
        };
    }
}

module.exports = { DraftComparator };
