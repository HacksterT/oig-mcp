#!/usr/bin/env python3
"""Add, list, or remove the named bearer tokens that can call /mcp.

    python3 deploy/mcp_clients.py add alice
    python3 deploy/mcp_clients.py list
    python3 deploy/mcp_clients.py remove alice

Tokens are kept in MCP_CLIENT_TOKENS in `.env`. A change recreates the container,
which takes the server down for a few seconds. `add` prints the new token once, so
run it in your own terminal and not through a tool that records its output. `list`
prints names only. MCP_AUTH_TOKEN isn't managed here.
"""

from __future__ import annotations

import argparse
import os
import re
import secrets
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEY = "MCP_CLIENT_TOKENS"
NAME = re.compile(r"[a-z0-9][a-z0-9_-]*")
HEALTH_URL = "http://127.0.0.1:8000/health"
HEALTH_TIMEOUT_SECONDS = 60


def read_clients(env_file: Path) -> dict[str, str]:
    for line in env_file.read_text().splitlines():
        if line.startswith(f"{KEY}="):
            entries = line.split("=", 1)[1].split(",")
            return dict(entry.split(":", 1) for entry in entries if entry)
    return {}


def write_clients(env_file: Path, clients: dict[str, str]) -> None:
    """Replace the file atomically, readable only by its owner."""
    lines = [
        line
        for line in env_file.read_text().splitlines()
        if not line.startswith(f"{KEY}=")
    ]
    if clients:
        lines.append(f"{KEY}=" + ",".join(f"{n}:{t}" for n, t in clients.items()))
    with tempfile.NamedTemporaryFile(
        "w", dir=env_file.parent, delete=False, prefix=".env."
    ) as handle:
        handle.write("\n".join(lines) + "\n")
    os.chmod(handle.name, 0o600)
    os.replace(handle.name, env_file)


def restart_server() -> bool:
    """Recreate the container so it reads the new list, then wait for it."""
    subprocess.run(
        ["docker", "compose", "up", "-d", "oig-mcp"],
        cwd=ROOT,
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    deadline = time.monotonic() + HEALTH_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(HEALTH_URL, timeout=2) as response:
                if response.status == 200:
                    return True
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(1)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("action", choices=["add", "list", "remove"])
    parser.add_argument("name", nargs="?")
    parser.add_argument("--env-file", type=Path, default=ROOT / ".env")
    parser.add_argument("--no-restart", action="store_true")
    args = parser.parse_args()

    clients = read_clients(args.env_file)

    if args.action == "list":
        print("\n".join(clients) if clients else "No named clients.")
        return 0

    if not args.name or not NAME.fullmatch(args.name):
        parser.error("give a name using lowercase letters, digits, - or _")
    if args.name == "mcp-client":
        parser.error("mcp-client is reserved for MCP_AUTH_TOKEN")

    token = None
    if args.action == "add":
        if args.name in clients:
            parser.error(f"{args.name} already has a token; remove it first")
        token = secrets.token_hex(32)
        clients[args.name] = token
    else:
        if args.name not in clients:
            parser.error(f"{args.name} has no token")
        del clients[args.name]

    write_clients(args.env_file, clients)
    healthy = args.no_restart or restart_server()

    if token:
        print(token)
    if not healthy:
        print("The server didn't report healthy after the restart.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
