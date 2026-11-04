"""Inbound authentication for the HTTP MCP endpoint.

The caller presents `Authorization: Bearer <MCP_AUTH_TOKEN>`. This credential is
separate from the Cloudflare Access service token used for the data API: it is
never forwarded upstream, and neither one grants access to the other's hop.
"""

from __future__ import annotations

import hmac

from fastmcp.server.auth import AccessToken, TokenVerifier


class SharedTokenVerifier(TokenVerifier):
    """Accept one operator-issued bearer token, compared in constant time."""

    def __init__(self, expected_token: str) -> None:
        super().__init__()
        self._expected = expected_token.encode()

    async def verify_token(self, token: str) -> AccessToken | None:
        if not hmac.compare_digest(token.encode(), self._expected):
            return None
        return AccessToken(token=token, client_id="mcp-client", scopes=[])
