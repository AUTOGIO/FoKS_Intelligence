# Security Policy for FoKS Intelligence (AUTOGIO)

FoKS Intelligence is designed to run entirely on your local machine with a strong focus on privacy and security. This document explains how to report vulnerabilities and what you can expect in return.

---

## Supported Versions

This is an early‑stage project; only the `main` branch is considered supported.

If you are running a fork or a heavily modified version, please first try to reproduce the issue on a clean checkout of `main`.

---

## Reporting a Vulnerability

If you discover a security issue, **please do not open a public GitHub issue** with details.

Instead:

1. Prepare a short report including:
   - A clear description of the issue.
   - Steps to reproduce (if possible).
   - Impact (what an attacker could do).
   - Any logs or stack traces (with secrets removed).
2. Use one of these channels (in order of preference):
   - GitHub: open a **private security advisory** for the `AUTOGIO` repository.
   - Or, if security advisories are not available, open a minimal public issue marked “Security” that only states you have found a vulnerability; a maintainer will contact you to coordinate a private channel.

Please **do not**:

- Publish exploit details or PoCs before we have had reasonable time to investigate.
- Share secrets, access tokens, or personal data in any report.

---

## What We Consider “In Scope”

Examples of issues we treat as security vulnerabilities:

- Remote code execution via API endpoints.
- Escalation of privileges within the local system beyond expected behavior.
- Bypassing authentication/rate‑limiting when they are configured.
- Exposure of sensitive local files (e.g. arbitrary file reads outside the project path).
- Injection issues in places where user input is supposed to be trusted only locally.

What is usually **out of scope**:

- Misconfiguration of local machine (weak OS passwords, world‑writable dirs, etc.).
- Use of the project in environments explicitly not recommended (e.g. exposing it to the public internet without a reverse proxy, TLS, or auth).
- Issues inside external tools (LM Studio, FBP backend, n8n, Node‑RED) that are not caused by this project.

---

## Handling & Disclosure Process

After we receive a security report:

1. **Acknowledgement** – We will confirm reception as soon as possible.
2. **Assessment** – We will triage the issue, attempt to reproduce it, and assess impact.
3. **Fix** – We will work on a fix and prepare tests/documentation as needed.
4. **Release** – We will publish a patched version on `main`, update `CHANGELOG.md`, and (optionally) credit the reporter if they agree.

We aim for responsible disclosure and will coordinate with you if public disclosure is appropriate.

---

## Secure Usage Recommendations

Even with no known vulnerabilities, please:

- Bind APIs only to `127.0.0.1` unless you know what you are doing.
- Use API keys / auth in production environments.
- Avoid exposing FoKS endpoints directly to the internet without:
  - TLS termination,
  - Authentication,
  - Proper reverse proxy configuration.
- Keep dependencies up‑to‑date (`pip install -r requirements.txt --upgrade` under a controlled process).

If you are unsure whether something is a security concern, **err on the side of reporting**. It is always better to review a non‑issue than to miss a real vulnerability.


