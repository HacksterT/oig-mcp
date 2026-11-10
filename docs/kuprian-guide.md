# Testing Guide for Mike Kuprian

You're the only tester on the MCP server for now. You connect to the copy running on Troy's Mac as a client, so you don't need to clone or run anything, and you don't need a Cloudflare token.

- **Endpoint:** `https://mcp.troymd.com/mcp`
- **Authentication:** `Authorization: Bearer <your token>`
- **Data:** the November 4, 2026 snapshot

## Issuing the token (Troy)

Run this on the Mac, in the `oig-mcp` repo. It creates the token, adds it to `.env`, restarts the MCP server, and copies the token to the clipboard without displaying it.

```bash
cd ~/Projects/mcp-hackathon/oig-mcp
python3 deploy/mcp_clients.py add mkuprian | pbcopy
```

The server is down for a few seconds during the restart, and no other restart step is needed. Paste the token into your message to Mike before copying anything else, because it's only available from the clipboard or `.env` afterward.

To confirm it worked:

```bash
python3 deploy/mcp_clients.py list     # should show mkuprian
curl -s -o /dev/null -w '%{http_code}\n' https://mcp.troymd.com/health     # should show 200
```

To replace the token, for example if it's exposed, run `remove` and then `add`. To end access, run `remove` alone. Each change restarts the server.

```bash
python3 deploy/mcp_clients.py remove mkuprian
python3 deploy/mcp_clients.py add mkuprian | pbcopy
```

## Connecting (Mike)

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

**Claude Desktop** needs a local bridge and Node.js. This route hasn't been tested with this server, so please tell Troy whether it works. Add this to `claude_desktop_config.json`:

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

To check the connection, ask: "Check the OIG dataset status." The answer should give a data date of November 4, 2026. A 401 means the token is wrong, and a 404 usually means the URL is missing `/mcp`.

## What to test

- "Staff left medication carts unlocked in a hallway. Has OIG cited this?"
- "Help me prepare for the next inspection at the VA El Paso Healthcare System."
- "Is communicating test results to patients still a problem?"
- A question from your own work, in your own words.

Check the answers against the linked reports on vaoig.gov. Search is a starting point: in a small test, fewer than half of the top results were relevant.

You'll also be the first person to use this from outside Troy's network, so connection problems are as useful to report as wrong answers.

## What to report

Send Troy the question, the client and model you used, the answer, and what went wrong. These matter most:

- A report number, finding, or link that's wrong or doesn't exist
- A claim the cited report doesn't support
- A count or trend that looks wrong, or that reads more into the data than it shows
- A question it should have answered but couldn't
- Errors, slow responses, or trouble connecting

## What to expect

- **Sensitive information:** don't enter patient information or anything nonpublic. Questions pass through your AI provider, Cloudflare, and Troy's Mac.
- **What's recorded:** throughout the hackathon, including judging, everything the server sees: your token's name, each tool call and its arguments, including your questions, every request it makes to the data API and what came back, and the answer each tool returned. Your conversation with your AI model isn't visible to the server, so it isn't recorded. Records stay on Troy's Mac, are capped at about 1 GB, and are used to see how the tool works and where it goes wrong.
- **Downtime:** everything runs on one Mac. After a reboot, FileVault can keep it down until Troy unlocks the machine. If a tool fails, try again in a minute, and tell Troy if it keeps failing.
- **Limits:** your token can make about two requests a second, with bursts up to 30. A "rate limit exceeded" error clears within seconds.
- **Your token:** keep it out of repos and shared configs. If it's exposed, tell Troy and he'll replace it.
