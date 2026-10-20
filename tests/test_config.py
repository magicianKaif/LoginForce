from __future__ import annotations

from pathlib import Path

import pytest

from loginforce.config import ConfigError, RunConfig


def _write_passwords(tmp_path: Path, lines=("pw1", "pw2")) -> Path:
    p = tmp_path / "passwords.txt"
    p.write_text("\n".join(lines) + "\n")
    return p


def test_valid_config(tmp_path):
    pw_file = _write_passwords(tmp_path)
    cfg = RunConfig(
        target_url="http://127.0.0.1:5000/login",
        username="admin",
        password_list_path=pw_file,
        success_contains=["Welcome"],
    )
    assert cfg.target_host == "127.0.0.1"


def test_invalid_url_rejected(tmp_path):
    pw_file = _write_passwords(tmp_path)
    with pytest.raises(ConfigError):
        RunConfig(
            target_url="not-a-url",
            username="admin",
            password_list_path=pw_file,
            success_contains=["Welcome"],
        )


def test_missing_password_file_rejected(tmp_path):
    with pytest.raises(ConfigError):
        RunConfig(
            target_url="http://127.0.0.1:5000/login",
            username="admin",
            password_list_path=tmp_path / "does-not-exist.txt",
            success_contains=["Welcome"],
        )


def test_empty_password_file_rejected(tmp_path):
    pw_file = _write_passwords(tmp_path, lines=())
    with pytest.raises(ConfigError):
        RunConfig(
            target_url="http://127.0.0.1:5000/login",
            username="admin",
            password_list_path=pw_file,
            success_contains=["Welcome"],
        )


def test_missing_success_indicator_rejected(tmp_path):
    pw_file = _write_passwords(tmp_path)
    with pytest.raises(ConfigError):
        RunConfig(
            target_url="http://127.0.0.1:5000/login",
            username="admin",
            password_list_path=pw_file,
            # no success_contains / success_status_codes / success_redirect_contains
        )


def test_overlapping_success_failure_markers_rejected(tmp_path):
    pw_file = _write_passwords(tmp_path)
    with pytest.raises(ConfigError):
        RunConfig(
            target_url="http://127.0.0.1:5000/login",
            username="admin",
            password_list_path=pw_file,
            success_contains=["Welcome"],
            failure_contains=["Welcome"],
        )


def test_request_limit_hard_max_enforced(tmp_path):
    pw_file = _write_passwords(tmp_path)
    with pytest.raises(ConfigError):
        RunConfig(
            target_url="http://127.0.0.1:5000/login",
            username="admin",
            password_list_path=pw_file,
            success_contains=["Welcome"],
            request_limit=999_999,
        )


def test_default_tor_proxy_rejected(tmp_path):
    pw_file = _write_passwords(tmp_path)
    with pytest.raises(ConfigError):
        RunConfig(
            target_url="http://127.0.0.1:5000/login",
            username="admin",
            password_list_path=pw_file,
            success_contains=["Welcome"],
            proxy_url="socks5h://127.0.0.1:9050",
        )
