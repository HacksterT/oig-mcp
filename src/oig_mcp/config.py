"""Server configuration loaded from environment variables or a .env file.

Every field can be overridden by an environment variable of the same name
(upper- or lower-case). Copy `.env.example` to `.env` for local development.
"""

from __future__ import annotations

from urllib.parse import urlsplit

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
_MIN_AUTH_TOKEN_LENGTH = 32


class Settings(BaseSettings):
    """MCP server settings. Override any field via environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
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
