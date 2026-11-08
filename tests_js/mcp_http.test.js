"use strict";

const assert = require("node:assert/strict");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");
const net = require("node:net");
const { spawn } = require("node:child_process");

function availablePort() {
    return new Promise((resolve, reject) => {
        const server = net.createServer();
        server.once("error", reject);
        server.listen(0, "127.0.0.1", () => {
            const { port } = server.address();
            server.close(error => error ? reject(error) : resolve(port));
        });
    });
}

function waitForReady(child) {
    return new Promise((resolve, reject) => {
        const timer = setTimeout(() => reject(new Error("MCP HTTP server did not start")), 8000);
        let output = "";
        child.stderr.on("data", chunk => {
            output += chunk.toString();
            if (output.includes("Local URL")) {
                clearTimeout(timer);
                resolve();
            }
        });
        child.once("exit", code => {
            clearTimeout(timer);
            reject(new Error(`MCP HTTP server exited early (${code}): ${output}`));
        });
    });
}

(async () => {
    const port = await availablePort();
    const home = fs.mkdtempSync(path.join(os.tmpdir(), "plag-mcp-test-"));
    const key = "test-mcp-http-key";
    const child = spawn(process.execPath, [path.join(__dirname, "../bin/mcp-http-server.js")], {
        env: { ...process.env, HOME: home, MCP_PORT: String(port), MCP_API_KEY: key },
        stdio: ["ignore", "pipe", "pipe"],
    });

    try {
        await waitForReady(child);
        const endpoint = `http://127.0.0.1:${port}/mcp`;

        let response = await fetch(endpoint, {
            method: "POST", headers: { "content-type": "application/json" },
            body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "ping" }),
        });
        assert.equal(response.status, 401);

        const headers = { "content-type": "application/json", authorization: `Bearer ${key}` };
        response = await fetch(endpoint, {
            method: "POST", headers,
            body: JSON.stringify({ jsonrpc: "2.0", id: 2, method: "ping" }),
        });
        assert.equal(response.status, 200);
        assert.deepEqual(await response.json(), { jsonrpc: "2.0", id: 2, result: {} });

        response = await fetch(endpoint, {
            method: "POST", headers,
            body: JSON.stringify({ jsonrpc: "2.0", method: "notifications/initialized" }),
        });
        assert.equal(response.status, 202);
        assert.equal(await response.text(), "");

        response = await fetch(endpoint, {
            method: "POST", headers,
            body: JSON.stringify([
                { jsonrpc: "2.0", id: 3, method: "tools/list" },
                { jsonrpc: "2.0", method: "notifications/initialized" },
                null,
            ]),
        });
        const batch = await response.json();
        assert.equal(batch.length, 2);
        assert.ok(batch[0].result.tools.some(tool => tool.name === "plag_scan_text"));
        assert.equal(batch[1].error.code, -32600);

        response = await fetch(endpoint, {
            method: "POST", headers,
            body: JSON.stringify({
                jsonrpc: "2.0", id: 4, method: "tools/call",
                params: { name: "plag_scan_text", arguments: { text: 123 } },
            }),
        });
        const invalid = await response.json();
        assert.equal(invalid.result.isError, true);
        assert.equal(invalid.result.content[0].text, "Check the tool name and arguments.");
        console.log("MCP HTTP transport regressions passed.");
    } finally {
        child.kill("SIGTERM");
        fs.rmSync(home, { recursive: true, force: true });
    }
})().catch(error => {
    console.error(error);
    process.exitCode = 1;
});
