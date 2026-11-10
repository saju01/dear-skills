# First install (setup)

Resumable: `state.setup.stage` records progress; `setup resume` continues from it. Never initialise over an existing head: a foreign or broken head is recovery, shown to the user.

## S0 — Consent (one prompt)

1. Get the user's address, timezone and working hours (`me`). Propose `account_key` (a short slug, e.g. `work`, never the address).
2. Ask once, as a multi-select: which channels (mail, calendar, Teams); what will be read (sent mail 12 months, inbox 30 days, calendar ±30 days, Teams chats 30 days); what is stored (rules, ids, short summaries; never bodies); where (`OneDrive/dear-inbox-zero/<account_key>/`); and that nothing is ever sent.
3. `python engine/dear_engine.py store-init --store <working>/store --account <account_key> --tz <tz> --channels mail,calendar,teams` → upload the store folder. Stage `s0_done`.

## S1 — Behaviour study (paged, resumable)

Collect, in batches, the user's own behaviour:
- sent mail (12 months): who they reply to, how fast, in which language;
- inbox (30 days): what they read, flag, leave unread; Focused/Other overrides; existing mail rules;
- calendar (±30 days): which organisers/series they accept, decline or ignore;
- Teams (30 days): which chats and mentions they answer.

Write them as observations (`schemas/observation.schema.json`), then
`python engine/dear_engine.py study --state … --observations obs.json --out facts.json`. This creates inferred rules, VIPs and person facts at confidence 0.6–0.8. Stage `s1_done`.

## S2 — Voice study

Sample up to 40 of the user's sent replies in memory (never stored). Record voice facts: greeting, sign-off, length, formality, language per contact (`engine … add-facts`). Stage `s2_done`.

## S3 — Calibration (one question at a time)

`python engine/dear_engine.py calibrate --state … --out questions.json` lists the senders/series with the most volume and the least certainty (max 15). Ask each one: Noise · FYI · Reply · Personal · skip. Answers become explicit rules. Ask about VIPs and personal senders the same way. Stage `s3_done`.

## S4 — Dry run

Run the daily run with `--dry-run`: no writes. Show the report: what it would tag, flag, draft and recommend. Ask "Go live?". Yes → autonomy level 1 for every bucket, stage `live`. Offer to schedule a daily run.
