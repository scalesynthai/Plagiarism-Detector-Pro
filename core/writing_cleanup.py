"""Deterministic, offline, reviewable word-swap cleanup.

This is not a rewrite engine. It only ever applies the exact predictable-
vocabulary substitutions already surfaced as `suggestion` on writing-pattern
evidence (see core/ai_detector.py and THIRD_PARTY_NOTICES.md) -- a plain
word or short phrase in, a plain word or short phrase out, nothing
regenerated or paraphrased. Phrases needing editorial judgment (the ones
whose suggestion is a parenthetical instruction, not a replacement) are
never auto-applied; they stay a suggestion-only tip.

No network access, no external model, and no attempt to change how a
third-party AI detector scores the result: this is a mechanical find-and-
replace over what this project's own heuristic already flagged, run
locally, with every change shown for the writer to accept or reject.
"""

import re
from typing import Any, Dict, List, Optional, Tuple

from core.ai_detector import AIDetector

_ARTICLE_RE = re.compile(r"\b([Aa]n?)\s+$")
_PROTECTED_PATTERNS = (
    ("quotation", re.compile(r'["“][^"”\n]{1,2000}["”]')),
    ("inline code", re.compile(r"`[^`\n]+`|```[\s\S]*?```")),
    ("URL or DOI", re.compile(r"https?://\S+|\bdoi:\s*10\.\d{4,9}/\S+|\b10\.\d{4,9}/\S+", re.I)),
    ("LaTeX command or equation", re.compile(r"\\(?:cite|ref|eqref|url|doi)\{[^}]+\}|\$[^$\n]+\$")),
    ("citation", re.compile(r"\([^()\n]{0,100}\b(?:19|20)\d{2}[a-z]?[^()\n]{0,100}\)|\[\d+(?:\s*[-,]\s*\d+)*\]", re.I)),
)
_LENGTH_MODES = {"any", "same", "no_increase", "shorter"}


class WritingCleanup:
    """Builds and applies a reviewable list of predictable-vocabulary swaps."""

    @classmethod
    def _protected_spans(cls, text: str, protected_terms: Optional[List[str]] = None) -> List[Tuple[int, int, str]]:
        spans: List[Tuple[int, int, str]] = []
        for reason, pattern in _PROTECTED_PATTERNS:
            spans.extend((match.start(), match.end(), reason) for match in pattern.finditer(text))

        reference_heading = re.search(r"(?im)^\s*(references|bibliography|works cited)\s*$", text)
        if reference_heading:
            spans.append((reference_heading.start(), len(text), "reference section"))

        for raw_term in protected_terms or []:
            term = str(raw_term).strip()
            if not term:
                continue
            pattern = re.compile(rf"(?<!\w){re.escape(term)}(?!\w)", re.I)
            spans.extend((match.start(), match.end(), f'protected term: {term}') for match in pattern.finditer(text))
        return sorted(spans)

    @staticmethod
    def _length_allowed(edit: Dict[str, Any], length_mode: str) -> bool:
        original_words = len(re.findall(r"\b\w+\b", edit["original"]))
        replacement_words = len(re.findall(r"\b\w+\b", edit["replacement"]))
        edit["word_delta"] = replacement_words - original_words
        if length_mode == "same":
            return replacement_words == original_words
        if length_mode == "no_increase":
            return replacement_words <= original_words
        if length_mode == "shorter":
            return replacement_words < original_words
        return True

    @classmethod
    def review(cls, text: str, protected_terms: Optional[List[str]] = None,
               length_mode: str = "any") -> Dict[str, Any]:
        """Return eligible and excluded edits with explicit protection reasons."""
        if not isinstance(length_mode, str) or length_mode not in _LENGTH_MODES:
            raise ValueError("length_mode must be any, same, no_increase, or shorter.")
        spans = cls._protected_spans(text, protected_terms)
        candidates = cls._candidate_edits(text)
        eligible: List[Dict[str, Any]] = []
        excluded: List[Dict[str, Any]] = []
        for edit in candidates:
            overlap = next((reason for start, end, reason in spans
                            if edit["start"] < end and edit["end"] > start), None)
            if overlap:
                edit["excluded_reason"] = overlap
                excluded.append(edit)
                continue
            if not cls._length_allowed(edit, length_mode):
                edit["excluded_reason"] = f"excluded by {length_mode} length mode"
                excluded.append(edit)
                continue
            eligible.append(edit)
        for index, edit in enumerate(eligible):
            edit["index"] = index
        return {
            "edits": eligible,
            "excluded_edits": excluded,
            "edits_count": len(eligible),
            "excluded_count": len(excluded),
            "length_mode": length_mode,
            "protected_terms": [str(term).strip() for term in protected_terms or [] if str(term).strip()],
        }

    @classmethod
    def _candidate_edits(cls, text: str) -> List[Dict[str, Any]]:
        """Return the edit-eligible predictable-vocabulary findings for `text`.

        Deterministic: the same text always produces the same list, in the
        same order, with the same indices, so a client can display this list
        and later send back which indices to apply without re-sending the
        edit content itself.
        """
        analysis = AIDetector.analyze(text or "")
        predictability = next(
            (row for row in analysis.get("categories", []) if row.get("id") == "predictability"),
            None,
        )
        edits: List[Dict[str, Any]] = []
        for row in (predictability or {}).get("evidence", []):
            suggestion = row.get("suggestion")
            if not suggestion or suggestion.startswith("("):
                continue  # judgment call (a deletion/rewrite), not an auto-appliable swap
            edits.append({
                "start": row["start"], "end": row["end"],
                "original": row["text"], "replacement": suggestion,
                "category": "predictability",
            })
        edits.sort(key=lambda e: e["start"])
        return edits

    @classmethod
    def suggest_edits(cls, text: str, protected_terms: Optional[List[str]] = None,
                      length_mode: str = "any") -> List[Dict[str, Any]]:
        return cls.review(text or "", protected_terms, length_mode)["edits"]

    @staticmethod
    def apply_edits(text: str, edits: List[Dict[str, Any]]) -> str:
        """Apply non-overlapping edits to `text` and return the result.

        Each edit's start/end are absolute offsets into the original `text`
        (as produced by `suggest_edits`). A minimal a/an fix-up runs on the
        single article word immediately before each edit, since a plain
        word swap can otherwise leave "a important role" or similar. This
        does not fix any other grammar around an edit; that is exactly what
        the accept/reject review step is for.
        """
        if not edits:
            return text

        kept: List[Dict[str, Any]] = []
        for edit in sorted(edits, key=lambda e: e["start"]):
            if kept and edit["start"] < kept[-1]["end"]:
                continue  # overlapping with an already-kept edit; skip defensively
            kept.append(edit)

        resolved = []
        for edit in kept:
            start, end, replacement = edit["start"], edit["end"], edit["replacement"]
            match = _ARTICLE_RE.search(text[:start])
            if match and replacement and replacement[0].isalpha():
                needs_an = replacement[0].lower() in "aeiou"
                has_an = match.group(1).lower() == "an"
                if needs_an != has_an:
                    was_capitalized = match.group(1)[0] == "A"
                    fixed_article = ("An" if was_capitalized else "an") if needs_an else ("A" if was_capitalized else "a")
                    gap = text[match.end(1):start]
                    replacement = fixed_article + gap + replacement
                    start = match.start(1)
            resolved.append((start, end, replacement))

        out = text
        for start, end, replacement in sorted(resolved, key=lambda item: item[0], reverse=True):
            out = out[:start] + replacement + out[end:]
        return out
