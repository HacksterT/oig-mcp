# Testing the VA OIG Recommendations Assistant

This MCP server lets an AI assistant answer questions across what the VA Office of Inspector General publishes: 4,410 reports and 15,649 recommendations, as of November 4, 2026. It's a personal test project running on Troy's computer. It isn't a VA or OIG service.

## What you need

- **Endpoint:** `https://mcp.troymd.com/mcp`
- **Your token:** Troy sends you one. It's yours alone, so please don't share it. If it gets exposed, tell Troy and he'll replace it.
- **An MCP client:** one that can send a custom header over HTTP.

## Connect

**Claude Code**

```bash
claude mcp add --transport http oig-mcp https://mcp.troymd.com/mcp \
  --header "Authorization: Bearer YOUR_TOKEN"
```

**Other clients with HTTP and custom headers**

```text
URL:    https://mcp.troymd.com/mcp
Header: Authorization: Bearer YOUR_TOKEN
```

**Claude Desktop** needs a local bridge and Node.js. This route hasn't been tested with this server yet, so please tell Troy whether it works. Add this to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "oig-mcp": {
      "command": "npx",
      "args": ["-y", "mcp-remote", "https://mcp.troymd.com/mcp",
               "--header", "Authorization:${OIG_AUTH}"],
      "env": { "OIG_AUTH": "Bearer YOUR_TOKEN" }
    }
  }
}
```

Connecting from a VA network or VA-furnished device hasn't been tested. Please check that it's allowed before you try.

To check the connection, ask: "Check the OIG dataset status." The answer should give a data date of November 4, 2026.

## What to try

- "Staff left medication carts unlocked in a hallway. Has OIG cited this?"
- "Help me prepare for the next inspection at the VA El Paso Healthcare System."
- "Is communicating test results to patients still a problem?"
- A question from your own work, in your own words.

Check the answers against the linked reports on vaoig.gov. Search is a starting point: in a small test, fewer than half of the top results were relevant.

## What to report

Send Troy the question, the client and model you used, the answer, and what went wrong. These matter most:

- A report number, finding, or link that's wrong or doesn't exist
- A claim the cited report doesn't support
- A count or trend that looks wrong, or that reads more into the data than it shows
- A question it should have answered but couldn't
- Errors, slow responses, or trouble connecting

## What to expect

- **Don't enter patient information or anything nonpublic.** Questions pass through your AI provider, Cloudflare, and Troy's computer. The server only holds public OIG material.
- **What's recorded:** while testing, everything the server sees: your token's name, each tool call and its arguments, including your questions, every request it makes to the data API and what came back, and the answer each tool returned. Your conversation with your AI model isn't visible to the server, so it isn't recorded. Records stay on Troy's Mac, are capped at about 1 GB, and are used to see how the tool works and where it goes wrong.
- **Downtime:** it runs on one computer, so it can go down, and it restarts for a few seconds when testers are added or removed. If a tool fails, try again in a minute. If it keeps failing, tell Troy.
- **Limits:** each token can make about two requests a second, with bursts up to 30. A "rate limit exceeded" error clears within seconds.
