# Adapter: Microsoft 365 Copilot Cowork

Batch every per-item loop in one tool script (`RunScript`), never one call per item.

<!-- adapter-ops:begin -->
| Operation | Tool | Notes |
|---|---|---|
| `me` | `GetMyDetails` | timezone from the user's settings |
| `mail.list` | `ExecuteSql` over `messages` | `SELECT TOP n id, conversationId, sender, senderName, subject, receivedDateTime, isRead, importance, categories, flag, inferenceClassification, bodyPreview … WHERE receivedDateTime >= '<checkpoint>'` |
| `mail.meta` | `ExecuteSql` over `messages WHERE id IN (…)` | ≤ 50 ids per statement |
| `mail.body` | `GetMessage` | only for drafting |
| `mail.sent` | `ExecuteSql` over `messages` in Sent Items | `parentFolderId` of Sent Items |
| `mail.tag` | `UpdateMessage` | `categories` = existing + DIZ tag |
| `mail.read` | `UpdateMessage` | `isRead: true` |
| `mail.flag` | `FlagEmail` | **gated**: may raise an approval card per call. Run in step 10 as direct calls, never inside `RunScript` (a card suspends the whole script) |
| `mail.reply_draft` | `CreateReplyDraft` / `CreateReplyAllDraft` | always `body_file_path=` a Markdown file; re-read with `GetMessage` |
| `mail.categories` | `QueryGraph` `/me/outlook/masterCategories` | create the four DIZ categories once |
| `cal.view` | `ListCalendarView` | not raw Graph calendarView (can return 0 rows) |
| `cal.accept` | `AcceptEvent` | one occurrence id at a time; sends the organiser a response, so only when invite accepts are on |
| `teams.needs_response` | `ListChats` + `ListChatMessages`; `SearchM365` for channel mentions | in one tool script |
| `teams.thread` | `ListChatMessages` / `ListChannelMessages` | last 10 messages |
| `teams.my_replies` | `ListChatMessages` filtered on the user's id | |
| `store.list` | `GetDriveChildren` | `OneDrive/dear-inbox-zero/<account_key>/…` |
| `store.read` | `ReadFileContent` (mode download) | |
| `store.write` | `UploadFileContent` | **gated** in unattended runs (may be refused): upload the head in its own call; on refusal park the files in the task output and report |
| `ask` | `AskUserQuestion` | one item per question |
| `run_python` | `Bash` / `RunScript` | Python 3.10+ |
| `schedule` | `GetScheduledPrompts` then `SetupScheduledPrompt` | one prompt per job from `automation`; never duplicate an existing one |
<!-- adapter-ops:end -->

## Never call

`SendEmailWithAttachments`, `SendDraftMessage`, `ReplyToMessage`, `ReplyAllToMessage`, `ForwardMessage` (sends immediately), `CreateForwardDraft`, `DeleteMessage`, `MoveMessage`, `DeclineEvent`, `TentativelyAcceptEvent`, `PostMessage`, `PostChannelMessage`, `ReplyToChannelMessage`.

## Notes

- Raw Graph reads (`QueryGraph`): pass `$filter` as a plain expression. A URL-encoded filter returns 0 rows with no error (#15).
- Gated operations (`mail.flag`, `mail.reply_draft`, `cal.accept`, `store.write`) may raise an approval card. They run after the report (SKILL.md step 10) so a card nobody answers never blocks memory or the report (#12).

- Schedule with the host's scheduled prompts; check existing schedules first so runs never double up.
- If the working folder disappears after a disconnect, re-download the head and continue; never re-initialise.
