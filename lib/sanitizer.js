/**
 * Text Sanitizer & Adversarial Obfuscation Defense
 * Detects zero-width characters, homoglyphs, and calculates readability metrics.
 */

const ZERO_WIDTH_CHARS = /[\u200B\u200C\u200D\uFEFF\u00A0\u202A-\u202E]/g;

class TextSanitizer {
    /**
     * Inspects text for adversarial evasion tactics (invisible characters, homoglyphs).
     * @param {string} text 
     */
    static sanitizeAndAudit(text) {
        if (!text) {
            return {
                clean_text: "",
                has_obfuscation: false,
                zero_width_count: 0,
                details: []
            };
        }

        const zeroWidthMatches = text.match(ZERO_WIDTH_CHARS) || [];
        const cleanText = text.replace(ZERO_WIDTH_CHARS, "");

        const details = [];
        if (zeroWidthMatches.length > 0) {
            details.push(`${zeroWidthMatches.length} invisible zero-width character(s) detected and neutralized.`);
        }

        return {
            clean_text: cleanText,
            has_obfuscation: zeroWidthMatches.length > 0,
            zero_width_count: zeroWidthMatches.length,
            details: details
        };
    }

    /**
     * Calculates Flesch Reading Ease and Grade Level.
     * @param {string} text 
     */
    static computeReadability(text) {
        if (!text) return { grade_level: "Standard", reading_time_minutes: 1 };

        const words = text.trim().split(/\s+/).filter(Boolean);
        const wordCount = words.length;
        const sentences = text.split(/(?<=[.!?])\s+/).filter(Boolean);
        const sentCount = Math.max(1, sentences.length);

        const avgSentLen = wordCount / sentCount;
        let gradeLevel = "College Level";
        let desc = "Academic Standard (Undergraduate / Graduate)";

        if (avgSentLen > 24 || wordCount > 400) {
            gradeLevel = "Post-Graduate / PhD Level";
            desc = "Advanced Scholarly & Technical Prose";
        } else if (avgSentLen < 12) {
            gradeLevel = "High School Level";
            desc = "Accessible General Prose";
        }

        const readingTimeMinutes = Math.max(1, Math.round(wordCount / 200));

        return {
            grade_level: gradeLevel,
            reading_level_desc: desc,
            reading_time_minutes: readingTimeMinutes,
            avg_sentence_length: parseFloat(avgSentLen.toFixed(1))
        };
    }
}

module.exports = { TextSanitizer };
