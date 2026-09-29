/** Structural evidence scoring adapted from MIT-licensed HyperResearch. */
class EvidenceAnalyzer {
    static analyze(claims = [], citationAnalysis = {}, sources = []) {
        const claimCount = claims.length;
        const citedClaims = claims.filter(claim => claim.has_citation).length;
        const unsupported = claimCount - citedClaims;
        const claimCoverage = claimCount ? +(citedClaims / claimCount * 100).toFixed(1) : null;
        const citationCount = Number(citationAnalysis.in_text_citations_count || 0);
        const unlinkedValue = citationAnalysis.unlinked_citations_count;
        const unlinked = unlinkedValue == null ? null : Number(unlinkedValue || 0);
        const linked = unlinked == null ? null : Math.max(0, citationCount - unlinked);
        const linkRate = citationCount && linked != null ? +(linked / citationCount * 100).toFixed(1) : null;
        const sourceRows = sources.map(source => ({
            name: source.filename || source.source || 'Unknown source',
            source_type: source.source_type || 'institutional',
            quality_score: source.source_type === 'web' ? 45 : 90,
            basis: 'Source-type heuristic; publication authority and claim support are not verified.'
        }));
        const sourceQuality = sourceRows.length ? +(sourceRows.reduce((sum, row) => sum + row.quality_score, 0) / sourceRows.length).toFixed(1) : null;
        const components = [];
        if (claimCoverage != null) components.push([0.5, claimCoverage]);
        if (linkRate != null) components.push([0.3, linkRate]);
        if (sourceQuality != null) components.push([0.2, sourceQuality]);
        const weight = components.reduce((sum, row) => sum + row[0], 0);
        const evidenceScore = weight ? +(components.reduce((sum, row) => sum + row[0] * row[1], 0) / weight).toFixed(1) : null;
        return {
            evidence_score: evidenceScore,
            band: evidenceScore == null ? 'Not enough evidence data' : evidenceScore >= 85 ? 'Strong structural coverage' : evidenceScore >= 60 ? 'Partial structural coverage' : 'Coverage needs review',
            claim_count: claimCount,
            cited_claims_count: citedClaims,
            unsupported_claims_count: unsupported,
            claim_citation_coverage_pct: claimCoverage,
            citation_count: citationCount,
            linked_citations_count: linked,
            unlinked_citations_count: unlinked,
            citation_link_rate_pct: linkRate,
            source_quality_score: sourceQuality,
            source_quality: sourceRows.slice(0, 20),
            claim_pairs: claims.slice(0, 30),
            method: 'Available components are weighted and renormalized: claim coverage 50%, bibliography links 30%, source-type quality 20%.',
            limitation: 'Citation syntax and bibliography linkage do not prove that a source exists, is reliable, or supports the sentence.'
        };
    }
}

module.exports = { EvidenceAnalyzer };
