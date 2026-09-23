/**
 * Local standalone exact-passage coverage engine.
 */

const fs = require("fs");
const path = require("path");
const { DEFAULT_ACADEMIC_CORPUS } = require("./default_corpus");

class PlagiarismChecker {
    constructor(sourcesDir = null) {
        this.includeDefaults = !sourcesDir;
        this.sources = [];
        this.sourcesDir = sourcesDir || path.join(__dirname, "..", "sources");
        this.loadLocalSources();
    }

    loadLocalSources() {
        // 1. Initialize with built-in academic reference corpus
        this.sources = [];
        (this.includeDefaults ? DEFAULT_ACADEMIC_CORPUS : []).forEach(src => {
            this.sources.push({
                filename: src.filename,
                text: src.text,
                words: src.text.trim().split(/\s+/).length
            });
        });

        // 2. Supplement with any additional local filesystem sources if directory exists
        if (fs.existsSync(this.sourcesDir)) {
            const files = fs.readdirSync(this.sourcesDir);
            const loaded = new Set(this.sources.map(s => s.filename));
            files.forEach(f => {
                const fullPath = path.join(this.sourcesDir, f);
                if (fs.statSync(fullPath).isFile() && !f.startsWith(".") && !loaded.has(f)) {
                    try {
                        const content = require("./extractor").DocumentExtractor.extractFromFile(fullPath);
                        this.sources.push({
                            filename: f,
                            text: content,
                            words: content.trim().split(/\s+/).length
                        });
                    } catch {}
                }
            });
        }
    }

    /**
     * Performs lexical passage-overlap analysis against configured sources.
     * @param {string} text 
     * @param {object} [options] 
     */
    analyze(text, options = {}) {
        if (typeof text !== 'string') throw new TypeError('Document text must be a string.');
        if (text.length > 100000) throw new Error('Document exceeds the 100,000 character analysis limit.');
        const matching = require('./matching').matchDocument(text, this.sources, options);
        const score = matching.overall_similarity;
        return { ...matching,
            safeassign_risk: score >= 40 ? 'High Risk' : score >= 15 ? 'Medium Risk' : 'Low Risk',
            status_class: score >= 40 ? 'danger' : score >= 15 ? 'warning' : 'success',
        };
    }
}
module.exports = { PlagiarismChecker };
