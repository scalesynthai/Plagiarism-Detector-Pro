/**
 * Multi-Format Document Text Extractor
 * Supports plain text, Markdown, LaTeX, Jupyter Notebooks, and JSON files.
 */

const fs = require("fs");
const path = require("path");

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
