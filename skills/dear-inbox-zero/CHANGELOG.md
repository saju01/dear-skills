# Changelog

## Unreleased

- **Invite accepts are opt-in, off by default at every preset.** Accepting sends the organiser a response, so it now needs its own switch (`automation --invite-accept on`, or the unticked box in setup) on top of a confirmed rule and calendar level 3. Without it the report asks about every invite and says when a rule would have accepted. Existing installs, High included, stop accepting until the user switches it on.
- The description, `SKILL.md` hard rules and `policy/safety.md` now say exactly what can reach other people: an invite accept, only when switched on. Tags, flags, read state, drafts and memory stay with the user.

## 0.1.0 — first public build

- Mail, calendar and Teams in one skill; recipe-only package, memory in the user's OneDrive.
- First install: consent, Sent-box study (whom you answer and how fast, VIPs, language per contact, working hours, own domain, voice), behaviour study, one-question calibration, dry run.
- Daily Sent-box signals: replies close open loops and teach Reply rules; sent drafts are compared with the run's draft; the voice follows how you actually write.
- Engine (Python 3.10+, standard library only): content-addressed store, rule precedence, invite clash check, learning loop with expiring proposals, per-bucket autonomy, open-loop ledger, report, doctor.
- Adapters: Microsoft 365 Copilot Cowork, Microsoft Graph (any agent with Graph access), template for new agents.
- Agent-led install: `AGENTS.md`, `INSTALL.md`, `install.json` with sha256 per file.
- Automation presets Low / **Auto · Medium (default)** / High; recommended daily run + weekly learn scheduled at go-live (`automation`).
- Microsoft Graph collectors (`collect-mail`, `collect-sent`, `collect-calendar`, `collect-teams`) and Teams needs-response filter and signals (`teams-filter`, `teams-signals`), built by Copilot coding agent (#1, #2).
- GitHub Copilot + Graph setup guide (#4).
- 62 tests on synthetic data; CI with privacy scan and manifest check.
