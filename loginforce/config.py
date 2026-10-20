"""Runtime configuration: parsing, validation, sensible+safe defaults."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

DEFAULT_REQUEST_LIMIT = 25
HARD_MAX_REQUEST_LIMIT = 2000
DEFAULT_TIMEOUT = 10.0
DEFAULT_DELAY = 0.5
DEFAULT_MAX_CONSECUTIVE_ERRORS = 5
DEFAULT_MAX_REDIRECT_HOPS = 3


class ConfigError(ValueError):
    """Raised for invalid or unsafe configuration. Maps to CLI exit code 1."""


def is_valid_url(url: str) -> bool:
    try:
        result = urlparse(url)
    except ValueError:
        return False
    return bool(result.scheme in ("http", "https") and result.netloc)


@dataclass
class RunConfig:
    target_url: str
    username: str
    password_list_path: Path

    username_field: str = "username"
    password_field: str = "password"

    login_page_url: Optional[str] = None  # GET page for cookies/CSRF; defaults to target_url
    csrf_field: Optional[str] = None

    success_contains: list[str] = field(default_factory=list)
    failure_contains: list[str] = field(default_factory=list)
    success_status_codes: list[int] = field(default_factory=list)
    success_redirect_contains: Optional[str] = None

    request_timeout: float = DEFAULT_TIMEOUT
    delay: float = DEFAULT_DELAY
    request_limit: int = DEFAULT_REQUEST_LIMIT
    max_consecutive_errors: int = DEFAULT_MAX_CONSECUTIVE_ERRORS
    max_redirect_hops: int = DEFAULT_MAX_REDIRECT_HOPS

    allow_hosts: frozenset[str] = field(default_factory=frozenset)
    confirm_authorized: bool = False

    proxy_url: Optional[str] = None  # explicit only — never defaulted to Tor or anything else

    dry_run: bool = False
    output_dir: Path = Path("./reports")
    no_color: bool = False

    def __post_init__(self) -> None:
        errors: list[str] = []

        if not is_valid_url(self.target_url):
            errors.append(f"Target URL is not a valid http(s) URL: {self.target_url!r}")

        if not self.username:
            errors.append("Username must not be empty.")

        if not self.password_list_path or not os.fspath(self.password_list_path):
            errors.append("A password list file is required.")
        elif not Path(self.password_list_path).is_file():
            errors.append(f"Password list file not found: {self.password_list_path}")
        else:
            try:
                non_empty = [
                    line
                    for line in Path(self.password_list_path).read_text(
                        encoding="utf-8", errors="replace"
                    ).splitlines()
                    if line.strip()
                ]
            except OSError as exc:
                errors.append(f"Could not read password list file: {exc}")
                non_empty = []
            if not non_empty:
                errors.append(f"Password list file is empty: {self.password_list_path}")

        if self.request_limit <= 0:
            errors.append("request_limit must be a positive integer.")
        if self.request_limit > HARD_MAX_REQUEST_LIMIT:
            errors.append(
                f"request_limit ({self.request_limit}) exceeds the hard maximum "
                f"({HARD_MAX_REQUEST_LIMIT}). Lower it or split the run."
            )

        if self.request_timeout <= 0:
            errors.append("request_timeout must be positive.")
        if self.delay < 0:
            errors.append("delay must not be negative.")

        if not self.success_contains and not self.success_status_codes and not self.success_redirect_contains:
            errors.append(
                "No success indicator configured (--success-contains / "
                "--success-status / --success-redirect). Without one, every "
                "result would be reported as inconclusive, which defeats the "
                "point of the run."
            )

        overlap = set(self.success_contains) & set(self.failure_contains)
        if overlap:
            errors.append(
                f"The same text cannot be both a success and a failure indicator: {sorted(overlap)}"
            )

        if self.proxy_url and "9050" in self.proxy_url and "socks5" in self.proxy_url.lower():
            errors.append(
                "A default Tor-style SOCKS proxy on port 9050 was detected. This "
                "tool does not default to or endorse routing authorized tests "
                "through Tor; pass an explicit, justified proxy only if your "
                "engagement scope requires one."
            )

        if errors:
            raise ConfigError("; ".join(errors))

    @property
    def target_host(self) -> Optional[str]:
        return urlparse(self.target_url).hostname

    @property
    def target_origin(self) -> str:
        parsed = urlparse(self.target_url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def proxies(self) -> dict:
        if not self.proxy_url:
            return {}
        return {"http": self.proxy_url, "https": self.proxy_url}
