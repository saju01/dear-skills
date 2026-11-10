# Changelog

## 0.1.0 — first public build

- Mail, calendar and Teams in one skill; recipe-only package, memory in the user's OneDrive.
- First install: consent, Sent-box study (whom you answer and how fast, VIPs, language per contact, working hours, own domain, voice), behaviour study, one-question calibration, dry run.
- Daily Sent-box signals: replies close open loops and teach Reply rules; sent drafts are compared with the run's draft; the voice follows how you actually write.
- Engine (Python 3.10+, standard library only): content-addressed store, rule precedence, invite clash check, learning loop with expiring proposals, per-bucket autonomy, open-loop ledger, report, doctor.
- Adapters: Microsoft 365 Copilot Cowork, Microsoft Graph (any agent with Graph access), template for new agents.
- Agent-led install: `AGENTS.md`, `INSTALL.md`, `install.json` with sha256 per file.
- 33 tests on synthetic data; CI with privacy scan and manifest check.
