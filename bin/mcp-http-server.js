#!/usr/bin/env node

/**
 * Plagiarism Detector Pro — Personal Remote MCP HTTP Server
 *
 * Transport : Streamable HTTP  (MCP spec 2024-11-05)
 * Auth      : Bearer token (auto-generated and stored in ~/.plag-mcp.json)
 * Usage     : node bin/mcp-http-server.js
 *             MCP_PORT=3456 MCP_API_KEY=mykey node bin/mcp-http-server.js
 *
 * Add to Claude Web (claude.ai → Settings → Integrations → Add MCP Server):
 *   URL : https://<your-tunnel>.trycloudflare.com/mcp
 *   Key : (shown on startup)
 */

"use strict";

const http    = require("http");
const fs      = require("fs");
const os      = require("os");
const path    = require("path");
const crypto  = require("crypto");


const {
    scan,
    AcademicParaphraser,
    AcademicStudentCoach,
    DocumentExtractor,
    CitationGenerator,
    DraftComparator
} = require("../lib/index");

// ── ANSI colors (startup banner only) ───────────────────────────────────────
const C = {
    reset : "\x1b[0m", bold : "\x1b[1m",
    cyan  : "\x1b[36m", green: "\x1b[32m",
    yellow: "\x1b[33m", gray : "\x1b[90m",
    red   : "\x1b[31m", magenta: "\x1b[35m"
};

// ── Persistent config (~/.plag-mcp.json) ────────────────────────────────────
const CONFIG_PATH = path.join(os.homedir(), ".plag-mcp.json");

function loadConfig() {
    try {
        if (fs.existsSync(CONFIG_PATH)) {
            const cfg = JSON.parse(fs.readFileSync(CONFIG_PATH, "utf8"));
            if (cfg && cfg.api_key) return cfg;
        }
    } catch { /* fall through to generate */ }
    const cfg = { api_key: crypto.randomBytes(28).toString("hex") };
    fs.writeFileSync(CONFIG_PATH, JSON.stringify(cfg, null, 2), { mode: 0o600 });
    return cfg;
}

const PORT    = parseInt(process.env.MCP_PORT    || "3456", 10);
const cfg     = loadConfig();
const API_KEY = process.env.MCP_API_KEY || cfg.api_key;

// ── MCP Tool Definitions ─────────────────────────────────────────────────────
const TOOLS = [
    {
        name: "plag_scan_text",
        description: "Measures lexical overlap against configured sources and reports an uncalibrated writing-pattern score.",
        inputSchema: {
            type: "object",
            properties: {
                text:                 { type: "string",  description: "The academic text or essay to scan." },
                exclude_bibliography: { type: "boolean", description: "Exclude the References section from scoring." },
                exclude_quotes:       { type: "boolean", description: "Exclude only quoted text from similarity scoring." }
            },
            required: ["text"]
        }
    },
    {
        name: "plag_scan_file",
        description: "Scans a local document file (.tex, .ipynb, .md, .txt, .docx) for lexical overlap and writing-pattern signals.",
        inputSchema: {
            type: "object",
            properties: {
                file_path:            { type: "string",  description: "Absolute or relative path to the manuscript file." },
                exclude_bibliography: { type: "boolean", description: "Exclude the References section from scoring." },
                exclude_quotes:       { type: "boolean", description: "Exclude only quoted text." }
            },
            required: ["file_path"]
        }
    },
    {
        name: "plag_paraphrase",
        description: "Synthesizes and restructures overlapping sentences into 3 distinct, high-integrity academic formulations with formal attribution.",
        inputSchema: {
            type: "object",
            properties: {
                sentence:     { type: "string", description: "The sentence to restructure." },
                source_title: { type: "string", description: "Name of author or reference publication for citation attribution." }
            },
            required: ["sentence"]
        }
    },
    {
        name: "plag_academic_coach",
        description: "Scans an essay for unsupported empirical claims, conversational phrases with scholarly alternatives, and thesis strength (0–100).",
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
        description: "Generates BibTeX, APA 7th, MLA 9th, and IEEE citations from a DOI, arXiv ID, or paper title.",
        inputSchema: {
            type: "object",
            properties: {
                query: { type: "string", description: "DOI (e.g. 10.1145/...), arXiv ID (e.g. 1706.03762), or Paper Title." }
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

// ── Tool execution ────────────────────────────────────────────────────────────
async function handleToolCall(name, args) {
    const tool = TOOLS.find(t => t.name === name);
    if (!tool) throw new Error(`Unknown tool: ${name}`);

    if (!args || typeof args !== "object" || Array.isArray(args)) {
        throw new Error("Arguments must be a JSON object");
    }

    for (const key of (tool.inputSchema.required || [])) {
        if (typeof args[key] !== "string" || !args[key].trim()) {
            throw new Error(`${key} must be a non-empty string`);
        }
    }

    switch (name) {
        case "plag_scan_text":
            return await scan(args.text, {
                excludeQuotes:       args.exclude_quotes,
                excludeBibliography: args.exclude_bibliography
            });

        case "plag_scan_file": {
            const text = DocumentExtractor.extractFromFile(args.file_path);
            return await scan(text, {
                excludeQuotes:       args.exclude_quotes,
                excludeBibliography: args.exclude_bibliography
            });
        }

        case "plag_paraphrase":
            return AcademicParaphraser.synthesizeSentence(
                args.sentence, args.source_title, args.source_title
            );

        case "plag_academic_coach": {
            const claims = AcademicStudentCoach.scanUnsupportedClaims(args.text);
            const tone   = AcademicStudentCoach.analyzeToneAndVocabulary(args.text);
            const thesis = AcademicStudentCoach.evaluateThesisAbstract(args.text);
            return {
                unsupported_claims:       claims,
                unsupported_claims_count: claims.length,
                tone_suggestions:         tone,
                tone_suggestions_count:   tone.length,
                thesis_evaluation:        thesis
            };
        }

        case "plag_generate_citation":
            return await CitationGenerator.resolveCitation(args.query);

        case "plag_alphabetize_references":
            return AcademicStudentCoach.alphabetizeAndFormatReferences(args.references_text);

        case "plag_compare_drafts":
            return DraftComparator.compare(args.draft_v1, args.draft_v2);

        default:
            throw new Error(`No handler for tool: ${name}`);
    }
}

// ── JSON-RPC router ───────────────────────────────────────────────────────────
const PKG = require("../package.json");

async function routeRpc(request) {
    if (!request || typeof request !== "object" || request.jsonrpc !== "2.0") {
        return { jsonrpc: "2.0", id: null, error: { code: -32600, message: "Invalid Request" } };
    }

    const { id, method, params } = request;

    switch (method) {
        case "initialize":
            return {
                jsonrpc: "2.0", id,
                result: {
                    protocolVersion: "2024-11-05",
                    serverInfo: { name: "plagiarism-detector-pro-mcp", version: PKG.version },
                    capabilities: { tools: {} }
                }
            };

        case "ping":
            return { jsonrpc: "2.0", id, result: {} };

        case "tools/list":
            return { jsonrpc: "2.0", id, result: { tools: TOOLS } };

        case "tools/call": {
            const { name, arguments: args } = params || {};
            try {
                const result = await handleToolCall(name, args || {});
                return {
                    jsonrpc: "2.0", id,
                    result: { content: [{ type: "text", text: JSON.stringify(result, null, 2) }] }
                };
            } catch (err) {
                return {
                    jsonrpc: "2.0", id,
                    result: { isError: true, content: [{ type: "text", text: `Error: ${err.message}` }] }
                };
            }
        }

        default:
            return { jsonrpc: "2.0", id, error: { code: -32601, message: "Method not found" } };
    }
}

// ── HTTP server ───────────────────────────────────────────────────────────────
const server = http.createServer(async (req, res) => {
    const pathname = (req.url || "/").split("?")[0];

    // CORS — allow claude.ai and any tunnel origin
    res.setHeader("Access-Control-Allow-Origin",  "*");
    res.setHeader("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
    res.setHeader("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Api-Key, Mcp-Session-Id");
    res.setHeader("Access-Control-Max-Age", "86400");

    if (req.method === "OPTIONS") {
        res.writeHead(204);
        res.end();
        return;
    }

    // ── Health / info (no auth required) ────────────────────────────────────
    if (req.method === "GET" && (pathname === "/health" || pathname === "/")) {
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify({
            status:  "ok",
            server:  "plagiarism-detector-pro-mcp",
            version: PKG.version,
            tools:   TOOLS.length,
            transport: "streamable-http"
        }));
        return;
    }

    // ── Bearer-token auth (all MCP endpoints) ────────────────────────────────
    const authHeader  = req.headers["authorization"] || "";
    const apiKeyHeader= req.headers["x-api-key"] || "";
    const token = authHeader.startsWith("Bearer ") ? authHeader.slice(7) : apiKeyHeader;

    if (token !== API_KEY) {
        res.writeHead(401, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ error: "Unauthorized", hint: "Pass your API key as: Authorization: Bearer <key>" }));
        return;
    }

    // ── MCP endpoint: POST /mcp ──────────────────────────────────────────────
    if (req.method === "POST" && (pathname === "/mcp" || pathname === "/")) {
        let body = "";
        req.on("data", chunk => { body += chunk; });
        req.on("end", async () => {
            let request;
            try {
                request = JSON.parse(body);
            } catch {
                res.writeHead(400, { "Content-Type": "application/json" });
                res.end(JSON.stringify({ jsonrpc: "2.0", id: null, error: { code: -32700, message: "Parse error" } }));
                return;
            }

            // Handle batch requests (array of JSON-RPC)
            if (Array.isArray(request)) {
                const responses = await Promise.all(request.map(routeRpc));
                res.writeHead(200, { "Content-Type": "application/json" });
                res.end(JSON.stringify(responses));
                return;
            }

            // Single request
            const response = await routeRpc(request);
            res.writeHead(200, { "Content-Type": "application/json" });
            res.end(JSON.stringify(response));
        });
        return;
    }

    res.writeHead(404, { "Content-Type": "application/json" });
    res.end(JSON.stringify({ error: "Not found", endpoints: ["GET /health", "POST /mcp"] }));
});

// ── Startup ───────────────────────────────────────────────────────────────────
server.listen(PORT, "0.0.0.0", () => {
    const divider = `${C.bold}${C.cyan}${"─".repeat(60)}${C.reset}`;
    console.error(divider);
    console.error(`${C.bold}${C.cyan} 🎓 Plagiarism Detector Pro — Personal MCP HTTP Server${C.reset}`);
    console.error(`${C.gray}    v${PKG.version} · Streamable HTTP Transport${C.reset}`);
    console.error(divider);
    console.error(`\n${C.bold} Local URL   :${C.reset}  ${C.green}http://localhost:${PORT}/mcp${C.reset}`);
    console.error(`${C.bold} API Key     :${C.reset}  ${C.yellow}${API_KEY}${C.reset}`);
    console.error(`${C.gray} Key saved at: ${CONFIG_PATH}${C.reset}`);
    console.error(`${C.bold} Health      :${C.reset}  ${C.green}http://localhost:${PORT}/health${C.reset}\n`);
    console.error(`${C.bold}${C.magenta} ─── Expose via Cloudflare Tunnel (Free, No Account Needed) ───${C.reset}`);
    console.error(`${C.gray}  brew install cloudflare/cloudflare/cloudflared${C.reset}`);
    console.error(`  ${C.cyan}cloudflared tunnel --url http://localhost:${PORT}${C.reset}`);
    console.error(`${C.gray}  → Copy the https://xxxx.trycloudflare.com URL it prints${C.reset}\n`);
    console.error(`${C.bold}${C.magenta} ─── Expose via ngrok ──────────────────────────────────────────${C.reset}`);
    console.error(`${C.gray}  brew install ngrok/ngrok/ngrok   # one-time${C.reset}`);
    console.error(`  ${C.cyan}ngrok http ${PORT}${C.reset}`);
    console.error(`${C.gray}  → Copy the https://xxxx.ngrok-free.app URL it prints${C.reset}\n`);
    console.error(`${C.bold}${C.magenta} ─── Add to Claude Web ─────────────────────────────────────────${C.reset}`);
    console.error(`${C.gray}  claude.ai → Settings → Integrations → Add MCP Server${C.reset}`);
    console.error(`${C.bold}  URL :${C.reset}  https://<your-tunnel-url>/mcp`);
    console.error(`${C.bold}  Key :${C.reset}  ${C.yellow}${API_KEY}${C.reset}`);
    console.error(divider + "\n");
});

server.on("error", err => {
    if (err.code === "EADDRINUSE") {
        console.error(`${C.red}✗ Port ${PORT} is already in use. Set a different port:${C.reset}`);
        console.error(`  MCP_PORT=3457 node bin/mcp-http-server.js`);
    } else {
        console.error(`${C.red}Server error: ${err.message}${C.reset}`);
    }
    process.exit(1);
});

// Graceful shutdown
process.on("SIGINT",  () => { console.error("\n👋  MCP server stopped."); server.close(); process.exit(0); });
process.on("SIGTERM", () => { server.close(); process.exit(0); });
