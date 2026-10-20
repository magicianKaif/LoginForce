from __future__ import annotations

from pathlib import Path

import pytest

from loginforce import cli


def _pw_file(tmp_path: Path, lines: list[str]) -> Path:
    p = tmp_path / "passwords.txt"
    p.write_text("\n".join(lines) + "\n")
    return p


def _base_args(live_server, tmp_path, pw_file, extra=None):
    args = [
        "-u", f"{live_server}/login",
        "-U", "admin",
        "-P", str(pw_file),
        "--login-page-url", f"{live_server}/login",
        "--csrf-field", "csrf_token",
        "--success-redirect-contains", "/dashboard",
        "--failure-contains", "Invalid username or password",
        "--delay", "0",
        "--output-dir", str(tmp_path / "reports"),
        "--no-color",
    ]
    if extra:
        args += extra
    return args


def test_dry_run_exits_ok(live_server, tmp_path):
    pw_file = _pw_file(tmp_path, ["irrelevant"])
    args = _base_args(live_server, tmp_path, pw_file, extra=["--dry-run"])
    assert cli.run(args) == cli.EXIT_OK


def test_active_run_finds_credentials(live_server, tmp_path):
    pw_file = _pw_file(tmp_path, ["wrong-1", "correct-horse-battery-staple", "wrong-2"])
    args = _base_args(live_server, tmp_path, pw_file, extra=["--limit", "10"])
    code = cli.run(args)
    assert code == cli.EXIT_OK
    reports = list((tmp_path / "reports").glob("*.json"))
    assert len(reports) == 1


def test_active_run_confirms_no_valid_credentials(live_server, tmp_path):
    pw_file = _pw_file(tmp_path, ["wrong-1", "wrong-2", "wrong-3"])
    args = _base_args(live_server, tmp_path, pw_file, extra=["--limit", "10"])
    code = cli.run(args)
    # All three attempts should confirm FAILURE (not inconclusive), and no
    # success was found among them — but the run completed its full list,
    # so this is a conclusive, non-early-stop result.
    assert code == cli.EXIT_OK


def test_request_limit_stops_run_early(live_server, tmp_path):
    pw_file = _pw_file(tmp_path, ["wrong-1", "wrong-2", "wrong-3", "wrong-4", "wrong-5"])
    args = _base_args(live_server, tmp_path, pw_file, extra=["--limit", "2"])
    code = cli.run(args)
    assert code == cli.EXIT_STOPPED_EARLY


def test_rate_limited_target_stops_run(live_server, tmp_path):
    pw_file = _pw_file(tmp_path, ["a", "b", "c"])
    args = [
        "-u", f"{live_server}/rate-limited",
        "-U", "admin",
        "-P", str(pw_file),
        "--success-contains", "Welcome",
        "--delay", "0",
        "--limit", "10",
        "--output-dir", str(tmp_path / "reports"),
        "--no-color",
    ]
    code = cli.run(args)
    assert code == cli.EXIT_STOPPED_EARLY


def test_out_of_scope_target_rejected(tmp_path):
    pw_file = _pw_file(tmp_path, ["a"])
    args = [
        "-u", "http://example.com/login",
        "-U", "admin",
        "-P", str(pw_file),
        "--success-contains", "Welcome",
        "--output-dir", str(tmp_path / "reports"),
        "--no-color",
    ]
    code = cli.run(args)
    assert code == cli.EXIT_CONFIG_ERROR


def test_allowlisted_host_without_confirmation_rejected(tmp_path):
    pw_file = _pw_file(tmp_path, ["a"])
    args = [
        "-u", "http://example.com/login",
        "-U", "admin",
        "-P", str(pw_file),
        "--success-contains", "Welcome",
        "--allow-host", "example.com",
        "--output-dir", str(tmp_path / "reports"),
        "--no-color",
    ]
    code = cli.run(args)
    assert code == cli.EXIT_CONFIG_ERROR


def test_keyboard_interrupt_stops_cleanly_and_writes_report(live_server, tmp_path, monkeypatch):
    pw_file = _pw_file(tmp_path, ["wrong-1", "wrong-2", "wrong-3"])
    args = _base_args(live_server, tmp_path, pw_file, extra=["--limit", "10"])

    def _raise_interrupt(*_args, **_kwargs):
        raise KeyboardInterrupt()

    monkeypatch.setattr(cli.time, "sleep", _raise_interrupt)
    code = cli.run(args)
    assert code == cli.EXIT_STOPPED_EARLY
    reports = list((tmp_path / "reports").glob("*.json"))
    assert len(reports) == 1
    import json

    data = json.loads(reports[0].read_text())
    assert data["stop_reason"] == "interrupted_by_user"


def test_inconclusive_run_when_indicators_never_match(live_server, tmp_path):
    pw_file = _pw_file(tmp_path, ["wrong-1", "wrong-2"])
    args = [
        "-u", f"{live_server}/login",
        "-U", "admin",
        "-P", str(pw_file),
        "--login-page-url", f"{live_server}/login",
        "--csrf-field", "csrf_token",
        # Indicators that will never appear in this app's responses:
        "--success-contains", "something-that-never-appears",
        "--delay", "0",
        "--limit", "10",
        "--output-dir", str(tmp_path / "reports"),
        "--no-color",
    ]
    code = cli.run(args)
    assert code == cli.EXIT_INCONCLUSIVE
