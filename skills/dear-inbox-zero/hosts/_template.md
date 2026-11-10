# Adapter template

Copy to `hosts/<your-host>.md`, fill the **Tool** column with your agent's tools, then set `config/host.json` and run `doctor`.

<!-- adapter-ops:begin -->
| Operation | Tool | Notes |
|---|---|---|
| `me` | | address, timezone, working hours |
| `mail.list` | | inbox since a timestamp, metadata only, paged |
| `mail.meta` | | metadata for given ids |
| `mail.body` | | one message body |
| `mail.sent` | | sent items since a timestamp (signals) |
| `mail.tag` | | append a category |
| `mail.read` | | mark read |
| `mail.flag` | | set / clear a follow-up flag |
| `mail.reply_draft` | | create a reply draft from an HTML/Markdown file |
| `mail.categories` | | list / create master categories |
| `cal.view` | | events in a window, with my response |
| `cal.accept` | | accept one event or occurrence |
| `teams.needs_response` | | chats and @mentions since a timestamp |
| `teams.thread` | | last messages of one thread |
| `teams.my_replies` | | the user's own posts since a timestamp (signals) |
| `store.list` | | list a OneDrive folder |
| `store.read` | | download a OneDrive file |
| `store.write` | | upload a new OneDrive file (never overwrite facts) |
| `ask` | | ask the user one question with options |
| `run_python` | | run the engine (optional; prose mode without it) |
| `schedule` | | create a recurring prompt (daily run, weekly learn); list existing first |
<!-- adapter-ops:end -->

## Forbidden (must not be mapped)

`mail.send`, `mail.forward`, `mail.delete`, `mail.move`, `cal.decline`, `teams.post`.
