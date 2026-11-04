"""Smoke tests for the VA OIG Recommendations MCP server.

These verify the server imports and every submodule registers without error.
Add functional tests for your own tools as you build them.
"""

from __future__ import annotations

import pytest
from fastmcp import FastMCP

from oig_mcp.app import mcp
from oig_mcp.config import settings


def test_server_is_importable():
    assert mcp is not None


def test_server_has_name():
    assert mcp.name == "VA OIG Recommendations"


def test_default_transport_is_stdio():
    """Guard against accidentally shipping with a non-stdio default."""
    assert settings.mcp_transport == "stdio"


def test_tools_register_without_error():
    from oig_mcp.tools import register_tools

    register_tools(FastMCP("test"))  # must not raise


def test_prompts_register_without_error():
    from oig_mcp.prompts import register_prompts

    register_prompts(FastMCP("test"))  # must not raise


def test_resources_register_without_error():
    from oig_mcp.resources import register_resources

    register_resources(FastMCP("test"))  # must not raise


def test_routes_register_without_error():
    from oig_mcp.routes import register_routes

    register_routes(FastMCP("test"))  # must not raise


@pytest.mark.asyncio
async def test_dataset_status_tool_is_discoverable():
    """The dataset status tool should be registered and discoverable."""
    tools = await mcp.list_tools()
    tool_names = {t.name for t in tools}
    assert "vaoig_get_dataset_status" in tool_names


@pytest.mark.asyncio
async def test_about_resource_is_discoverable():
    resources = await mcp.list_resources()
    assert "vaoig://about" in {str(r.uri) for r in resources}
