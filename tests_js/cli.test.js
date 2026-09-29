const assert = require("assert");
const { execSync } = require("child_process");
const path = require("path");
const {
    scan,
    PlagiarismChecker,
    AIDetector,
    AcademicParaphraser,
    AcademicStudentCoach,
    DocumentExtractor,
    CitationGenerator,
    DraftComparator,
    CertificateGenerator,
    EvidenceAnalyzer,
    WritingCleanup,
    buildCheckSummary
} = require("../lib/index");

console.log("🧪 Starting Plagiarism Detector Pro JavaScript & CLI Test Suite...\n");

// 1. Test Paraphraser
console.log("Testing AcademicParaphraser...");
const paraRes = AcademicParaphraser.synthesizeSentence(
    "Deep neural networks learn representations from massive text corpora.",
    "Attention Is All You Need",
    "Attention Is All You Need"
);
assert.strictEqual(paraRes.suggestions.length, 3);
assert.ok(paraRes.suggestions[0].text.includes("According to Attention Is All You Need"));
console.log("✓ AcademicParaphraser passed.");

// 2. Test Student Coach: Claims & Tone
console.log("Testing AcademicStudentCoach claims & tone...");
const coachText = "Studies show that machine learning is basically a big deal. However, 85% of models fail.";
const claims = AcademicStudentCoach.scanUnsupportedClaims(coachText);
assert.ok(claims.length >= 1);
assert.ok(claims.some(c => c.claim_marker.includes("Studies show") || c.claim_marker.includes("85%")));

const tone = AcademicStudentCoach.analyzeToneAndVocabulary(coachText);
assert.ok(tone.length >= 1);
assert.ok(tone.some(t => t.matched_term.toLowerCase() === "basically" || t.matched_term.toLowerCase() === "big deal"));
console.log("✓ AcademicStudentCoach claims and tone passed.");

// 3. Test Student Coach: Reference Alphabetizer
console.log("Testing AcademicStudentCoach alphabetizer...");
const rawRefs = "Vaswani, A. (2017). Attention.\nBrown, T. (2020). GPT-3.\nAchiam, J. GPT-4.";
const alphaRes = AcademicStudentCoach.alphabetizeAndFormatReferences(rawRefs);
assert.strictEqual(alphaRes.count, 3);
assert.ok(alphaRes.sorted_references[0].startsWith("Achiam"));
assert.ok(alphaRes.sorted_references[1].startsWith("Brown"));
assert.ok(alphaRes.sorted_references[2].startsWith("Vaswani"));
assert.ok(alphaRes.issues.length > 0); // Achiam missing year
console.log("✓ AcademicStudentCoach alphabetizer passed.");

// 4. Test Student Coach: Thesis Evaluator
console.log("Testing AcademicStudentCoach thesis evaluator...");
const thesisText = "In this paper, we hypothesize that transformer architectures optimize representation learning. We evaluate our method using empirical benchmarks. Our findings demonstrate fundamental significance.";
const thesisRes = AcademicStudentCoach.evaluateThesisAbstract(thesisText);
assert.ok(thesisRes.score >= 80);
assert.strictEqual(thesisRes.has_hypothesis, true);
assert.strictEqual(thesisRes.has_method, true);
assert.strictEqual(thesisRes.has_significance, true);
console.log("✓ AcademicStudentCoach thesis evaluator passed.");

// 5. Test AI Detector
console.log("Testing AIDetector...");
const aiText = "Furthermore, it is important to note that the holistic approach plays a pivotal role in the seamless integration. In conclusion, this vibrant tapestry is a testament to innovation.";
const aiRes = AIDetector.analyze(aiText);
assert.ok(aiRes.ai_probability > 30.0);
assert.strictEqual(aiRes.pattern_version, "2.1.0");
assert.strictEqual(aiRes.categories.length, 9);
const emDashRes = AIDetector.analyze(("The documented result—recorded after review—was retained for the final analysis. ").repeat(18));
assert.strictEqual(emDashRes.style_metrics.em_dash_count, 36);
assert.ok(emDashRes.categories.find(row => row.id === "punctuation").score > 0);
assert.ok(emDashRes.assessment_scope.includes("not evidence"));

const provenanceRes = AIDetector.analyze(
    "Please fill in [Your Name] before submitting. See details citeturn0search0 and also " +
    "contentReference[oaicite:0]{index=0} here. Visit https://example.com/report?utm_source=chatgpt.com for the source."
);
assert.strictEqual(provenanceRes.provenance_flags_count, 4);
assert.deepStrictEqual(
    new Set(provenanceRes.provenance_flags.map(row => row.kind)),
    new Set(["unfilled template placeholder", "AI-assistant citation markup", "AI-tool tracking link"])
);
const cleanProvenanceRes = AIDetector.analyze(
    "The result is consistent with prior work [1]. See [Smith, 2024] for details, and [sic] as quoted. " +
    "Refer to [Figure 1] and visit https://example.com/report?utm_source=google.com for the dataset."
);
assert.strictEqual(cleanProvenanceRes.provenance_flags_count, 0);

const allClaims = AcademicStudentCoach.scanClaims("Studies show that feedback helps (Smith, 2024). 85% of students revised their paper.");
assert.strictEqual(allClaims.length, 2);
assert.strictEqual(allClaims.filter(claim => claim.has_citation).length, 1);
const evidenceRes = EvidenceAnalyzer.analyze(allClaims, { in_text_citations_count: 1, unlinked_citations_count: 0 }, []);
assert.strictEqual(evidenceRes.claim_citation_coverage_pct, 50.0);
assert.strictEqual(evidenceRes.evidence_score, 68.8);
console.log("✓ AIDetector passed.");

// 5b. Test WritingCleanup (deterministic, offline word-swap cleanup)
console.log("Testing WritingCleanup...");
const cleanupText = "This holistic approach plays a pivotal role and it is important to note we leverage a robust framework.";
const cleanupEdits = WritingCleanup.suggestEdits(cleanupText);
const cleanupSwapped = Object.fromEntries(cleanupEdits.map(e => [e.original, e.replacement]));
assert.strictEqual(cleanupSwapped["holistic approach"], "overall approach");
assert.strictEqual(cleanupSwapped["pivotal role"], "important role");
assert.strictEqual(cleanupSwapped["leverage"], "use");
assert.strictEqual(cleanupSwapped["robust"], "reliable");
assert.ok(!("it is important to note" in cleanupSwapped), "judgment-call phrases must not be auto-appliable");
const cleanupResult = WritingCleanup.applyEdits(cleanupText, cleanupEdits);
assert.ok(cleanupResult.includes("an important role"), "a -> an fix-up should apply around the swapped word");
assert.ok(cleanupResult.includes("it is important to note"), "judgment-call phrase must stay untouched");
assert.ok(!cleanupResult.includes("leverage") && !cleanupResult.includes("robust"));
const cleanupPartial = WritingCleanup.applyEdits(cleanupText, cleanupEdits.filter(e => e.original === "leverage"));
assert.ok(cleanupPartial.includes("robust") && cleanupPartial.includes("use a"));
console.log("✓ WritingCleanup passed.");

// 5c. Test buildCheckSummary (combines ai_analysis + evidence_analysis into one verdict)
console.log("Testing buildCheckSummary...");
const provenanceAnalysis = AIDetector.analyze("Please review this draft, [Your Name], before the growth claim is finalized.");
const emptyEvidence = EvidenceAnalyzer.analyze([], { in_text_citations_count: 0 }, []);
const provenanceSummary = buildCheckSummary(provenanceAnalysis, emptyEvidence);
assert.strictEqual(provenanceSummary.verdict, "needs_review");
assert.ok(provenanceSummary.provenance_flags_count > 0);
assert.strictEqual(provenanceSummary.top_fixes[0].kind, "provenance");
assert.strictEqual(provenanceSummary.top_fixes[0].priority, "critical");

const cleanAnalysis = AIDetector.analyze(
    "Photosynthesis converts light into chemical energy stored in glucose molecules, a process first " +
    "quantified experimentally by Jan Ingenhousz in 1779 through controlled observation of oxygen " +
    "bubbles forming on submerged leaves under sunlight."
);
const cleanSummary = buildCheckSummary(cleanAnalysis, emptyEvidence);
assert.strictEqual(cleanSummary.verdict, "clear");
assert.deepStrictEqual(cleanSummary.reasons, []);

const insufficientSummary = buildCheckSummary(AIDetector.analyze(""), EvidenceAnalyzer.analyze([], {}, []));
assert.strictEqual(insufficientSummary.verdict, "insufficient_text");
console.log("✓ buildCheckSummary passed.");

// 6. Test Draft Comparator
console.log("Testing DraftComparator...");
const cmpRes = DraftComparator.compare(
    "Linear regression models predict outcomes.",
    "Linear regression models predict outcomes. Adam optimizer accelerates convergence."
);
assert.strictEqual(cmpRes.unchanged_count, 1);
assert.strictEqual(cmpRes.added_count, 1);
assert.strictEqual(cmpRes.words_delta > 0, true);
console.log("✓ DraftComparator passed.");

// 7. Test Local Plagiarism Checker & Shingling
console.log("Testing PlagiarismChecker...");
const checker = new PlagiarismChecker(path.join(__dirname, "..", "sources"));
const scanRes = checker.analyze("Supervised learning models predict continuous outcomes via linear regression.");
assert.ok(typeof scanRes.overall_similarity === "number");
console.log("✓ PlagiarismChecker passed.");

// 8. Test Citation Generator
console.log("Testing CitationGenerator...");
CitationGenerator.resolveCitation("1706.03762").then(citeRes => {
    assert.ok(citeRes.bibtex.includes("@article"));
    assert.ok(citeRes.apa.length > 10);
    assert.ok(citeRes.mla.length > 10);
    assert.ok(citeRes.ieee.length > 10);
    console.log("✓ CitationGenerator passed.");

    // 9. Test CLI Execution
    console.log("Testing CLI binary execution...");
    const cliPath = path.join(__dirname, "..", "bin", "plag.js");

    const helpOut = execSync(`node "${cliPath}" --help`).toString();
    assert.ok(helpOut.includes("Plagiarism Detector Pro CLI"));

    const paraOut = execSync(`node "${cliPath}" paraphrase "Linear regression models predict outcomes." --json`).toString();
    const paraJson = JSON.parse(paraOut);
    assert.strictEqual(paraJson.suggestions.length, 3);

    const coachOut = execSync(`node "${cliPath}" coach "Studies show that AI is basically a big deal." --json`).toString();
    const coachJson = JSON.parse(coachOut);
    assert.ok(coachJson.unsupported_claims.length > 0);

    const diffOut = execSync(`node "${cliPath}" diff "Draft one text." "Draft one text. Plus new revision." --json`).toString();
    const diffJson = JSON.parse(diffOut);
    assert.strictEqual(diffJson.unchanged_count, 1);

    const auditOut = execSync(`node "${cliPath}" audit "In our previous work, we tested." --json`).toString();
    const auditJson = JSON.parse(auditOut);
    assert.strictEqual(auditJson.is_anonymity_compliant, false);

    const certOut = execSync(`node "${cliPath}" certificate "In this paper we examine deep models." --name "Jane Doe" --title "Deep Learning" --json`).toString();
    const certJson = JSON.parse(certOut);
    assert.ok(certJson.certificate_id.startsWith("ANALYSIS-"));
    const certInput = { studentName: 'Jane Doe', paperTitle: 'Deep Learning', plagiarismScore: 12,
        aiScore: 8, wordCount: 7, text: 'In this paper we examine deep models.' };
    assert.strictEqual(CertificateGenerator.generate(certInput).sha256_hash,
        CertificateGenerator.generate(certInput).sha256_hash);

    const batchOut = execSync(`node "${cliPath}" batch "${path.join(__dirname, '..', 'sources')}" --json`).toString();
    const batchJson = JSON.parse(batchOut);
    assert.ok(batchJson.total_submissions > 0);

    const scanOut = execSync(`node "${cliPath}" scan "It is important to note that we leverage a comprehensive framework. Studies show that many organizations report significant improvements when this method is applied."`).toString();
    assert.ok(scanOut.includes("TOP FIXES"));
    assert.ok(scanOut.includes("try: use"));
    assert.ok(scanOut.includes("Unsupported claims"));

    const cleanupOut = execSync(`node "${cliPath}" cleanup "This holistic approach plays a pivotal role and we leverage a robust framework." --apply`).toString();
    assert.ok(cleanupOut.includes("DETERMINISTIC WRITING CLEANUP"));
    assert.ok(cleanupOut.includes('"leverage"') && cleanupOut.includes('"use"'));
    assert.ok(cleanupOut.includes("CLEANED TEXT"));
    assert.ok(cleanupOut.includes("an important role"));
    assert.ok(!cleanupOut.split("CLEANED TEXT:")[1].includes("leverage"));

    const checkOut = execSync(`node "${cliPath}" check "Please review this draft, [Your Name], before the growth claim is finalized." --json`).toString();
    const checkJson = JSON.parse(checkOut);
    assert.strictEqual(checkJson.verdict, "needs_review");
    assert.strictEqual(checkJson.top_fixes[0].kind, "provenance");

    console.log("✓ CLI binary execution tests passed.");
    console.log("\n🎉 ALL JAVASCRIPT & CLI TESTS PASSED SUCCESSFULLY (14/14)!");
}).catch(err => {
    console.error("Test failure:", err);
    process.exit(1);
});
