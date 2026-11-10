# GitHub Copilot with Microsoft Graph

This guide uses the Graph adapter in `skills/dear-inbox-zero/hosts/graph-mcp.md`
with GitHub Copilot in VS Code agent mode or the Copilot CLI. You need a
Microsoft Graph MCP server that supports delegated OAuth and can expose the
operations in that adapter. Copilot does not provide a Microsoft Graph server;
choose and configure one that meets these requirements.

## Permissions and safety

Grant only these delegated Microsoft Graph scopes, and only if the matching
channels are enabled:

- `User.Read`
- `Mail.ReadWrite`
- `Calendars.ReadWrite`
- `Chat.Read`
- `ChannelMessage.Read.All`
- `Files.ReadWrite`

The server should request consent interactively and act as the signed-in user.
Do not put access tokens, tenant IDs, or application IDs in a checked-in MCP
configuration. Do not grant `Mail.Send` or `ChatMessage.Send`.

Expose only the adapter's operation-specific tools. Do not expose a generic
arbitrary-Graph-request tool, or tools for sending, forwarding, deleting,
moving, declining, or posting. In particular, accepting an event is allowed
only as described by the adapter and the skill's confirmed-rule safeguards.
Use tool allowlists where the host supports them.

## VS Code agent mode

1. Install the skill in `.github/skills/dear-inbox-zero/` in your workspace, or
   another Agent Skills folder recognized by your VS Code setup.
2. Create `.vscode/mcp.json` and replace the URL placeholder with the endpoint
   for your delegated-auth Graph MCP server:

   ```json
   {
     "servers": {
       "microsoft-graph": {
         "type": "http",
         "url": "https://<graph-mcp-host>/<mcp-path>"
       }
     }
   }
   ```

   The server must implement an OAuth flow supported by VS Code. Keep
   credentials in that flow, not in this file. Review the server's tools and
   approve only the safe operation-specific tools required by the adapter.
3. Open the workspace in VS Code, trust it only if appropriate, and enable the
   configured MCP server when prompted. Sign in through the server's delegated
   OAuth flow.
4. Set `skills/dear-inbox-zero/config/host.json` in the installed skill folder
   to:

   ```json
   { "host": "github-copilot", "adapter": "hosts/graph-mcp.md" }
   ```

5. Run `python <skill-folder>/engine/dear_engine.py doctor --skill-dir <skill-folder>`.
   Confirm the server exposes the mappings in `hosts/graph-mcp.md`, then ask
   Copilot to perform a dry run with synthetic or redacted data before using
   real mailbox data.

See the [VS Code MCP configuration reference](https://code.visualstudio.com/docs/agents/reference/mcp-configuration)
for host-specific settings.

## Copilot CLI

Install the skill in a CLI-discovered Agent Skills folder, such as
`.github/skills/dear-inbox-zero/` for the workspace. Configure the Graph MCP
server in the CLI's MCP configuration file (commonly
`~/.copilot/mcp-config.json`):

```json
{
  "mcpServers": {
    "microsoft-graph": {
      "type": "http",
      "url": "https://<graph-mcp-host>/<mcp-path>",
      "tools": [
        "<tool-for-me-and-mailbox-settings>",
        "<tool-for-mail-read-and-metadata>",
        "<tool-for-mail-category-read-and-write>",
        "<tool-for-mail-flag-and-read-state>",
        "<tool-for-reply-draft-creation>",
        "<tool-for-calendar-view-and-confirmed-accept>",
        "<tool-for-teams-chat-and-mention-read>",
        "<tool-for-onedrive-file-read-and-write>"
      ]
    }
  }
}
```

Replace each tool placeholder with the exact safe tool name published by your
server; these are examples of tool groups, not standard Graph MCP tool names.
Do not allowlist a tool that can also send, forward, delete, move, decline, or
post. If the server requires authentication, use its delegated OAuth flow and
keep credentials out of the config file. Confirm the CLI's current MCP
configuration format and OAuth support before connecting.

Set `config/host.json` as shown above, run `doctor`, inspect the server's
available tools, and perform a dry run with synthetic or redacted data. A
successful local `doctor` check does not verify that a particular server or
Copilot installation works.

See [Configure MCP servers for your repository](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/configure-mcp-servers)
for GitHub's MCP security guidance. Repository-level MCP configuration is
separate from local VS Code and CLI configuration.
