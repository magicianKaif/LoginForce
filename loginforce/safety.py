"""Authorization scope and stop-condition controls.

Everything in this module exists to keep the tool from being pointed at
something it hasn't been explicitly told it may touch, and to make sure a
run stops itself rather than relying on the operator to watch it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1", "0.0.0.0"}


class ScopeError(Exception):
    """Raised when a request would leave the authorized target scope."""


@dataclass
class ScopeGuard:
    """Decides whether a given host may be contacted.

    Local hosts (localhost / 127.0.0.1 / ::1 / 0.0.0.0) are always in
    scope, since they're the tool's safe default for controlled testing.
    Any other host must be listed in ``allowed_hosts`` *and* the operator
    must have passed ``confirmed_authorized=True`` (the CLI's
    ``--confirm-authorized`` flag) as an explicit attestation that
    permission to test that host exists.
    """

    allowed_hosts: frozenset[str] = field(default_factory=frozenset)
    confirmed_authorized: bool = False

    @staticmethod
    def is_local(host: Optional[str]) -> bool:
        return (host or "").lower() in LOCAL_HOSTS

    def check(self, host: Optional[str]) -> None:
        if not host:
            raise ScopeError("Request has no resolvable host; refusing to send it.")
        host = host.lower()
        if self.is_local(host):
            return
        if host not in {h.lower() for h in self.allowed_hosts}:
            raise ScopeError(
                f"Host '{host}' is outside the authorized scope "
                f"({sorted(self.allowed_hosts) or 'none configured'}). "
                "Add it with --allow-host if you are authorized to test it."
            )
        if not self.confirmed_authorized:
            raise ScopeError(
                f"Host '{host}' is allow-listed but testing a non-local target "
                "requires --confirm-authorized to attest you have permission."
            )


class StopReason(Enum):
    COMPLETED = "completed"
    LIMIT_REACHED = "request_limit_reached"
    RATE_LIMITED = "rate_limited_by_target"
    TOO_MANY_ERRORS = "too_many_consecutive_errors"
    CREDENTIALS_CONFIRMED = "credentials_confirmed"
    INTERRUPTED = "interrupted_by_user"
    OUT_OF_SCOPE = "target_left_authorized_scope"


@dataclass
class RunController:
    """Tracks attempt counts and decides when a run must stop.

    A stopped run never resumes itself — stopping is a terminal state for
    the process; restarting is a deliberate, separate invocation by the
    operator.
    """

    request_limit: int
    max_consecutive_errors: int = 5

    attempts: int = field(default=0, init=False)
    consecutive_errors: int = field(default=0, init=False)
    rate_limited: bool = field(default=False, init=False)

    def record_attempt(self) -> None:
        self.attempts += 1

    def record_error(self) -> None:
        self.consecutive_errors += 1

    def record_non_error(self) -> None:
        self.consecutive_errors = 0

    def record_rate_limit_signal(self) -> None:
        self.rate_limited = True

    def should_stop(self) -> Optional[StopReason]:
        if self.rate_limited:
            return StopReason.RATE_LIMITED
        if self.consecutive_errors >= self.max_consecutive_errors:
            return StopReason.TOO_MANY_ERRORS
        if self.attempts >= self.request_limit:
            return StopReason.LIMIT_REACHED
        return None
