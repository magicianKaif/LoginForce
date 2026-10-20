"""Structured, redacted reporting. Passwords never appear in any report —
not in plaintext, not hashed, not partially. Only attempt metadata and
outcomes are recorded."""

from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from . import __version__
from .result_detector import Outcome
from .safety import StopReason

_SECRET_HEADER_NAMES = {"authorization", "cookie", "set-cookie", "x-csrf-token", "x-api-key"}
_SECRET_VALUE_PATTERNS = [
    re.compile(r"(?i)(password|passwd|pwd)=([^&\s]+)"),
]


def redact_headers(headers: dict) -> dict:
    redacted = {}
    for key, value in headers.items():
        redacted[key] = "[REDACTED]" if key.lower() in _SECRET_HEADER_NAMES else value
    return redacted


def redact_text(text: str) -> str:
    for pattern in _SECRET_VALUE_PATTERNS:
        text = pattern.sub(lambda m: f"{m.group(1)}=[REDACTED]", text)
    return text


@dataclass
class Attempt:
    index: int
    timestamp: str
    outcome: str  # Outcome.value, or "error"
    status_code: Optional[int] = None
    elapsed_ms: Optional[float] = None
    error: Optional[str] = None  # redacted-safe message only, never raw password


@dataclass
class Report:
    run_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tool_version: str = __version__
    target_origin: str = ""
    started_at: str = ""
    ended_at: str = ""
    config_summary: dict = field(default_factory=dict)
    request_limit: int = 0
    attempts: list = field(default_factory=list)
    stop_reason: str = ""
    notes: list = field(default_factory=list)

    def start(self) -> None:
        self.started_at = datetime.now(timezone.utc).isoformat()

    def finish(self, stop_reason: StopReason) -> None:
        self.ended_at = datetime.now(timezone.utc).isoformat()
        self.stop_reason = stop_reason.value

    def add_attempt(
        self,
        index: int,
        outcome: Outcome,
        status_code: Optional[int] = None,
        elapsed_ms: Optional[float] = None,
        error: Optional[str] = None,
    ) -> None:
        self.attempts.append(
            Attempt(
                index=index,
                timestamp=datetime.now(timezone.utc).isoformat(),
                outcome=outcome.value if isinstance(outcome, Outcome) else outcome,
                status_code=status_code,
                elapsed_ms=elapsed_ms,
                error=redact_text(error) if error else None,
            )
        )

    def add_note(self, note: str) -> None:
        self.notes.append(note)

    def summary_counts(self) -> dict:
        counts = {"success": 0, "failure": 0, "inconclusive": 0, "error": 0}
        for a in self.attempts:
            counts[a.outcome] = counts.get(a.outcome, 0) + 1
        return counts

    def has_confirmed_success(self) -> bool:
        return any(a.outcome == Outcome.SUCCESS.value for a in self.attempts)

    def all_non_error_inconclusive(self) -> bool:
        non_error = [a for a in self.attempts if a.outcome != "error"]
        return bool(non_error) and all(a.outcome == Outcome.INCONCLUSIVE.value for a in non_error)

    def to_dict(self) -> dict:
        return {
            "run_id": self.run_id,
            "tool_version": self.tool_version,
            "target_origin": self.target_origin,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "config_summary": self.config_summary,
            "request_limit": self.request_limit,
            "attempts_completed": len(self.attempts),
            "summary_counts": self.summary_counts(),
            "stop_reason": self.stop_reason,
            "notes": self.notes,
            "attempts": [a.__dict__ for a in self.attempts],
        }

    def write_json(self, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"loginforce-{self.run_id}.json"
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return path

    def write_markdown(self, output_dir: Path) -> Path:
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"loginforce-{self.run_id}.md"
        counts = self.summary_counts()
        lines = [
            f"# LOGIN FORCE report — {self.run_id}",
            "",
            f"- Tool version: {self.tool_version}",
            f"- Target origin: {self.target_origin}",
            f"- Started: {self.started_at}",
            f"- Ended: {self.ended_at}",
            f"- Stop reason: {self.stop_reason}",
            f"- Request limit: {self.request_limit}",
            f"- Attempts completed: {len(self.attempts)}",
            "",
            "## Outcome summary",
            "",
            f"- Confirmed success: {counts['success']}",
            f"- Confirmed failure: {counts['failure']}",
            f"- Inconclusive: {counts['inconclusive']}",
            f"- Network errors: {counts['error']}",
            "",
            "## Configuration (secrets excluded)",
            "",
        ]
        for k, v in self.config_summary.items():
            lines.append(f"- {k}: {v}")
        if self.notes:
            lines += ["", "## Notes", ""]
            lines += [f"- {n}" for n in self.notes]
        lines += [
            "",
            "## Caveats",
            "",
            "A `success` outcome reflects an application-specific indicator "
            "matching, not an independent confirmation. An `inconclusive` "
            "outcome means the configured indicators did not provide enough "
            "evidence either way — it is not evidence that the application is "
            "secure, nor that it is vulnerable.",
        ]
        path.write_text("\n".join(lines), encoding="utf-8")
        return path
