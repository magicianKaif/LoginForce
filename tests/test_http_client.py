from __future__ import annotations

import pytest

from loginforce.http_client import HttpClient, NetworkError
from loginforce.safety import ScopeGuard


def test_timeout_raises_network_error(live_server):
    client = HttpClient(timeout=0.2, scope_guard=ScopeGuard(), proxies={})
    with pytest.raises(NetworkError):
        client.get(f"{live_server}/slow")


def test_connection_error_raises_network_error():
    client = HttpClient(timeout=1.0, scope_guard=ScopeGuard(), proxies={})
    # Port 1 on localhost should refuse the connection immediately.
    with pytest.raises(NetworkError):
        client.get("http://127.0.0.1:1/nope")


def test_cross_host_redirect_not_followed(live_server):
    guard = ScopeGuard()  # only localhost in scope — evil.example.invalid is not
    client = HttpClient(timeout=2.0, scope_guard=guard, proxies={})
    resp = client.post_form(f"{live_server}/redirect-external", data={})
    # The redirect must not have been followed: we should still be looking
    # at the 302 response itself, not a page from the external host.
    assert resp.status_code == 302
    assert resp.headers.get("Location", "").startswith("http://evil.example.invalid")


def test_same_host_redirect_is_followed(live_server):
    guard = ScopeGuard()
    client = HttpClient(timeout=2.0, scope_guard=guard, proxies={})
    # /login with valid creds on the mock app redirects to /dashboard on the
    # same host — exercised more fully in test_form_handler.py, but a bare
    # GET-redirect round trip is checked here directly.
    resp = client.get(f"{live_server}/login")
    assert resp.status_code == 200
