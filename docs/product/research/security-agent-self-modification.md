# Security Research: Agent Self-Modification Safety

> **Date:** 2026-04-06
> **Context:** Research for PRODUCT-BEHAVIOR-SPEC-next-architecture.md, Sections 4.2 and 8

## Threat Model

Ranked by severity x likelihood for a personal agent that can edit its own config.

### CRITICAL
- **T1: Indirect Prompt Injection via External Data** — attacker embeds instructions in email/calendar/web results. Google Gemini exploited via calendar invites (GeminiJack), Microsoft 365 Copilot data leak (CVE-2025-32711).
- **T2: Config Modification to Remove Restrictions** — agent reasons that removing a permission gate helps complete its task. Claude Code CVE-2025-59536.

### HIGH
- **T3: Memory Poisoning** — malicious content stored in agent memory, persists across sessions.
- **T4: Sub-Agent Privilege Escalation** — agent creates helper with broader permissions.

### MEDIUM
- **T5: Runaway Self-Modification Loop** — bad edit causes worse judgment causes more bad edits.

## Architectural Patterns

1. **Immutable Base + Mutable Overlay** — security boundaries in files agent can't write to.
2. **Out-of-Process Policy Enforcement** — in-process guardrails fail because agent IS the process.
3. **Config Diff + Approval Gate** — every modification produces a diff, threshold triggers approval.
4. **Input Sanitization Boundary** — external data tagged as untrusted at ingestion.
5. **Audit Log + Rollback** — every change logged immutably, enables post-hoc detection.
6. **Capability Attenuation** — sub-agents can only receive subset of parent's permissions.

## Minimum Viable Safety Model

1. Immutable security boundary (agent can't write allowlists/tiers)
2. Tap-to-approve for non-security changes (MVP simplification)
3. Tainted data tagging (external content can't be sole basis for config change)
4. Audit log with auto-rollback on degraded metrics

## Red Button

Allow unattended self-modification outside the security boundary. Risk is low with audit + rollback. Full autonomy including security tier is genuinely dangerous — scary warning, user's risk.

## Sources

- [CVE-2025-59536: Claude Code Project File RCE (Check Point)](https://research.checkpoint.com/2026/rce-and-api-token-exfiltration-through-claude-code-project-files-cve-2025-59536/)
- [Privilege Escalation Kill Chain (Arun Baby)](https://www.arunbaby.com/ai-security/0001-agent-privilege-escalation-kill-chain/)
- [OWASP Top 10 for Agentic Applications 2026](https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/)
- [OWASP AI Agent Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/AI_Agent_Security_Cheat_Sheet.html)
- [Microsoft Agent Governance Toolkit](https://opensource.microsoft.com/blog/2026/04/02/introducing-the-agent-governance-toolkit-open-source-runtime-security-for-ai-agents/)
- [AWS Four Security Principles for Agentic AI](https://aws.amazon.com/blogs/security/four-security-principles-for-agentic-ai-systems/)
