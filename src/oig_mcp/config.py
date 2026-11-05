"""Server configuration loaded from environment variables or a .env file.

Every field can be overridden by an environment variable of the same name
(upper- or lower-case). Copy `.env.example` to `.env` for local development.
"""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
_MIN_AUTH_TOKEN_LENGTH = 32
_CLIENT_NAME = re.compile(r"[a-z0-9][a-z0-9_-]*")
# The client name given to MCP_AUTH_TOKEN, so no named token may use it.
_PRIMARY_CLIENT = "mcp-client"


def _parse_client_tokens(value: str) -> dict[str, str]:
    """Read `name:token,name:token`. Errors name the client, never the token."""
    tokens: dict[str, str] = {}
    for entry in filter(None, (part.strip() for part in value.split(","))):
        # Without a separator, the whole entry could be a bare token.
        name, separator, token = entry.partition(":")
        if not separator or not _CLIENT_NAME.fullmatch(name):
            raise ValueError("MCP_CLIENT_TOKENS entries must look like name:token")
        if name == _PRIMARY_CLIENT:
            raise ValueError(f"MCP_CLIENT_TOKENS can't use the name {_PRIMARY_CLIENT}")
        if name in tokens:
            raise ValueError(f"MCP_CLIENT_TOKENS lists {name} twice")
        if len(token) < _MIN_AUTH_TOKEN_LENGTH:
            raise ValueError(
                f"MCP_CLIENT_TOKENS: the token for {name} must be at least "
                f"{_MIN_AUTH_TOKEN_LENGTH} characters"
            )
        tokens[name] = token
    return tokens


class Settings(BaseSettings):
    """MCP server settings. Override any field via environment variables."""

    # Token settings would otherwise appear in validation errors, and so in logs.
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )

    # ── Transport ─────────────────────────────────────────────────────────────
    # "stdio"           — local subprocess (Claude Desktop / Claude Code / Zed)
    # "streamable-http" — remote HTTP server (containers, cloud deploys)
    #
    # app.py also auto-selects HTTP when the platform injects PORT (IBM Code
    # Engine does), so you usually do NOT need to set this on a cloud host.
    mcp_transport: str = "stdio"
    mcp_host: str = "0.0.0.0"
    mcp_port: int = 8000

    # Bearer token callers must present to /mcp. Required to serve over HTTP;
    # unused over stdio. Not related to the Cloudflare Access token below.
    mcp_auth_token: str = ""

    # Optional tokens for other clients, as `name:token,name:token`, so one can be
    # removed without affecting the rest. deploy/mcp_clients.py manages this list.
    mcp_client_tokens: str = ""

    # Optional file for the usage log, which also goes to stderr. It records the
    # client, tool, outcome, and duration of each call, never the arguments.
    mcp_usage_log: str = ""

    # Full tool-call traces for closed testing (tracing.py): arguments, API calls,
    # and results. Empty turns them off. Keep them off for public use.
    mcp_trace_dir: str = ""
    mcp_trace_max_mb: int = 400

    # ── OIG data API (served by the oig-data-source repository) ───────────────
    # The one outbound origin this server calls. Operator-controlled: never
    # taken from a tool argument. Defaults to the local oig-data-source container.
    oig_data_api_base_url: str = "http://127.0.0.1:8787/v1/"

    # Cloudflare Access service token for the hosted data API. Leave both empty
    # for a local API; when set, they are sent as CF-Access-Client-Id and
    # CF-Access-Client-Secret on every request.
    cf_access_client_id: str = ""
    cf_access_client_secret: str = ""

    # Responses flag data older than this many days as stale.
    stale_after_days: int = 30

    @field_validator("mcp_auth_token")
    @classmethod
    def _validate_auth_token(cls, value: str) -> str:
        """Reject tokens short enough to guess; empty means not configured."""
        if value and len(value) < _MIN_AUTH_TOKEN_LENGTH:
            raise ValueError(
                f"MCP_AUTH_TOKEN must be at least {_MIN_AUTH_TOKEN_LENGTH} characters"
            )
        return value

    @field_validator("mcp_client_tokens")
    @classmethod
    def _validate_client_tokens(cls, value: str) -> str:
        _parse_client_tokens(value)
        return value

    @model_validator(mode="after")
    def _require_distinct_tokens(self) -> Settings:
        """Removing a client must end its access, so no two may share a token."""
        tokens = list(self.inbound_tokens().values())
        if len(tokens) != len(set(tokens)):
            raise ValueError("MCP tokens must all be different")
        return self

    def inbound_tokens(self) -> dict[str, str]:
        """Every bearer token /mcp accepts, by client name."""
        primary = {_PRIMARY_CLIENT: self.mcp_auth_token} if self.mcp_auth_token else {}
        return primary | _parse_client_tokens(self.mcp_client_tokens)

    @field_validator("oig_data_api_base_url")
    @classmethod
    def _validate_base_url(cls, value: str) -> str:
        """Require https (except for a local API) and a trailing slash."""
        parts = urlsplit(value)
        host = (parts.hostname or "").lower()
        if parts.scheme not in {"http", "https"} or not host:
            raise ValueError("OIG_DATA_API_BASE_URL must be an http(s) URL")
        if parts.scheme == "http" and host not in _LOCAL_HOSTS:
            raise ValueError("OIG_DATA_API_BASE_URL must use https unless local")
        if parts.username or parts.password or parts.query or parts.fragment:
            raise ValueError(
                "OIG_DATA_API_BASE_URL must not carry credentials, query, or fragment"
            )
        return value if value.endswith("/") else value + "/"


settings = Settings()
