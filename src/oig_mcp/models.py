"""Pydantic models and enums for tool parameters and responses.

Typed parameters give MCP clients a precise schema, which helps the LLM call
tools correctly. Enums cover closed sets of values; models cover structured
inputs and outputs shared across tools.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ResponseFormat(str, Enum):
    """How a tool should shape its return value.

    - JSON     → machine-readable dict/list (best for chaining tool calls)
    - MARKDOWN → human-readable text (best for direct display)
    """

    JSON = "json"
    MARKDOWN = "markdown"


class RecommendationStatus(str, Enum):
    """Recommendation status as VA OIG publishes it."""

    OPEN = "open"
    CLOSED_IMPLEMENTED = "closed-implemented"
    CLOSED_NOT_IMPLEMENTED = "closed-not-implemented"


class PaginationParams(BaseModel):
    """Reusable pagination inputs for list-style tools."""

    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of items to return (1–100).",
    )
    offset: int = Field(
        default=0,
        ge=0,
        description="Number of items to skip from the start of the result set.",
    )


class Provenance(BaseModel):
    """Where a response's data came from and how fresh it is.

    Every tool response carries one of these so the assistant can cite its
    source and warn when the data may be out of date.
    """

    source: str = Field(
        default="VA Office of Inspector General public pages (vaoig.gov)",
        description="Origin of the underlying data.",
    )
    data_as_of: str | None = Field(
        default=None, description="Date the data was collected (YYYY-MM-DD)."
    )
    days_old: int | None = Field(
        default=None, description="Days between data_as_of and today."
    )
    stale: bool | None = Field(
        default=None,
        description="True when the data is older than the configured threshold.",
    )
    source_urls: list[str] = Field(
        default_factory=list, description="vaoig.gov pages backing this response."
    )
