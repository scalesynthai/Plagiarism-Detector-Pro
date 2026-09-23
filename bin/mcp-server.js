#!/usr/bin/env node

/**
 * Model Context Protocol (MCP) Stdio Server
 * Enables Claude Desktop, Codex, Antigravity, and Cursor to natively call
 * Plagiarism Detector Pro tools via JSON-RPC.
 */

const readline = require("readline");
const {
    scan,
    AcademicParaphraser,
    AcademicStudentCoach,
    DocumentExtractor,
    CitationGenerator,
    DraftComparator
} = require("../lib/index");

const TOOLS = [
    {
        name: "plag_scan_text",
        description: "Measures lexical overlap against configured sources and reports an uncalibrated writing-pattern score.",
        inputSchema: {
            type: "object",
            properties: {
                text: { type: "string", description: "The academic text or essay to scan." },
                exclude_bibliography: { type: "boolean", description: "Exclude the References section from scoring." },
                exclude_quotes: { type: "boolean", description: "Exclude only quoted text from similarity scoring; citations remain included." },
                server: { type: "string", description: "Optional remote server endpoint (e.g. https://plag.subba.dev)." }
            },
            required: ["text"]
        }
    },
    {
        name: "plag_scan_file",
        description: "Scans a local document file (.tex, .ipynb, .md, .txt) for lexical overlap and writing-pattern signals.",
        inputSchema: {
            type: "object",
            properties: {
                file_path: { type: "string", description: "Absolute or relative path to the manuscript file." },
                exclude_bibliography: { type: "boolean", description: "Exclude the References section from scoring." },
                exclude_quotes: { type: "boolean", description: "Exclude only quoted text." }
            },
            required: ["file_path"]
        }
    },
    {
        name: "plag_paraphrase",
        description: "Synthesizes and restructures overlapping sentences into 3 distinct, high-integrity academic formulations with formal attribution (Active Inversion, Methodological, Conceptual).",
        inputSchema: {
            type: "object",
            properties: {
                sentence: { type: "string", description: "The sentence to restructure." },
                source_title: { type: "string", description: "Name of author or reference publication for citation attribution." }
            },
            required: ["sentence"]
        }
    },
    {
        name: "plag_academic_coach",
        description: "Scans an essay or paper for: (1) Unsupported empirical claims lacking citations, (2) Conversational phrases with scholarly vocabulary replacements, and (3) Opening thesis/abstract strength evaluation.",
        inputSchema: {
            type: "object",
            properties: {
                text: { type: "string", description: "Manuscript text or excerpt to evaluate." }
            },
            required: ["text"]
        }
    },
    {
        name: "plag_generate_citation",
        description: "Generates BibTeX, APA 7th, MLA 9th, and IEEE citations from available DOI, arXiv, or title metadata; unresolved templates require review.",
        inputSchema: {
            type: "object",
            properties: {
                query: { type: "string", description: "DOI (e.g. 10.1145/3318464.3389700), arXiv ID (e.g. 1706.03762), or Paper Title." }
            },
            required: ["query"]
        }
    },
    {
        name: "plag_alphabetize_references",
        description: "Alphabetizes an unorganized bibliography by primary author last name, validates publication years, and checks for DOIs.",
        inputSchema: {
            type: "object",
            properties: {
                references_text: { type: "string", description: "Raw bibliography or list of references (one per line)." }
            },
            required: ["references_text"]
        }
    },
    {
        name: "plag_compare_drafts",
        description: "Compares Draft 1 against Draft 2 to calculate revision delta percentages, newly added sections, and retained phrasing.",
        inputSchema: {
            type: "object",
            properties: {
                draft_v1: { type: "string", description: "Original draft text." },
                draft_v2: { type: "string", description: "Revised draft text." }
            },
            required: ["draft_v1", "draft_v2"]
        }
    }
];

const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
    terminal: false
});

rl.on("line", async (line) => {
    if (!line.trim()) return;
    let request;
    try {
        request = JSON.parse(line);
    } catch {
        sendError(null, -32700, "Parse error");
        return;
    }

    if (!request || typeof request !== "object" || Array.isArray(request) || request.jsonrpc !== "2.0" || typeof request.method !== "string") {
        sendError(null, -32600, "Invalid Request");
        return;
    }
    const { id, method, params } = request;
    if (id === undefined) return; // JSON-RPC notifications never receive responses.

    if (method === "tools/list") {
        sendResponse(id, { tools: TOOLS });
    } else if (method === "tools/call") {
        const { name, arguments: args } = params || {};
        try {
            const result = await handleToolCall(name, args || {});
            sendResponse(id, { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] });
        } catch (err) {
            sendResponse(id, { isError: true, content: [{ type: "text", text: `Error: ${err.message}` }] });
        }
    } else if (method === "ping") {
        sendResponse(id, {});
    } else if (method === "initialize") {
        sendResponse(id, {
            protocolVersion: "2024-11-05",
            serverInfo: { name: "plagiarism-detector-pro-mcp", version: "1.0.0" },
            capabilities: { tools: {} }
        });
    } else {
        sendError(id, -32601, "Method not found");
    }
});

function sendError(id, code, message) {
    process.stdout.write(JSON.stringify({ jsonrpc: "2.0", id, error: { code, message } }) + "\n");
}

function sendResponse(id, result) {
    const payload = JSON.stringify({ jsonrpc: "2.0", id, result });
    process.stdout.write(payload + "\n");
}

async function handleToolCall(name, args) {
    const tool = TOOLS.find(tool => tool.name === name);
    if (!tool) throw new Error(`Unknown tool: ${name}`);
    if (!args || typeof args !== "object" || Array.isArray(args)) throw new Error("Arguments must be an object");
    for (const key of tool.inputSchema.required || []) {
        if (typeof args[key] !== "string" || !args[key].trim()) throw new Error(`${key} must be a non-empty string`);
    }
    for (const [key, value] of Object.entries(args)) {
        const property = tool.inputSchema.properties[key];
        if (property && typeof value !== property.type) throw new Error(`Invalid type for ${key}`);
    }
    switch (name) {
        case "plag_scan_text":
            return await scan(args.text, {
                excludeQuotes: args.exclude_quotes,
                excludeBibliography: args.exclude_bibliography,
                server: args.server
            });

        case "plag_scan_file": {
            const text = DocumentExtractor.extractFromFile(args.file_path);
            return await scan(text, { excludeQuotes: args.exclude_quotes, excludeBibliography: args.exclude_bibliography });
        }

        case "plag_paraphrase":
            return AcademicParaphraser.synthesizeSentence(args.sentence, args.source_title, args.source_title);

        case "plag_academic_coach": {
            const claims = AcademicStudentCoach.scanUnsupportedClaims(args.text);
            const tone = AcademicStudentCoach.analyzeToneAndVocabulary(args.text);
            const thesis = AcademicStudentCoach.evaluateThesisAbstract(args.text);
            return {
                unsupported_claims: claims,
                unsupported_claims_count: claims.length,
                tone_suggestions: tone,
                tone_suggestions_count: tone.length,
                thesis_evaluation: thesis
            };
        }

        case "plag_generate_citation":
            return await CitationGenerator.resolveCitation(args.query);

        case "plag_alphabetize_references":
            return AcademicStudentCoach.alphabetizeAndFormatReferences(args.references_text);

        case "plag_compare_drafts":
            return DraftComparator.compare(args.draft_v1, args.draft_v2);

        default:
            throw new Error(`Unknown tool: ${name}`);
    }
}
