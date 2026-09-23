# Reliability review — 2026-09-23

## Fixed and covered by regression checks

- API objects, text fields, booleans, and report structures are validated; malformed requests return JSON client errors.
- HTML report/certificate values are escaped and report links permit only HTTP(S). Certificate language no longer claims heuristic scores verify human authorship.
- Corpus changes require a configured admin secret in a header; there is no default production PIN. Uploads validate content before publishing, reject overwrites and path traversal, and publish atomically. Workers refresh snapshots when files change; deleted vector entries are cleared.
- ZIP batches allow at most 100 entries, 8 MB per expanded document, and 32 MB total expanded content. Encrypted entries are rejected. DOCX packages have expanded-size and entry-count checks. Extraction caps file size at 8 MB; Python text analysis caps input at 100,000 characters and 500 words per passage.
- Unexpected scan errors no longer expose internal exception messages. API responses are not cached. Debug mode is off by default.
- Node API calls and citation lookups have deadlines. Unsupported local binary files fail explicitly instead of being scanned as UTF-8. Literal prose ending in a filename extension is not automatically treated as a path.
- MCP rejects malformed requests, returns JSON-RPC error envelopes, ignores notifications, supports ping, and validates tool arguments.
- Batch UI uses Python response fields, shows extraction failures, and opens individual results. Node batch averages exclude failed documents.
- Failed citation lookups use unknown metadata and an explicit warning instead of invented author/year/publication values.
- Removed the npm self-dependency and regenerated its lockfile. CI covers Python and Node. Deployment requires successful push CI and treats failed webhooks as failures.
- Python tests use temporary corpus copies rather than modifying project sources.

## Remaining production work and limitations

This is a hardening pass, not a claim of failure-proof operation or a completed independent security assessment.

1. **Detection validity:** there is no labeled evaluation dataset establishing accuracy, false-positive rates, or calibration of AI probabilities. Python and Node implementations differ. Similarity does not establish plagiarism; low scores do not establish authorship. Placeholder citations generated from corpus filenames still need bibliographic verification. Certificate input is client supplied and unsigned.
2. **Internet and privacy:** web providers may fail or return incomplete coverage; there is no completeness guarantee or access to proprietary university repositories. Private draft mode prevents no external requests by itself. Use `include_web=false` for local-only processing. Offline/outage tests do not establish current provider availability.
3. **Abuse and resource isolation:** bounded inputs reduce risk but do not replace request rate limits, authenticated scan quotas, bounded job queues, or isolated PDF/DOCX workers with CPU/memory deadlines. Similarity matching is expensive for large corpora. Add these before exposing the service to untrusted high-volume traffic.
4. **Access and operations:** the shared admin secret is not multi-user authentication, authorization, or an audit log. Source listing exposes corpus previews. Define access policy, TLS termination, backups, recovery tests, monitoring, and retention for the intended deployment.
5. **Releases:** Python dependencies use open lower bounds; there is no fully locked Python environment. Python wheel packaging and installed template/static discovery still need dedicated packaging tests. The webhook targets a branch, not an immutable tested SHA; configure the deployment system to deploy the tested revision.
6. **Validation scope:** local Python/Node regression suites and syntax checks ran. Docker deployment, browser interaction, live provider behavior, concurrency load, and the remote CI version matrix have not been exercised here. ZIP/PDF fuzzing and a representative accuracy benchmark remain separate work.

## Configuration changes

Set a strong `ADMIN_PIN` and stable random `SECRET_KEY` in the deployment environment. Compose requires both. The web UI asks for the admin secret before uploads. API clients must send `X-Admin-PIN` for uploads and deletions; query-string PINs are no longer accepted. Existing source names are not overwritten. Oversized or unusually long passages return explicit errors rather than being silently truncated.

## Local checks

```sh
python -m unittest discover tests -v
npm test
node --check static/js/app.js
git diff --check
```
