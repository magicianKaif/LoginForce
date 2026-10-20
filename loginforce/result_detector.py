"""Turns an HTTP response into a conservative outcome judgement.

The guiding rule: a response is only ever called SUCCESS or FAILURE when
a configured, application-specific indicator actually matched. Anything
else — including a bare HTTP 200, or no indicators matching at all — is
INCONCLUSIVE. Inconclusive is a legitimate, expected outcome, not an
error to be hidden.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import requests


class Outcome(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    INCONCLUSIVE = "inconclusive"


@dataclass
class DetectorConfig:
    success_contains: list[str] = field(default_factory=list)
    failure_contains: list[str] = field(default_factory=list)
    success_status_codes: list[int] = field(default_factory=list)
    success_redirect_contains: Optional[str] = None


@dataclass
class ResultDetector:
    config: DetectorConfig

    def evaluate(self, response: requests.Response) -> Outcome:
        # Redirect-based evidence first: a login that redirects somewhere
        # recognizable (e.g. "/dashboard") is strong, app-specific evidence.
        # The HTTP client already follows same-scope redirects, so by the
        # time a response reaches here it is usually the *final* page, not
        # the redirect itself — check both the final URL reached and, for
        # the case where a redirect was deliberately left unfollowed
        # because it left scope, the Location header of that redirect.
        if self.config.success_redirect_contains:
            final_url = getattr(response, "url", "") or ""
            location = response.headers.get("Location", "") if response.is_redirect else ""
            if self.config.success_redirect_contains in final_url or self.config.success_redirect_contains in location:
                return Outcome.SUCCESS

        body = response.text if response.content else ""
        success_hit = any(marker in body for marker in self.config.success_contains)
        failure_hit = any(marker in body for marker in self.config.failure_contains)

        if success_hit and failure_hit:
            # Both markers present — the indicators are miscalibrated for
            # this app. Don't guess; surface it as ambiguous.
            return Outcome.INCONCLUSIVE
        if success_hit:
            return Outcome.SUCCESS
        if failure_hit:
            return Outcome.FAILURE

        # No text indicator matched. A configured status code is weaker,
        # supporting evidence only — never sufficient on its own — so we
        # only use it here, as a fallback, and only when nothing else fired.
        if self.config.success_status_codes and response.status_code in self.config.success_status_codes:
            return Outcome.SUCCESS

        return Outcome.INCONCLUSIVE
