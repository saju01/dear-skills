# dear-skills

Personal skills for personal automation. Each one ships as a recipe, gets customised for you at first install, and keeps its own memory in your storage.

## dear-inbox-zero

**A personal inbox-zero skill that learns from what you do.**

Mail, meeting invites and Teams messages, all in one place. It sorts what needs you from what doesn't, drafts replies in your voice, and earns more autonomy only as it proves accurate.

- **Learns from you, not from a template.** At first install it studies your Sent box (whom you answer and how fast, your language per contact, your working hours and how you write) and how you handle invites and chats, then asks about the cases it isn't sure of, one at a time.
- **Gets better with use.** Every tag you change, reply you send or draft you bin is a signal. Repeated signals become proposed rules; you confirm them once.
- **Never acts behind your back.** It never sends, forwards, deletes or declines. Replies are drafts.
- **Token-efficient.** Rules decide first; the model only sees what rules can't decide.
- **Your memory stays yours.** The store lives in your OneDrive or a local folder. Nothing about you is in this repo.

Works with Microsoft Outlook, Outlook Calendar and Microsoft Teams. One core runs in any [Agent Skills](https://github.com/agentskills/agentskills)–compatible agent; a small adapter per agent maps its tools (see [DESIGN.md §11](DESIGN.md#11-portability-one-core-thin-host-adapters)). Adding your agent is one file. See the [GitHub Copilot and Graph setup guide](docs/hosts/github-copilot.md).

> Status: **v0.1.0**: mail, calendar and Teams. See [DESIGN.md](DESIGN.md), an [example report](examples/persona-alex/report.md) and the [changelog](skills/dear-inbox-zero/CHANGELOG.md).

### Install with your agent

Ask your agent:

> Install dear-inbox-zero from https://github.com/saju01/dear-skills

Agents read [AGENTS.md](AGENTS.md) and follow [INSTALL.md](INSTALL.md), using the [install.json](install.json) manifest. The manifest lists every file with its sha256, the skills folder for each agent and the adapter to use. The agent copies and verifies the files, picks the adapter, runs a health check, then hands over to `dear-inbox-zero setup`, which asks your consent before reading anything.

### Manual install

```text
1. Copy skills/dear-inbox-zero into your agent's skills folder
   (e.g. .github/skills/ for GitHub Copilot, Documents/Cowork/skills for Cowork)
   and pick the adapter for your agent in skills/dear-inbox-zero/hosts/.
2. Run:  dear-inbox-zero setup
3. Review the dry-run report, then run:  dear-inbox-zero
```

### Commands

| Command | What it does |
|---|---|
| `dear-inbox-zero setup` | first install: consent, memory in your OneDrive, behaviour study, voice study, calibration, dry run |
| `dear-inbox-zero` | the daily run |
| `dear-inbox-zero learn` | weekly review of proposals and accuracy |
| `dear-inbox-zero show <bucket>` | what is in a bucket and why |
| `dear-inbox-zero doctor` | checks the store, the host mapping and the token budget |

### Safety

| Never | Always |
|---|---|
| send, forward, post | drafts in Outlook; suggested replies for Teams messages that need you |
| delete or move | tags and read state; your own rules stay in charge |
| decline invites | learns with you and asks; accepts only under rules you confirmed |
| open personal mail | counts it |

---

Independent project, not affiliated with or endorsed by Microsoft or Inbox Zero (getinboxzero.com). Microsoft, Outlook, Teams and Microsoft 365 are trademarks of the Microsoft group of companies.

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). The one hard rule: no personal data, ever.

License: [Apache-2.0](LICENSE)
