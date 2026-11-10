# First install (setup)

Resumable: `state.setup.stage` records progress; `setup resume` continues from it. Never initialise over an existing head: a foreign or broken head is recovery, shown to the user.

## S0 — Consent (one prompt)

1. Get the user's address, timezone and working hours (`me`). Propose `account_key` (a short slug, e.g. `work`, never the address).
2. Ask once, as a multi-select (all on by default): which channels (mail, calendar, Teams); the automation level (**Auto · Medium** recommended, or Low / High, see `policy/buckets.md`); a daily run on weekdays plus a weekly learn (scheduled at S4); what will be read (sent mail 12 months, inbox 30 days, calendar ±30 days, Teams chats 30 days); what is stored (rules, ids, short summaries; never bodies); where (`OneDrive/dear-inbox-zero/<account_key>/`); and that no mail or message is ever sent. Ask separately, **unticked**: "Accept invites for me under rules I confirm? This sends the organiser my acceptance." Only a tick switches it on (`go-live --invite-accept on`).
3. `python engine/dear_engine.py store-init --store <working>/store --account <account_key> --tz <tz> --channels mail,calendar,teams` → upload the store folder. Stage `s0_done`.

## S1 — Behaviour study (paged, resumable)

**Sent box first** (`learn/sent-box.md`): 12 months of sent metadata plus up to 40 reply bodies (working memory only) →
`python engine/dear_engine.py sent-study --state … --sent sent.json --bodies bodies.json`.
This learns whom the user answers and how fast, language per contact, working hours, their own domain and voice.

Then the rest of their behaviour, as aggregated observations (`schemas/observation.schema.json`):
- inbox (30 days): what they read without replying (`read_no_reply`), leave unread (`ignored`); Focused/Other overrides; existing mail rules;
- calendar (±30 days): organisers/series they accept or decline;
- Teams (30 days): chats and mentions they answer (`teams_replied`).

`python engine/dear_engine.py study --state … --observations obs.json` creates inferred rules and proposals. Stage `s1_done`.

## S2 — Voice check

`sent-study` already wrote the voice fact (greeting, sign-off, length, bullets, default language). Show it to the user in one line and ask: "Is this how you write? Yes / adjust". Adjustments become an explicit `voice` fact (`engine … add-facts`). Stage `s2_done`.

## S3 — Calibration (one question at a time)

`python engine/dear_engine.py calibrate --state … --out questions.json` lists the senders/series with the most volume and the least certainty (max 15). Ask each one: Noise · FYI · Reply · Personal · skip. Answers become explicit rules. Ask about VIPs and personal senders the same way. Stage `s3_done`.

## S4 — Dry run

Run the daily run with `--dry-run`: no writes. Show the report: what it would tag, flag, draft and recommend. Ask "Go live on Auto · Medium?" (or the level chosen in S0). Yes → `python engine/dear_engine.py go-live --state … --preset medium` (add `--invite-accept on` only if the user ticked it in S0). It sets the levels and returns the recommended automation (a daily run at the start of the user's working day, weekdays, and a weekly learn on Monday). Create those jobs with the `schedule` operation if the user ticked them in S0 (list existing schedules first; never duplicate). Publish. From here every run keeps learning from the Sent box and the user's actions.
