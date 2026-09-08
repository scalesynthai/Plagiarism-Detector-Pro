import re
from typing import Dict, List, Any, Set, Tuple, Optional


class CitationValidator:
    """
    Academic In-Text Citation & Bibliography Integrity Validator.
    Supports APA, MLA, IEEE, and Chicago styles.
    """

    # In-text citation regex patterns
    PATTERNS = {
        "apa_parenthetical": r'\(([A-Z][a-zA-Z\s]+(?:,\s*(?:et\s+al\.|&\s*[A-Z][a-zA-Z\s]+))?,\s*\d{4}(?:,\s*p{1,2}\.?\s*\d+)?)\)',
        "apa_narrative": r'\b([A-Z][a-zA-Z]+(?:\s+(?:et\s+al\.|and\s+[A-Z][a-zA-Z]+))?)\s*\((19\d{2}|20\d{2})\)',
        "ieee_numeric": r'\[(\d+(?:\s*[-–,]\s*\d+)*)\]',
        "mla_author_page": r'\(([A-Z][a-zA-Z]+)\s+(\d{1,4})\)',
    }

    # Bibliography section header keywords
    BIBLIOGRAPHY_HEADERS = [
        r'\b(?:references|works\s+cited|bibliography|literature\s+cited|reference\s+list)\b'
    ]

    def split_manuscript_and_bibliography(self, text: str) -> Tuple[str, str]:
        """
        Separates the main text from the Bibliography / References section.
        """
        lines = text.split('\n')
        split_idx = -1

        for idx, line in enumerate(lines):
            clean_line = line.strip().lower()
            for header_pattern in self.BIBLIOGRAPHY_HEADERS:
                if re.fullmatch(header_pattern, clean_line) or re.match(r'^(?:#+|\d+\.|\*+)?\s*' + header_pattern + r'\s*[:#*]*$', clean_line):
                    split_idx = idx
                    break
            if split_idx != -1:
                break

        if split_idx != -1:
            body_text = "\n".join(lines[:split_idx]).strip()
            bib_text = "\n".join(lines[split_idx:]).strip()
            return body_text, bib_text
        return text, ""

    def extract_in_text_citations(self, text: str) -> List[Dict[str, Any]]:
        """
        Extracts all in-text citations from text with their style and location.
        """
        citations = []
        for style, pattern in self.PATTERNS.items():
            for match in re.finditer(pattern, text):
                citations.append({
                    "raw": match.group(0),
                    "content": match.group(1),
                    "style": style.split('_')[0].upper(),
                    "start": match.start(),
                    "end": match.end(),
                })
        # Sort citations by start position
        citations.sort(key=lambda x: x["start"])
        return citations

    def parse_bibliography_entries(self, bib_text: str) -> List[str]:
        """
        Extracts individual reference entries from the bibliography section.
        """
        if not bib_text:
            return []

        lines = bib_text.split('\n')
        entries = []
        current_entry = []

        for line in lines:
            stripped = line.strip()
            if not stripped:
                if current_entry:
                    entries.append(" ".join(current_entry))
                    current_entry = []
                continue

            # Ignore main header
            if any(re.search(h, stripped.lower()) for h in self.BIBLIOGRAPHY_HEADERS) and len(stripped.split()) < 4:
                continue

            # Check if line starts a new entry (e.g. [1], author name, or hanging indent)
            if re.match(r'^(?:\[\d+\]|\d+\.|\*|[A-Z][a-zA-Z]+,)', stripped) and current_entry:
                entries.append(" ".join(current_entry))
                current_entry = [stripped]
            else:
                current_entry.append(stripped)

        if current_entry:
            entries.append(" ".join(current_entry))

        return [e for e in entries if len(e) > 15]

    def has_in_text_citation(self, sentence: str) -> Tuple[bool, Optional[str]]:
        """
        Checks if a specific sentence contains an in-text citation.
        """
        for style, pattern in self.PATTERNS.items():
            match = re.search(pattern, sentence)
            if match:
                return True, match.group(0)
        return False, None

    def validate_citations(self, text: str) -> Dict[str, Any]:
        """
        Performs full academic citation and bibliography integrity check.
        """
        body_text, bib_text = self.split_manuscript_and_bibliography(text)
        citations = self.extract_in_text_citations(body_text)
        bib_entries = self.parse_bibliography_entries(bib_text)

        # Cross-reference check: check if citation author or number appears in bibliography
        matched_citations = []
        unmatched_citations = []

        for c in citations:
            raw = c["raw"]
            content = c["content"]
            # Extract key author surname or number
            key = re.sub(r'[,.\d\(\)\[\]]', '', content).split()[0] if not content.isdigit() else content
            
            is_in_bib = any(key.lower() in b.lower() for b in bib_entries) if bib_entries else True
            if is_in_bib:
                matched_citations.append(c)
            else:
                unmatched_citations.append(c)

        has_bib = bool(bib_entries)
        return {
            "has_bibliography": has_bib,
            "bibliography_entries_count": len(bib_entries),
            "in_text_citations_count": len(citations),
            "citations": citations,
            "bibliography_entries": bib_entries[:10],
            "body_text": body_text,
            "has_unlinked_citations": len(unmatched_citations) > 0 and has_bib,
            "unlinked_citations_count": len(unmatched_citations) if has_bib else 0,
        }
