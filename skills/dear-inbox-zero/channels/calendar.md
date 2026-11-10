# Channel: calendar

## Collect

- Invites, updates and cancellations from mail (`is_invite`), plus `cal.view(now-1d, now+14d)` for clash checks.
- Item fields (`channel: "invite"`): `id`, `event_id`, `organizer`, `sender_domain`, `subject`, `series`, `start`, `end`, `invitees` (count), `external` (any attendee outside the user's domains), `is_series`, `my_response`.
- Calendar rows for clash checks go to `calendar.json`: `{event_id, subject, start, end, my_response, external}`.

## Learn with the user, then ask

The engine returns one recommendation per invite: `accept`, `ask` or `fyi`.

| Situation | Recommendation |
|---|---|
| Broadcast (invitees ≥ `profile.broadcast_threshold`, default 50) | `fyi`: never flagged, no RSVP needed unless a rule says otherwise |
| Overlaps an accepted meeting or one with external attendees | `ask` with the clash listed; never answered automatically |
| Matches a rule the user **confirmed** and the calendar bucket is at autonomy level 3 | `accept` (one occurrence at a time unless the rule covers the series) |
| Anything else | `ask`: one question per invite ("Accept / Tentative-by-you / Skip / Always accept from this organiser") |

Never decline. Never answer on the user's behalf without a confirmed rule. "Always accept from this organiser" creates a proposal the user confirms once.

## Act

`accept` → `cal.accept(event_id, occurrence)`, then mark the invite mail read. `ask` → list in the report under **Decide today**; flag the invite mail only on a clash.

## Observe

`answered_differently` (the user's response ≠ recommendation), `answered_after_ask` (with the response), `clash_resolved` (the user moved/declined one side), `left_unanswered` (start passed with no response).
