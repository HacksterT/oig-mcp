"""Prompts submodule — reusable conversation starters.

Prompts appear in the client UI as slash commands / preset starters. Each
prompt module exposes a `register(mcp)` function; this file aggregates them
into `register_prompts(mcp)`.

Planned prompts (added with the tools they drive): an inspection readiness
checklist and an open-recommendation aging brief for leadership.
"""

from __future__ import annotations


def register_prompts(mcp) -> None:
    """Register all prompts with the MCP server. None yet."""
    _ = mcp


__all__ = ["register_prompts"]
