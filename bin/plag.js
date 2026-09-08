#!/usr/bin/env node

/**
 * Plagiarism Detector Pro CLI
 * Command-line academic originality scanner, AI detector, and student coach.
 */

const fs = require("fs");
const path = require("path");
const {
    scan,
    AcademicParaphraser,
    AcademicStudentCoach,
    DocumentExtractor,
    CitationGenerator,
    DraftComparator
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
    console.log(`${colors.gray} Enterprise Academic Originality, AI Detector & Coach${colors.reset}`);
    console.log(`${colors.bold}${colors.cyan}======================================================${colors.reset}\n`);
}

function printHelp() {
    printBanner();
    console.log(`${colors.bold}USAGE:${colors.reset}`);
    console.log(`  ${colors.green}plag scan <file|text>${colors.reset}       Scan document or text for plagiarism & AI content`);
    console.log(`  ${colors.green}plag paraphrase <sentence>${colors.reset}  Generate 3 academic restructurings & citations`);
    console.log(`  ${colors.green}plag coach <file|text>${colors.reset}       Scan unsupported claims, tone booster & thesis`);
    console.log(`  ${colors.green}plag cite <query>${colors.reset}            Auto-generate BibTeX, APA, MLA, and IEEE`);
    console.log(`  ${colors.green}plag alphabetize <file|text>${colors.reset} Auto-sort references & validate DOIs/years`);
    console.log(`  ${colors.green}plag diff <file1> <file2>${colors.reset}   Compare Draft 1 vs Draft 2 deltas`);
    console.log(`  ${colors.green}plag mcp${colors.reset}                    Launch Model Context Protocol (MCP) server for Claude/Codex`);
    console.log(`\n${colors.bold}OPTIONS:${colors.reset}`);
    console.log(`  ${colors.yellow}--json${colors.reset}                   Output results in raw JSON`);
    console.log(`  ${colors.yellow}--server <url>${colors.reset}           Connect to live cloud API (e.g. https://plag.subba.dev)`);
    console.log(`  ${colors.yellow}--exclude-quotes${colors.reset}         Exclude verified citations from similarity index`);
    console.log(`  ${colors.yellow}--source <name>${colors.reset}          Source name for paraphrasing/citation attribution`);
    console.log(`\n${colors.bold}EXAMPLES:${colors.reset}`);
    console.log(`  ${colors.gray}$ plag scan essay.docx${colors.reset}`);
    console.log(`  ${colors.gray}$ plag scan "In this empirical study, we examine..." --json${colors.reset}`);
    console.log(`  ${colors.gray}$ plag paraphrase "Deep learning models predict continuous outcomes." --source "Smith2024"${colors.reset}`);
    console.log(`  ${colors.gray}$ plag cite 10.1145/3318464.3389700${colors.reset}`);
    console.log(`  ${colors.gray}$ plag mcp${colors.reset}\n`);
}

async function main() {
    const isJson = args.includes("--json");
    const serverIdx = args.indexOf("--server");
    const serverUrl = serverIdx !== -1 ? args[serverIdx + 1] : null;
    const sourceIdx = args.indexOf("--source");
    const sourceName = sourceIdx !== -1 ? args[sourceIdx + 1] : null;

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
                console.log(`${colors.cyan}🔍 Scanning originality and AI content...${colors.reset}\n`);
            }

            try {
                const res = await scan(text, {
                    server: serverUrl,
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

                if (res.sources_breakdown && res.sources_breakdown.length > 0) {
                    console.log(`\n${colors.bold}📑 MATCHED SOURCES:${colors.reset}`);
                    res.sources_breakdown.slice(0, 5).forEach(s => {
                        console.log(`  - ${colors.yellow}${s.similarity}%${colors.reset} • ${s.filename} (${s.badge || 'Source'})`);
                    });
                }

                if (res.student_coach) {
                    console.log(`\n${colors.bold}🧑‍🎓 STUDENT INTEGRITY COACH:${colors.reset}`);
                    console.log(`  • Unsupported Claims:     ${res.student_coach.unsupported_claims_count}`);
                    console.log(`  • Tone Booster Boosts:    ${res.student_coach.tone_suggestions_count}`);
                    console.log(`  • Thesis Strength Score:  ${res.student_coach.thesis_evaluation.score}/100`);
                }
                console.log("");
            } catch (err) {
                console.error(`${colors.red}Scan Error: ${err.message}${colors.reset}`);
                process.exit(1);
            }
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

        case "mcp": {
            // Spawn the MCP server
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
