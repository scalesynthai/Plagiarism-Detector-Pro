const fs = require('node:fs');
const { PlagiarismChecker } = require('../lib/checker');
const cases = JSON.parse(fs.readFileSync(0,'utf8'));
const results = cases.map(c => {
    const checker = Object.create(PlagiarismChecker.prototype);
    checker.sources = c.sources;
    return checker.analyze(c.text, {excludeQuotes:!!c.options.exclude_quotes,excludeBibliography:!!c.options.exclude_bibliography});
});
process.stdout.write(JSON.stringify(results));
