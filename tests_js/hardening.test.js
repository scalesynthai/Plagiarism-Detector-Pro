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
        const unsupported = path.join(directory, 'test.xyz');
        fs.writeFileSync(unsupported, 'content');
        assert.throws(() => DocumentExtractor.extractFromFile(unsupported), /Unsupported/);
        const pdf = path.join(directory, 'test.pdf');
        fs.writeFileSync(pdf, '%PDF-1.4 binary content');
        assert.throws(() => DocumentExtractor.extractFromFile(pdf), /No extractable text/);
        fs.writeFileSync(pdf, 'not a pdf');
        assert.throws(() => DocumentExtractor.extractFromFile(pdf), /Failed to read PDF/);
        const zlibForPdf = require('node:zlib');
        // Simple-font PDF: plain objects, Tj/TJ operators, kerning that must not split words, and a line move.
        const content = 'BT /F1 12 Tf 72 700 Td (Hello \\(PDF\\) world) Tj 0 -14 Td [(Kern) -20 (ed) -300 (words)] TJ ET';
        fs.writeFileSync(pdf, [
            '%PDF-1.4',
            '1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj',
            '2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 /Resources << /Font << /F1 5 0 R >> >> >> endobj',
            '3 0 obj << /Type /Page /Parent 2 0 R /Contents 4 0 R >> endobj',
            `4 0 obj << /Length ${content.length} >> stream\n${content}\nendstream endobj`,
            '5 0 obj << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> endobj',
            '%%EOF',
        ].join('\n'));
        assert.equal(DocumentExtractor.extractFromFile(pdf), 'Hello (PDF) world\nKerned words');
        // CID font with a ToUnicode CMap, compressed content, and page objects stored in an object stream.
        const cmap = '/CIDInit begincmap 1 begincodespacerange <0000> <FFFF> endcodespacerange '
            + '2 beginbfchar <0001> <0048> <0002> <0069> endbfchar 1 beginbfrange <0003> <0005> <0061> endbfrange endcmap';
        const cidContent = zlibForPdf.deflateSync(Buffer.from('BT /F1 10 Tf 0 0 Td <00010002000300040005> Tj ET'));
        const inner = ['<< /Type /Catalog /Pages 11 0 R >>', '<< /Type /Pages /Kids [12 0 R] /Count 1 /Resources << /Font << /F1 14 0 R >> >> >>',
            '<< /Type /Page /Parent 11 0 R /Contents 13 0 R >>'];
        let offset = 0; const header = [];
        inner.forEach((body, i) => { header.push(`${10 + i} ${offset}`); offset += body.length + 1; });
        const objStm = zlibForPdf.deflateSync(Buffer.from(header.join(' ') + '\n' + inner.join('\n')));
        const parts = [
            Buffer.from('%PDF-1.5\n'),
            Buffer.from(`20 0 obj << /Type /ObjStm /N 3 /First ${header.join(' ').length + 1} /Filter /FlateDecode /Length ${objStm.length} >> stream\n`), objStm, Buffer.from('\nendstream endobj\n'),
            Buffer.from(`13 0 obj << /Filter /FlateDecode /Length ${cidContent.length} >> stream\n`), cidContent, Buffer.from('\nendstream endobj\n'),
            Buffer.from(`14 0 obj << /Type /Font /Subtype /Type0 /ToUnicode 15 0 R >> endobj\n15 0 obj << /Length ${cmap.length} >> stream\n${cmap}\nendstream endobj\n`),
        ];
        fs.writeFileSync(pdf, Buffer.concat(parts));
        assert.equal(DocumentExtractor.extractFromFile(pdf), 'Hiabc');
        fs.writeFileSync(pdf, '%PDF-1.6\n1 0 obj << /Encrypt 9 0 R /Root 2 0 R >> endobj');
        assert.throws(() => DocumentExtractor.extractFromFile(pdf), /encrypted/);
        const zlib = require('node:zlib');
        const docXml = '<w:document><w:body><w:p><w:r><w:t>Fish &amp; chips</w:t></w:r><w:r><w:tab/><w:t xml:space="preserve"> are tasty.</w:t></w:r></w:p>'
            + '<w:p><w:del><w:r><w:delText>removed</w:delText></w:r></w:del><w:r><w:t>Second paragraph.</w:t></w:r></w:p>'
            + '<w:tbl><w:tr><w:tc><w:p><w:r><w:t>Cell A</w:t></w:r></w:p></w:tc><w:tc><w:p><w:r><w:t>Cell B</w:t></w:r></w:p></w:tc></w:tr></w:tbl></w:body></w:document>';
        const name = Buffer.from('word/document.xml');
        const data = zlib.deflateRawSync(Buffer.from(docXml));
        const local = Buffer.alloc(30); local.writeUInt32LE(0x04034b50, 0); local.writeUInt16LE(8, 8);
        local.writeUInt32LE(data.length, 18); local.writeUInt32LE(docXml.length, 22); local.writeUInt16LE(name.length, 26);
        const central = Buffer.alloc(46); central.writeUInt32LE(0x02014b50, 0); central.writeUInt16LE(8, 10);
        central.writeUInt32LE(data.length, 20); central.writeUInt32LE(docXml.length, 24); central.writeUInt16LE(name.length, 28);
        const end = Buffer.alloc(22); end.writeUInt32LE(0x06054b50, 0); end.writeUInt16LE(1, 8); end.writeUInt16LE(1, 10);
        const cdOffset = local.length + name.length + data.length;
        end.writeUInt32LE(central.length + name.length, 12); end.writeUInt32LE(cdOffset, 16);
        const docx = path.join(directory, 'test.docx');
        fs.writeFileSync(docx, Buffer.concat([local, name, data, central, name, end]));
        assert.equal(DocumentExtractor.extractFromFile(docx), 'Fish & chips\t are tasty.\n\nSecond paragraph.\n\nCell A\n\nCell B');
        fs.writeFileSync(docx, 'not a zip');
        assert.throws(() => DocumentExtractor.extractFromFile(docx), /Failed to read DOCX/);
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
