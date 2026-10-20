from __future__ import annotations

from types import SimpleNamespace

from loginforce.result_detector import DetectorConfig, Outcome, ResultDetector


def _fake_response(text="", status_code=200, headers=None, is_redirect=False, url=""):
    return SimpleNamespace(
        text=text,
        content=text.encode() if text else b"",
        status_code=status_code,
        headers=headers or {},
        is_redirect=is_redirect,
        url=url,
    )


def test_success_marker_detected():
    detector = ResultDetector(DetectorConfig(success_contains=["Welcome back"]))
    resp = _fake_response(text="Welcome back, authenticated user!")
    assert detector.evaluate(resp) == Outcome.SUCCESS


def test_failure_marker_detected():
    detector = ResultDetector(DetectorConfig(failure_contains=["Invalid username or password"]))
    resp = _fake_response(text="Invalid username or password.")
    assert detector.evaluate(resp) == Outcome.FAILURE


def test_no_markers_is_inconclusive():
    detector = ResultDetector(DetectorConfig(success_contains=["Welcome"], failure_contains=["Invalid"]))
    resp = _fake_response(text="Something unrelated happened.")
    assert detector.evaluate(resp) == Outcome.INCONCLUSIVE


def test_both_markers_present_is_inconclusive():
    detector = ResultDetector(DetectorConfig(success_contains=["Welcome"], failure_contains=["Invalid"]))
    resp = _fake_response(text="Welcome, but also: Invalid session state.")
    assert detector.evaluate(resp) == Outcome.INCONCLUSIVE


def test_bare_200_without_markers_is_never_success():
    detector = ResultDetector(DetectorConfig(success_contains=["Welcome"]))
    resp = _fake_response(text="OK", status_code=200)
    assert detector.evaluate(resp) == Outcome.INCONCLUSIVE


def test_status_code_is_only_a_fallback():
    detector = ResultDetector(DetectorConfig(success_status_codes=[302]))
    resp = _fake_response(text="", status_code=302)
    assert detector.evaluate(resp) == Outcome.SUCCESS


def test_redirect_location_match_is_success():
    detector = ResultDetector(DetectorConfig(success_redirect_contains="/dashboard"))
    resp = _fake_response(status_code=302, headers={"Location": "/dashboard"}, is_redirect=True)
    assert detector.evaluate(resp) == Outcome.SUCCESS


def test_followed_redirect_final_url_match_is_success():
    # Regression: HttpClient follows same-scope redirects before the
    # detector ever sees the response, so by then is_redirect is False and
    # there's no Location header — the only evidence left is the URL the
    # client ended up at.
    detector = ResultDetector(DetectorConfig(success_redirect_contains="/dashboard"))
    resp = _fake_response(
        text="Welcome back, authenticated user!",
        status_code=200,
        is_redirect=False,
        url="http://127.0.0.1:5000/dashboard",
    )
    assert detector.evaluate(resp) == Outcome.SUCCESS
