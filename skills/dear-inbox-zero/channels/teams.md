# Channel: Teams

The engine applies the needs-response rules. Collect each chat's messages and
channel mentions, then run:

```text
python engine/dear_engine.py teams-filter --state state.json --chats chats.json --user-id <me-id> --out items.json
```

`chats.json` is a list of `{id, thread_id, direct, subject, messages}` records.
Each message has `id`, `sender_id`, `sent_at`, and optional `sender`,
`sender_name`, `has_question`, `mentions_me`, and `preview` (or `text`).
The latest message is tested; its preview stays in working files only. The
engine reads `profile.tz`, `profile.working_hours`, and
`profile.teams_reply_hours` (default 4).

Read recent thread context with `teams.thread` and show a suggested reply; the
user posts it. Never post from the engine or host.

For reply signals, collect the user's own posts (`teams.my_replies`) and run
before `observe`:

```text
python engine/dear_engine.py teams-signals --state state.json --posts own-posts.json --user-id <me-id> --out signals.json
```

Posts use `id`, `thread_id`, `sender_id`, and `sent_at`; optional
`reply_to_sender` identifies the other participant for an unsurfaced thread.
The command emits `replied`, `replied_not_proposed`, and `ignored` (after two
working days without a reply) from the user's own posts and open Teams loops.
