# dear-skills

Personal skills for personal automation. Each one ships as a recipe, gets customised for you at first install, and keeps its own memory in your storage.

## dear-inbox-zero

**A personal inbox-zero skill that learns from what you do.**

Mail, meeting invites and Teams messages, all in one place. It sorts what needs you from what doesn't, drafts replies in your voice, and earns more autonomy only as it proves accurate.

- **Learns from you, not from a template.** At first install it studies your Sent box (whom you answer and how fast, your language per contact, your working hours and how you write) and how you handle invites and chats, then asks about the cases it isn't sure of, one at a time.
- **Gets better with use.** Every tag you change, reply you send or draft you bin is a signal. Repeated signals become proposed rules; you confirm them once.
- **Never acts behind your back.** It never sends mail, forwards, deletes or declines. Replies are drafts. The one thing that can reach someone else is accepting a meeting invite, and that's off unless you switch it on.
- **Token-efficient.** Rules decide first; the model only sees what rules can't decide.
- **Your memory stays yours.** The store lives in your OneDrive or a local folder. Nothing about you is in this repo.

Works with Microsoft Outlook, Outlook Calendar and Microsoft Teams. One core runs in any [Agent Skills](https://github.com/agentskills/agentskills)–compatible agent; a small adapter per agent maps its tools (see [DESIGN.md §11](DESIGN.md#11-portability-one-core-thin-host-adapters)). Adding your agent is one file. See the [GitHub Copilot and Graph setup guide](docs/hosts/github-copilot.md).

> Status: **v0.1.0**: mail, calendar and Teams. See [DESIGN.md](DESIGN.md), an [example report](examples/persona-alex/report.md) and the [changelog](skills/dear-inbox-zero/CHANGELOG.md).

## Install: let your agent do it

You don't install anything by hand. Your agent does the installation, then starts customising itself to you.

### Copilot Cowork

1. **Download** [dear-inbox-zero-v0.1.0.zip](https://github.com/saju01/dear-skills/raw/v0.1.0/dist/dear-inbox-zero-v0.1.0.zip) (the [v0.1.0 release](https://github.com/saju01/dear-skills/releases/tag/v0.1.0)).
2. **Upload** it to a new Cowork task.
3. **Say:** `Install this skill and set it up.`

### Any other agent (GitHub Copilot and other Agent Skills–compatible agents)

Say:

> Install dear-inbox-zero from https://github.com/saju01/dear-skills and set it up.

The agent reads [AGENTS.md](AGENTS.md) and [INSTALL.md](INSTALL.md), copies every file listed in [install.json](install.json), checks each file's sha256, picks the adapter for itself, and runs a health check. For GitHub Copilot with Microsoft Graph, see the [setup guide](docs/hosts/github-copilot.md).

## What happens at first install

Setup starts as soon as the install finishes. You answer a few questions; the skill does the rest.

| Step | What you see | What it does |
|---|---|---|
| 1. Consent | One prompt | Shows what it will read, that your memory lives in your own OneDrive, and that it never sends mail or messages. You pick channels and the automation level (**Auto · Medium** is preselected). Accepting invites for you is a separate box, unticked. |
| 2. Learns from your Sent box | Nothing to do | Whom you answer and how fast, your language per contact, your working hours, your own domain and how you write. |
| 3. Learns your habits | Nothing to do | What you read, ignore or flag, which invites you accept, which Teams chats you answer. |
| 4. Customises itself | A few questions, one at a time | Confirms VIPs, your writing style and the senders it isn't sure about. |
| 5. Dry run | A report | Shows what it would tag, flag, draft and recommend, without changing anything. |
| 6. Goes live | "Go live on Auto · Medium?" | Sets the automation level and schedules the recommended daily automation. |

## The default: Auto · Medium, every weekday

At go-live the skill builds a recommended daily automation for you:

- **Daily run** every weekday at the start of your working day (learned from your Sent box; 08:30 if unknown).
- **Weekly learn** on Monday: accuracy per bucket, rules learned, proposals to confirm.

On **Auto · Medium** each daily run:

| Bucket | What it does on its own |
|---|---|
| Noise | tags it and marks it read (only under rules you confirmed) |
| FYI | tags it, gives you one digest line, marks it read |
| Reply | tags it, flags it for To Do, writes a draft in your voice |
| Invites | recommends and asks. Only if you switch invite accepts on: once you've confirmed a rule and it has proven accurate, it accepts those for you, and the organiser gets your acceptance |
| Teams | lists messages that need your answer, with a suggested reply |
| Personal | counts it, never opens it |

Prefer less or more? **Low** only tags and drafts. **High** starts calendar at the top level, so if you switch invite accepts on, confirmed rules apply from day one. Change it any time: `dear-inbox-zero automation --preset low|medium|high`; invite accepts: `--invite-accept on|off` (off by default at every level).

It keeps learning every day: each reply you send, tag you change and draft you rewrite is a signal. A wrong action drops that bucket a level and pauses the rule.

### Manual install (only if your agent can't fetch files)

Copy `skills/dear-inbox-zero` into your agent's skills folder (`.github/skills/` for GitHub Copilot, `Documents/Cowork/skills` for Cowork), set `config/host.json` to your agent's adapter in `hosts/`, then say `dear-inbox-zero setup`.

### Commands

| Command | What it does |
|---|---|
| `dear-inbox-zero setup` | first install: consent, memory in your OneDrive, behaviour study, voice study, calibration, dry run |
| `dear-inbox-zero` | the daily run |
| `dear-inbox-zero learn` | weekly review of proposals and accuracy |
| `dear-inbox-zero show <bucket>` | what is in a bucket and why |
| `dear-inbox-zero automation` | shows or changes the automation level and the daily schedule |
| `dear-inbox-zero doctor` | checks the store, the host mapping and the token budget |

### Safety

| Never | Always |
|---|---|
| send, forward, post | drafts in Outlook; suggested replies for Teams messages that need you |
| delete or move | tags and read state; your own rules stay in charge |
| decline invites | learns with you and asks; accepts only if you switched that on and under rules you confirmed (the organiser then gets your acceptance) |
| open personal mail | counts it |

---

Independent project, not affiliated with or endorsed by Microsoft, by Inbox Zero (getinboxzero.com) or by any holder of an "Inbox Zero" mark. "Inbox zero" is used here in its common descriptive sense. Microsoft, Outlook, Teams and Microsoft 365 are trademarks of the Microsoft group of companies. The names "dear-skills" and "dear-inbox-zero" are covered by [TRADEMARKS.md](TRADEMARKS.md).

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md). The one hard rule: no personal data, ever.

License: [Apache-2.0](LICENSE)
