# Changelog

## Unreleased

- **Lite mode**: mail only, no Python. The agent applies the bucket and safety rules from `lite/run.md` and keeps memory in one small `lite.json` (OneDrive, or the agent's own memory). Graph scopes: `User.Read` and `Mail.ReadWrite`, plus `Files.ReadWrite` only for OneDrive memory. Lite setup is shorter: consent, a metadata-only study, calibration, voice check, dry run.
- `SKILL.md` picks lite or pro from what the host can do (Python 3.10+ and the engine → pro); `config/host.json` `mode` (`auto` / `lite` / `pro`) overrides.
- `doctor` checks the lite guides, their token budget and the `mode` setting, and accepts lite-only adapters marked `<!-- adapter-mode: lite -->`.
- `install.json` describes both modes under `modes`.

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
