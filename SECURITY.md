# Security Policy

## Supported Versions

We actively provide security updates and patches for the following versions of **Plagiarism Detector Pro**:

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |
| < 1.0   | :x:                |

---

## 🛡️ Reporting a Vulnerability

The Plagiarism Detector Pro team takes security seriously. If you discover a security vulnerability, please give us the opportunity to fix it before disclosing it publicly.

### How to Report

1. **Email Us Privately**: Please send vulnerability details to **`security@subba.dev`** or **`maintainers@subba.dev`**.
2. **Include Details**:
   - Type of vulnerability (e.g., SSRF, Remote Code Execution, Path Traversal, DoS).
   - Step-by-step reproduction instructions or a minimal Proof of Concept (PoC).
   - Impact assessment (what an attacker could achieve).
   - Potential mitigation or patch if you have one.
3. **GitHub Private Security Advisory**: Alternatively, if enabled, you may submit a report through the **[GitHub Security Advisory](https://github.com/ScaleSynthAI/Plagiarism-Detector-Pro/security/advisories/new)** tab.

---

## ⏱️ Response Timeline

- **Initial Response**: Within 24-48 hours acknowledging receipt of your report.
- **Triage & Validation**: Within 3-5 business days confirming severity and scope.
- **Remediation & Patch**: Security fixes are prioritized and released in a patch version promptly.
- **Public Disclosure**: Coordinated disclosure after a patch has been released and deployed.

---

## 🔒 Security Best Practices in Plagiarism Detector Pro

Our codebase enforces several foundational security controls:

1. **File Upload Hardening**:
   - Strict file extension validation (`.txt`, `.docx`, `.pdf`, `.md`, `.zip`).
   - Filename sanitization via `werkzeug.utils.secure_filename`.
   - File size limits (enforced via Flask `MAX_CONTENT_LENGTH = 16 * 1024 * 1024` for 16 MB max payload).

2. **Server-Side Request Forgery (SSRF) Prevention**:
   - Academic search integrations (Wikipedia, arXiv, CrossRef, OpenAlex) use static, validated HTTPS API base endpoints.
   - User inputs are parameterized and URL-encoded.

3. **Denial of Service (DoS) Protections**:
   - RegEx pattern limits to prevent ReDoS (Regular Expression Denial of Service).
   - Memory buffer streaming for batch ZIP archives to avoid disk exhaustion.

---

## 🏆 Bug Bounty & Recognition

While we do not operate a commercial bug bounty program, we are happy to publicly acknowledge researchers and contributors in our release notes and Hall of Fame for responsibly disclosed vulnerabilities.
