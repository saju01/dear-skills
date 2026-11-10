# dear-inbox-zero — Design (v0.1 draft for review)

> A personal-automation skill that takes the mental load out of everything that asks for your attention: mail, meeting invites and Teams messages. It ships as a recipe with no personal data. The first install customises it for one person. It keeps that person's memory in their own storage and gets better from what they actually do.

Status: v0.1.0 built (decisions of 10 Nov 2026 applied) · Repo: `dear-skills` · Skill: `dear-inbox-zero` · License: Apache-2.0

---

## 1. Principles

| # | Principle | What it means in practice |
|---|---|---|
| P1 | **The package is a recipe** | No names, addresses, customers, senders or sample mail from a real person ship in the repo. CI fails the build if any are found. |
| P2 | **Memory belongs to the user** | Everything learned lives in a store the user owns (OneDrive or a local folder), created at first install. The skill never writes memory into its own folder. |
| P3 | **Learn only from the user's own actions** | Tags changed, replies sent, flags set or cleared, invites answered, drafts binned or edited. Never from other people's behaviour or another assistant. |
| P4 | **Nothing leaves without the user** | Never send, never forward, never delete. Replies are drafts. Teams replies are suggested text. Calendar accepts, the only action that reaches another person (the organiser gets the response), happen only when the user switched them on (off by default at every preset) and under a rule they confirmed. |
| P5 | **Trust is earned per bucket** | Each bucket has an autonomy level that rises after a run of accurate days and drops after a mistake. |
| P6 | **Token-efficient by design** | Deterministic rules decide first. The model only sees what the rules can't decide, and reads metadata before bodies. |
| P7 | **Agent-agnostic** | Agent Skills format (a folder with `SKILL.md`), plain Markdown + Python, no host-specific syntax in the core. A thin host adapter translates abstract operations into each agent's tools (see §11). |
| P8 | **Ask one question at a time** | Calibration and confirmations ask one item at a time, with clear options, never as a bulk table. |

## 2. Non-goals (v0.x)

- Sending mail or posting messages on the user's behalf.
- Deleting or moving content (it tags and marks read; the user's own rules still apply).
- Mailboxes other than Microsoft 365 / Outlook (Gmail is a possible later channel adapter).
- Team or shared-mailbox triage. One person, one store.

## 3. Architecture

```
            ┌──────────────────────────── dear-inbox-zero (recipe, public) ───────────────────────────┐
 user ──►   │ SKILL.md (router, ≤ 6 KB)  →  run · setup · learn · show · doctor                        │
            │                                                                                         │
            │  channels/        policy/            engine/ (Python, deterministic)    hosts/          │
            │   mail.md          defaults.md        classify · ledger · learn          cowork.md       │
            │   calendar.md      safety.md          autonomy · report · store          graph.md        │
            │   teams.md         voice.md                                              (copilot, …)   │
            └───────────────┬─────────────────────────────────────────────────────────────────────────┘
                            │ abstract operations (mail.list, cal.respond, teams.mentions, store.write …)
                            ▼
            host tools (Cowork tools · Microsoft Graph via MCP · …)       user's private store (memory)
```

### 3.1 Repo layout

```
dear-skills/
├── README.md
├── LICENSE                         MIT
├── SECURITY.md · CONTRIBUTING.md
├── skills/
│   └── dear-inbox-zero/
│       ├── SKILL.md                router: commands, step order, which file to load when
│       ├── channels/               mail.md · calendar.md · teams.md (loaded only if enabled)
│       ├── policy/                 defaults.md · safety.md · voice.md · invites.md
│       ├── setup/                  first-install.md · behaviour-study.md · calibration.md
│       ├── learn/                  learning-loop.md · weekly-review.md
│       ├── hosts/                  cowork.md · graph.md   (abstract op → host tool)
│       ├── engine/                 Python package source (no compiled bundle)
│       ├── schemas/                store + head + fact JSON schemas
│       └── tests/                  unit tests on synthetic fixtures only
├── examples/persona-alex/          a fictional user's store, to show what a tuned memory looks like
└── .github/workflows/              tests · personal-data scan · skill lint
```

## 4. Memory model (the user's private store)

Location: the user's own **OneDrive**, default `OneDrive/dear-inbox-zero/<account_key>/` (confirmed at install, changeable). A local folder is a fallback only for hosts without OneDrive access. Never inside the skill, never in the repo.

```
<account_key>/
  head/memory-<sha256>.json   always loaded, bounded (target ≤ 16 KB), parent-linked history
  store/<fact_id>.json        append-only facts, one per file, never rewritten
  store/sup-<fact_id>.json    supersession record (old → new)
  index.json                  live facts only, rebuilt at publish, read on demand
```

| Head key | Purpose |
|---|---|
| `profile` | timezone, working hours, languages, VIPs, key domains, personal senders (pins) |
| `autonomy` | per bucket: level 0–3, recent runs (decisions, overrides, wrong actions) |
| `ledger` | open loops: item, first/last reported, times skipped, state |
| `checkpoints` | per channel: processed-through timestamp |
| `drafts` | drafts the skill wrote and what happened to them (sent, edited, binned) |
| `proposals` | rules waiting for confirmation, with an expiry date |
| `index_ref` | hash of the published `index.json` |

**Fact kinds:** `rule` (sender/domain/series/thread → bucket, explicit or inferred + confidence), `correction`, `person` (role, VIP, personal), `voice` (greeting, sign-off, length, language), `preference` (e.g. "one question at a time", "large broadcast invites are never flagged"), `commitment`.

**Never stored:** message bodies, attachments, Teams message text, tokens or secrets. Only IDs, digests and summaries of 200 characters or less.

## 5. First install (setup)

| Stage | What happens | Writes |
|---|---|---|
| S0 Consent | Show what will be read (sent mail 12 months, inbox 30 days, calendar ±30 days, Teams chats 30 days), what is stored, where, and that nothing is ever sent. Choose the store folder and channels. | empty store, head v0 |
| S1 Behaviour study | **Sent box first**: 12 months of sent metadata show whom the user answers, how fast, in which language, their working hours and own domain. Then inbox, calendar and Teams behaviour, existing mail rules and Focused/Other overrides. Paged and resumable. | inferred `rule`/`person`/profile facts |
| S2 Voice study | Up to 40 sent replies (in memory only, quoted history stripped) → greeting, sign-off, typical length, bullets, default language; confirmed with the user in one line. | `voice` facts |
| S3 Calibration | Asks about the uncertain senders/series one at a time (Noise · FYI · Reply · Personal · skip). | explicit rules |
| S4 Dry run | One full run with no writes. Shows what it would have tagged, flagged, drafted and answered. | report only |
| Live | Automation preset applied (default **Auto · Medium**) and the recommended daily run + weekly learn scheduled. | head, schedule |

Resumable at every stage (`setup resume`). A broken or foreign head is treated as recovery, never overwritten.

## 6. The daily run

```
collect (metadata only, batched)  →  classify by rules (engine)  →  model only for unknowns
→ act within autonomy level  →  observe the user's actions since last run (signals)
→ learn (proposals, corrections)  →  publish new head  →  short report
```

### 6.1 Buckets

| Bucket | Meaning | Default actions |
|---|---|---|
| **Noise** | needs no human | tag; mark read once a confirmed rule allows it |
| **FYI** | only needs knowing | tag; one digest line in the report; mark read |
| **Reply** | needs the user | tag; flag (To Do); write a reply draft in the user's voice |
| **Personal** | private life | counted only; never opened, summarised or learned from; marked read only after the user acted on it (RSVP or reply) |
| unknown | no rule yet | left untouched; asked about once in the report |

Precedence: Personal → Reply (VIP, live ask, deadline, explicit rule) → confirmed rules → inferred rules above threshold (0.8) → unknown.

## 7. Channels

| Channel | Collect | Actions (by level) | Signals learned from |
|---|---|---|---|
| **Mail** (v0.1) | inbox since checkpoint: sender, subject, thread, flags, categories, Focused/Other | tag · mark read · flag · reply draft | tag changed/removed, replied, flag added/cleared/completed, draft binned/edited, marked unread |
| **Calendar** (v0.1) | invites and updates in mail plus calendar view ±14 days | **learn with the user, then ask**: recommend + ask per invite (one question each); once a pattern is learned, propose a rule; accept automatically only under a rule the user confirmed; never decline | answered differently from recommendation, clash resolved by hand, invite left unanswered |
| **Teams** (v0.2) | 1:1 and group chats plus channel @mentions since checkpoint, kept only when they **need a response** from the user (a question, ask, or unanswered mention) | list what needs a response; help the user answer it (suggested reply in their voice, context from the thread); the user posts it; never posts itself | replied to a surfaced item, ignored it, replied to something not surfaced |

Calendar rules learned from real use:
- Broadcast invites above a size threshold (default 50 invitees) are never flagged.
- Before accepting under a rule, check for overlap with meetings already accepted or with external attendees. On a clash, don't respond: flag it and list the clash in the report.
- Recurring series are answered one occurrence at a time unless the user confirms the series.

## 8. Learning loop and autonomy

**From signals to rules**
1. Signals are grouped by series rule, else sender, over a rolling 7-day window.
2. At least 2 signals in the same direction create a proposal: an inferred rule at confidence 0.6, with evidence IDs.
3. The report asks the user to confirm the proposal (one question). Confirmed rules become explicit, at confidence 1.0.
4. Proposals expire after 14 days if unanswered. Inferred rules with no supporting signals in 30 days decay and are retired.
5. Mixed signals are listed as inconsistent and never promoted.

**Autonomy ladder (per bucket)**

| Level | Allowed |
|---|---|
| 0 | report only |
| 1 | tag |
| 2 | + mark read, flag |
| 3 | + calendar accept under rules the user confirmed, only with invite accepts switched on (never before a learned pattern was proposed and confirmed) |

**Presets** set the starting level and the ceiling: Low (1 everywhere), **Auto · Medium, the default** (Noise/FYI/Reply 2, calendar 1 → may earn 3), High (calendar 3 from the start). Invite accepts are a separate opt-in, off at every preset. Inside the ceiling, levels still move with accuracy.

Promotion: at least 5 counted runs with an override rate under 5%, and at least 30 decisions in the streak. Demotion: any wrong action (e.g. a binned draft for a sender, or a Noise item marked unread again) pauses that rule and drops the bucket one level. Sending is not on the ladder.

### 8.1 The Sent box in the loop

Every run reads Sent Items since the checkpoint before anything else. A reply in a thread the run tagged Reply agrees and closes the open loop. A reply to something tagged Noise/FYI (or never surfaced) is `replied_not_proposed`; two of those for a sender or series become a proposal. A run draft that was sent with more than half its words changed is a voice signal; when the user's greeting, sign-off or length drift over five or more replies, the voice fact is replaced. Details: `skills/dear-inbox-zero/learn/sent-box.md`.

## 9. Safety guarantees (enforced in engine and host mapping)

- Forbidden operations: send, forward, delete, decline, post. Host mappings must not expose them, and the engine never plans them. (Many hosts' "forward" sends immediately.)
- Drafts are written as formatted HTML/Markdown, never plain text that loses its line breaks, and re-read after writing.
- Existing categories, flags and rules set by the user are never removed.
- Unattended runs only write to locations the host allows. Anything else is parked and reported, never forced.
- Personal mail is never opened.

## 10. Token budget

| Item | Budget (target) |
|---|---|
| `SKILL.md` router, loaded on every invocation | ≤ 6 KB (≈ 1.5k tokens) |
| Additional guides loaded in one daily run | ≤ 15 KB |
| Head memory | ≤ 16 KB; index read only for rules the run needs |
| Model input per unknown item | metadata ≤ 300 chars; body only when drafting a reply |
| Report | counts + items needing the user; FYI as one line each |

The mechanism behind these budgets: the engine does classification, ledgering and learning in Python. The model handles only judgement (unknown items, drafting, summarising FYI). Reads are batched in one script per channel rather than one tool call per item.

Reference point: the author's private predecessor loads a 23.6 KB main skill file (≈ 5.9k tokens) every run, and 20% of its engine is legacy. v0.1 drops both.

## 11. Portability: one core, thin host adapters

Goal: install the same folder in any agent that can read a skill folder and call Microsoft 365 tools, with no edits to the core.

**Portability rules for the core**
- Only the Agent Skills basics: `SKILL.md` with `name` + `description` frontmatter, Markdown guides, Python scripts. No host-specific frontmatter, tool names or UI syntax in the core.
- Every action is an **abstract operation** (table below). Only `hosts/<host>.md` names concrete tools.
- The engine is plain Python 3.10+, standard library only, run as `python -m dear_engine …` with JSON in/out files, so any host that can run Python (or a script tool) can use it. Hosts that can't run Python can still use the recipe; the guides describe each step in prose as a fallback.
- Questions to the user go through `ask(question, options)`, which maps to the host's own prompt tool or plain chat.

**Abstract operations**

| Operation | Purpose |
|---|---|
| `mail.list(since, folder)` · `mail.meta(ids)` · `mail.body(id)` | collect |
| `mail.tag(id, category)` · `mail.read(id)` · `mail.flag(id, state)` | act |
| `mail.reply_draft(id, html)` · `mail.sent(since)` | draft · signals |
| `cal.view(start, end)` · `cal.accept(event_id, occurrence)` | calendar |
| `teams.needs_response(since)` · `teams.thread(id)` · `teams.my_replies(since)` | Teams |
| `store.list/read/write(path)` | memory (OneDrive) |
| `ask(question, options)` | one-question-at-a-time prompts |

**Adapters**

| Adapter | Covers | Built in |
|---|---|---|
| `hosts/cowork.md` | Microsoft 365 Copilot Cowork | v0.1 |
| `hosts/graph-mcp.md` | any agent that can call Microsoft Graph through an MCP server or HTTP tool (GitHub Copilot, Microsoft 365 Copilot agents, other assistants) | v0.1.x |
| `hosts/<new>.md` | any other agent: copy the template, map each operation, run `doctor` | community |

Each adapter lists least-privilege scopes: `Mail.ReadWrite`, `Calendars.ReadWrite`, `Chat.Read`, `ChannelMessage.Read.All` (mentions only), `Files.ReadWrite`. No `Mail.Send`, no `ChatMessage.Send`. `doctor` checks that an adapter maps every required operation and exposes none of the forbidden ones.

A host is listed as **supported** in the README only after `doctor` passes and a dry run on that host has been verified.

## 11a. Agent-led install

Users don't install by hand: they ask their agent ("install dear-inbox-zero from <repo>"). The repo carries three agent-readable entry points:

| File | Role |
|---|---|
| `AGENTS.md` | rules for any agent working in or installing from the repo |
| `INSTALL.md` | deterministic install procedure: read manifest → identify host → choose folder → copy + verify sha256 → pick adapter → `doctor` → hand over to setup |
| `install.json` | machine-readable manifest: files with sha256, host skills folders and detection hints, adapter per host, required and forbidden capabilities, memory location |
| `llms.txt` | short index so a model can find the above |

Installing never touches mail, calendar, chats or memory. Setup (with consent) does. Upgrades back up the old folder; nothing is deleted. CI regenerates `install.json` hashes on every release and fails if they're out of date.

## 12. Testing and privacy

- Unit tests run on synthetic fixtures only (fictional persona "Alex", `example.com` domains).
- CI runs a personal-data scan: email addresses outside `example.*`, phone numbers, known-name allowlist checks, high-entropy strings. The build fails on any hit.
- Skill lint: frontmatter, file sizes against the token budget, broken references.
- An evaluation set of labelled synthetic mail/invite/chat items measures bucket accuracy per release.

## 13. What carries over from the private predecessor

| Keep (generalised) | Drop |
|---|---|
| append-only store, head/index, supersession | shadow/handover mode, v4→v5 migration code |
| rule precedence and box assignment | "Deliver" bucket (retired) |
| signal → proposal → confirm learning loop | lanes tied to one tenant's mail rules |
| autonomy ladder and promotion maths | compiled `.pyz` bundle (ship source) |
| sent-mail and voice study, calibration | anything referencing a real person, customer or sender |
| report layout (today plan, open loops, digest) | |
| fixes for known bugs: crash on learning rows with no outcome; proposals that never expire | |

Every ported module is scanned before commit. Tests are rewritten on synthetic data, not copied.

## 14. Roadmap

| Version | Scope | Built by |
|---|---|---|
| **v0.1** | mail + calendar, setup S0–S4, learning loop, autonomy, Cowork mapping, synthetic tests, CI privacy scan | author with Copilot (Cowork) |
| v0.1.x | Graph/MCP host adapter (GitHub Copilot and other agents), adapter template | GitHub Copilot coding agent (issue) |
| **v0.2** | Teams: messages that need a response, help answering them, reply signals | GitHub Copilot coding agent (issue) |
| v0.3 | weekly learn report, store hygiene, evaluation dashboard | open |

## 15. Decisions (10 Nov 2026)

| # | Question | Decision |
|---|---|---|
| 1 | Where does memory live? | The user's own OneDrive (`OneDrive/dear-inbox-zero/<account_key>/`); local folder only as fallback |
| 2 | Calendar autonomy | Learn with the user and ask: recommend + ask per invite; propose a rule once a pattern is clear; auto-accept only under rules the user confirmed |
| 3 | Teams | Find chats and @mentions that need a response and help the user answer them; the user posts |
| 4 | Licence | **Apache-2.0**: permissive for broad use, explicit patent grant, and its contribution clause (§5) makes contributions flow back under the same terms without a separate CLA |
| 5 | Hosts | One core for every agent; host adapters per agent (§11) |
| 6 | Install | Agent-led: the agent installs (zip upload in Cowork, or from the repo), then starts setup straight away |
| 7 | Default automation | Auto · Medium, with a daily run each weekday and a weekly learn |
| 8 | Names | Apache-2.0 for the code; names covered by `TRADEMARKS.md` |
