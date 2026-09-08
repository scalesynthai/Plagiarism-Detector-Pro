let currentAnalysisData = null;
let currentSentenceObj = null;
let allSourcesData = [];
let targetDeleteFilename = null;

// Academic Preset Samples
const PRESETS = {
    ai: `Artificial intelligence and modern machine learning have fundamentally transformed natural language processing. Deep neural networks and transformer architectures leverage self-attention mechanisms to learn rich contextual representations from massive text corpora (Vaswani et al., 2017). In this paper, we evaluate causal reasoning in large language models using targeted intervention experiments. Our empirical results demonstrate that while parameter scaling improves factual retrieval, logical generalization requires explicit neuro-symbolic reasoning frameworks.`,
    
    diamond: `In this empirical investigation, we analyze diamond pricing distributions across cut, color, and clarity dimensions. Working through this analysis reinforced that data visualization is not merely an aesthetic reporting step, but a primary diagnostic tool for causal reasoning. The near-collinearity uncovered among the physical dimensions (x, y, z) and carat (r > .95) would destabilize regression coefficients if left unaddressed. Regression conditioning alongside discrete binning isolates confounding effects systematically.`,
    
    crispr: `Clustered Regularly Interspaced Short Palindromic Repeats (CRISPR) and CRISPR-associated proteins (Cas) represent a revolutionary paradigm in molecular biology (Doudna & Charpentier, 2014). By utilizing synthetic single-guide RNAs (sgRNAs), the endonuclease Cas9 induces targeted double-strand breaks at specific genomic loci. Repair occurs through either non-homologous end joining (NHEJ) or homology-directed repair (HDR). This precision enables therapeutic gene editing for hereditary disorders.`
};

document.addEventListener('DOMContentLoaded', () => {

    // 1. Tab Navigation
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabPanels = document.querySelectorAll('.tab-panel');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            const targetTab = btn.getAttribute('data-tab');
            tabBtns.forEach(b => b.classList.remove('active'));
            tabPanels.forEach(p => p.classList.remove('active'));

            btn.classList.add('active');
            const activePanel = document.getElementById(targetTab);
            if (activePanel) activePanel.classList.add('active');
        });
    });

    // 2. Setup Dropzones
    setupDropzone('scan-dropzone', 'file-input', 'scan-file-preview', 'scan-file-name', 'scan-file-size', 'scan-remove-file');
    setupDropzone('batch-dropzone', 'batch-file-input', 'batch-file-preview', 'batch-file-name', 'batch-file-size', 'batch-remove-file');
    setupDropzone('source-dropzone', 'source-file-input', 'source-file-preview', 'source-file-name', 'source-file-size', 'source-remove-file');

    // 3. Live Editor Stats, Presets & Hotkeys
    initEditorTools();

    // 4. Handle Direct Text Form Submit
    const textForm = document.getElementById('text-scan-form');
    if (textForm) {
        textForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const text = document.getElementById('query-text').value.trim();
            if (!text) return alert('Please enter text to analyze.');
            const privateDraft = document.getElementById('text-private-draft') ? document.getElementById('text-private-draft').checked : true;
            const includeWeb = document.getElementById('text-live-search') ? document.getElementById('text-live-search').checked : true;
            const excludeQuotes = document.getElementById('text-exclude-quotes') ? document.getElementById('text-exclude-quotes').checked : false;
            await runScan({ query: text, include_web: includeWeb, exclude_quotes: excludeQuotes, private_draft: privateDraft });
        });
    }

    // 5. Handle Single Document Form Submit
    const fileForm = document.getElementById('file-scan-form');
    if (fileForm) {
        fileForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const fileInput = document.getElementById('file-input');
            if (!fileInput.files || fileInput.files.length === 0) {
                return alert('Please select a document file (.docx, .pdf, .tex, .ipynb, .txt).');
            }
            const privateDraft = document.getElementById('file-private-draft') ? document.getElementById('file-private-draft').checked : true;
            const includeWeb = document.getElementById('file-live-search') ? document.getElementById('file-live-search').checked : true;
            const excludeQuotes = document.getElementById('file-exclude-quotes') ? document.getElementById('file-exclude-quotes').checked : false;

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);
            formData.append('include_web', includeWeb);
            formData.append('exclude_quotes', excludeQuotes);
            formData.append('private_draft', privateDraft);
            await runScan(formData, true);
        });
    }

    // 6. Handle Draft-to-Draft Revision Comparison
    const compareForm = document.getElementById('compare-drafts-form');
    if (compareForm) {
        compareForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const v1 = document.getElementById('draft-v1-text').value.trim();
            const v2 = document.getElementById('draft-v2-text').value.trim();
            if (!v1 || !v2) return alert('Please input both Draft 1 and Draft 2 texts for comparison.');
            await runDraftComparison(v1, v2);
        });
    }

    // 7. Handle DOI & Citation Generator Form
    const citeForm = document.getElementById('cite-generator-form');
    if (citeForm) {
        citeForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const query = document.getElementById('cite-query-input').value.trim();
            if (!query) return alert('Please enter a DOI, arXiv link, or paper title.');
            await runCitationGeneration(query);
        });
    }

    // 7.1 Handle Reference List Alphabetizer Form
    const alphabetizeForm = document.getElementById('alphabetize-references-form');
    if (alphabetizeForm) {
        alphabetizeForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const rawRefs = document.getElementById('raw-references-input').value.trim();
            if (!rawRefs) return alert('Please paste your reference list into the box.');
            await runAlphabetizeReferences(rawRefs);
        });
    }

    // 7.2 Sample References Button
    const sampleRefBtn = document.getElementById('btn-sample-references');
    if (sampleRefBtn) {
        sampleRefBtn.addEventListener('click', () => {
            const rawInput = document.getElementById('raw-references-input');
            if (rawInput) {
                rawInput.value = `Vaswani, A., Shazeer, N., Parmar, N., Uszkoreit, J., Jones, L., Gomez, A. N., Kaiser, Ł., & Polosukhin, I. (2017). Attention is all you need. Advances in Neural Information Processing Systems, 30, 5998-6008.
Devlin, J., Chang, M. W., Lee, K., & Toutanova, K. (2018). BERT: Pre-training of deep bidirectional transformers for language understanding. arXiv:1810.04805.
Brown, T., Mann, B., Ryder, N., Subbiah, M., Kaplan, J. D., Dhariwal, P., ... & Amodei, D. (2020). Language models are few-shot learners. NeurIPS. https://doi.org/10.48550/arXiv.2005.14165
Doudna, J. A., & Charpentier, E. (2014). The new frontier of genome engineering with CRISPR-Cas9. Science, 346(6213), 1258096. https://doi.org/10.1126/science.1258096
Achiam, J., Adler, S., Agarwal, S., Ahmad, L., Akkaya, I., Aleman, F. L., ... & McGrew, B. (2023). GPT-4 technical report. arXiv:2303.08774.`;
                runAlphabetizeReferences(rawInput.value);
            }
        });
    }

    // 7.3 Copy Formatted Alphabetized Bibliography
    const copyAlphabetizedBtn = document.getElementById('btn-copy-alphabetized');
    if (copyAlphabetizedBtn) {
        copyAlphabetizedBtn.addEventListener('click', () => {
            const container = document.getElementById('alphabetized-output-list');
            if (!container) return;
            const entries = container.querySelectorAll('.ref-entry');
            const cleanText = Array.from(entries).map(el => {
                const textEl = el.querySelector('.ref-text');
                return textEl ? textEl.textContent.trim() : el.textContent.trim();
            }).join('\n\n');

            navigator.clipboard.writeText(cleanText);
            const orig = copyAlphabetizedBtn.textContent;
            copyAlphabetizedBtn.textContent = '✓ Copied to Clipboard!';
            setTimeout(() => { copyAlphabetizedBtn.textContent = orig; }, 2000);
        });
    }

    // 8. Handle Batch Scan Form Submit
    const batchForm = document.getElementById('batch-scan-form');
    if (batchForm) {
        batchForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const fileInput = document.getElementById('batch-file-input');
            if (!fileInput.files || fileInput.files.length === 0) {
                return alert('Please select a ZIP file or multiple documents.');
            }
            await runBatchScan(fileInput.files);
        });
    }

    // 9. Handle Add Institutional Source Submit
    const addSourceForm = document.getElementById('add-source-form');
    if (addSourceForm) {
        addSourceForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const fileInput = document.getElementById('source-file-input');
            if (!fileInput.files || fileInput.files.length === 0) {
                return alert('Please choose a file to add as an institutional reference source.');
            }
            const submitBtn = addSourceForm.querySelector('button[type="submit"]');
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner"></span> Adding to Repository...';

            const formData = new FormData();
            formData.append('file', fileInput.files[0]);

            try {
                const res = await fetch('/sources/upload', {
                    method: 'POST',
                    body: formData
                });
                const data = await res.json();
                if (res.ok && data.success) {
                    alert('Document added successfully to institutional corpus!');
                    fileInput.value = '';
                    const preview = document.getElementById('source-file-preview');
                    if (preview) preview.style.display = 'none';
                    loadSourcesList();
                } else {
                    alert('Error: ' + (data.error || 'Failed to upload document'));
                }
            } catch (err) {
                alert('Upload network error: ' + err.message);
            } finally {
                submitBtn.disabled = false;
                submitBtn.innerHTML = '<span>➕ Add to Institutional Repository</span>';
            }
        });
    }

    // 10. Modals, Certs, and PIN Security Setup
    setupModalsAndActions();

    // 11. Initial load of institutional corpus
    loadSourcesList();
});

/* ==============================================================================
   CLAY INITIALIZATION
   ============================================================================== */
function initTheme() {
    // Clay design system uses a persistent warm cream canvas (#fffaf0).
}

/* ==============================================================================
   EDITOR TOOLBAR, LIVE STATS & PRESETS
   ============================================================================== */
function initEditorTools() {
    const textarea = document.getElementById('query-text');
    if (!textarea) return;

    const targetSelect = document.getElementById('budget-target-select');
    const customInput = document.getElementById('budget-custom-input');
    const progressFill = document.getElementById('budget-progress-fill');
    const countSpan = document.getElementById('budget-words-count');
    const remainingSpan = document.getElementById('budget-words-remaining');
    const statusPill = document.getElementById('budget-status-pill');

    const getTargetWords = () => {
        if (!targetSelect) return 1000;
        if (targetSelect.value === 'custom') {
            return parseInt(customInput.value, 10) || 1000;
        }
        return parseInt(targetSelect.value, 10) || 1000;
    };

    if (targetSelect) {
        targetSelect.addEventListener('change', () => {
            if (targetSelect.value === 'custom') {
                if (customInput) customInput.style.display = 'inline-block';
            } else {
                if (customInput) customInput.style.display = 'none';
            }
            updateMetrics();
        });
    }

    if (customInput) {
        customInput.addEventListener('input', updateMetrics);
    }

    // Live Metrics Update
    function updateMetrics() {
        const text = textarea.value;
        const words = text.trim() ? text.trim().split(/\s+/).length : 0;
        const chars = text.length;
        const sentences = text.trim() ? (text.match(/[.!?]+(?=\s|\n|$)/g) || []).length || (words > 0 ? 1 : 0) : 0;
        const paragraphs = text.trim() ? text.split(/\n+/).filter(p => p.trim().length > 0).length : 0;
        const readingTime = Math.max(1, Math.round(words / 200));

        const wordsElem = document.getElementById('live-words');
        const charsElem = document.getElementById('live-chars');
        const sentsElem = document.getElementById('live-sentences');
        const parasElem = document.getElementById('live-paragraphs');
        const timeElem = document.getElementById('live-reading-time');
        const readElem = document.getElementById('live-readability');

        if (wordsElem) wordsElem.textContent = words;
        if (charsElem) charsElem.textContent = chars;
        if (sentsElem) sentsElem.textContent = sentences;
        if (parasElem) parasElem.textContent = paragraphs;
        if (timeElem) timeElem.textContent = `~${readingTime} min`;

        if (readElem) {
            if (words > 400) readElem.textContent = 'PhD / Scholarly';
            else if (words > 100) readElem.textContent = 'College Level';
            else readElem.textContent = 'Standard';
        }

        // Update Assignment Word Budget
        const targetWords = getTargetWords();
        const percent = Math.round((words / targetWords) * 100);

        if (progressFill) {
            progressFill.style.width = `${Math.min(percent, 100)}%`;
            if (percent > 115) {
                progressFill.classList.add('over-budget');
            } else {
                progressFill.classList.remove('over-budget');
            }
        }

        if (countSpan) {
            countSpan.textContent = `${words.toLocaleString()} / ${targetWords.toLocaleString()} words written`;
        }

        if (remainingSpan) {
            const diff = targetWords - words;
            if (diff > 0) {
                remainingSpan.textContent = `${diff.toLocaleString()} words needed`;
            } else if (diff === 0) {
                remainingSpan.textContent = `🎯 Target reached exactly!`;
            } else {
                remainingSpan.textContent = `${Math.abs(diff).toLocaleString()} words over target`;
            }
        }

        if (statusPill) {
            statusPill.className = 'budget-status-pill';
            if (percent < 80) {
                statusPill.classList.add('under');
                statusPill.textContent = `${percent}% of target • In Progress`;
            } else if (percent <= 110) {
                statusPill.classList.add('on-track');
                statusPill.textContent = `${percent}% of target • Optimal Sweet Spot`;
            } else {
                statusPill.classList.add('over');
                statusPill.textContent = `${percent}% of target • Exceeds Target`;
            }
        }
    }

    textarea.addEventListener('input', updateMetrics);
    updateMetrics();

    // Hotkey: Cmd/Ctrl + Enter
    textarea.addEventListener('keydown', (e) => {
        if ((e.metaKey || e.ctrlKey) && e.key === 'Enter') {
            e.preventDefault();
            const textForm = document.getElementById('text-scan-form');
            if (textForm) textForm.requestSubmit();
        }
    });

    // Preset Buttons
    document.querySelectorAll('.preset-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const key = btn.getAttribute('data-preset');
            if (PRESETS[key]) {
                textarea.value = PRESETS[key];
                updateMetrics();
                textarea.focus();
            }
        });
    });

    // Paste Clipboard
    const pasteBtn = document.getElementById('btn-paste-clipboard');
    if (pasteBtn) {
        pasteBtn.addEventListener('click', async () => {
            try {
                const clipText = await navigator.clipboard.readText();
                if (clipText) {
                    textarea.value = clipText;
                    updateMetrics();
                }
            } catch {
                textarea.focus();
                alert('Please use Cmd+V / Ctrl+V to paste.');
            }
        });
    }

    // Clear Text
    const clearBtn = document.getElementById('btn-clear-text');
    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            textarea.value = '';
            updateMetrics();
            textarea.focus();
        });
    }
}

/* ==============================================================================
   PLAGIARISM & AI DUAL SCAN LOGIC
   ============================================================================== */
async function runScan(payload, isFormData = false) {
    const activePanel = document.querySelector('.tab-panel.active');
    const submitBtn = activePanel.querySelector('button[type="submit"]');
    const originalHtml = submitBtn.innerHTML;

    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner"></span> Analyzing Originality & AI Likelihood...';

    try {
        const fetchOptions = {
            method: 'POST',
            body: isFormData ? payload : JSON.stringify(payload)
        };
        if (!isFormData) {
            fetchOptions.headers = { 'Content-Type': 'application/json' };
        }

        const res = await fetch('/check', fetchOptions);
        const data = await res.json();

        if (!res.ok) {
            throw new Error(data.error || 'Failed to complete analysis');
        }

        currentAnalysisData = data;
        renderResults(data);

        const resultsSection = document.getElementById('results-section');
        resultsSection.style.display = 'block';
        resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });

    } catch (err) {
        alert('Scan Error: ' + err.message);
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalHtml;
    }
}

function renderResults(data) {
    // 1. Obfuscation Alert Banner
    const obfAlert = document.getElementById('obfuscation-alert');
    const obfDesc = document.getElementById('obfuscation-desc');
    if (data.obfuscation_info && data.obfuscation_info.has_obfuscation) {
        obfDesc.textContent = data.obfuscation_info.details.join(' • ');
        obfAlert.style.display = 'block';
    } else {
        obfAlert.style.display = 'none';
    }

    // 2. Pre-Submission Checklist
    renderChecklist(data);

    // 2.1 PhD Conference & Anonymity Auditor
    renderPhdAuditor(data);

    // 2.2 Student Academic Writing & Integrity Coach
    renderStudentCoach(data);

    // 3. Score Gauges: Plagiarism + AI
    const plagScore = data.overall_similarity || 0;
    const aiData = data.ai_analysis || {};
    const aiScore = aiData.ai_probability || 0;

    const circlePlag = document.getElementById('score-circle-plag');
    const numPlag = document.getElementById('score-number-plag');
    const circleAi = document.getElementById('score-circle-ai');
    const numAi = document.getElementById('score-number-ai');

    numPlag.textContent = `${plagScore.toFixed(1)}%`;
    circlePlag.className = `score-circle ${data.status_class || 'success'}`;

    numAi.textContent = `${aiScore.toFixed(1)}%`;
    const aiStatus = aiScore >= 65 ? 'danger' : (aiScore >= 25 ? 'warning' : 'success');
    circleAi.className = `score-circle ${aiStatus}`;

    // Verdict Card
    const verdictBadge = document.getElementById('verdict-badge');
    const verdictTitle = document.getElementById('verdict-title');
    const verdictDesc = document.getElementById('verdict-desc');

    verdictBadge.className = `verdict-badge ${data.status_class}`;
    verdictBadge.textContent = `${data.safeassign_risk} • ${aiData.ai_risk_level || 'Human-Written'}`;

    if (data.highest_matching_source) {
        const urlAttr = data.highest_matching_url ? ` <a href="${escapeHtml(data.highest_matching_url)}" target="_blank" rel="noopener noreferrer" style="color: var(--primary); font-size: 13px;">[Open Reference ↗]</a>` : '';
        verdictTitle.innerHTML = `Top Match: ${escapeHtml(data.highest_matching_source)}${urlAttr}`;
        verdictDesc.textContent = data.verdict_description || `Highest single source similarity is ${data.highest_similarity}%.`;
    } else {
        verdictTitle.textContent = 'Original Academic Work';
        verdictDesc.textContent = 'No significant matching sequences found across scanned global databases.';
    }

    // Stats Grid
    const citationData = data.citation_analysis || {};
    document.getElementById('stat-total-words').textContent = data.total_words;
    document.getElementById('stat-flagged-words').textContent = `${data.flagged_word_count || 0} (${Math.round(((data.flagged_word_count || 0) / Math.max(data.total_words, 1)) * 100)}%)`;
    document.getElementById('stat-ai-burstiness').textContent = `${aiData.burstiness || 50.0}`;
    document.getElementById('stat-citations-count').textContent = citationData.in_text_citations_count || 0;
    document.getElementById('stat-sources-searched').textContent = `${data.total_corpus_searched || data.sources_breakdown.length} (${data.live_sources_queried || 0} Online)`;

    // 4. Interactive Full-Text Manuscript Inspector
    renderManuscriptInspector(data);

    // 5. Breakdown Table
    const tableBody = document.getElementById('sources-breakdown-body');
    tableBody.innerHTML = '';
    
    if (data.sources_breakdown && data.sources_breakdown.length > 0) {
        data.sources_breakdown.forEach(s => {
            const tr = document.createElement('tr');
            const barClass = s.similarity >= 40 ? 'high' : (s.similarity >= 15 ? 'med' : 'low');
            const nameHtml = s.url 
                ? `<a href="${escapeHtml(s.url)}" target="_blank" rel="noopener noreferrer" class="source-link">🔗 ${escapeHtml(s.filename)}</a>`
                : `<strong>🏛️ ${escapeHtml(s.filename)}</strong>`;

            tr.innerHTML = `
                <td>${nameHtml}</td>
                <td><span class="source-badge ${escapeHtml(s.source_type || 'institutional')}">${escapeHtml(s.badge || '🏛️ Institutional')}</span></td>
                <td>${s.source_word_count} words</td>
                <td style="width: 32%;">
                    <div style="display: flex; justify-content: space-between; font-weight: 600; font-size: 13px;">
                        <span>${s.similarity}%</span>
                    </div>
                    <div class="sim-bar-container">
                        <div class="sim-bar ${barClass}" style="width: ${Math.min(s.similarity, 100)}%;"></div>
                    </div>
                </td>
            `;
            tableBody.appendChild(tr);
        });
    } else {
        tableBody.innerHTML = '<tr><td colspan="4" style="text-align: center; color: var(--text-muted);">No reference sources available.</td></tr>';
    }

    // 6. Highlighted Text Viewer
    const textContainer = document.getElementById('highlighted-text');
    textContainer.innerHTML = '';

    if (data.highlighted_sentences && data.highlighted_sentences.length > 0) {
        data.highlighted_sentences.forEach(s => {
            const span = document.createElement('span');
            span.className = `sentence-chunk ${s.is_plagiarized ? 'plagiarized' : ''}`;
            span.textContent = s.text + ' ';

            if (s.is_plagiarized) {
                span.title = `Click to inspect Side-by-Side Match & Coaching Tips (${s.similarity}%):\n"${s.matched_source_sentence || ''}"`;
                span.addEventListener('click', () => {
                    openDiffModal(s);
                });
            }
            textContainer.appendChild(span);
        });
    } else {
        textContainer.textContent = 'No text content available to display.';
    }
}

/* ==============================================================================
   INTERACTIVE FULL-TEXT MANUSCRIPT INSPECTOR
   ============================================================================== */
function renderManuscriptInspector(data) {
    const viewer = document.getElementById('manuscript-viewer');
    if (!viewer) return;
    viewer.innerHTML = '';

    if (!data.highlighted_sentences || data.highlighted_sentences.length === 0) {
        viewer.textContent = 'No text to display.';
        return;
    }

    data.highlighted_sentences.forEach((s, idx) => {
        const span = document.createElement('span');
        span.className = 'sent-span';

        if (s.is_plagiarized) {
            if (s.similarity >= 70) span.classList.add('flag-high');
            else span.classList.add('flag-med');
        } else {
            span.classList.add('orig');
        }

        if (s.has_citation) span.classList.add('has-cite');

        span.textContent = s.text + ' ';
        span.title = `Sentence #${idx + 1} • Similarity: ${s.similarity}%${s.source ? ' • ' + s.source : ' • Original'}`;

        span.addEventListener('click', () => {
            if (s.is_plagiarized) {
                openDiffModal(s);
            } else {
                alert(`Sentence #${idx + 1} is 100% Original Academic Prose.\nNo overlapping passages found.`);
            }
        });

        viewer.appendChild(span);
    });
}

function renderChecklist(data) {
    const plagScore = data.overall_similarity || 0;
    const aiScore = (data.ai_analysis && data.ai_analysis.ai_probability) || 0;
    const citeData = data.citation_analysis || {};
    const readability = data.readability || {};

    const chkPlagPill = document.getElementById('chk-plag-pill');
    const chkPlagDesc = document.getElementById('chk-plag-desc');
    const chkPlag = document.getElementById('chk-plag');
    if (chkPlagPill) {
        if (plagScore < 15.0) {
            chkPlagPill.className = 'badge-pill success';
            chkPlagPill.textContent = `${plagScore}% Safe (< 15%)`;
            if (chkPlagDesc) chkPlagDesc.textContent = 'Well within standard academic submission threshold.';
            if (chkPlag) chkPlag.style.borderLeft = '3px solid var(--success)';
        } else if (plagScore < 40.0) {
            chkPlagPill.className = 'badge-pill warning';
            chkPlagPill.textContent = `${plagScore}% Moderate`;
            if (chkPlagDesc) chkPlagDesc.textContent = 'Review flagged sentences to ensure all citations are attributed.';
            if (chkPlag) chkPlag.style.borderLeft = '3px solid var(--warning)';
        } else {
            chkPlagPill.className = 'badge-pill danger';
            chkPlagPill.textContent = `${plagScore}% High Risk`;
            if (chkPlagDesc) chkPlagDesc.textContent = 'Significant verbatim overlap detected. Rewrite uncredited sections.';
            if (chkPlag) chkPlag.style.borderLeft = '3px solid var(--danger)';
        }
    }

    const chkAiPill = document.getElementById('chk-ai-pill');
    const chkAiDesc = document.getElementById('chk-ai-desc');
    const chkAi = document.getElementById('chk-ai');
    if (chkAiPill) {
        if (aiScore < 25.0) {
            chkAiPill.className = 'badge-pill success';
            chkAiPill.textContent = `${aiScore}% Human`;
            if (chkAiDesc) chkAiDesc.textContent = 'High burstiness and natural syntactic entropy detected.';
            if (chkAi) chkAi.style.borderLeft = '3px solid var(--success)';
        } else if (aiScore < 65.0) {
            chkAiPill.className = 'badge-pill warning';
            chkAiPill.textContent = `${aiScore}% Mixed AI`;
            if (chkAiDesc) chkAiDesc.textContent = 'Portions resemble AI-assisted drafting. Review phrasing.';
            if (chkAi) chkAi.style.borderLeft = '3px solid var(--warning)';
        } else {
            chkAiPill.className = 'badge-pill danger';
            chkAiPill.textContent = `${aiScore}% Likely AI`;
            if (chkAiDesc) chkAiDesc.textContent = 'Uniform low perplexity and synthetic cadence detected.';
            if (chkAi) chkAi.style.borderLeft = '3px solid var(--danger)';
        }
    }

    const chkCitePill = document.getElementById('chk-cite-pill');
    const chkCiteDesc = document.getElementById('chk-cite-desc');
    const chkCite = document.getElementById('chk-cite');
    if (chkCitePill) {
        if (citeData.in_text_citations_count > 0) {
            chkCitePill.className = 'badge-pill info';
            chkCitePill.textContent = `${citeData.in_text_citations_count} Verified`;
            if (chkCiteDesc) chkCiteDesc.textContent = `Identified formatted references (${citeData.styles_detected ? citeData.styles_detected.join(', ') : 'Standard'}).`;
            if (chkCite) chkCite.style.borderLeft = '3px solid #6366f1';
        } else {
            chkCitePill.className = 'badge-pill warning';
            chkCitePill.textContent = `0 Citations`;
            if (chkCiteDesc) chkCiteDesc.textContent = 'Consider adding APA/MLA in-text citations for cited references.';
            if (chkCite) chkCite.style.borderLeft = '3px solid var(--warning)';
        }
    }

    const chkReadPill = document.getElementById('chk-read-pill');
    const chkReadDesc = document.getElementById('chk-read-desc');
    const chkRead = document.getElementById('chk-read');
    if (chkReadPill && readability.grade_level) {
        chkReadPill.className = 'badge-pill info';
        chkReadPill.textContent = `${readability.grade_level}`;
        if (chkReadDesc) chkReadDesc.textContent = `${readability.reading_level_desc || 'Academic Standard'} • ~${readability.reading_time_minutes || 1} min read.`;
        if (chkRead) chkRead.style.borderLeft = '3px solid #8b5cf6';
    }

    const overallBadge = document.getElementById('checklist-overall-badge');
    if (overallBadge) {
        if (plagScore < 15.0 && aiScore < 30.0) {
            overallBadge.className = 'badge-pill success';
            overallBadge.textContent = '🌟 Ready for LMS / Canvas Submission';
            overallBadge.style.background = '';
            overallBadge.style.color = '';
        } else {
            overallBadge.className = 'badge-pill warning';
            overallBadge.textContent = '⚠️ Revision Recommended Prior to Submission';
            overallBadge.style.background = '';
            overallBadge.style.color = '';
        }
    }
}

function renderPhdAuditor(data) {
    const phdAudit = data.phd_audit || {};
    const anonPill = document.getElementById('phd-anon-pill');
    const anonDesc = document.getElementById('phd-anon-desc');
    const readinessBadge = document.getElementById('phd-readiness-badge');

    if (phdAudit.is_anonymity_compliant) {
        if (anonPill) {
            anonPill.className = 'badge-pill success';
            anonPill.textContent = '100% Compliant';
        }
        if (anonDesc) anonDesc.textContent = 'Zero self-identifying prior citations or unblinded repository links found.';
        if (readinessBadge) {
            readinessBadge.className = 'badge-pill success';
            readinessBadge.textContent = '100/100 • Conference Ready';
            readinessBadge.style.background = '';
            readinessBadge.style.color = '';
        }
    } else {
        if (anonPill) {
            anonPill.className = 'badge-pill danger';
            anonPill.textContent = `${phdAudit.anonymity_count || 1} Violation(s)`;
        }
        if (anonDesc) anonDesc.textContent = (phdAudit.anonymity_violations && phdAudit.anonymity_violations.join(' • ')) || 'Self-referential citations detected.';
        if (readinessBadge) {
            readinessBadge.className = 'badge-pill danger';
            readinessBadge.textContent = 'Action Required • Unblinded Passages';
            readinessBadge.style.background = '';
            readinessBadge.style.color = '';
        }
    }

    // Sections Table
    const secTableContainer = document.getElementById('phd-sections-table-container');
    const secBody = document.getElementById('phd-sections-body');
    if (secTableContainer && secBody && phdAudit.sections_breakdown && phdAudit.sections_breakdown.length > 0) {
        secBody.innerHTML = '';
        phdAudit.sections_breakdown.forEach(sec => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${escapeHtml(sec.heading)}</strong></td>
                <td>${sec.word_count} words</td>
                <td>${sec.avg_sentence_len} words/sent</td>
                <td><span class="source-badge institutional">${escapeHtml(sec.cadence_profile)}</span></td>
            `;
            secBody.appendChild(tr);
        });
        secTableContainer.style.display = 'block';
    }
}

/* ==============================================================================
   STUDENT ACADEMIC WRITING & INTEGRITY COACH
   ============================================================================== */
function renderStudentCoach(data) {
    const coach = data.student_coach || {};
    const claims = coach.unsupported_claims || [];
    const toneSuggestions = coach.tone_suggestions || [];
    const thesis = coach.thesis_evaluation || {};

    // 1. Overall Status Badge
    const overallBadge = document.getElementById('coach-overall-badge');
    const totalIssues = claims.length + toneSuggestions.length;
    if (overallBadge) {
        if (totalIssues === 0 && (thesis.score || 0) >= 70) {
            overallBadge.textContent = '🌟 Stellar Scholarly Writing';
            overallBadge.style.background = 'rgba(16,185,129,0.2)';
            overallBadge.style.color = '#34d399';
        } else {
            overallBadge.textContent = `${claims.length} Citation Check(s) • ${toneSuggestions.length} Tone Boost(s)`;
            overallBadge.style.background = 'rgba(245,158,11,0.2)';
            overallBadge.style.color = '#fbbf24';
        }
    }

    // 2. Unsupported Claims
    const claimsBadge = document.getElementById('coach-claims-count-badge');
    const claimsList = document.getElementById('coach-claims-list');
    if (claimsBadge) claimsBadge.textContent = `${claims.length} Claim${claims.length === 1 ? '' : 's'}`;
    if (claimsList) {
        claimsList.innerHTML = '';
        if (claims.length > 0) {
            claims.forEach((c, idx) => {
                const item = document.createElement('div');
                item.className = 'claim-item';
                item.innerHTML = `
                    <div class="claim-snippet"><strong>#${idx + 1}:</strong> "${escapeHtml(c.sentence)}"</div>
                    <div class="claim-advice">
                        <span>⚠️ Key phrase: <em>"${escapeHtml(c.claim_marker)}"</em></span>
                        <button class="tone-alt-btn" style="background: rgba(245,158,11,0.2); border-color: rgba(245,158,11,0.4); color: #f59e0b;" title="Copy citation placeholder">➕ Copy (Author, Year)</button>
                    </div>
                `;
                const btn = item.querySelector('button');
                if (btn) {
                    btn.addEventListener('click', () => {
                        navigator.clipboard.writeText('(Author, 2024)');
                        btn.textContent = '✓ Copied!';
                        setTimeout(() => { btn.textContent = '➕ Copy (Author, Year)'; }, 1500);
                    });
                }
                claimsList.appendChild(item);
            });
        } else {
            claimsList.innerHTML = '<div style="font-size: 12px; color: var(--text-muted); font-style: italic;">All empirical statements have accompanying citations or no unsupported claims found.</div>';
        }
    }

    // 3. Tone & Vocabulary Booster
    const toneBadge = document.getElementById('coach-tone-count-badge');
    const toneList = document.getElementById('coach-tone-list');
    if (toneBadge) toneBadge.textContent = `${toneSuggestions.length} Suggestion${toneSuggestions.length === 1 ? '' : 's'}`;
    if (toneList) {
        toneList.innerHTML = '';
        if (toneSuggestions.length > 0) {
            toneSuggestions.forEach(t => {
                const item = document.createElement('div');
                item.className = 'tone-item';
                const altsHtml = (t.scholarly_replacements || []).map(alt => 
                    `<button class="tone-alt-btn" title="Click to copy replacement">✨ ${escapeHtml(alt)}</button>`
                ).join(' ');

                item.innerHTML = `
                    <div><span class="tone-orig">${escapeHtml(t.matched_term)}</span> <span style="color: var(--text-secondary); font-size: 11px;">in context: ${escapeHtml(t.context_snippet)}</span></div>
                    <div class="tone-alts">${altsHtml}</div>
                `;
                item.querySelectorAll('.tone-alt-btn').forEach(btn => {
                    btn.addEventListener('click', () => {
                        const word = btn.textContent.replace('✨ ', '').trim();
                        navigator.clipboard.writeText(word);
                        const orig = btn.textContent;
                        btn.textContent = '✓ Copied!';
                        setTimeout(() => { btn.textContent = orig; }, 1500);
                    });
                });
                toneList.appendChild(item);
            });
        } else {
            toneList.innerHTML = '<div style="font-size: 12px; color: var(--text-muted); font-style: italic;">Strong formal scholarly tone detected throughout manuscript.</div>';
        }
    }

    // 4. Thesis & Abstract Strength
    const thesisScoreBadge = document.getElementById('coach-thesis-score-badge');
    const thesisContent = document.getElementById('coach-thesis-content');
    if (thesisScoreBadge) {
        thesisScoreBadge.textContent = `Score: ${thesis.score || 0}/100`;
    }
    if (thesisContent) {
        thesisContent.innerHTML = `
            <div class="thesis-check-item">
                <span class="thesis-check-icon">${thesis.has_hypothesis ? '✅' : '❌'}</span>
                <span><strong>Central Thesis / Hypothesis:</strong> ${thesis.has_hypothesis ? 'Clearly Stated' : 'Missing explicit claim'}</span>
            </div>
            <div class="thesis-check-item">
                <span class="thesis-check-icon">${thesis.has_method ? '✅' : '❌'}</span>
                <span><strong>Methodology / Approach:</strong> ${thesis.has_method ? 'Method context specified' : 'Method context missing'}</span>
            </div>
            <div class="thesis-check-item">
                <span class="thesis-check-icon">${thesis.has_significance ? '✅' : '❌'}</span>
                <span><strong>Scholarly Significance:</strong> ${thesis.has_significance ? 'Implications articulated' : 'Significance unstated'}</span>
            </div>
            <div class="thesis-tip-box">
                💡 <strong>Advisor Advice:</strong> ${(thesis.feedback && thesis.feedback.join(' ')) || 'Good opening formulation.'}
            </div>
        `;
    }
}

/* ==============================================================================
   REFERENCE LIST ALPHABETIZER & FORMATTER
   ============================================================================== */
async function runAlphabetizeReferences(rawRefs) {
    const container = document.getElementById('alphabetize-results-container');
    const outputList = document.getElementById('alphabetized-output-list');
    const countElem = document.getElementById('alphabetized-count');
    if (!container || !outputList) return;

    try {
        const res = await fetch('/api/student-coach/alphabetize-references', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ references: rawRefs })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to alphabetize references');

        outputList.innerHTML = '';
        if (data.sorted_references && data.sorted_references.length > 0) {
            data.sorted_references.forEach((ref, idx) => {
                const entry = document.createElement('div');
                entry.className = 'ref-entry';
                const hasDoi = /10\.\d{4,9}\/|doi\.org|http/i.test(ref);
                const yearMatch = ref.match(/\b(19\d\d|20\d\d)\b/);
                const year = yearMatch ? yearMatch[1] : null;

                entry.innerHTML = `
                    <span class="ref-num">${idx + 1}.</span>
                    <span class="ref-text">${escapeHtml(ref)}</span>
                    <div class="ref-entry-meta">
                        ${year ? `<span class="ref-badge year">📅 Year: ${year}</span>` : '<span class="ref-badge" style="background: rgba(239,68,68,0.2); color: #f87171;">⚠️ No Year</span>'}
                        ${hasDoi ? '<span class="ref-badge doi">🔗 DOI / Link Verified</span>' : '<span class="ref-badge" style="background: rgba(245,158,11,0.2); color: #fbbf24;">ℹ️ No DOI detected</span>'}
                    </div>
                `;
                outputList.appendChild(entry);
            });
            if (countElem) countElem.textContent = data.count;
            container.style.display = 'block';
        } else {
            outputList.innerHTML = '<div style="color: var(--text-muted); font-size: 13px;">No parseable references found.</div>';
            container.style.display = 'block';
        }
    } catch (err) {
        alert('Alphabetizer Error: ' + err.message);
    }
}

/* ==============================================================================
   DRAFT-TO-DRAFT REVISION COMPARATOR
   ============================================================================== */
async function runDraftComparison(draft1, draft2) {
    const compareForm = document.getElementById('compare-drafts-form');
    const submitBtn = compareForm.querySelector('button[type="submit"]');
    const originalHtml = submitBtn.innerHTML;

    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner"></span> Comparing Revision Deltas...';

    try {
        const res = await fetch('/check/compare-drafts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ draft_v1: draft1, draft_v2: draft2 })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to compare drafts');

        document.getElementById('cmp-similarity').textContent = `${data.similarity_percentage}%`;
        document.getElementById('cmp-revision').textContent = `${data.revision_percentage}%`;
        
        const deltaElem = document.getElementById('cmp-words-delta');
        const sign = data.words_delta >= 0 ? '+' : '';
        deltaElem.textContent = `${sign}${data.words_delta}`;
        deltaElem.style.color = data.words_delta >= 0 ? '#34d399' : '#f87171';

        document.getElementById('cmp-modified-count').textContent = data.modified_blocks_count;

        const detailsContainer = document.getElementById('cmp-details-container');
        detailsContainer.innerHTML = '';

        if (data.added_sentences && data.added_sentences.length > 0) {
            const addCard = document.createElement('div');
            addCard.style.cssText = 'background: rgba(16, 185, 129, 0.1); border-left: 3px solid var(--success); padding: 12px; border-radius: 6px; margin-bottom: 12px;';
            addCard.innerHTML = `<strong style="color: #34d399;">✨ Newly Added Passages (${data.added_count}):</strong><ul style="margin: 6px 0 0 20px; font-size: 13px; color: #e2e8f0;">${data.added_sentences.map(s => `<li>${escapeHtml(s)}</li>`).join('')}</ul>`;
            detailsContainer.appendChild(addCard);
        }

        if (data.deleted_sentences && data.deleted_sentences.length > 0) {
            const delCard = document.createElement('div');
            delCard.style.cssText = 'background: rgba(239, 68, 68, 0.1); border-left: 3px solid var(--danger); padding: 12px; border-radius: 6px; margin-bottom: 12px;';
            delCard.innerHTML = `<strong style="color: #f87171;">🗑️ Removed Passages (${data.deleted_count}):</strong><ul style="margin: 6px 0 0 20px; font-size: 13px; color: #fca5a5;">${data.deleted_sentences.map(s => `<li>${escapeHtml(s)}</li>`).join('')}</ul>`;
            detailsContainer.appendChild(delCard);
        }

        const resContainer = document.getElementById('compare-results-container');
        resContainer.style.display = 'block';
        resContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    } catch (err) {
        alert('Draft Comparison Error: ' + err.message);
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalHtml;
    }
}

/* ==============================================================================
   DOI & CITATION GENERATOR
   ============================================================================== */
async function runCitationGeneration(query) {
    const citeForm = document.getElementById('cite-generator-form');
    const submitBtn = citeForm.querySelector('button[type="submit"]');
    const originalHtml = submitBtn.innerHTML;

    submitBtn.disabled = true;
    submitBtn.innerHTML = '<span class="spinner"></span> Fetching Metadata...';

    try {
        const res = await fetch('/api/cite', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Could not resolve citation');

        document.getElementById('cite-res-title').textContent = data.title;
        document.getElementById('cite-res-authors').textContent = `Authors: ${data.authors || 'Unknown'}`;
        document.getElementById('cite-res-meta').textContent = `${data.journal || ''} • Published: ${data.year || '2024'} • ${data.doi_or_url || ''}`;

        document.getElementById('cite-val-bibtex').textContent = data.bibtex || '';
        document.getElementById('cite-val-apa').textContent = data.apa || '';
        document.getElementById('cite-val-mla').textContent = data.mla || '';
        document.getElementById('cite-val-ieee').textContent = data.ieee || '';

        const resContainer = document.getElementById('cite-results-container');
        resContainer.style.display = 'block';
        resContainer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    } catch (err) {
        alert('Citation Error: ' + err.message);
    } finally {
        submitBtn.disabled = false;
        submitBtn.innerHTML = originalHtml;
    }
}

/* ==============================================================================
   1-CLICK AI PARAPHRASER & DIFF MODAL
   ============================================================================== */
function openDiffModal(sentenceObj) {
    currentSentenceObj = sentenceObj;
    const modal = document.getElementById('diff-modal');
    
    document.getElementById('diff-student-text').textContent = sentenceObj.text;
    document.getElementById('diff-source-text').textContent = sentenceObj.matched_source_sentence || 'No direct contiguous sentence extract available.';
    document.getElementById('diff-source-name').textContent = sentenceObj.source || 'Reference Document';
    document.getElementById('diff-modal-meta').textContent = `Match Confidence: ${sentenceObj.similarity}% • Type: ${sentenceObj.badge || '🏛️ Institutional'}`;

    const linkElem = document.getElementById('diff-source-link');
    if (sentenceObj.url) {
        linkElem.href = sentenceObj.url;
        linkElem.style.display = 'inline';
    } else {
        linkElem.style.display = 'none';
    }

    const tipElem = document.getElementById('diff-paraphrase-tip');
    tipElem.textContent = sentenceObj.paraphrase_advice || 'Synthesize the finding in your own words and introduce with an attribution clause.';

    // Hide previous paraphrase suggestions
    const pBox = document.getElementById('paraphrase-suggestions-box');
    if (pBox) pBox.style.display = 'none';

    modal.classList.add('active');
}

async function triggerParaphraseSuggestions() {
    if (!currentSentenceObj) return;

    const btn = document.getElementById('btn-trigger-paraphrase');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span class="spinner"></span> Synthesizing...';

    try {
        const res = await fetch('/api/paraphrase', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                sentence: currentSentenceObj.text,
                source_name: currentSentenceObj.source,
                source_title: currentSentenceObj.smart_citations ? currentSentenceObj.smart_citations.source_title : null
            })
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to generate paraphrase');

        const pBox = document.getElementById('paraphrase-suggestions-box');
        const pList = document.getElementById('paraphrase-items-list');
        pList.innerHTML = '';

        data.suggestions.forEach(sug => {
            const item = document.createElement('div');
            item.className = 'paraphrase-item';
            item.innerHTML = `
                <div>
                    <div class="paraphrase-style">${escapeHtml(sug.style)}</div>
                    <div class="paraphrase-text">"${escapeHtml(sug.text)}"</div>
                </div>
                <button class="btn-apply-phrase" title="Copy suggestion">📋 Copy</button>
            `;

            item.querySelector('.btn-apply-phrase').addEventListener('click', () => {
                navigator.clipboard.writeText(sug.text);
                alert('✓ Paraphrased sentence copied to clipboard!');
            });

            pList.appendChild(item);
        });

        pBox.style.display = 'block';

    } catch (err) {
        alert('Paraphrase Error: ' + err.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

/* ==============================================================================
   MODALS, CERTIFICATES & PIN VERIFICATION
   ============================================================================== */
function setupModalsAndActions() {
    // Diff Modal
    const diffModal = document.getElementById('diff-modal');
    const closeDiffBtn = document.getElementById('close-diff-modal');
    const closeDiffBtn2 = document.getElementById('diff-modal-close-btn');
    if (closeDiffBtn) closeDiffBtn.addEventListener('click', () => diffModal.classList.remove('active'));
    if (closeDiffBtn2) closeDiffBtn2.addEventListener('click', () => diffModal.classList.remove('active'));

    // Paraphrase button in diff modal
    const paraBtn = document.getElementById('btn-trigger-paraphrase');
    if (paraBtn) paraBtn.addEventListener('click', triggerParaphraseSuggestions);

    // Copy Citation buttons in diff modal
    ['apa', 'mla', 'ieee'].forEach(style => {
        const btn = document.getElementById(`btn-copy-${style}`);
        if (btn) {
            btn.addEventListener('click', () => {
                if (!currentSentenceObj || !currentSentenceObj.smart_citations) return;
                const citeText = currentSentenceObj.smart_citations[style];
                if (citeText) {
                    navigator.clipboard.writeText(citeText);
                    const fb = document.getElementById('copy-citation-feedback');
                    if (fb) {
                        fb.style.display = 'block';
                        setTimeout(() => { fb.style.display = 'none'; }, 2500);
                    }
                }
            });
        }
    });

    // Copy buttons in Citation Generator Tab
    document.querySelectorAll('.btn-copy-cite').forEach(btn => {
        btn.addEventListener('click', () => {
            const targetId = btn.getAttribute('data-target');
            const targetElem = document.getElementById(targetId);
            if (targetElem) {
                navigator.clipboard.writeText(targetElem.textContent);
                const orig = btn.textContent;
                btn.textContent = '✓ Copied!';
                setTimeout(() => { btn.textContent = orig; }, 2000);
            }
        });
    });

    // Student Certificate Modal
    const certModal = document.getElementById('cert-modal');
    const openCertBtn = document.getElementById('download-cert-btn');
    const closeCertBtn = document.getElementById('close-cert-modal');
    const cancelCertBtn = document.getElementById('cert-cancel-btn');
    const confirmCertBtn = document.getElementById('cert-confirm-btn');

    if (openCertBtn) openCertBtn.addEventListener('click', () => certModal.classList.add('active'));
    if (closeCertBtn) closeCertBtn.addEventListener('click', () => certModal.classList.remove('active'));
    if (cancelCertBtn) cancelCertBtn.addEventListener('click', () => certModal.classList.remove('active'));
    if (confirmCertBtn) confirmCertBtn.addEventListener('click', generateCertificate);

    // Admin PIN Modal
    const pinModal = document.getElementById('pin-modal');
    const closePinBtn = document.getElementById('close-pin-modal');
    const cancelPinBtn = document.getElementById('pin-cancel-btn');
    const confirmPinBtn = document.getElementById('pin-confirm-btn');
    const pinInput = document.getElementById('admin-pin-input');

    if (closePinBtn) closePinBtn.addEventListener('click', () => pinModal.classList.remove('active'));
    if (cancelPinBtn) cancelPinBtn.addEventListener('click', () => pinModal.classList.remove('active'));
    if (confirmPinBtn) confirmPinBtn.addEventListener('click', confirmDeleteWithPin);
    if (pinInput) {
        pinInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') confirmDeleteWithPin();
        });
    }

    // PDF Report Export
    const pdfBtn = document.getElementById('download-pdf-btn');
    if (pdfBtn) pdfBtn.addEventListener('click', exportPrintableReport);

    // Sources Live Search Filter
    const searchInput = document.getElementById('sources-search-input');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            const q = e.target.value.toLowerCase().trim();
            filterSourcesList(q);
        });
    }
}

/* ==============================================================================
   INSTITUTIONAL CORPUS & PIN DELETION
   ============================================================================== */
async function loadSourcesList() {
    const listContainer = document.getElementById('sources-list-container');
    const navCountElem = document.getElementById('nav-sources-count');
    if (!listContainer) return;

    try {
        const res = await fetch('/sources');
        const data = await res.json();
        allSourcesData = data.sources || [];

        if (navCountElem) navCountElem.textContent = allSourcesData.length;
        renderSourcesList(allSourcesData);

    } catch (err) {
        listContainer.innerHTML = `<div style="color: var(--danger); font-size: 13px;">Error loading sources: ${escapeHtml(err.message)}</div>`;
    }
}

function renderSourcesList(sources) {
    const listContainer = document.getElementById('sources-list-container');
    if (!listContainer) return;
    listContainer.innerHTML = '';

    if (!sources || sources.length === 0) {
        listContainer.innerHTML = '<div style="color: var(--text-muted); font-size: 13px; text-align: center; padding: 24px;">No reference documents found.</div>';
        return;
    }

    sources.forEach(s => {
        const item = document.createElement('div');
        item.className = 'source-item';
        item.innerHTML = `
            <div class="source-details">
                <div class="source-name">
                    <span>🏛️</span>
                    <span>${escapeHtml(s.filename)}</span>
                </div>
                <div class="source-meta">
                    <span class="source-meta-tag">📊 ${s.word_count || 0} words</span>
                    <span class="source-meta-tag">📝 ${s.sentence_count || 0} sentences</span>
                </div>
                <div class="source-preview">
                    "${escapeHtml(s.preview || 'No excerpt available')}"
                </div>
            </div>
            <button class="delete-btn" data-filename="${escapeHtml(s.filename)}" title="Delete from institutional database">
                <span>🗑️ Delete</span>
            </button>
        `;

        item.querySelector('.delete-btn').addEventListener('click', () => {
            openPinModal(s.filename);
        });

        listContainer.appendChild(item);
    });
}

function filterSourcesList(query) {
    if (!query) {
        renderSourcesList(allSourcesData);
        return;
    }
    const filtered = allSourcesData.filter(s => 
        s.filename.toLowerCase().includes(query) || 
        (s.preview && s.preview.toLowerCase().includes(query))
    );
    renderSourcesList(filtered);
}

function openPinModal(filename) {
    targetDeleteFilename = filename;
    const pinModal = document.getElementById('pin-modal');
    const fnElem = document.getElementById('pin-modal-filename');
    const pinInput = document.getElementById('admin-pin-input');
    const fb = document.getElementById('pin-error-feedback');

    if (fnElem) fnElem.textContent = filename;
    if (pinInput) pinInput.value = '';
    if (fb) fb.style.display = 'none';

    if (pinModal) {
        pinModal.classList.add('active');
        setTimeout(() => { if (pinInput) pinInput.focus(); }, 100);
    }
}

async function confirmDeleteWithPin() {
    if (!targetDeleteFilename) return;

    const pinInput = document.getElementById('admin-pin-input');
    const pin = pinInput ? pinInput.value.trim() : '';
    const fb = document.getElementById('pin-error-feedback');
    const pinModal = document.getElementById('pin-modal');

    if (!pin) {
        if (fb) {
            fb.textContent = '⚠️ Please enter the Admin PIN.';
            fb.style.display = 'block';
        }
        return;
    }

    const confirmBtn = document.getElementById('pin-confirm-btn');
    if (confirmBtn) {
        confirmBtn.disabled = true;
        confirmBtn.innerHTML = '<span class="spinner"></span> Verifying...';
    }

    try {
        const res = await fetch(`/sources/${encodeURIComponent(targetDeleteFilename)}`, {
            method: 'DELETE',
            headers: { 'X-Admin-PIN': pin }
        });
        const data = await res.json();

        if (res.ok && data.success) {
            if (pinModal) pinModal.classList.remove('active');
            targetDeleteFilename = null;
            loadSourcesList();
        } else {
            if (fb) {
                fb.textContent = `❌ ${data.error || 'Invalid Admin PIN. Deletion forbidden.'}`;
                fb.style.display = 'block';
            }
            if (pinInput) pinInput.select();
        }
    } catch (err) {
        if (fb) {
            fb.textContent = '❌ Network error during deletion: ' + err.message;
            fb.style.display = 'block';
        }
    } finally {
        if (confirmBtn) {
            confirmBtn.disabled = false;
            confirmBtn.innerHTML = '🗑️ Authorize & Delete';
        }
    }
}

/* ==============================================================================
   REPORTS & CERTIFICATES
   ============================================================================== */
async function generateCertificate() {
    const studentName = document.getElementById('cert-student-name').value.trim();
    const paperTitle = document.getElementById('cert-paper-title').value.trim();

    if (!studentName || !paperTitle) {
        return alert('Please enter both student name and paper title.');
    }

    try {
        const res = await fetch('/reports/certificate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                student_name: studentName,
                paper_title: paperTitle,
                data: currentAnalysisData
            })
        });
        const html = await res.text();
        const win = window.open('', '_blank');
        win.document.write(html);
        win.document.close();
        document.getElementById('cert-modal').classList.remove('active');
    } catch (err) {
        alert('Failed to generate certificate: ' + err.message);
    }
}

async function exportPrintableReport() {
    if (!currentAnalysisData) return;
    try {
        const res = await fetch('/reports/html', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(currentAnalysisData)
        });
        const html = await res.text();
        const win = window.open('', '_blank');
        win.document.write(html);
        win.document.close();
    } catch (err) {
        alert('Failed to generate printable report: ' + err.message);
    }
}

/* ==============================================================================
   BATCH SCANNING & DROPZONE HELPERS
   ============================================================================== */
async function runBatchScan(files) {
    const batchBtn = document.querySelector('#batch-scan-form button[type="submit"]');
    const origText = batchBtn.innerHTML;
    batchBtn.disabled = true;
    batchBtn.innerHTML = '<span class="spinner"></span> Scanning Class Submissions Concurrently...';

    const formData = new FormData();
    for (let i = 0; i < files.length; i++) {
        formData.append('files', files[i]);
    }
    formData.append('include_web', 'false');

    try {
        const res = await fetch('/check/batch', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        if (!res.ok) throw new Error(data.error || 'Failed to process batch submissions');

        renderBatchGradebook(data);

    } catch (err) {
        alert('Batch Error: ' + err.message);
    } finally {
        batchBtn.disabled = false;
        batchBtn.innerHTML = origText;
    }
}

function renderBatchGradebook(data) {
    const container = document.getElementById('batch-results-container');
    const tbody = document.getElementById('batch-gradebook-body');
    if (!container || !tbody) return;

    document.getElementById('batch-stat-total').textContent = data.total_submissions || 0;
    document.getElementById('batch-stat-avg-plag').textContent = `${data.average_plagiarism || 0}%`;
    document.getElementById('batch-stat-avg-ai').textContent = `${data.average_ai_probability || 0}%`;

    let highRiskCount = 0;
    tbody.innerHTML = '';

    (data.gradebook || []).forEach(row => {
        if (row.safeassign_risk === 'High Risk') highRiskCount++;
        const tr = document.createElement('tr');
        const badgeClass = row.safeassign_risk === 'Low Risk' ? 'success' : (row.safeassign_risk === 'Medium Risk' ? 'warning' : 'danger');

        tr.innerHTML = `
            <td><strong>📄 ${escapeHtml(row.student_or_filename)}</strong></td>
            <td>${row.word_count || 0} words</td>
            <td><span style="font-weight: 700; color: ${row.plagiarism_score > 40 ? 'var(--danger)' : 'var(--text-primary)'};">${row.plagiarism_score}%</span></td>
            <td>${row.ai_probability}%</td>
            <td><span class="source-badge ${badgeClass}">${escapeHtml(row.safeassign_risk)}</span></td>
            <td><button class="btn-pdf" style="padding: 3px 8px; font-size: 11px;">🔍 View</button></td>
        `;

        tbody.appendChild(tr);
    });

    document.getElementById('batch-stat-high-risk').textContent = highRiskCount;
    container.style.display = 'block';
    container.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function setupDropzone(zoneId, inputId, previewId, nameId, sizeId, removeId) {
    const zone = document.getElementById(zoneId);
    const input = document.getElementById(inputId);
    const preview = document.getElementById(previewId);
    const nameElem = document.getElementById(nameId);
    const sizeElem = document.getElementById(sizeId);
    const removeBtn = document.getElementById(removeId);

    if (!zone || !input) return;

    zone.addEventListener('click', () => input.click());

    zone.addEventListener('dragover', (e) => {
        e.preventDefault();
        zone.classList.add('dragover');
    });

    ['dragleave', 'dragend'].forEach(type => {
        zone.addEventListener(type, () => zone.classList.remove('dragover'));
    });

    zone.addEventListener('drop', (e) => {
        e.preventDefault();
        zone.classList.remove('dragover');
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            input.files = e.dataTransfer.files;
            handleFileSelect();
        }
    });

    input.addEventListener('change', handleFileSelect);

    function handleFileSelect() {
        if (input.files && input.files.length > 0) {
            const f = input.files[0];
            if (nameElem) nameElem.textContent = input.files.length > 1 ? `${input.files.length} files selected` : f.name;
            if (sizeElem) sizeElem.textContent = input.files.length > 1 ? 'Multiple documents' : formatBytes(f.size);
            if (preview) preview.style.display = 'flex';
        }
    }

    if (removeBtn) {
        removeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            input.value = '';
            if (preview) preview.style.display = 'none';
        });
    }
}

function formatBytes(bytes, decimals = 1) {
    if (!+bytes) return '0 B';
    const k = 1024;
    const dm = decimals < 0 ? 0 : decimals;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${parseFloat((bytes / Math.pow(k, i)).toFixed(dm))} ${sizes[i]}`;
}

function escapeHtml(str) {
    if (!str) return '';
    return str.replace(/[&<>'"]/g, tag => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        "'": '&#39;',
        '"': '&quot;'
    }[tag] || tag));
}
