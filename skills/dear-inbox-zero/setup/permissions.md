# Permissions

Every Microsoft Graph permission dear-inbox-zero can ask for: what it's for, whether a tenant admin usually has to approve it, and which mode needs it. All of them are **delegated**, so the skill acts as the signed-in user and sees only what that user can see. It never uses application (app-only) permissions.

## The short version

| Mode | Grant | Admin consent |
|---|---|---|
| **Lite** | `User.Read`, `Mail.ReadWrite`, plus `Files.ReadWrite` if memory lives in OneDrive | none |
| **Pro** | lite's three, plus `MailboxSettings.ReadWrite`, `Calendars.Read`, `Chat.Read` | none |
| Pro, invite accepts on | swap `Calendars.Read` for `Calendars.ReadWrite` | none |
| Pro, Teams channels | add `ChannelMessage.Read.All` | **yes** |

Lite never needs a scope that requires admin consent. Pro needs one only if you want Teams channel threads and channel mentions. Without it, Teams covers your chats only.

## Every scope

The "Admin consent" column is Microsoft's default for the delegated permission ([permissions reference](https://learn.microsoft.com/graph/permissions-reference)). Your tenant can be stricter: see [When your organisation decides](#when-your-organisation-decides).

<!-- scopes:begin -->
| Scope | What it's for | Operations | Admin consent | Lite | Pro |
|---|---|---|---|---|---|
| `User.Read` | your address and name | `me` | No | yes | yes |
| `Mail.ReadWrite` | read mail metadata, read one body when drafting, add tags, mark read, flag, create reply drafts; it can't send | `mail.list`, `mail.meta`, `mail.body`, `mail.sent`, `mail.tag`, `mail.read`, `mail.flag`, `mail.reply_draft` | No | yes | yes |
| `Files.ReadWrite` | memory under `OneDrive/dear-inbox-zero/` | `store.list`, `store.read`, `store.write` | No | optional | yes |
| `MailboxSettings.ReadWrite` | timezone and working hours; creates the four coloured DIZ categories once | `me`, `mail.categories` | No | no | yes |
| `Calendars.Read` | meeting invites and clashes | `cal.view` | No | no | yes |
| `Calendars.ReadWrite` | accept an invite, which sends the organiser a response | `cal.accept` | No | no | only with invite accepts on |
| `Chat.Read` | Teams one-to-one and group chats, chat mentions | `teams.needs_response`, `teams.thread`, `teams.my_replies` | No | no | yes |
| `ChannelMessage.Read.All` | Teams channel threads and channel mentions | `teams.needs_response`, `teams.thread` | **Yes** | no | optional |
<!-- scopes:end -->

Pro can run with `MailboxSettings.Read` instead of `MailboxSettings.ReadWrite`. Then add four categories in Outlook yourself (`DIZ Noise`, `DIZ FYI`, `DIZ Reply`, `DIZ Personal`); everything else works the same.

## Never grant

<!-- never-grant:begin -->
- `Mail.Send`, `Mail.Send.Shared`: sending mail. Drafts never need it.
- `ChatMessage.Send`, `ChannelMessage.Send`, `Chat.ReadWrite`: posting in Teams.
- `Mail.ReadWrite.Shared`: other people's mailboxes.
- `Mail-Advanced.ReadWrite`, `MailboxItem.ReadWrite`: changing mail that isn't a draft, or whole mailbox items.
- `Calendars.ReadWrite.Shared`: other people's calendars.
- `Files.ReadWrite.All`: every file you can reach. Memory needs only your own OneDrive.
- Any application (app-only) permission.
<!-- never-grant:end -->

An adapter or MCP server that asks for any of these is wider than the skill needs. Say no and report it (see `SECURITY.md`).

## When your organisation decides

By default a user can consent for themselves to every scope marked "No" above. Many organisations restrict that, and then even those scopes need an admin:

- **User consent is off.** Only an admin can grant any scope.
- **Verified publishers and low-impact permissions only.** The MCP server or agent app must be from a verified publisher or registered in your tenant, and each scope must be one your admin classified as low impact.
- **The app requires user assignment.** An admin has to consent for it, whatever the scopes.

If the sign-in screen says you need an admin, ask for approval through it if your tenant offers the admin consent workflow, or send IT this page. Ask for the lite set first: three low-risk scopes, none of which can send.

## Where the grant happens

- **Microsoft Graph adapter** (`hosts/graph-mcp.md`): the MCP server or HTTP tool requests these scopes when you sign in. Configure it to request only your mode's set.
- **Copilot Cowork** (`hosts/cowork.md`): Cowork uses Microsoft 365 Copilot's own connectors, and your organisation's Copilot settings decide what it can reach. You don't grant scopes per skill. Gated operations may show an approval card instead.
- **Personal Microsoft accounts** have no Teams scopes. Lite works; pro runs mail and calendar only.
