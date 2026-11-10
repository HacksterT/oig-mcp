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


def _undescribed(schema: dict, path: str) -> list[str]:
    """Paths of properties without a description, including inside nested objects."""
    missing = []
    for name, prop in schema.get("properties", {}).items():
        if not prop.get("description"):
            missing.append(f"{path}.{name}")
        for arm in prop.get("anyOf", []):
            missing += _undescribed(arm, f"{path}.{name}")
        missing += _undescribed(prop, f"{path}.{name}")
    for model, definition in schema.get("$defs", {}).items():
        missing += _undescribed(definition, f"{path}.{model}")
    return missing


async def test_every_tool_parameter_has_a_description():
    """A model fills parameters from their descriptions, so none may be blank."""
    missing = []
    for tool in await mcp.list_tools():
        missing += _undescribed(tool.parameters, tool.name)
    assert missing == []


@pytest.mark.parametrize(
    ("tool", "arguments"),
    [
        ("vaoig_get_report", {"node_id": 0}),
        ("vaoig_get_report", {"report_number": "x" * 31}),
        ("vaoig_find_systemic_clusters", {"cluster_id": -1}),
        ("vaoig_find_systemic_clusters", {"active_since": 26}),
        ("vaoig_search_findings", {"question": "carts", "filters": {"node_id": 0}}),
    ],
)
async def test_out_of_range_arguments_are_refused(tool, arguments):
    from fastmcp import Client
    from fastmcp.exceptions import ToolError

    async with Client(mcp) as client:
        with pytest.raises(ToolError):
            await client.call_tool(tool, arguments)
