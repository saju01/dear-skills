# Channel: Teams

Goal: find the messages that **need a response** from the user and help them answer. The skill never posts.

## Collect

- 1:1 and group chats with activity since the Teams checkpoint, and channel messages that @mention the user.
- Keep only messages where the latest message isn't from the user **and** it asks the user something, mentions them, or is a 1:1 message left unanswered for more than `profile.teams_reply_hours` (default 4 working hours).
- Item fields (`channel: "teams"`): `id` (message id), `thread_id` (chat/channel thread), `sender`, `sender_name`, `sender_domain`, `subject` (chat topic or channel name), `mentions_me`, `direct` (1:1), `has_question`, `received_at`, `preview` (≤ 300 chars, kept in working files only, never stored).

## Help the user answer

For each Teams item in Reply: read the last few messages of that thread (`teams.thread`), then put in the report:
- who, where and what they need, in one line;
- a suggested reply in the user's voice (`policy/voice.md`), ready to paste;
- a link to the message.

## Observe

`replied` (the user posted in the thread after the message), `ignored` (no reply after 2 working days), `replied_not_proposed` (the user answered a thread the run didn't surface).
