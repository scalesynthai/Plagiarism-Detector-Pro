"""Academic claim-to-citation coverage and source-quality diagnostics.

The mechanical pairing and renormalized component score are adapted from the
MIT-licensed HyperResearch project. This analyzer verifies citation structure
and coverage; it does not claim that a cited source semantically proves a claim.
"""

from typing import Any, Dict, List


class EvidenceAnalyzer:
    """Build a transparent evidence-integrity profile from existing diagnostics."""

    SOURCE_TIERS = {
        "global_academic": 1.0,
        "institutional": 0.9,
        "arxiv": 0.8,
        "openalex": 0.9,
        "crossref": 0.9,
        "wikipedia": 0.55,
        "web": 0.45,
    }

    @classmethod
    def analyze(
        cls,
        claims: List[Dict[str, Any]],
        citation_analysis: Dict[str, Any],
        sources: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        claims = claims or []
        citation_analysis = citation_analysis or {}
        sources = sources or []
        claim_count = len(claims)
        cited_claims = sum(1 for claim in claims if claim.get("has_citation"))
        unsupported = claim_count - cited_claims
        claim_coverage = round(cited_claims / claim_count * 100, 1) if claim_count else None

        citation_count = int(citation_analysis.get("in_text_citations_count", 0) or 0)
        unlinked_count = int(citation_analysis.get("unlinked_citations_count", 0) or 0)
        linked_count = max(0, citation_count - unlinked_count)
        link_rate = round(linked_count / citation_count * 100, 1) if citation_count else None

        source_rows = []
        for source in sources:
            source_type = str(source.get("source_type") or "institutional").lower()
            tier_score = cls.SOURCE_TIERS.get(source_type, 0.6)
            source_rows.append({
                "name": source.get("filename") or source.get("source") or "Unknown source",
                "source_type": source_type,
                "quality_score": round(tier_score * 100, 1),
                "basis": "Source-type heuristic; publication authority and claim support are not verified.",
            })
        source_quality = round(sum(row["quality_score"] for row in source_rows) / len(source_rows), 1) if source_rows else None

        components = []
        if claim_coverage is not None:
            components.append((0.5, claim_coverage))
        if link_rate is not None:
            components.append((0.3, link_rate))
        if source_quality is not None:
            components.append((0.2, source_quality))
        if components:
            available_weight = sum(weight for weight, _ in components)
            evidence_score = round(sum(weight * value for weight, value in components) / available_weight, 1)
        else:
            evidence_score = None

        if evidence_score is None:
            band = "Not enough evidence data"
        elif evidence_score >= 85:
            band = "Strong structural coverage"
        elif evidence_score >= 60:
            band = "Partial structural coverage"
        else:
            band = "Coverage needs review"

        return {
            "evidence_score": evidence_score,
            "band": band,
            "claim_count": claim_count,
            "cited_claims_count": cited_claims,
            "unsupported_claims_count": unsupported,
            "claim_citation_coverage_pct": claim_coverage,
            "citation_count": citation_count,
            "linked_citations_count": linked_count,
            "unlinked_citations_count": unlinked_count,
            "citation_link_rate_pct": link_rate,
            "source_quality_score": source_quality,
            "source_quality": source_rows[:20],
            "claim_pairs": claims[:30],
            "method": "Available components are weighted and renormalized: claim coverage 50%, bibliography links 30%, source-type quality 20%.",
            "limitation": "Citation syntax and bibliography linkage do not prove that a source exists, is reliable, or supports the sentence. Verify each important claim against the source.",
        }
