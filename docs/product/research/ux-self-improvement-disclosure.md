# UX Research: Self-Improving Agent Disclosure Patterns

> **Date:** 2026-04-06
> **Context:** Research for PRODUCT-BEHAVIOR-SPEC-next-architecture.md, Section 4.3

## Summary

When the agent changes its own behavior, what should the user experience? Research across existing products, academic studies, and UX case studies.

## Key Finding

All three disclosure modes (transparent, middle-ground, silent) are correct — for different situations. Gate disclosure level to trust tier and change reversibility.

## How Existing Products Handle It

- **Silent adaptation (low stakes):** Spotify, Netflix, Gmail spam filters. Works because bad recommendations cost 30 seconds.
- **Middle ground (inform after):** Gmail Smart Categories, Google Assistant routines. Google's 2025 settings rewording caused viral backlash (147K reposts) — framing matters.
- **Transparent/opt-in (high stakes):** Apple Intelligence requires per-request consent for external model calls. Notion AI Agents use explicit approval gates.

## What Research Says

- **Transparency paradox:** Disclosing AI involvement can reduce perceived trustworthiness by triggering "algorithm aversion" (2025 study, Journal of Organizational Behavior).
- **Concealment discovered later is worse:** Facebook emotional contagion experiment caused lasting reputational damage.
- **NNGroup (2026):** Trust requires transparency, control, consistency, and support when the system fails. Explainability (why) matters more than transparency (what).
- **GitLab (2025):** Trust builds through "micro-inflection points." Users frustrated by tools that couldn't remember preferences.

## Recommendation

1. **Default to middle ground.** "I adjusted X. Here's why. Undo?"
2. **Full transparency only for:** actions on user's behalf, first time a new category of change occurs.
3. **Silent adaptation for:** internal model improvements, low-stakes reversible changes, Act-tier domains.
4. **Changelog view:** pullable, not pushed. Available on demand.
5. **Graduate disclosure downward as trust increases,** never fully silent for action-taking domains.
6. **Anti-pattern:** Don't make this a settings page.

## Sources

- [Psychology of Trust in AI (Smashing Magazine, 2025)](https://www.smashingmagazine.com/2025/09/psychology-trust-ai-guide-measuring-designing-user-confidence/)
- [Transparency Dilemma (ScienceDirect, 2025)](https://www.sciencedirect.com/science/article/pii/S0749597825000172)
- [Levels of Autonomy for AI Agents (arXiv, 2025)](https://arxiv.org/html/2506.12469v1)
- [Building Trust in Agentic Tools (GitLab, 2025)](https://about.gitlab.com/blog/building-trust-in-agentic-tools-what-we-learned-from-our-users/)
- [State of UX 2026 (NNGroup)](https://www.nngroup.com/articles/state-of-ux-2026/)
