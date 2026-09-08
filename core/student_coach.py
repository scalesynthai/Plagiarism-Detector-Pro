import re
from typing import Dict, List, Any, Tuple


class AcademicStudentCoach:
    """
    Student Writing & Academic Integrity Coach.
    Features:
      1. Unsupported Claim & Missing Citation Scanner
      2. Scholarly Tone & Formal Vocabulary Booster
      3. Reference List Alphabetizer & Formatter
      4. Thesis & Abstract Strength Evaluator
    """

    INFORMAL_TERMS = {
        r'\ba lot of\b': ["a substantial proportion of", "numerous", "an extensive quantity of"],
        r'\bbasically\b': ["fundamentally", "primarily", "essentially"],
        r'\bget rid of\b': ["eliminate", "mitigate", "eradicate"],
        r'\bbig impact\b': ["significant effect", "substantial influence", "pronounced outcome"],
        r'\bgood results\b': ["statistically significant outcomes", "favorable empirical metrics", "robust performance"],
        r'\btalk about\b': ["discuss", "examine", "articulate", "analyze"],
        r'\bshows clearly\b': ["substantiates", "empirically illustrates", "demonstrates"],
        r'\breally important\b': ["paramount", "critical", "pivotal", "of foundational importance"],
        r'\bthings\b': ["factors", "variables", "phenomena", "elements", "mechanisms"],
        r'\bkind of\b': ["moderately", "partially", "to a certain degree"],
        r'\bsort of\b': ["qualitatively similar to", "resembling"],
        r'\ba bunch of\b': ["a cluster of", "an array of", "a multiplicity of"],
        r'\bcannot be denied\b': ["evidence indicates", "literature demonstrates"],
        r'\beveryone knows\b': ["it is widely recognized in scholarly consensus that"],
        r'\bdeal with\b': ["address", "manage", "intervene upon"],
        r'\bfind out\b': ["ascertain", "determine", "uncover"],
        r'\bmake sure\b': ["ensure", "verify", "ascertain"],
        r'\blooked at\b': ["investigated", "evaluated", "scrutinized"],
    }

    CLAIM_MARKERS = [
        r'\b(?:studies|research|scholars|scientists|experts|investigators|literature)\s+(?:show|shows|prove|proves|suggest|suggests|state|states|found|demonstrate|demonstrates)\b',
        r'\b(?:it is (?:proven|established|known|evident|widely accepted|acknowledged))\b',
        r'\b(?:\d+%\s+of|\d+\s+percent\s+of)\b',
        r'\b(?:according to recent (?:findings|reports|data|surveys))\b',
        r'\b(?:has been shown to (?:cause|reduce|increase|improve|lead to))\b',
    ]

    CITATION_PATTERN = re.compile(
        r'\((?:[A-Z][a-zA-Z\s\.\,\&]+(?:et al\.)?,\s*\d{4}[a-z]?(?:;\s*[A-Z][a-zA-Z\s\.\,\&]+(?:et al\.)?,\s*\d{4}[a-z]?)*|\d{4})\)|\[\d+\]'
    )

    @classmethod
    def scan_unsupported_claims(cls, text: str) -> List[Dict[str, Any]]:
        """
        Flags empirical, factual, or statistical assertions that lack parenthetical or numeric citations.
        """
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+|\n+', text) if len(s.strip()) > 20]
        unsupported = []

        for s in sentences:
            has_cite = bool(cls.CITATION_PATTERN.search(s))
            if has_cite:
                continue

            for marker in cls.CLAIM_MARKERS:
                match = re.search(marker, s, re.I)
                if match:
                    unsupported.append({
                        "sentence": s,
                        "claim_marker": match.group(0),
                        "recommendation": f"Sentence contains empirical assertion ('{match.group(0)}') without a cited authority. Insert (Author, Year) or numeric reference.",
                    })
                    break

        return unsupported

    @classmethod
    def analyze_tone_and_vocabulary(cls, text: str) -> List[Dict[str, Any]]:
        """
        Identifies conversational words and suggests scholarly alternatives.
        """
        suggestions = []
        for pattern, replacements in cls.INFORMAL_TERMS.items():
            matches = list(re.finditer(pattern, text, re.I))
            for m in matches:
                start = max(0, m.start() - 25)
                end = min(len(text), m.end() + 25)
                snippet = "..." + text[start:end].replace("\n", " ") + "..."
                
                suggestions.append({
                    "matched_term": m.group(0),
                    "context_snippet": snippet,
                    "scholarly_replacements": replacements,
                    "tip": f"Replace conversational phrase '{m.group(0)}' with scholarly formal vocabulary."
                })

        return suggestions[:12]

    @classmethod
    def alphabetize_and_format_references(cls, references_text: str) -> Dict[str, Any]:
        """
        Sorts bibliography entries strictly alphabetically by primary author last name,
        validates year formatting, and identifies missing DOIs.
        """
        lines = [line.strip() for line in references_text.split('\n') if len(line.strip()) > 10]
        if not lines:
            return {"sorted_references": [], "count": 0, "issues": []}

        parsed_entries = []
        issues = []

        for idx, line in enumerate(lines):
            # Clean numbered prefixes e.g. "1. " or "[1]"
            clean_line = re.sub(r'^(\[\d+\]|\d+[\.\)]\s*)', '', line).strip()
            
            # Extract author sort key (first word or last name before comma/parenthesis)
            author_match = re.match(r'^([A-Z][a-zA-Z\-\'\`]+)', clean_line)
            sort_key = author_match.group(1).lower() if author_match else clean_line.lower()

            # Check year
            has_year = bool(re.search(r'\b(19\d\d|20\d\d)\b', clean_line))
            if not has_year:
                issues.append(f"Entry #{idx + 1} ('{clean_line[:40]}...'): Missing publication year.")

            # Check DOI / URL
            has_doi = bool(re.search(r'(10\.\d{4,9}/|doi\.org|http)', clean_line))

            parsed_entries.append({
                "original": line,
                "cleaned": clean_line,
                "sort_key": sort_key,
                "has_year": has_year,
                "has_doi": has_doi,
            })

        parsed_entries.sort(key=lambda x: x["sort_key"])
        sorted_refs = [e["cleaned"] for e in parsed_entries]

        return {
            "sorted_references": sorted_refs,
            "count": len(sorted_refs),
            "formatted_text": "\n\n".join(sorted_refs),
            "issues": issues,
        }

    @classmethod
    def evaluate_thesis_abstract(cls, text: str) -> Dict[str, Any]:
        """
        Evaluates the opening abstract/thesis for scientific completeness.
        """
        first_para = text.strip().split('\n\n')[0] if '\n\n' in text else text[:1000]
        words = first_para.split()
        word_count = len(words)

        has_hypothesis = bool(re.search(r'\b(hypothesize|argue|propose|demonstrate|investigate|examine|aims to|objective)\b', first_para, re.I))
        has_method = bool(re.search(r'\b(using|method|methodology|dataset|experiment|analyzed|evaluated|simulation|framework)\b', first_para, re.I))
        has_significance = bool(re.search(r'\b(crucial|significance|implication|contributes|advance|fundamental|impact)\b', first_para, re.I))

        score = 40
        if has_hypothesis: score += 25
        if has_method: score += 20
        if has_significance: score += 15

        feedback = []
        if not has_hypothesis:
            feedback.append("State your central thesis, hypothesis, or research question explicitly.")
        if not has_method:
            feedback.append("Specify the analytical methodology, empirical dataset, or experimental approach used.")
        if not has_significance:
            feedback.append("Highlight the broader academic significance or practical implications of your findings.")

        return {
            "score": min(100, score),
            "word_count": word_count,
            "has_hypothesis": has_hypothesis,
            "has_method": has_method,
            "has_significance": has_significance,
            "feedback": feedback if feedback else ["Opening paragraph possesses clear thesis framing and methodology context."],
        }
