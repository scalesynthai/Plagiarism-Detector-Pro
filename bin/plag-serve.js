#!/usr/bin/env node
/**
 * plag-serve.js — One-command launcher
 * Starts the MCP HTTP server + Cloudflare Tunnel and prints your live URL.
 *
 * Usage:
 *   node bin/plag-serve.js
 *   MCP_PORT=3456 node bin/plag-serve.js
 */

"use strict";

const { spawn } = require("child_process");
const fs        = require("fs");
const os        = require("os");
const path      = require("path");

const PORT = parseInt(process.env.MCP_PORT || "3456", 10);

const C = {
    reset: "\x1b[0m", bold: "\x1b[1m",
    cyan: "\x1b[36m", green: "\x1b[32m",
    yellow: "\x1b[33m", gray: "\x1b[90m",
    red: "\x1b[31m", magenta: "\x1b[35m"
};

const CONFIG_PATH = path.join(os.homedir(), ".plag-mcp.json");
let API_KEY = process.env.MCP_API_KEY || "";
try {
    const cfg = JSON.parse(fs.readFileSync(CONFIG_PATH, "utf8"));
    API_KEY = cfg.api_key || API_KEY;
} catch {}

function findCloudflared() {
    const candidates = [
        "/opt/homebrew/bin/cloudflared",          // Apple Silicon Homebrew
        "/usr/local/bin/cloudflared",              // Intel Homebrew
        "/usr/bin/cloudflared",
        "cloudflared"
    ];
    for (const c of candidates) {
        try {
            if (c === "cloudflared" || fs.existsSync(c)) return c;
        } catch {}
    }
    return "cloudflared";
}

console.log(`\n${C.bold}${C.cyan}════════════════════════════════════════════════════${C.reset}`);
console.log(`${C.bold}${C.cyan}  🎓 Plagiarism Detector Pro — Personal MCP Launcher${C.reset}`);
console.log(`${C.bold}${C.cyan}════════════════════════════════════════════════════${C.reset}\n`);

// 1. Start MCP HTTP server
const serverScript = path.join(__dirname, "mcp-http-server.js");
const server = spawn(process.execPath, [serverScript], {
    env: { ...process.env, MCP_PORT: String(PORT) },
    stdio: ["ignore", "ignore", "pipe"]   // stderr → pipe so we can read startup
});

let serverReady = false;
server.stderr.on("data", (chunk) => {
    // Echo server banner once
    if (!serverReady) {
        process.stderr.write(chunk);
        if (chunk.toString().includes("────")) serverReady = true;
    }
});

server.on("exit", (code) => {
    if (code !== null) {
        console.error(`${C.red}✗ MCP server exited with code ${code}${C.reset}`);
        process.exit(1);
    }
});

// 2. Wait 1.5s for the server to bind, then start tunnel
setTimeout(() => {
    const cfBin = findCloudflared();
    console.log(`${C.gray}Starting Cloudflare Tunnel on port ${PORT}…${C.reset}`);

    const tunnel = spawn(cfBin, ["tunnel", "--url", `http://localhost:${PORT}`], {
        stdio: ["ignore", "pipe", "pipe"]
    });

    function handleTunnelOutput(data) {
        const text = data.toString();

        // Capture the trycloudflare.com URL from cloudflared output
        const match = text.match(/https:\/\/[a-zA-Z0-9\-]+\.trycloudflare\.com/);
        if (match) {
            const tunnelUrl = match[0];
            const mcpUrl    = `${tunnelUrl}/mcp`;

            console.log(`\n${C.bold}${C.green}✔  Tunnel is live!${C.reset}\n`);
            console.log(`${C.bold}═══════════════════════════════════════════════════════${C.reset}`);
            console.log(`${C.bold}  Add this to Claude Web:${C.reset}`);
            console.log(`${C.bold}  claude.ai → Settings → Integrations → Add MCP Server${C.reset}`);
            console.log(`${C.bold}═══════════════════════════════════════════════════════${C.reset}`);
            console.log(`\n  ${C.bold}MCP URL :${C.reset}  ${C.cyan}${mcpUrl}${C.reset}`);
            console.log(`  ${C.bold}API Key :${C.reset}  ${C.yellow}${API_KEY}${C.reset}`);
            console.log(`\n${C.gray}  (key also saved at ~/.plag-mcp.json)${C.reset}`);
            console.log(`${C.bold}═══════════════════════════════════════════════════════${C.reset}\n`);
            console.log(`${C.gray}Press Ctrl+C to stop both the server and tunnel.${C.reset}\n`);

            // Also write to .plag-mcp.json for easy retrieval
            try {
                const cfg = JSON.parse(fs.readFileSync(CONFIG_PATH, "utf8"));
                cfg.last_tunnel_url = mcpUrl;
                cfg.last_started    = new Date().toISOString();
                fs.writeFileSync(CONFIG_PATH, JSON.stringify(cfg, null, 2));
            } catch {}
        }
    }

    tunnel.stdout.on("data", handleTunnelOutput);
    tunnel.stderr.on("data", handleTunnelOutput);

    tunnel.on("exit", (code) => {
        if (code !== null && code !== 0) {
            console.error(`\n${C.red}✗ Cloudflare Tunnel exited (code ${code}).${C.reset}`);
            console.error(`${C.gray}  Try running manually: cloudflared tunnel --url http://localhost:${PORT}${C.reset}`);
            server.kill();
            process.exit(1);
        }
    });

    // Forward Ctrl+C → kill both processes cleanly
    process.on("SIGINT", () => {
        console.log(`\n${C.gray}Shutting down…${C.reset}`);
        tunnel.kill("SIGTERM");
        server.kill("SIGTERM");
        setTimeout(() => process.exit(0), 500);
    });

    process.on("SIGTERM", () => {
        tunnel.kill("SIGTERM");
        server.kill("SIGTERM");
        process.exit(0);
    });

}, 1500);
