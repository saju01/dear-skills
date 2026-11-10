# The Sent box

What the user sends is the best evidence of what matters to them. It's used at first install to customise the skill and every day to learn. Bodies are read in working memory only and never stored. Memory keeps counts, medians and short greeting/sign-off patterns.

## At first install (setup S1–S2): `sent-study`

1. **Collect metadata, 12 months** (`mail.sent`, paged, one batched read per page): for each sent item `{id, conversation_id, sent_at, to[], cc[]}`. For replies, also the message it answered: `in_reply_to_sender` and `in_reply_to_received_at` (the latest received message in the same conversation before `sent_at`). Skip meeting responses and auto-replies.
2. **Collect up to 40 recent reply bodies** (`mail.body`) into a working file `{id: body}`, plus each recipient's first name in `recipient_names` so greetings can be templated. Never upload this file.
3. Run
   `python engine/dear_engine.py sent-study --state state.json --sent sent.json --bodies bodies.json`
   then delete `bodies.json`.

| What it learns | How | Becomes |
|---|---|---|
| Who the user answers | ≥ 3 replies in 12 months | inferred **Reply** rule for that sender (0.7, or 0.8 at ≥ 6) |
| Who matters most | ≥ 8 replies with a median reply time ≤ 4 h | **VIP** proposal, confirmed in calibration |
| Reply speed per contact | median hours between receipt and reply | `person.median_reply_hours`, used to age open loops |
| Language per contact | language of the user's own replies to them | `person.language`: drafts to that contact use it |
| Voice | most common greeting and sign-off, median length, bullet use, default language | one `voice` fact (`policy/voice.md`) |
| Working hours | weekday hours with ≥ 5% of sends | `profile.working_hours`: report timing, Teams reply window |
| Own organisation | the domain the user writes to most | `profile.internal_domains`: decides "external" for invites |

Calibration (S3) then asks about the uncertain results one at a time: "You answered Pat 14 times, usually within 2 hours. Treat Pat as VIP?"

## Every daily run: `sent-signals`

1. Collect sent items since the mail checkpoint (`mail.sent`): `{id, conversation_id, sent_at, is_meeting_response}`.
2. For replies to a thread where the run left a draft, read both bodies into working files (`bodies.json` for sent, `draft-bodies.json` for the run's drafts).
3. Run
   `python engine/dear_engine.py sent-signals --state state.json --sent sent.json --bodies bodies.json --draft-bodies draft-bodies.json --out signals.json`
   **before** `observe`. It appends to `signals.json`.

| Evidence | Signal | Effect |
|---|---|---|
| The user replied in a thread the run tagged Reply | `replied` | agrees; closes the open loop |
| The user replied in a thread the run tagged Noise/FYI (or didn't surface) | `replied_not_proposed` | after 2 such signals for a sender/series → proposal to treat it as Reply |
| The user sent the run's draft with > 50% of the words changed | `draft_edited_heavily` | voice signal; repeated → voice update |
| Greeting, sign-off or length of the user's own replies drift (≥ 5 samples) | — | a new `voice` fact replaces the old one |
| A meeting response | ignored | invites learn from the calendar channel instead |

Replies sent before an item arrived never count. The draft registry records each run draft by thread so a sent draft is matched to what the user actually sent.

## Customising to the user (summary)

After setup the skill knows, for this user: whom to treat as Reply or VIP, the language and tone per contact, their working hours and their own domain. The daily Sent signals keep this current: new people the user starts answering become proposals, people they stop answering decay after 30 days, and the voice follows how they actually write.
