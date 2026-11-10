# Channel: mail

## Collect (`mail.list` since the mail checkpoint)

One batched read, metadata only. Map each message to an item (`schemas/item.schema.json`, `channel: "mail"`):

| Item field | From |
|---|---|
| `id`, `thread_id` | message id, conversation id |
| `sender`, `sender_name`, `sender_domain` | from address (lower-case), display name, domain |
| `subject`, `series` | subject; `series` = subject with dates, numbers and `RE:/FW:` removed (engine fills it if empty) |
| `to_me`, `cc_only` | user is in To / only in Cc |
| `has_question` | the ≤ 300-char preview contains a direct question or ask to the user |
| `deadline_hint` | a date phrase in subject/preview ("by Friday", "EOD", a date) |
| `is_read`, `flagged`, `categories`, `importance`, `other_tab` | as on the message (`other_tab` = Focused Inbox "Other") |
| `is_invite` | meeting request → route to `channels/calendar.md` instead |

Never read bodies at collect. Read one body only when drafting a Reply.

## Act (engine plans the actions; you perform them)

| Action | Operation |
|---|---|
| `tag` | `mail.tag(id, "DIZ <Bucket>")`: append to existing categories, never replace |
| `mark_read` | `mail.read(id)` |
| `flag` | `mail.flag(id, "flagged")` (shows in To Do) |
| `draft` | read the body (`mail.body`), write a reply draft (`policy/voice.md`), `mail.reply_draft(id, html_file)`, re-read it |

First run only: create the four categories if missing (`DIZ Noise` grey, `DIZ FYI` blue, `DIZ Reply` orange, `DIZ Personal` none).

## Observe (signals for the learning loop)

Compare the items the last run acted on (`state.last_run`) with their state now:

| Signal | When |
|---|---|
| `tag_removed` / `tag_changed:<bucket>` | the user cleared or changed a DIZ tag |
| `marked_unread` | a Noise/FYI item the run marked read is unread again |
| `replied` | the user sent a reply in the thread after the item arrived (not meeting responses) |
| `replied_not_proposed` | the user replied to an item that wasn't tagged Reply |
| `flag_added` / `flag_removed` / `flag_completed` | the user changed a flag (flags the run set and left alone are not signals) |
| `draft_binned` / `draft_edited_heavily` | a run draft was deleted unsent / changed a lot before sending |

Write them to `signals.json` as `{id, signal, at}`.
