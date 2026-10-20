from __future__ import annotations

import pytest

from loginforce.safety import RunController, ScopeError, ScopeGuard, StopReason


def test_localhost_always_in_scope():
    guard = ScopeGuard()
    guard.check("127.0.0.1")
    guard.check("localhost")


def test_unlisted_remote_host_rejected():
    guard = ScopeGuard()
    with pytest.raises(ScopeError):
        guard.check("example.com")


def test_allowlisted_host_without_confirmation_rejected():
    guard = ScopeGuard(allowed_hosts=frozenset({"example.com"}), confirmed_authorized=False)
    with pytest.raises(ScopeError):
        guard.check("example.com")


def test_allowlisted_host_with_confirmation_allowed():
    guard = ScopeGuard(allowed_hosts=frozenset({"example.com"}), confirmed_authorized=True)
    guard.check("example.com")  # should not raise


def test_empty_host_rejected():
    guard = ScopeGuard()
    with pytest.raises(ScopeError):
        guard.check(None)


def test_request_limit_stop_condition():
    controller = RunController(request_limit=3)
    for _ in range(3):
        controller.record_attempt()
        controller.record_non_error()
    assert controller.should_stop() == StopReason.LIMIT_REACHED


def test_consecutive_error_stop_condition():
    controller = RunController(request_limit=100, max_consecutive_errors=2)
    controller.record_error()
    controller.record_error()
    assert controller.should_stop() == StopReason.TOO_MANY_ERRORS


def test_error_streak_reset_by_success():
    controller = RunController(request_limit=100, max_consecutive_errors=2)
    controller.record_error()
    controller.record_non_error()
    controller.record_error()
    assert controller.should_stop() is None


def test_rate_limit_stop_condition():
    controller = RunController(request_limit=100)
    controller.record_rate_limit_signal()
    assert controller.should_stop() == StopReason.RATE_LIMITED
