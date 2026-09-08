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
    DraftComparator
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
console.log("✓ AIDetector passed.");

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

    console.log("✓ CLI binary execution tests passed.");
    console.log("\n🎉 ALL JAVASCRIPT & CLI TESTS PASSED SUCCESSFULLY (9/9)!");
}).catch(err => {
    console.error("Test failure:", err);
    process.exit(1);
});
