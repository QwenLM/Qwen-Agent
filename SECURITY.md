# Security Policy

The Qwen-Agent team takes security issues seriously and appreciates the effort of researchers and users who report vulnerabilities responsibly.

## Reporting a Vulnerability

**Please do not open a public GitHub issue for security vulnerabilities.**

Instead, use one of the following private channels so we can validate and fix the issue before it becomes public:

1. **GitHub Security Advisories (preferred).** Open a private report from the [Security tab](https://github.com/QwenLM/Qwen-Agent/security/advisories/new). Only Qwen-Agent maintainers see the report until the advisory is published.
2. **Email.** If GitHub Security Advisories are not usable for you, contact the Qwen team through the address listed on the [Qwen organization page](https://github.com/QwenLM) or via the community channels linked from the project README (WeChat, Discord).

When reporting, please include as much of the following as you can:

- A clear description of the issue and the affected component (agent, tool, integration, etc.).
- The version, commit SHA, or release tag where you observed the behavior.
- Reproduction steps or a minimal proof-of-concept.
- The impact you believe the issue has (data exposure, code execution, denial of service, etc.).
- Any suggested remediation, if you have one.

## What to Expect

- **Acknowledgement:** we aim to acknowledge new reports within a few business days.
- **Triage:** we will work with you to reproduce the issue and confirm its impact.
- **Fix and disclosure:** for confirmed vulnerabilities we will prepare a fix, coordinate a release, and publish a security advisory. We are happy to credit reporters in the advisory unless they prefer to remain anonymous.
- **Please give us reasonable time** to investigate and remediate before any public disclosure.

## Scope

This policy covers the code in the `QwenLM/Qwen-Agent` repository. Vulnerabilities in third-party dependencies should generally be reported to the corresponding upstream project; if the exposure is specific to how Qwen-Agent uses that dependency, we still want to hear about it.

Out of scope (unless combined with a concrete impact against Qwen-Agent):

- Reports generated purely from automated scanners without an exploitation path.
- Findings limited to example code, documentation snippets, or benchmarks intended for local experimentation.
- Missing security headers on documentation sites, or informational best-practice suggestions.

Thank you for helping keep Qwen-Agent and its users safe.
