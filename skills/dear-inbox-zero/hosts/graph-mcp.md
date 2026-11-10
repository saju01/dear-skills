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
| `mail.sent` | `GET /me/mailFolders/sentitems/messages?$filter=sentDateTime ge {t}&$select=conversationId,sentDateTime,toRecipients` | |
| `mail.tag` | `PATCH /me/messages/{id}` `{categories: [...existing, tag]}` | |
| `mail.read` | `PATCH /me/messages/{id}` `{isRead: true}` | |
| `mail.flag` | `PATCH /me/messages/{id}` `{flag: {flagStatus: "flagged"}}` | |
| `mail.reply_draft` | `POST /me/messages/{id}/createReply` then `PATCH` the draft `{body: {contentType: "HTML", content}}` | never `/send` |
| `mail.categories` | `GET/POST /me/outlook/masterCategories` | |
| `cal.view` | `GET /me/calendarView?startDateTime=…&endDateTime=…&$select=subject,start,end,responseStatus,attendees,organizer,seriesMasterId` | |
| `cal.accept` | `POST /me/events/{id}/accept` `{sendResponse: true}` | occurrence id |
| `teams.needs_response` | `GET /me/chats?$expand=lastMessagePreview` + `GET /chats/{id}/messages?$top=20`; mentions via `POST /search/query` (entityTypes `chatMessage`) | |
| `teams.thread` | `GET /chats/{id}/messages?$top=10` or `GET /teams/{t}/channels/{c}/messages/{m}/replies` | |
| `teams.my_replies` | same, filtered on `from.user.id = me` | |
| `store.list` | `GET /me/drive/root:/dear-inbox-zero/{account_key}/{sub}:/children` | |
| `store.read` | `GET /me/drive/root:/{path}:/content` | |
| `store.write` | `PUT /me/drive/root:/{path}:/content?@microsoft.graph.conflictBehavior=fail` | never overwrite facts |
| `ask` | the agent's chat | one question per message |
| `run_python` | the agent's terminal / code tool | Python 3.10+ |
<!-- adapter-ops:end -->

## Never call

`/send`, `/forward`, `/createForward`, `/move`, `DELETE /me/messages/*`, `/decline`, `/tentativelyAccept`, `POST /chats/*/messages`, `POST /teams/*/channels/*/messages`.
