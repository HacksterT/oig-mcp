"""Inbound authentication for the HTTP MCP endpoint.

The caller presents `Authorization: Bearer <token>`, using `MCP_AUTH_TOKEN` or one
of the named tokens in `MCP_CLIENT_TOKENS`. These credentials are separate from the
Cloudflare Access service token used for the data API: they are never forwarded
upstream, and neither kind grants access to the other's hop.
"""

from __future__ import annotations

import hmac
from collections.abc import Mapping

from fastmcp.server.auth import AccessToken, TokenVerifier


class BearerTokenVerifier(TokenVerifier):
    """Accept operator-issued bearer tokens, each tied to a client name."""

    def __init__(self, tokens: Mapping[str, str]) -> None:
        super().__init__()
        self._tokens = {name: token.encode() for name, token in tokens.items()}

    async def verify_token(self, token: str) -> AccessToken | None:
        presented = token.encode()
        client_id = None
        # Compare against every token, so timing doesn't reveal how far the
        # search got.
        for name, expected in self._tokens.items():
            if hmac.compare_digest(presented, expected):
                client_id = name
        if client_id is None:
            return None
        return AccessToken(token=token, client_id=client_id, scopes=[])
