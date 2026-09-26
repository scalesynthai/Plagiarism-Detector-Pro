/**
 * Multi-Format Document Text Extractor
 * Supports plain text, Markdown, LaTeX, Jupyter Notebooks, JSON, and Word (.docx), and PDF files.
 */

const fs = require("fs");
const path = require("path");
const zlib = require("zlib");
const { extractPdfText } = require("./pdf_extractor");

const MAX_DOCUMENT_BYTES = 8 * 1024 * 1024;
const MAX_DOCX_XML_BYTES = 32 * 1024 * 1024;

class DocumentExtractor {
    /**
     * Extracts clean plain text from a file path.
     * @param {string} filePath 
     * @returns {string}
     */
    static extractFromFile(filePath) {
        if (!fs.existsSync(filePath)) {
            throw new Error(`File not found: ${filePath}`);
        }

        const ext = path.extname(filePath).toLowerCase();
        if (![".txt", ".md", ".tex", ".ipynb", ".json", ".csv", ".bib", ".docx", ".pdf"].includes(ext)) {
            throw new Error(`Unsupported local document format: ${ext}. Supported: .pdf, .docx, .txt, .md, .tex, .ipynb, .json, .csv, .bib.`);
        }
        const stat = fs.statSync(filePath);
        if (!stat.isFile() || stat.size > MAX_DOCUMENT_BYTES) {
            throw new Error("Document must be a regular file no larger than 8 MB.");
        }
        if (ext === ".docx") {
            return this.extractFromDocx(fs.readFileSync(filePath));
        }
        if (ext === ".pdf") {
            return this.extractFromPdf(fs.readFileSync(filePath));
        }
        const content = fs.readFileSync(filePath, "utf8");

        switch (ext) {
            case ".ipynb":
                return this.extractFromJupyter(content);
            case ".tex":
                return this.extractFromLatex(content);
            case ".md":
                return this.extractFromMarkdown(content);
            case ".json":
                try {
                    const parsed = JSON.parse(content);
                    if (parsed.cells) return this.extractFromJupyter(content);
                    return typeof parsed === "string" ? parsed : JSON.stringify(parsed, null, 2);
                } catch {
                    return content;
                }
            default:
                return content;
        }
    }

    /**
     * Extracts text from a PDF buffer. Scanned (image-only) PDFs have no text layer and are rejected.
     * @param {Buffer} buffer
     * @returns {string}
     */
    static extractFromPdf(buffer) {
        let text;
        try {
            text = extractPdfText(buffer);
        } catch (error) {
            throw new Error(`Failed to read PDF file: ${error.message}`);
        }
        if (!text) {
            throw new Error("No extractable text found in PDF. It may be a scanned/image-only document; run OCR on it first.");
        }
        return text;
    }

    /**
     * Extracts paragraph and table text from a Word .docx buffer.
     * A .docx is a zip archive; the body lives in word/document.xml.
     * @param {Buffer} buffer
     * @returns {string}
     */
    static extractFromDocx(buffer) {
        let xml;
        try {
            xml = this._readZipEntry(buffer, "word/document.xml").toString("utf8");
        } catch (error) {
            throw new Error(`Failed to read DOCX file: ${error.message}`);
        }
        const text = xml
            .replace(/<w:del\b[^>]*>[\s\S]*?<\/w:del>/g, "")
            .replace(/<w:instrText\b[^>]*>[\s\S]*?<\/w:instrText>/g, "")
            .replace(/<w:tab\b[^>]*\/>/g, "\t")
            .replace(/<w:(?:br|cr)\b[^>]*\/>/g, "\n")
            .replace(/<\/w:p>/g, "\n\n")
            .replace(/<[^>]+>/g, "")
            .replace(/&(#x[0-9a-fA-F]+|#\d+|amp|lt|gt|quot|apos);/g, (m, e) => {
                if (e[0] !== "#") return { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'" }[e];
                const code = e[1] === "x" ? parseInt(e.slice(2), 16) : parseInt(e.slice(1), 10);
                return code <= 0x10ffff ? String.fromCodePoint(code) : "";
            });
        return text.replace(/[ \t]+\n/g, "\n").replace(/\n{3,}/g, "\n\n").trim();
    }

    /**
     * Reads and inflates one entry from a zip buffer (no external dependencies).
     * @param {Buffer} buf
     * @param {string} name
     * @returns {Buffer}
     */
    static _readZipEntry(buf, name) {
        // Locate the end-of-central-directory record (may be followed by a comment).
        let eocd = -1;
        for (let i = buf.length - 22; i >= Math.max(0, buf.length - 22 - 0xffff); i--) {
            if (buf.readUInt32LE(i) === 0x06054b50) { eocd = i; break; }
        }
        if (eocd < 0) throw new Error("not a valid zip archive");
        const count = buf.readUInt16LE(eocd + 10);
        let pos = buf.readUInt32LE(eocd + 16);
        if (count > 2000) throw new Error("archive exceeds extraction limits");
        for (let n = 0; n < count; n++) {
            if (pos + 46 > buf.length || buf.readUInt32LE(pos) !== 0x02014b50) throw new Error("corrupt zip directory");
            const method = buf.readUInt16LE(pos + 10);
            const compSize = buf.readUInt32LE(pos + 20);
            const nameLen = buf.readUInt16LE(pos + 28);
            const extraLen = buf.readUInt16LE(pos + 30);
            const commentLen = buf.readUInt16LE(pos + 32);
            const localOffset = buf.readUInt32LE(pos + 42);
            const entryName = buf.toString("utf8", pos + 46, pos + 46 + nameLen);
            pos += 46 + nameLen + extraLen + commentLen;
            if (entryName !== name) continue;
            if (localOffset + 30 > buf.length || buf.readUInt32LE(localOffset) !== 0x04034b50) throw new Error("corrupt zip entry");
            const dataStart = localOffset + 30 + buf.readUInt16LE(localOffset + 26) + buf.readUInt16LE(localOffset + 28);
            const data = buf.subarray(dataStart, dataStart + compSize);
            if (method === 0) return data;
            if (method !== 8) throw new Error(`unsupported compression method ${method}`);
            return zlib.inflateRawSync(data, { maxOutputLength: MAX_DOCX_XML_BYTES });
        }
        throw new Error(`${name} not found (is this a Word document?)`);
    }

    /**
     * Extracts markdown and code text from Jupyter notebook JSON.
     * @param {string} rawJson 
     */
    static extractFromJupyter(rawJson) {
        try {
            const nb = JSON.parse(rawJson);
            const textParts = [];
            (nb.cells || []).forEach(cell => {
                if (cell.cell_type === "markdown" || cell.cell_type === "raw") {
                    const src = Array.isArray(cell.source) ? cell.source.join("") : cell.source;
                    if (src) textParts.push(src);
                } else if (cell.cell_type === "code") {
                    const src = Array.isArray(cell.source) ? cell.source.join("") : cell.source;
                    if (src && src.trim()) {
                        // Extract comments and string docstrings
                        const comments = src.split("\n").filter(l => l.trim().startsWith("#")).map(l => l.replace(/^#+\s*/, ""));
                        if (comments.length > 0) textParts.push(comments.join("\n"));
                    }
                }
            });
            return textParts.join("\n\n");
        } catch {
            return rawJson;
        }
    }

    /**
     * Strips LaTeX markup into clean prose.
     * @param {string} latexText 
     */
    static extractFromLatex(latexText) {
        let clean = latexText;
        // Remove comments
        clean = clean.replace(/%.*$/gm, "");
        // Remove math environments
        clean = clean.replace(/\$\$.*?\$\$/gs, " [Equation] ");
        clean = clean.replace(/\$.*?\$/g, " [Math] ");
        clean = clean.replace(/\\begin\{equation\}.*?\\end\{equation\}/gs, " [Equation] ");
        // Strip common commands e.g. \section{...} -> ...
        clean = clean.replace(/\\(?:section|subsection|subsubsection|paragraph|textbf|textit|emph)\{([^}]+)\}/g, "$1");
        // Remove generic backslash commands
        clean = clean.replace(/\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{[^}]*\})?/g, " ");
        // Normalize whitespace
        return clean.replace(/\s+/g, " ").trim();
    }

    /**
     * Cleans Markdown formatting.
     * @param {string} mdText 
     */
    static extractFromMarkdown(mdText) {
        let clean = mdText;
        // Strip headers
        clean = clean.replace(/^#+\s+/gm, "");
        // Strip code blocks
        clean = clean.replace(/```[\s\S]*?```/g, " [Code Block] ");
        clean = clean.replace(/`([^`]+)`/g, "$1");
        // Strip images and links
        clean = clean.replace(/!\[([^\]]*)\]\([^)]+\)/g, "$1");
        clean = clean.replace(/\[([^\]]+)\]\([^)]+\)/g, "$1");
        return clean.trim();
    }
}

module.exports = { DocumentExtractor };
