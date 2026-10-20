"""HTTP transport: persistent session, explicit timeouts, scope-checked
redirect following. No retries of authentication attempts — only bounded
retries of transient, pre-response network failures are allowed, and only
where the caller opts in."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from urllib.parse import urljoin, urlparse

import requests

from .safety import ScopeError, ScopeGuard


class NetworkError(Exception):
    """A transport-level failure (DNS, connection, TLS, timeout)."""


class RedirectOutOfScope(Exception):
    """A redirect pointed at a host outside the authorized scope."""

    def __init__(self, location: str):
        super().__init__(f"Redirect target is out of scope: {location}")
        self.location = location


@dataclass
class HttpClient:
    timeout: float
    scope_guard: ScopeGuard
    proxies: dict
    max_redirect_hops: int = 3

    def __post_init__(self) -> None:
        self.session = requests.Session()

    def _check_scope(self, url: str) -> None:
        host = urlparse(url).hostname
        self.scope_guard.check(host)

    def get(self, url: str):
        self._check_scope(url)
        try:
            return self.session.get(
                url, timeout=self.timeout, proxies=self.proxies, allow_redirects=False
            )
        except requests.exceptions.Timeout as exc:
            raise NetworkError(f"Timed out contacting {url}: {exc}") from exc
        except requests.exceptions.SSLError as exc:
            raise NetworkError(f"TLS error contacting {url}: {exc}") from exc
        except requests.exceptions.ConnectionError as exc:
            raise NetworkError(f"Connection error contacting {url}: {exc}") from exc
        except requests.exceptions.RequestException as exc:
            raise NetworkError(f"Request to {url} failed: {exc}") from exc

    def post_form(self, url: str, data: dict):
        self._check_scope(url)
        try:
            resp = self.session.post(
                url, data=data, timeout=self.timeout, proxies=self.proxies, allow_redirects=False
            )
        except requests.exceptions.Timeout as exc:
            raise NetworkError(f"Timed out contacting {url}: {exc}") from exc
        except requests.exceptions.SSLError as exc:
            raise NetworkError(f"TLS error contacting {url}: {exc}") from exc
        except requests.exceptions.ConnectionError as exc:
            raise NetworkError(f"Connection error contacting {url}: {exc}") from exc
        except requests.exceptions.RequestException as exc:
            raise NetworkError(f"Request to {url} failed: {exc}") from exc
        return self._follow_safe_redirects(resp)

    def _follow_safe_redirects(self, resp: requests.Response):
        hops = 0
        while resp.is_redirect and hops < self.max_redirect_hops:
            location = resp.headers.get("Location")
            if not location:
                break
            next_url = urljoin(resp.url, location)
            host = urlparse(next_url).hostname
            try:
                self.scope_guard.check(host)
            except ScopeError:
                # Leave `resp` as the (unfollowed) redirect response. The
                # caller / result detector will see a redirect with no
                # further evidence and should treat it as inconclusive —
                # we never silently expand scope to chase it.
                break
            try:
                resp = self.session.get(
                    next_url, timeout=self.timeout, proxies=self.proxies, allow_redirects=False
                )
            except requests.exceptions.RequestException as exc:
                raise NetworkError(f"Failed following redirect to {next_url}: {exc}") from exc
            hops += 1
        return resp
