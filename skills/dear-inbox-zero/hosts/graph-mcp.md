# Adapter: Microsoft Graph (any agent with an MCP server or HTTP tool for Graph)

Works for GitHub Copilot and other agents that can call Microsoft Graph through an MCP server or an HTTP tool with the user's delegated token.

Least-privilege delegated scopes: `User.Read`, `Mail.ReadWrite`, `Calendars.ReadWrite`, `Chat.Read`, `ChannelMessage.Read.All`, `Files.ReadWrite`. **Do not grant** `Mail.Send` or `ChatMessage.Send`.

<!-- adapter-ops:begin -->
| Operation | Tool | Notes |
|---|---|---|
| `me` | `GET /me` + `GET /me/mailboxSettings` | timezone, working hours |
| `mail.list` | `GET /me/mailFolders/inbox/messages?$filter=receivedDateTime ge {t}&$select=id,conversationId,from,subject,receivedDateTime,isRead,importance,categories,flag,inferenceClassification,bodyPreview,toRecipients,ccRecipients&$top=50` | follow `@odata.nextLink` |
| `mail.meta` | `POST /$batch` of `GET /me/messages/{id}?$select=…` | ≤ 20 per batch |
| `mail.body` | `GET /me/messages/{id}?$select=body,uniqueBody` | only for drafting |
| `mail.sent` | `GET /me/mailFolders/sentitems/messages?$filter=sentDateTime ge {t}&$select=id,conversationId,sentDateTime,toRecipients,ccRecipients` | |
| `mail.tag` | `PATCH /me/messages/{id}` `{categories: [...existing, tag]}` | |
| `mail.read` | `PATCH /me/messages/{id}` `{isRead: true}` | |
| `mail.flag` | `PATCH /me/messages/{id}` `{flag: {flagStatus: "flagged"}}` | |
| `mail.reply_draft` | `POST /me/messages/{id}/createReply` then `PATCH` the draft `{body: {contentType: "HTML", content}}` | never `/send` |
| `mail.categories` | `GET/POST /me/outlook/masterCategories` | |
| `cal.view` | `GET /me/calendarView?startDateTime=…&endDateTime=…&$select=id,subject,start,end,responseStatus,attendees,organizer,seriesMasterId,type,isCancelled` | header `Prefer: outlook.timezone="UTC"` |
| `cal.accept` | `POST /me/events/{id}/accept` `{sendResponse: true}` | occurrence id |
| `teams.needs_response` | `GET /me/chats?$expand=lastMessagePreview` + `GET /chats/{id}/messages?$top=20`; mentions via `POST /search/query` (entityTypes `chatMessage`) | |
| `teams.thread` | `GET /chats/{id}/messages?$top=10` or `GET /teams/{t}/channels/{c}/messages/{m}/replies` | |
| `teams.my_replies` | same, filtered on `from.user.id = me` | |
| `store.list` | `GET /me/drive/root:/dear-inbox-zero/{account_key}/{sub}:/children` | |
| `store.read` | `GET /me/drive/root:/{path}:/content` | |
| `store.write` | `PUT /me/drive/root:/{path}:/content?@microsoft.graph.conflictBehavior=fail` | never overwrite facts |
| `ask` | the agent's chat | one question per message |
| `run_python` | the agent's terminal / code tool | Python 3.10+ |
| `schedule` | the agent's own scheduler, or OS cron / Task Scheduler running the agent CLI | if none exists, tell the user to run `dear-inbox-zero` each morning |
<!-- adapter-ops:end -->

## Collect saved JSON (no model mapping)

After setup consent, save Graph responses in a private temporary folder, **outside the skill and repository**. Follow every `@odata.nextLink` and save all pages; collectors never fetch URLs. `--input` accepts one or more files: Graph `{"value": [...]}` envelopes, resource arrays, arrays of pages, or single resources. Empty pages produce empty output; Graph errors fail.

Use the address/id from `me` for `--me`/`--me-id`. Load `state.json` with `store-load`. Calendar checks attendee **and organizer** domains against `head.profile.internal_domains` (exact, case-insensitive); with no internal domains, all addressed participants are external.

Run from the skill folder; `$WORK` is private temporary storage. Replace fictional address/id placeholders:

```sh
python engine/dear_engine.py collect-mail --input "$WORK/inbox-page-1.json" "$WORK/inbox-page-2.json" --me alex@example.com --state "$WORK/state.json" --out "$WORK/items.json"
python engine/dear_engine.py collect-sent --input "$WORK/sent-pages.json" --received "$WORK/items.json" --out "$WORK/sent.json"
python engine/dear_engine.py collect-calendar --input "$WORK/calendar-pages.json" --state "$WORK/state.json" --out "$WORK/calendar.json"
python engine/dear_engine.py collect-teams --input "$WORK/chat-messages.json" --chats "$WORK/chats.json" --me-id alex-id --state "$WORK/state.json" --out "$WORK/items.json" --append
```

- Mail uses `bodyPreview` only to derive `has_question` (question mark or common asks in en/nl/de/fr/es) and a short `deadline_hint`. These are heuristics, not semantic judgements. To/CC checks are exact and case-insensitive; To takes precedence.
- For invitation mail, save the related Graph event as the message's `event` property (expand/read the event relationship via `mail.meta`). The collector keeps the **message** id for mail actions and maps the event id/times/response for RSVP and clashes. Without complete event metadata, the engine asks instead of accepting, even under a confirmed rule. `--state` supplies internal domains for embedded events.
- Sent output feeds `sent-study` / `sent-signals`. `--received` takes normalized mail covering the study period. A **conversation heuristic**, not an In-Reply-To lookup, selects the latest strictly earlier message from a sent recipient for `in_reply_to_received_at` / `in_reply_to_sender`. No match/index means both are omitted.
- Calendar writes clash rows to `calendar.json`, excluding cancelled events. Event ids are not mail ids: do not append these rows to mail items or mark them read as messages. Request UTC as above; explicit timestamp offsets and IANA zone names are also supported. Windows zone names other than UTC require re-fetching with the UTC header, not guessing an offset.
- Teams reads `/chats/{id}/messages` with `chatId` on each message (attach the fetched chat id if absent). `--chats` supplies `/me/chats` metadata (`chatType`, `topic`). Include own messages to suppress answered chats. Only the latest message per chat is considered: questions, mentions, or unanswered one-to-one messages after `profile.teams_reply_hours` (default 4 weekday working hours; `profile.tz`, `profile.working_hours` or 09–17). Without chat metadata, no one-to-one timeout applies. Sender falls back to the user id. Item `id` is URL-escaped `chatId/messageId` to avoid cross-chat collisions; `message_id` retains the raw id for host lookups.
- `--append` merges items by `(channel, id)`, replacing duplicates while preserving other channels. Start each run with a fresh mail output; do not append to a previous run's Teams items, which may now be answered. Calendar clash rows and sent output always replace their files.

No preview, body, attachment or token is copied to output. Keep raw responses ephemeral; never publish them to memory. Feed items/calendar to `classify` and sent output to `sent-signals`; the host collects other user-action signals per the channel guides.

## Never call

`/send`, `/forward`, `/createForward`, `/move`, `DELETE /me/messages/*`, `/decline`, `/tentativelyAccept`, `POST /chats/*/messages`, `POST /teams/*/channels/*/messages`.
