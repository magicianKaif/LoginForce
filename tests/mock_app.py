"""A tiny local Flask app used ONLY as a controlled test fixture.

It is deliberately not a realistic app — just enough surface (CSRF token,
session cookie, redirect-on-success, 429 and slow endpoints) to exercise
loginforce's HTTP handling, form submission and result detection against
real sockets on 127.0.0.1.
"""

from __future__ import annotations

import secrets
import time

from flask import Flask, redirect, request, session

VALID_USERNAME = "admin"
VALID_PASSWORD = "correct-horse-battery-staple"

LOGIN_FORM = """
<html><body>
<form method="post" action="/login">
  <input type="hidden" name="csrf_token" value="{csrf_token}">
  <input type="text" name="username">
  <input type="password" name="password">
  <button type="submit">Log in</button>
</form>
</body></html>
"""

FAILURE_PAGE = "<html><body>Invalid username or password.</body></html>"
DASHBOARD_PAGE = "<html><body>Welcome back, authenticated user!</body></html>"


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = secrets.token_hex(16)

    @app.get("/login")
    def login_form():
        token = secrets.token_hex(16)
        session["csrf_token"] = token
        return LOGIN_FORM.format(csrf_token=token)

    @app.post("/login")
    def login_submit():
        submitted_token = request.form.get("csrf_token")
        expected_token = session.get("csrf_token")
        if not expected_token or submitted_token != expected_token:
            return "CSRF token invalid or missing.", 403

        username = request.form.get("username")
        password = request.form.get("password")
        if username == VALID_USERNAME and password == VALID_PASSWORD:
            return redirect("/dashboard", code=302)
        return FAILURE_PAGE, 200

    @app.get("/dashboard")
    def dashboard():
        return DASHBOARD_PAGE

    @app.get("/slow")
    def slow():
        time.sleep(2.0)
        return "done"

    @app.post("/rate-limited")
    def rate_limited():
        return "Too many requests", 429

    @app.post("/redirect-external")
    def redirect_external():
        # Points at a different host entirely — used to verify the client
        # refuses to follow it without the host being in allowed scope.
        resp = redirect("http://evil.example.invalid/steal", code=302)
        return resp

    return app
