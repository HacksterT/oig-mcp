"""Full traces of tool calls and resource reads, on through judging.

Each tool call gets a trace ID, sent to the data API as X-Trace-Id with the client
and tool names, so the API's own trace of each request can be matched to the call.
A resource read is traced as tool read_resource, with its URI as the argument.
When MCP_TRACE_DIR is set, the call is also written as one JSON file: who called,
the arguments, every API request it made, and the result. That includes what
people searched for, so anyone connected must be told: vaoig://about says so.
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from contextvars import ContextVar, Token
from datetime import UTC, datetime
from itertools import islice
from pathlib import Path
from typing import Any

# Arguments are traced before validation, so a caller could send megabytes that the
# tool then refuses. Bounding each value and each record keeps one client from
# flushing everyone's traces past the store's cap. Real results are kept whole: the
# largest seen is about 180 KB (a facility profile), so the record cap sits well
# above any real answer and only stops what no tool would return.
MAX_TRACED_STRING = 2_000
MAX_TRACED_ITEMS = 100
MAX_RECORD_BYTES = 1_000_000


def bounded(value: Any) -> Any:
    """A copy of an argument with long strings and lists cut, and marked."""
    if isinstance(value, str):
        if len(value) > MAX_TRACED_STRING:
            return value[:MAX_TRACED_STRING] + f"...[{len(value)} chars]"
        return value
    if isinstance(value, dict):
        items = islice(value.items(), MAX_TRACED_ITEMS)
        return {str(k)[:100]: bounded(v) for k, v in items}
    if isinstance(value, list | tuple):
        kept = [bounded(v) for v in value[:MAX_TRACED_ITEMS]]
        if len(value) > MAX_TRACED_ITEMS:
            kept.append(f"...[{len(value)} items]")
        return kept
    return value


_current: ContextVar[dict[str, Any] | None] = ContextVar("oig_trace", default=None)


def start(client: str, tool: str, arguments: Any) -> tuple[dict[str, Any], Token]:
    """Begin a trace for one tool call. Pass the token to finish()."""
    record = {
        "trace_id": uuid.uuid4().hex[:16],
        "time": datetime.now(UTC).isoformat(timespec="milliseconds"),
        "client": client,
        "tool": tool,
        "arguments": bounded(arguments),
        "api_calls": [],
    }
    return record, _current.set(record)


def current_id() -> str | None:
    """The trace ID of the call in progress, if there is one."""
    record = _current.get()
    return record["trace_id"] if record else None


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


def _encode(record: dict[str, Any]) -> bytes:
    return json.dumps(record, default=str, ensure_ascii=False, indent=1).encode()


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
        data = _encode(record)
        if len(data) > MAX_RECORD_BYTES:
            # Keep who asked what and how it went; drop the oversized result.
            record = {**record, "result": f"[omitted: {len(data)} bytes]"}
            data = _encode(record)
        day = self.directory / record["time"][:10]
        stamp = record["time"][11:23].replace(":", "").replace(".", "-")
        name = f"{stamp}-{record['trace_id']}-{record['tool']}.json"
        with self._lock:
            # Traces hold what people asked, so only the server's user may read them.
            day.mkdir(mode=0o700, parents=True, exist_ok=True)
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
            descriptor = os.open(day / name, flags, 0o600)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(data)
            if self._total is None:
                self._total = sum(f.stat().st_size for f in self._files())
            else:
                self._total += len(data)
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
