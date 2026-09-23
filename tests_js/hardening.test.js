const assert = require('node:assert/strict');
const { spawnSync } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const { scan, DocumentExtractor, PlagiarismApiClient, CitationGenerator } = require('../lib');

(async () => {
    await assert.rejects(scan(null), /required/);
    await assert.rejects(scan(' '), /required/);
    const result = await scan('This sentence mentions a file named example.txt');
    assert.equal(typeof result.overall_similarity, 'number');
    const directory = fs.mkdtempSync(path.join(os.tmpdir(), 'plag-tests-'));
    try {
        const pdf = path.join(directory, 'test.pdf');
        fs.writeFileSync(pdf, '%PDF-1.4 binary content');
        assert.throws(() => DocumentExtractor.extractFromFile(pdf), /Unsupported/);
    } finally { fs.rmSync(directory, { recursive: true }); }
    const originalFetch = global.fetch;
    try {
        global.fetch = async (url, options) => {
            assert.ok(options.signal instanceof AbortSignal);
            return { ok: false, status: 503, json: async () => { throw new Error('not JSON'); } };
        };
        await assert.rejects(new PlagiarismApiClient().scanText('test'), /503/);
        const citation = await CitationGenerator.resolveCitation('10.1234/example');
        assert.equal(citation.metadata_resolved, false);
        assert.equal(citation.year, 'n.d.');
        assert.ok(citation.warning);
    } finally { global.fetch = originalFetch; }
    const requests = [
        'bad JSON', 'null',
        JSON.stringify({ jsonrpc: '2.0', method: 'notifications/initialized' }),
        JSON.stringify({ jsonrpc: '2.0', id: 1, method: 'unknown' }),
        JSON.stringify({ jsonrpc: '2.0', id: 2, method: 'ping' }),
        JSON.stringify({ jsonrpc: '2.0', id: 3, method: 'tools/call', params: { name: 'plag_scan_text', arguments: { text: 123 } } }),
    ];
    const child = spawnSync(process.execPath, [path.join(__dirname, '../bin/mcp-server.js')], {
        input: requests.join('\n') + '\n', encoding: 'utf8', timeout: 10000,
    });
    assert.equal(child.status, 0, child.stderr);
    const responses = child.stdout.trim().split('\n').map(JSON.parse);
    assert.equal(responses.length, 5);
    assert.equal(responses[0].error.code, -32700);
    assert.equal(responses[1].error.code, -32600);
    assert.equal(responses.find(r => r.id === 1).error.code, -32601);
    assert.deepEqual(responses.find(r => r.id === 2).result, {});
    assert.equal(responses.find(r => r.id === 3).result.isError, true);
    console.log('JavaScript hardening regressions passed.');
})().catch(error => { console.error(error); process.exitCode = 1; });
