from __future__ import annotations

from loginforce.form_handler import FormHandlerConfig, FormSubmitter
from loginforce.http_client import HttpClient
from loginforce.safety import ScopeGuard


def _make_submitter(live_server):
    client = HttpClient(timeout=2.0, scope_guard=ScopeGuard(), proxies={})
    config = FormHandlerConfig(csrf_field="csrf_token", login_page_url=f"{live_server}/login")
    return FormSubmitter(http_client=client, config=config)


def test_csrf_token_fetched_and_accepted_on_valid_login(live_server):
    submitter = _make_submitter(live_server)
    resp = submitter.submit(f"{live_server}/login", "admin", "correct-horse-battery-staple")
    assert resp.status_code == 200  # redirect to /dashboard was followed
    assert "Welcome back" in resp.text


def test_csrf_token_fetched_and_login_fails_with_wrong_password(live_server):
    submitter = _make_submitter(live_server)
    resp = submitter.submit(f"{live_server}/login", "admin", "wrong-password")
    assert resp.status_code == 200
    assert "Invalid username or password" in resp.text


def test_each_submission_gets_a_fresh_csrf_token(live_server):
    # Two submissions in a row must each fetch their own token (the mock
    # app rotates the session's token on every GET /login) rather than
    # reusing a stale one.
    submitter = _make_submitter(live_server)
    first = submitter.submit(f"{live_server}/login", "admin", "wrong-1")
    second = submitter.submit(f"{live_server}/login", "admin", "wrong-2")
    assert first.status_code == 200
    assert second.status_code == 200
    assert "CSRF token invalid" not in first.text
    assert "CSRF token invalid" not in second.text
