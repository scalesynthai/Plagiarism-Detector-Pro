# Plagiarism Detector Pro v1.0.5

Version 1.0.5 lets the npm CLI, library, and MCP server read Word and PDF files directly.

## New local formats

- `plag scan essay.docx` now works. Body paragraphs and table text are extracted; tracked-change deletions and field codes are ignored. Headers, footers, and footnotes are not extracted.
- `plag scan paper.pdf` now works for text-based PDFs, including compressed streams, object streams, CID fonts with ToUnicode maps, and kerned text.
- Scanned (image-only) and encrypted PDFs are rejected with a clear error instead of being scanned as empty text. Run OCR on scanned files first.
- No new dependencies. Both readers are built in and enforce the existing 8 MB file limit plus decompression limits.

## Verification

- Added regression tests for DOCX, simple-font PDF, CID-font PDF, object streams, and encrypted PDFs.
- Checked against PDFs produced by macOS Quartz and Chrome, and fuzzed with corrupted files to confirm clean failures.

**Full Changelog**: https://github.com/scalesynthai/Plagiarism-Detector-Pro/compare/v1.0.4...v1.0.5
