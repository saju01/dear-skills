# Buckets and precedence

| Bucket | Category | Actions by autonomy level (1 / 2 / 3) |
|---|---|---|
| Noise | `DIZ Noise` | tag / + mark read (confirmed rules only) / same |
| FYI | `DIZ FYI` | tag / + mark read after the digest line / same |
| Reply | `DIZ Reply` | tag + draft / + flag / same |
| Personal | `DIZ Personal` | tag only; counted in the report; marked read only after the user acted (RSVP or reply) |
| unknown | none | nothing; asked once in the report |

Level 0 = report only. Calendar accept is level 3, needs a confirmed rule and needs invite accepts switched on (`profile.invite_accept`, off by default at every preset), because accepting sends the organiser a response (`channels/calendar.md`).

## Automation presets (chosen at setup; `automation --preset` changes it later)

| Preset | Starts at | Can earn up to | In practice |
|---|---|---|---|
| Low | 1 everywhere | 1 | tags and drafts only; nothing marked read or flagged |
| **Auto · Medium (default)** | Noise/FYI/Reply 2, calendar 1 | calendar 3 | tags, drafts, flags Reply, marks Noise (confirmed rules) and FYI (after the digest) read; asks about every invite |
| High | Noise/FYI/Reply 2, calendar 3 | same | as Medium; if the user switches invite accepts on, confirmed rules accept from day one |

Every preset: invite accepts start **off**; the user switches them on separately (`automation --invite-accept on`), and until then the report asks about every invite. A wrong action drops that bucket one level and pauses the rule. Never send mail, forward, post, delete or decline.

## Precedence (first match wins)

1. **Personal**: sender or domain pinned personal.
2. **Reply**: VIP sender; an explicit `respond` rule; a direct ask to the user (`to_me` and `has_question`); a `deadline_hint`; a Teams item that needs a response.
3. **Explicit rule**: series > exact sender > domain.
4. **Inferred rule** with confidence ≥ 0.8 (same order).
5. **Guard**: security, compliance, password, invoice-due and device alerts never go to Noise; lift to FYI.
6. **unknown**.

A VIP's mail is Reply even inside a Noise series, unless a series rule says `beats_vip`.

## What the report always shows

Counts per bucket, **Decide today** (invites to answer, clashes), **Reply** items with draft status, open loops older than 2 working days with the days elapsed, one digest line per FYI item, proposals waiting for confirmation (one question each), and unknowns.
