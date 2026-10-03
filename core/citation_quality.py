"""Local citation-quality checks kept separate from style and plagiarism scores."""

import re
from typing import Any, Dict, List
from urllib.parse import urlparse


class CitationQualityReviewer:
    DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+\b", re.I)
    DOI_LIKE_RE = re.compile(r"\bdoi\s*:\s*([^\s,;]+)", re.I)
    URL_RE = re.compile(r"\bhttps?://[^\s<>\]\[\"']+", re.I)
    ISBN_RE = re.compile(r"\b(?:ISBN(?:-1[03])?\s*:?[\s-]*)?((?:97[89][\s-]?)?\d[\dXx\s-]{8,16}\d|\d[\dXx\s-]{8,16}[Xx])\b")

    @staticmethod
    def valid_isbn(value: str) -> bool:
        digits = re.sub(r"[^0-9Xx]", "", value)
        if len(digits) == 10:
            total = sum((10 - index) * (10 if char.upper() == 'X' else int(char)) for index, char in enumerate(digits))
            return total % 11 == 0
        if len(digits) == 13 and digits.isdigit():
            total = sum(int(char) * (1 if index % 2 == 0 else 3) for index, char in enumerate(digits[:12]))
            return (10 - total % 10) % 10 == int(digits[-1])
        return False

    @classmethod
    def analyze(cls, text: str, citation_analysis: Dict[str, Any]) -> Dict[str, Any]:
        issues: List[Dict[str, Any]] = []
        for match in cls.URL_RE.finditer(text):
            raw = match.group(0).rstrip('.,);')
            parsed = urlparse(raw)
            if not parsed.hostname or parsed.hostname in {"localhost"} or parsed.hostname.endswith((".local", ".internal")):
                issues.append({"type": "invalid", "code": "malformed_or_private_url", "value": raw, "start": match.start(), "end": match.start() + len(raw), "message": "URL is malformed or points to a local/private name."})
        for match in cls.DOI_LIKE_RE.finditer(text):
            value = match.group(1).rstrip('.,);')
            if not cls.DOI_RE.fullmatch(value):
                issues.append({"type": "invalid", "code": "invalid_doi_syntax", "value": value, "start": match.start(1), "end": match.end(1), "message": "DOI syntax is invalid."})
        for match in cls.ISBN_RE.finditer(text):
            value = match.group(1)
            if not cls.valid_isbn(value):
                issues.append({"type": "invalid", "code": "invalid_isbn_checksum", "value": value, "start": match.start(1), "end": match.end(1), "message": "ISBN checksum is invalid."})

        entries = citation_analysis.get("bibliography_entries_all", citation_analysis.get("bibliography_entries", [])) or []
        normalized = [re.sub(r"\W+", " ", entry.lower()).strip() for entry in entries]
        seen = {}
        for index, value in enumerate(normalized):
            if value in seen:
                issues.append({"type": "invalid", "code": "duplicate_reference", "value": entries[index], "start": None, "end": None, "message": f"Duplicates bibliography entry {seen[value] + 1}."})
            else:
                seen[value] = index

        cited_entries = set()
        for citation in citation_analysis.get("linked_citations", []) or []:
            content = citation.get("content", "")
            surname = re.search(r"[A-Z][\w’'-]+", content)
            numbers = re.findall(r"\d+", content) if citation.get("style") == "IEEE" else []
            for index, entry in enumerate(entries):
                if surname and re.search(r"\b" + re.escape(surname.group()) + r"\b", entry, re.I):
                    cited_entries.add(index)
                if numbers and any(re.match(r"^\[?" + re.escape(number) + r"(?:\]|\.)", entry) for number in numbers):
                    cited_entries.add(index)
        for index, entry in enumerate(entries):
            if index not in cited_entries:
                issues.append({"type": "unverified", "code": "uncited_reference", "value": entry, "start": None, "end": None, "message": "Reference entry was not linked to a recognized in-text citation."})
        for citation in citation_analysis.get("unlinked_citations", []) or []:
            issues.append({"type": "invalid", "code": "citation_without_reference", "value": citation.get("raw"), "start": citation.get("start"), "end": citation.get("end"), "message": "Citation marker has no corresponding recognized reference entry."})
        return {
            "status": "issues_found" if issues else "no_local_issues_found",
            "issues": issues,
            "issue_count": len(issues),
            "network_verification": {"status": "not_requested", "available_states": ["unreachable", "access_restricted", "unverified", "metadata_mismatch"], "note": "A failed request would not prove fabrication. Network verification is disabled by default."},
            "claim_support": {"status": "requires_human_review", "note": "Resolution and valid metadata do not establish that a source supports a claim."},
        }
