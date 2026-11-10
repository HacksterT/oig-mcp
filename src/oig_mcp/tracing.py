"""Full tool-call traces, on through the hackathon including judging.

Each tool call gets a trace ID, sent to the data API as X-Trace-Id with the client
and tool names, so the API's own trace of each request can be matched to the call.
When MCP_TRACE_DIR is set, the call is also written as one JSON file: who called,
the arguments, every API request it made, and the result. That includes what
people searched for, so anyone connected must be told: vaoig://about says so.
"""

from __future__ import annotations

import json
import threading
import uuid
from contextvars import ContextVar, Token
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_current: ContextVar[dict[str, Any] | None] = ContextVar("oig_trace", default=None)


def start(client: str, tool: str, arguments: Any) -> tuple[dict[str, Any], Token]:
    """Begin a trace for one tool call. Pass the token to finish()."""
    record = {
        "trace_id": uuid.uuid4().hex[:16],
        "time": datetime.now(UTC).isoformat(timespec="milliseconds"),
        "client": client,
        "tool": tool,
        "arguments": arguments,
        "api_calls": [],
    }
    return record, _current.set(record)


def finish(token: Token) -> None:
    _current.reset(token)


def headers() -> dict[str, str]:
    """Headers that tie an API request to the tool call that made it."""
    record = _current.get()
    if record is None:
        return {}
    return {
        "X-Trace-Id": record["trace_id"],
        "X-OIG-Client": record["client"],
        "X-OIG-Tool": record["tool"],
    }


def api_call(
    path: str, params: Any, status: int | None, ms: int, size: int, error: str | None
) -> None:
    record = _current.get()
    if record is not None:
        record["api_calls"].append(
            {
                "path": path,
                "params": params,
                "status": status,
                "ms": ms,
                "bytes": size,
                "error": error,
            }
        )


class TraceStore:
    """One file per call in a folder per day, oldest removed past the cap."""

    def __init__(self, directory: Path, max_bytes: int) -> None:
        self.directory = directory
        self.max_bytes = max_bytes
        self._lock = threading.Lock()
        self._total: int | None = None

    def _files(self) -> list[Path]:
        return sorted(self.directory.glob("*/*.json"))

    def write(self, record: dict[str, Any]) -> None:
        data = json.dumps(record, default=str, ensure_ascii=False, indent=1)
        day = self.directory / record["time"][:10]
        stamp = record["time"][11:23].replace(":", "").replace(".", "-")
        name = f"{stamp}-{record['trace_id']}-{record['tool']}.json"
        with self._lock:
            day.mkdir(parents=True, exist_ok=True)
            (day / name).write_text(data)
            if self._total is None:
                self._total = sum(f.stat().st_size for f in self._files())
            else:
                self._total += len(data.encode())
            if self._total > self.max_bytes:
                self._prune()

    def _prune(self) -> None:
        target = self.max_bytes * 0.9
        for path in self._files():
            if self._total <= target:
                break
            size = path.stat().st_size
            path.unlink(missing_ok=True)
            self._total -= size
        for day in self.directory.iterdir():
            if day.is_dir() and not any(day.iterdir()):
                day.rmdir()
