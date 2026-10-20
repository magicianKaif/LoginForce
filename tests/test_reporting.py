from __future__ import annotations

import json

from loginforce.reporting import Report, redact_headers, redact_text
from loginforce.result_detector import Outcome
from loginforce.safety import StopReason


def test_redact_text_scrubs_password_pairs():
    assert redact_text("username=admin&password=hunter2") == "username=admin&password=[REDACTED]"


def test_redact_headers_scrubs_known_secret_headers():
    headers = {"Authorization": "Bearer xyz", "Set-Cookie": "session=abc", "Content-Type": "text/html"}
    redacted = redact_headers(headers)
    assert redacted["Authorization"] == "[REDACTED]"
    assert redacted["Set-Cookie"] == "[REDACTED]"
    assert redacted["Content-Type"] == "text/html"


def test_report_never_contains_plaintext_password(tmp_path):
    report = Report()
    report.target_origin = "http://127.0.0.1:5000"
    report.request_limit = 5
    report.start()
    # Simulate a network error whose message happened to include form data —
    # this is exactly the kind of string that must come out redacted.
    report.add_attempt(1, outcome="error", error="POST failed with body username=admin&password=hunter2")
    report.add_attempt(2, outcome=Outcome.FAILURE, status_code=200)
    report.finish(StopReason.COMPLETED)

    json_path = report.write_json(tmp_path)
    md_path = report.write_markdown(tmp_path)

    json_text = json_path.read_text()
    md_text = md_path.read_text()

    assert "hunter2" not in json_text
    assert "hunter2" not in md_text

    data = json.loads(json_text)
    assert data["summary_counts"]["error"] == 1
    assert data["summary_counts"]["failure"] == 1


def test_has_confirmed_success_and_inconclusive_helpers():
    report = Report()
    report.add_attempt(1, outcome=Outcome.INCONCLUSIVE)
    report.add_attempt(2, outcome=Outcome.INCONCLUSIVE)
    assert report.has_confirmed_success() is False
    assert report.all_non_error_inconclusive() is True

    report.add_attempt(3, outcome=Outcome.SUCCESS)
    assert report.has_confirmed_success() is True
    assert report.all_non_error_inconclusive() is False
