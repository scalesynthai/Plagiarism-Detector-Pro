/**
 * Plagiarism Detector Pro Cloud & Local Server API Client
 */

class PlagiarismApiClient {
    constructor(baseUrl = "https://plag.subba.dev") {
        this.baseUrl = baseUrl.replace(/\/+$/, "");
    }

    /**
     * Calls /check API endpoint.
     */
    async scanText(queryText, options = {}) {
        const url = `${this.baseUrl}/check`;
        const payload = {
            query: queryText,
            include_web: options.includeWeb !== false,
            exclude_quotes: Boolean(options.excludeQuotes),
            private_draft: options.privateDraft !== false
        };

        const res = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.error || `Server error (${res.status})`);
        }

        return await res.json();
    }

    /**
     * Calls /api/paraphrase endpoint.
     */
    async paraphraseSentence(sentence, sourceName = null, sourceTitle = null) {
        const url = `${this.baseUrl}/api/paraphrase`;
        const res = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                sentence,
                source_name: sourceName,
                source_title: sourceTitle
            })
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.error || `Server error (${res.status})`);
        }

        return await res.json();
    }

    /**
     * Calls /api/cite endpoint.
     */
    async generateCitation(query) {
        const url = `${this.baseUrl}/api/cite`;
        const res = await fetch(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ query })
        });

        if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            throw new Error(err.error || `Server error (${res.status})`);
        }

        return await res.json();
    }
}

module.exports = { PlagiarismApiClient };
