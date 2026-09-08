import re
from typing import Dict, List, Any, Optional


class AcademicParaphraser:
    """
    Synthesizes and paraphrases overlapping sentences into distinct,
    scholarly formulations with proper attribution and syntax restructuring.
    """

    TRANSITIONS = [
        "Specifically, empirical investigations indicate that",
        "Notably, prior research demonstrates that",
        "Furthermore, contemporary findings substantiate that",
        "In this context, domain literature reveals that",
        "As rigorously observed in experimental trials,",
    ]

    VERBS = [
        ("demonstrates", "establishes"),
        ("shows", "substantiates"),
        ("proves", "validates"),
        ("analyzes", "evaluates"),
        ("predicts", "estimates"),
        ("explains", "elucidates"),
        ("uses", "utilizes"),
        ("finds", "uncovers"),
        ("helps", "facilitates"),
    ]

    @classmethod
    def synthesize_sentence(
        cls,
        sentence: str,
        source_name: Optional[str] = None,
        source_title: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generates 3 distinct academic restructuring options:
        1. Active Inversion with Direct Attribution
        2. Passive Methodological Synthesis
        3. High-Density Conceptual Restructuring
        """
        clean_s = sentence.strip().rstrip(".!?")
        words = clean_s.split()
        if not words:
            return {"suggestions": []}

        clean_author = "the cited literature"
        if source_title:
            clean_author = f"{source_title}"
        elif source_name:
            clean_author = source_name.replace(".txt", "").replace(".pdf", "").replace("_", " ").title()

        # Option 1: Active Inversion with Authorial Attribution
        first_word_lower = words[0].lower() + " " + " ".join(words[1:])
        opt1 = f"According to {clean_author}, {first_word_lower}."

        # Option 2: Methodological Synthesis with Inversion
        syn_verb_applied = first_word_lower
        for old_v, new_v in cls.VERBS:
            if f" {old_v} " in syn_verb_applied:
                syn_verb_applied = syn_verb_applied.replace(f" {old_v} ", f" {new_v} ", 1)
                break
        
        opt2 = f"Empirical findings suggest that {syn_verb_applied} ({clean_author}, 2024)."

        # Option 3: High-Density Analytical Rephrasing
        if len(words) > 6:
            mid = len(words) // 2
            first_half = " ".join(words[:mid])
            second_half = " ".join(words[mid:])
            opt3 = f"Regarding {first_half.lower()}, subsequent analysis confirms that {second_half}."
        else:
            opt3 = f"Notably, {first_word_lower}, reflecting core principles documented in {clean_author}."

        return {
            "original_sentence": sentence,
            "source_attributed": clean_author,
            "suggestions": [
                {
                    "style": "Authorial Attribution (Active)",
                    "text": opt1,
                    "focus": "Direct scholarly attribution with formal introductory clause."
                },
                {
                    "style": "Methodological Synthesis (Passive)",
                    "text": opt2,
                    "focus": "Passive academic synthesis with parenthetical reference."
                },
                {
                    "style": "Analytical Restructuring (High-Density)",
                    "text": opt3,
                    "focus": "Sentence structure inversion with emphasis on findings."
                }
            ]
        }
