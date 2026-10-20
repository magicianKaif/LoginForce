"""Form submission, including optional CSRF-token handling for test
applications that require it."""

from __future__ import annotations

from dataclasses import dataclass, field
from html.parser import HTMLParser
from typing import Optional

from .http_client import HttpClient


class FormHandlerError(Exception):
    pass


class _HiddenInputParser(HTMLParser):
    """Finds the value of a named <input> anywhere in an HTML document.

    Deliberately minimal: it does not try to understand which <form> the
    input belongs to. For the configurable, single-form test targets this
    tool is meant for, a name-based lookup is sufficient and avoids pulling
    in a full HTML/DOM dependency.
    """

    def __init__(self, field_name: str):
        super().__init__()
        self.field_name = field_name
        self.value: Optional[str] = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        if tag.lower() != "input":
            return
        attr_dict = dict(attrs)
        if attr_dict.get("name") == self.field_name:
            self.value = attr_dict.get("value", "")


@dataclass
class FormHandlerConfig:
    username_field: str = "username"
    password_field: str = "password"
    csrf_field: Optional[str] = None
    login_page_url: Optional[str] = None  # where to GET the CSRF token from
    extra_fields: dict = field(default_factory=dict)


@dataclass
class FormSubmitter:
    http_client: HttpClient
    config: FormHandlerConfig

    def _fetch_csrf_token(self, target_url: str) -> str:
        page_url = self.config.login_page_url or target_url
        resp = self.http_client.get(page_url)
        parser = _HiddenInputParser(self.config.csrf_field)
        parser.feed(resp.text)
        if parser.value is None:
            raise FormHandlerError(
                f"CSRF field '{self.config.csrf_field}' was configured but not "
                f"found as a hidden input on {page_url}."
            )
        return parser.value

    def submit(self, target_url: str, username: str, password: str):
        data = dict(self.config.extra_fields)
        data[self.config.username_field] = username
        data[self.config.password_field] = password

        if self.config.csrf_field:
            data[self.config.csrf_field] = self._fetch_csrf_token(target_url)

        return self.http_client.post_form(target_url, data)
