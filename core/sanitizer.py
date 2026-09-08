import re
import unicodedata
from typing import Dict, Any, List, Tuple

# Mapping of common Cyrillic / Greek / Mathematical lookalike homoglyphs to Latin equivalents
HOMOGLYPH_MAP = {
    # Cyrillic lowercase
    '\u0430': 'a', '\u0435': 'e', '\u043e': 'o', '\u0440': 'p', '\u0441': 'c', 
    '\u0443': 'y', '\u0445': 'x', '\u0456': 'i', '\u0458': 'j', '\u0455': 's',
    '\u0432': 'b', '\u043d': 'h', '\u0442': 't',
    # Cyrillic uppercase
    '\u0410': 'A', '\u0412': 'B', '\u0415': 'E', '\u041a': 'K', '\u041c': 'M',
    '\u041d': 'H', '\u041e': 'O', '\u0420': 'P', '\u0421': 'C', '\u0422': 'T',
    '\u0425': 'X', '\u0423': 'Y',
    # Greek
    '\u03b1': 'a', '\u03b5': 'e', '\u03bf': 'o', '\u03c1': 'p', '\u03bd': 'v',
    '\u0391': 'A', '\u0392': 'B', '\u0395': 'E', '\u0397': 'H', '\u0399': 'I',
    '\u039a': 'K', '\u039c': 'M', '\u039d': 'N', '\u039f': 'O', '\u03a1': 'P',
    '\u03a4': 'T', '\u03a7': 'X', '\u03a5': 'Y', '\u0396': 'Z',
    # Mathematical Monospace / Alphanumeric Symbols
    '\uff41': 'a', '\uff42': 'b', '\uff43': 'c', '\uff44': 'd', '\uff45': 'e'
}

# Zero-width, invisible, and formatting control Unicode characters
ZERO_WIDTH_CHARS = {
    '\u200b': 'Zero-Width Space',
    '\u200c': 'Zero-Width Non-Joiner',
    '\u200d': 'Zero-Width Joiner',
    '\ufeff': 'Zero-Width No-Break Space (BOM)',
    '\u00ad': 'Soft Hyphen',
    '\u2060': 'Word Joiner',
    '\u200e': 'Left-to-Right Mark',
    '\u200f': 'Right-to-Left Mark',
    '\u202a': 'Left-to-Right Embedding',
    '\u202b': 'Right-to-Left Embedding',
    '\u202c': 'Pop Directional Formatting',
    '\u202d': 'Left-to-Right Override',
    '\u202e': 'Right-to-Left Override'
}


class TextSanitizer:
    """
    Analyzes and sanitizes academic submissions for adversarial evasion tricks:
    - Homoglyph character substitution (e.g. Cyrillic 'a' inside English text)
    - Hidden zero-width or directional Unicode characters
    - Computes Readability metrics (Flesch Reading Ease, Grade Level)
    """

    @classmethod
    def analyze_and_sanitize(cls, text: str) -> Dict[str, Any]:
        if not text:
            return {
                "sanitized_text": "",
                "has_obfuscation": False,
                "homoglyphs_detected": 0,
                "zero_width_chars_detected": 0,
                "obfuscation_details": [],
                "readability": cls.compute_readability("")
            }

        homoglyph_matches = []
        zero_width_matches = []
        cleaned_chars = []

        for idx, ch in enumerate(text):
            if ch in ZERO_WIDTH_CHARS:
                zero_width_matches.append({
                    "char_code": hex(ord(ch)),
                    "name": ZERO_WIDTH_CHARS[ch],
                    "position": idx
                })
                continue  # strip zero-width characters

            if ch in HOMOGLYPH_MAP:
                replacement = HOMOGLYPH_MAP[ch]
                homoglyph_matches.append({
                    "original": ch,
                    "replacement": replacement,
                    "char_code": hex(ord(ch)),
                    "position": idx
                })
                cleaned_chars.append(replacement)
            else:
                cleaned_chars.append(ch)

        sanitized = "".join(cleaned_chars)
        # Normalize general unicode
        sanitized = unicodedata.normalize("NFKC", sanitized)

        has_obfuscation = len(homoglyph_matches) > 0 or len(zero_width_matches) > 0

        details = []
        if homoglyph_matches:
            details.append(f"Detected {len(homoglyph_matches)} Cyrillic/Greek homoglyph character substitutions.")
        if zero_width_matches:
            details.append(f"Detected {len(zero_width_matches)} hidden zero-width or formatting control characters.")

        readability = cls.compute_readability(sanitized)

        return {
            "sanitized_text": sanitized,
            "has_obfuscation": has_obfuscation,
            "homoglyphs_detected": len(homoglyph_matches),
            "zero_width_chars_detected": len(zero_width_matches),
            "obfuscation_details": details,
            "readability": readability
        }

    @staticmethod
    def count_syllables(word: str) -> int:
        word = word.lower().strip(".:;?!")
        if not word:
            return 1
        count = 0
        vowels = "aeiouy"
        if word[0] in vowels:
            count += 1
        for i in range(1, len(word)):
            if word[i] in vowels and word[i - 1] not in vowels:
                count += 1
        if word.endswith("e") and not word.endswith("le") and count > 1:
            count -= 1
        return max(1, count)

    @classmethod
    def compute_readability(cls, text: str) -> Dict[str, Any]:
        if not text or not text.strip():
            return {
                "flesch_reading_ease": 100.0,
                "grade_level": "Grade 1-2 (Elementary)",
                "reading_level_desc": "Very Easy",
                "avg_sentence_len": 0.0,
                "reading_time_minutes": 0.0
            }

        words = re.findall(r'\b[A-Za-z0-9\'-]+\b', text)
        sentences = [s for s in re.split(r'[.!?]+', text) if s.strip()]

        total_words = len(words)
        total_sentences = max(1, len(sentences))

        if total_words == 0:
            return {
                "flesch_reading_ease": 100.0,
                "grade_level": "Grade 1-2",
                "reading_level_desc": "Very Easy",
                "avg_sentence_len": 0.0,
                "reading_time_minutes": 0.0
            }

        total_syllables = sum(cls.count_syllables(w) for w in words)

        # Flesch Reading Ease Formula: 206.835 - 1.015 * (words/sentences) - 84.6 * (syllables/words)
        asl = total_words / total_sentences
        asw = total_syllables / total_words
        flesch_score = 206.835 - (1.015 * asl) - (84.6 * asw)
        flesch_score = round(max(0.0, min(100.0, flesch_score)), 1)

        # Flesch-Kincaid Grade Level: 0.39 * (words/sentences) + 11.8 * (syllables/words) - 15.59
        fk_grade = (0.39 * asl) + (11.8 * asw) - 15.59
        fk_grade = round(max(1.0, fk_grade), 1)

        if flesch_score >= 80:
            level_desc = "Very Easy (Middle School)"
        elif flesch_score >= 60:
            level_desc = "Standard (High School)"
        elif flesch_score >= 40:
            level_desc = "Fairly Difficult (College Undergraduate)"
        elif flesch_score >= 20:
            level_desc = "Difficult (University Graduate)"
        else:
            level_desc = "Very Complex (Academic / Scientific)"

        reading_time_mins = round(total_words / 220.0, 1)  # average 220 wpm

        return {
            "flesch_reading_ease": flesch_score,
            "fk_grade_level": fk_grade,
            "grade_level": f"Grade {fk_grade}",
            "reading_level_desc": level_desc,
            "avg_sentence_len": round(asl, 1),
            "reading_time_minutes": max(0.1, reading_time_mins)
        }
