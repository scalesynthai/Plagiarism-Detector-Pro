#!/usr/bin/env node

/**
 * Plagiarism Detector Pro CLI
 * 100% Standalone Offline Academic Originality, AI Detector & Student Coach CLI
 */

const fs = require("fs");
const path = require("path");
const {
    scan,
    AcademicParaphraser,
    AcademicStudentCoach,
    PhdResearchAuditor,
    DocumentExtractor,
    CitationGenerator,
    DraftComparator,
    CertificateGenerator,
    BatchProcessor
} = require("../lib/index");

const args = process.argv.slice(2);
const command = args[0] || "help";

// ANSI colors
const colors = {
    reset: "\x1b[0m",
    bold: "\x1b[1m",
    cyan: "\x1b[36m",
    green: "\x1b[32m",
    yellow: "\x1b[33m",
    red: "\x1b[31m",
    magenta: "\x1b[35m",
    blue: "\x1b[34m",
    gray: "\x1b[90m"
};

function printBanner() {
    console.log(`\n${colors.bold}${colors.cyan}======================================================${colors.reset}`);
    console.log(`${colors.bold}${colors.cyan} 🎓 Plagiarism Detector Pro CLI (v1.0.0)${colors.reset}`);
    console.log(`${colors.gray} Enterprise Academic Originality, AI Detector & Coach (100% Offline)${colors.reset}`);
    console.log(`${colors.bold}${colors.cyan}======================================================${colors.reset}\n`);
}

function printHelp() {
    printBanner();
    console.log(`${colors.bold}USAGE:${colors.reset}`);
    console.log(`  ${colors.green}plag scan <file|text>${colors.reset}               Scan document or text for plagiarism & AI content`);
    console.log(`  ${colors.green}plag coach <file|text>${colors.reset}              Unsupported claims, tone booster & thesis score`);
    console.log(`  ${colors.green}plag audit <file|text>${colors.reset}              PhD & Conference double-blind pre-flight audit`);
    console.log(`  ${colors.green}plag paraphrase <sentence>${colors.reset}         Generate 3 academic restructurings & citations`);
    console.log(`  ${colors.green}plag cite <query>${colors.reset}                   Auto-generate BibTeX, APA, MLA, and IEEE`);
    console.log(`  ${colors.green}plag alphabetize <file|text>${colors.reset}        Auto-sort references & validate DOIs/years`);
    console.log(`  ${colors.green}plag diff <file1> <file2>${colors.reset}          Compare Draft 1 vs Draft 2 deltas`);
    console.log(`  ${colors.green}plag batch <dir|file1 file2...>${colors.reset}    Process class batch & print gradebook table`);
    console.log(`  ${colors.green}plag certificate <file|text>${colors.reset}        Generate verifiable Authorship Certificate`);
    console.log(`  ${colors.green}plag mcp${colors.reset}                           Launch Model Context Protocol (MCP) server for Claude/Codex`);
    console.log(`\n${colors.bold}OPTIONS:${colors.reset}`);
    console.log(`  ${colors.yellow}--json${colors.reset}                          Output results in raw JSON`);
    console.log(`  ${colors.yellow}--verbose${colors.reset}                       Show side-by-side matching sentence passages`);
    console.log(`  ${colors.yellow}--name <Student Name>${colors.reset}           Student full name for certificate`);
    console.log(`  ${colors.yellow}--title <Paper Title>${colors.reset}           Manuscript title for certificate`);
    console.log(`  ${colors.yellow}--source <name>${colors.reset}                 Source attribution key for paraphrasing`);
    console.log(`\n${colors.bold}EXAMPLES:${colors.reset}`);
    console.log(`  ${colors.gray}$ plag scan essay.docx${colors.reset}`);
    console.log(`  ${colors.gray}$ plag coach manuscript.tex${colors.reset}`);
    console.log(`  ${colors.gray}$ plag audit research_paper.pdf${colors.reset}`);
    console.log(`  ${colors.gray}$ plag batch ./student_submissions/${colors.reset}`);
    console.log(`  ${colors.gray}$ plag certificate essay.md --name "Jane Doe" --title "Deep Learning Essay"${colors.reset}`);
    console.log(`  ${colors.gray}$ plag mcp${colors.reset}\n`);
}

function getOption(flag) {
    const idx = args.indexOf(flag);
    return idx !== -1 ? args[idx + 1] : null;
}

async function main() {
    const isJson = args.includes("--json");
    const isVerbose = args.includes("--verbose");
    const sourceName = getOption("--source");
    const studentName = getOption("--name") || "Academic Scholar";
    const paperTitle = getOption("--title") || "Academic Manuscript";

    switch (command.toLowerCase()) {
        case "help":
        case "--help":
        case "-h":
            printHelp();
            break;

        case "scan": {
            const input = args[1];
            if (!input) {
                console.error(`${colors.red}Error: Missing document path or text to scan.${colors.reset}`);
                process.exit(1);
            }

            let text = input;
            if (fs.existsSync(input)) {
                text = DocumentExtractor.extractFromFile(input);
            }

            if (!isJson) {
                printBanner();
                console.log(`${colors.cyan}🔍 Scanning originality, AI content, and academic metrics...${colors.reset}\n`);
            }

            try {
                const res = await scan(text, {
                    excludeQuotes: args.includes("--exclude-quotes")
                });

                if (isJson) {
                    console.log(JSON.stringify(res, null, 2));
                    return;
                }

                const riskColor = res.safeassign_risk === "Low Risk" ? colors.green : (res.safeassign_risk === "Medium Risk" ? colors.yellow : colors.red);
                const aiColor = (res.ai_analysis && res.ai_analysis.ai_probability > 65) ? colors.red : colors.green;

                console.log(`${colors.bold}📊 ORIGINALITY & SAFEASSIGN METRICS:${colors.reset}`);
                console.log(`  • Plagiarism Similarity:  ${riskColor}${res.overall_similarity}% (${res.safeassign_risk})${colors.reset}`);
                if (res.ai_analysis) {
                    console.log(`  • AI-Generated Content:   ${aiColor}${res.ai_analysis.ai_probability}% (${res.ai_analysis.ai_risk_level})${colors.reset}`);
                    console.log(`  • Syntax Burstiness:      ${res.ai_analysis.burstiness}`);
                }
                console.log(`  • Total Analyzed Words:   ${res.total_words}`);
                console.log(`  • Matching Words:         ${res.flagged_word_count || 0}`);
                if (res.readability) {
                    console.log(`  • Reading Level:          ${res.readability.grade_level} (~${res.readability.reading_time_minutes} min read)`);
                }

                if (res.sources_breakdown && res.sources_breakdown.length > 0) {
                    console.log(`\n${colors.bold}📑 TOP MATCHED SOURCES:${colors.reset}`);
                    res.sources_breakdown.slice(0, 5).forEach(s => {
                        console.log(`  - ${colors.yellow}${s.similarity}%${colors.reset} • ${s.filename} (${s.badge || 'Institutional'})`);
                    });
                }

                if (res.student_coach) {
                    console.log(`\n${colors.bold}🧑‍🎓 STUDENT INTEGRITY COACH:${colors.reset}`);
                    console.log(`  • Unsupported Claims:     ${res.student_coach.unsupported_claims_count}`);
                    console.log(`  • Tone Booster Boosts:    ${res.student_coach.tone_suggestions_count}`);
                    console.log(`  • Thesis Strength Score:  ${res.student_coach.thesis_evaluation.score}/100`);
                }

                if (res.phd_audit) {
                    console.log(`\n${colors.bold}🔬 PHD & CONFERENCE AUDITOR:${colors.reset}`);
                    console.log(`  • Double-Blind Status:    ${res.phd_audit.is_anonymity_compliant ? colors.green + "100% Compliant" : colors.red + "Violations Found"}${colors.reset}`);
                    console.log(`  • Conference Readiness:   ${res.phd_audit.conference_readiness_score}/100`);
                }

                if (isVerbose && res.highlighted_sentences) {
                    console.log(`\n${colors.bold}📝 SIDE-BY-SIDE MATCHING PASSAGES:${colors.reset}`);
                    res.highlighted_sentences.filter(s => s.is_plagiarized).forEach((s, idx) => {
                        console.log(`\n  [Match #${idx + 1}] Similarity: ${s.similarity}% • Source: ${s.source}`);
                        console.log(`  ${colors.red}Submission:${colors.reset} "${s.text}"`);
                        console.log(`  ${colors.green}Reference: ${colors.reset} "${s.matched_source_sentence}"`);
                    });
                }
                console.log("");
            } catch (err) {
                console.error(`${colors.red}Scan Error: ${err.message}${colors.reset}`);
                process.exit(1);
            }
            break;
        }

        case "coach": {
            const input = args[1];
            if (!input) {
                console.error(`${colors.red}Error: Missing document or text to analyze.${colors.reset}`);
                process.exit(1);
            }
            let text = input;
            if (fs.existsSync(input)) {
                text = DocumentExtractor.extractFromFile(input);
            }
            const claims = AcademicStudentCoach.scanUnsupportedClaims(text);
            const tone = AcademicStudentCoach.analyzeToneAndVocabulary(text);
            const thesis = AcademicStudentCoach.evaluateThesisAbstract(text);

            if (isJson) {
                console.log(JSON.stringify({ unsupported_claims: claims, tone_suggestions: tone, thesis_evaluation: thesis }, null, 2));
                return;
            }

            printBanner();
            console.log(`${colors.bold}🎯 Thesis Strength Score: ${colors.magenta}${thesis.score}/100${colors.reset}`);
            thesis.feedback.forEach(f => console.log(`  • ${f}`));

            console.log(`\n${colors.bold}🔍 Unsupported Claims (${claims.length}):${colors.reset}`);
            if (claims.length === 0) console.log(`  ${colors.green}✓ All empirical statements have citations.${colors.reset}`);
            claims.slice(0, 5).forEach((c, idx) => {
                console.log(`  [${idx + 1}] "${c.sentence}"`);
                console.log(`      ${colors.yellow}⚠️ Marker: '${c.claim_marker}' — Missing (Author, Year)${colors.reset}`);
            });

            console.log(`\n${colors.bold}✍️ Scholarly Tone Booster (${tone.length} Suggestions):${colors.reset}`);
            if (tone.length === 0) console.log(`  ${colors.green}✓ High scholarly formality detected.${colors.reset}`);
            tone.slice(0, 5).forEach((t, idx) => {
                console.log(`  [${idx + 1}] Replace ${colors.red}'${t.matched_term}'${colors.reset} with: ${colors.green}${t.scholarly_replacements.join(", ")}${colors.reset}`);
            });
            console.log("");
            break;
        }

        case "audit": {
            const input = args[1];
            if (!input) {
                console.error(`${colors.red}Error: Missing document or text to audit.${colors.reset}`);
                process.exit(1);
            }
            let text = input;
            if (fs.existsSync(input)) {
                text = DocumentExtractor.extractFromFile(input);
            }
            const audit = PhdResearchAuditor.auditManuscript(text);
            if (isJson) {
                console.log(JSON.stringify(audit, null, 2));
                return;
            }
            printBanner();
            console.log(`${colors.bold}🔬 CONFERENCE PRE-FLIGHT AUDITOR (NeurIPS / ICML / IEEE):${colors.reset}`);
            console.log(`  • Conference Readiness Score: ${colors.magenta}${audit.conference_readiness_score}/100${colors.reset}`);
            console.log(`  • Anonymity Compliance:       ${audit.is_anonymity_compliant ? colors.green + "100% Compliant (Double-Blind)" : colors.red + "Violations Found"}${colors.reset}`);
            console.log(`  • LaTeX Equations Isolated:   ${audit.latex_equations_isolated}`);

            if (audit.anonymity_violations.length > 0) {
                console.log(`\n${colors.bold}${colors.red}⚠️ Anonymity Violations:${colors.reset}`);
                audit.anonymity_violations.forEach(v => console.log(`  • ${v}`));
            }

            if (audit.sections_breakdown.length > 0) {
                console.log(`\n${colors.bold}📐 Sections Cadence Breakdown:${colors.reset}`);
                audit.sections_breakdown.forEach(s => {
                    console.log(`  • ${s.heading.padEnd(20)} ${String(s.word_count).padStart(4)} words | ${s.avg_sentence_len} w/sent | ${s.cadence_profile}`);
                });
            }
            console.log("");
            break;
        }

        case "paraphrase": {
            const sentence = args[1];
            if (!sentence) {
                console.error(`${colors.red}Error: Please specify sentence to paraphrase.${colors.reset}`);
                process.exit(1);
            }
            const res = AcademicParaphraser.synthesizeSentence(sentence, sourceName, sourceName);
            if (isJson) {
                console.log(JSON.stringify(res, null, 2));
                return;
            }
            printBanner();
            console.log(`${colors.bold}Original Sentence:${colors.reset}\n"${sentence}"\n`);
            console.log(`${colors.bold}✨ Academic Restructuring Options:${colors.reset}`);
            res.suggestions.forEach((s, idx) => {
                console.log(`\n${colors.cyan}[${idx + 1}] ${s.style}:${colors.reset}`);
                console.log(`  ${colors.green}${s.text}${colors.reset}`);
                console.log(`  ${colors.gray}${s.description}${colors.reset}`);
            });
            console.log("");
            break;
        }

        case "cite": {
            const query = args[1];
            if (!query) {
                console.error(`${colors.red}Error: Please provide DOI, arXiv ID, or Paper Title.${colors.reset}`);
                process.exit(1);
            }
            try {
                const res = await CitationGenerator.resolveCitation(query);
                if (isJson) {
                    console.log(JSON.stringify(res, null, 2));
                    return;
                }
                printBanner();
                console.log(`${colors.bold}Paper:${colors.reset} ${res.title}`);
                console.log(`${colors.bold}Authors:${colors.reset} ${res.authors.join(", ")}`);
                console.log(`\n${colors.bold}${colors.cyan}BibTeX (@article):${colors.reset}\n${res.bibtex}`);
                console.log(`\n${colors.bold}${colors.cyan}APA 7th:${colors.reset}\n${res.apa}`);
                console.log(`\n${colors.bold}${colors.cyan}MLA 9th:${colors.reset}\n${res.mla}`);
                console.log(`\n${colors.bold}${colors.cyan}IEEE:${colors.reset}\n${res.ieee}\n`);
            } catch (err) {
                console.error(`${colors.red}Citation Error: ${err.message}${colors.reset}`);
                process.exit(1);
            }
            break;
        }

        case "alphabetize": {
            const input = args[1];
            if (!input) {
                console.error(`${colors.red}Error: Missing reference list file or text.${colors.reset}`);
                process.exit(1);
            }
            let text = input;
            if (fs.existsSync(input)) {
                text = fs.readFileSync(input, "utf8");
            }
            const res = AcademicStudentCoach.alphabetizeAndFormatReferences(text);
            if (isJson) {
                console.log(JSON.stringify(res, null, 2));
                return;
            }
            printBanner();
            console.log(`${colors.bold}✅ ${res.count} References Sorted Alphabetically:${colors.reset}\n`);
            console.log(res.formatted_text);
            if (res.issues.length > 0) {
                console.log(`\n${colors.yellow}⚠️ Warnings:${colors.reset}`);
                res.issues.forEach(iss => console.log(`  • ${iss}`));
            }
            console.log("");
            break;
        }

        case "diff": {
            const f1 = args[1];
            const f2 = args[2];
            if (!f1 || !f2) {
                console.error(`${colors.red}Error: Please provide two draft files: plag diff <file1> <file2>${colors.reset}`);
                process.exit(1);
            }
            const t1 = fs.existsSync(f1) ? DocumentExtractor.extractFromFile(f1) : f1;
            const t2 = fs.existsSync(f2) ? DocumentExtractor.extractFromFile(f2) : f2;
            const res = DraftComparator.compare(t1, t2);

            if (isJson) {
                console.log(JSON.stringify(res, null, 2));
                return;
            }
            printBanner();
            console.log(`${colors.bold}📑 DRAFT-TO-DRAFT REVISION DELTA:${colors.reset}`);
            console.log(`  • Draft 1 Words:       ${res.draft_v1_words}`);
            console.log(`  • Draft 2 Words:       ${res.draft_v2_words} (${res.words_delta >= 0 ? "+" : ""}${res.words_delta})`);
            console.log(`  • Draft Continuity:    ${colors.green}${res.similarity_percentage}%${colors.reset}`);
            console.log(`  • New Content Added:   ${colors.cyan}${res.revision_percentage}%${colors.reset}`);
            console.log(`  • Unchanged Sentences: ${res.unchanged_count}`);
            console.log(`  • Modified/Added:      ${res.added_count}\n`);
            break;
        }

        case "batch": {
            const targets = args.slice(1).filter(a => !a.startsWith("-"));
            if (targets.length === 0) {
                console.error(`${colors.red}Error: Please provide directory or files to batch process: plag batch <dir|files...>${colors.reset}`);
                process.exit(1);
            }
            const res = BatchProcessor.processBatch(targets);
            if (isJson) {
                console.log(JSON.stringify(res, null, 2));
                return;
            }
            printBanner();
            console.log(`${colors.bold}📦 BATCH SUBMISSION GRADEBOOK:${colors.reset}`);
            console.log(`  • Submissions Processed:  ${res.total_submissions}`);
            console.log(`  • Class Average Plag:     ${res.average_plagiarism}%`);
            console.log(`  • Class Average AI:       ${res.average_ai_probability}%`);
            console.log(`  • High Risk Papers:       ${res.high_risk_count > 0 ? colors.red : colors.green}${res.high_risk_count}${colors.reset}\n`);

            console.log(`${"Document".padEnd(30)} ${"Words".padStart(8)} ${"Plagiarism".padStart(12)} ${"AI Probability".padStart(16)} ${"Risk Tier".padStart(14)}`);
            console.log("-".repeat(84));
            res.gradebook.forEach(row => {
                const name = row.student_or_filename.slice(0, 28).padEnd(30);
                const words = String(row.word_count || 0).padStart(8);
                const plag = `${row.plagiarism_score || 0}%`.padStart(12);
                const ai = `${row.ai_probability || 0}%`.padStart(16);
                const risk = (row.safeassign_risk || "Low Risk").padStart(14);
                console.log(`${name} ${words} ${plag} ${ai} ${risk}`);
            });
            console.log("");
            break;
        }

        case "certificate": {
            const input = args[1];
            if (!input) {
                console.error(`${colors.red}Error: Missing document or text: plag certificate <file|text> --name "Name" --title "Title"${colors.reset}`);
                process.exit(1);
            }
            let text = input;
            if (fs.existsSync(input)) {
                text = DocumentExtractor.extractFromFile(input);
            }
            const scanRes = await scan(text);
            const cert = CertificateGenerator.generate({
                studentName,
                paperTitle,
                plagiarismScore: scanRes.overall_similarity,
                aiScore: scanRes.ai_analysis ? scanRes.ai_analysis.ai_probability : 0.0,
                wordCount: scanRes.total_words,
                safeassignRisk: scanRes.safeassign_risk,
                text
            });

            if (isJson) {
                console.log(JSON.stringify(cert, null, 2));
                return;
            }
            console.log(cert.ascii_certificate);
            console.log(`\nVerification Hash (SHA-256): ${cert.sha256_hash}\n`);
            break;
        }

        case "mcp": {
            require("./mcp-server");
            break;
        }

        default:
            printHelp();
            break;
    }
}

main().catch(err => {
    console.error(err);
    process.exit(1);
});
