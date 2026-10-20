# LOGIN FORCE

A controlled, evidence-based CLI tool for testing HTTP/HTTPS login forms
during **authorized** security assessments.

> **Authorized use only.** Run this only against systems you own, local test
> applications, dedicated cyber ranges, or targets you have explicit written
> permission to test. The tool enforces a scope check and will refuse to
> contact a non-local host unless you explicitly allow-list it and attest
> that you're authorized (`--allow-host` + `--confirm-authorized`).

## What changed from the original prototype

The original `loginforce.py` was a single-file script that defaulted to
routing every attempt through Tor, printed plaintext passwords to the
terminal on every line, had no timeouts, no scope check, no request limit,
and decided "success" by checking for the literal string `"Login successful"`
in a 200 response — which essentially never happens against a real app.

This version is a from-scratch rebuild around one idea: **don't claim
anything the evidence doesn't support, and don't let the tool run further
or wider than it was explicitly told to.** See `AUDIT.md` for the detailed
finding-by-finding writeup of the original script.

## Install

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

```bash
python -m loginforce \
  -u http://127.0.0.1:5000/login \
  -U admin \
  -P wordlist.txt \
  --login-page-url http://127.0.0.1:5000/login \
  --csrf-field csrf_token \
  --success-redirect-contains /dashboard \
  --failure-contains "Invalid username or password" \
  --limit 25 --delay 0.5
```

Or, against a non-local target you're authorized to test:

```bash
python -m loginforce \
  -u https://staging.example-client.test/login \
  -U testuser -P wordlist.txt \
  --allow-host staging.example-client.test --confirm-authorized \
  --success-contains "Welcome back" \
  --failure-contains "Invalid credentials" \
  --limit 10 --delay 1.0
```

Always try `--dry-run` first — it validates the URL, scope, password list
and (if configured) that the CSRF field can actually be found on the login
page, without sending a single login attempt.

### Key flags

| Flag | Purpose |
|---|---|
| `-u/--url` | Target login POST endpoint (required) |
| `-U/--username` | Username under test (required) |
| `-P/--password-list` | Path to newline-delimited password list (required) |
| `--success-contains` / `--failure-contains` | Text indicators in the response body (repeatable) |
| `--success-redirect-contains` | Substring to match against the URL the client ends up at after a successful-looking redirect |
| `--success-status` | A status code treated as *supporting*, never sufficient-alone, success evidence |
| `--csrf-field` / `--login-page-url` | Fetch a hidden CSRF input before each POST |
| `--limit` | Hard cap on attempts this run will make (default 25, hard max 2000) |
| `--delay` | Seconds between attempts (default 0.5) |
| `--allow-host` / `--confirm-authorized` | Explicitly scope a non-local target |
| `--proxy` | Explicit proxy URL. **There is no default proxy and Tor is never used automatically** — a proxy pointing at the default Tor SOCKS port is rejected at config time. |
| `--dry-run` | Validate everything, send nothing |

### What it deliberately does NOT do

Per the project's safety requirements, this tool does not implement CAPTCHA
bypass, MFA bypass, account-lockout evasion, WAF evasion, stealth
functionality, credential stuffing across multiple usernames, or proxy
rotation. It tests one username against one password list, against one
scoped target, with a hard attempt cap, and stops itself rather than
relying on the operator to watch it.

## How a result is classified

Every attempt is scored `success`, `failure`, or `inconclusive` —
never inferred from a bare HTTP 200. `inconclusive` means the configured
indicators didn't provide enough evidence either way; it's a normal,
expected outcome when indicators need tuning, not an error.

## Reports

Each run writes a JSON and a Markdown report to `--output-dir` (default
`./reports/`), named by a run UUID. **Passwords are never written to any
report, in any form** — not plaintext, not hashed. Any error message that
happens to contain `password=...`-style data is redacted before it's
stored. Cookies, `Authorization` headers and CSRF tokens are redacted from
anything that gets logged.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | Completed — confirmed success, or a full run with conclusive (non-inconclusive) failures |
| 1 | Configuration or scope error — nothing was sent |
| 2 | Stopped early — request limit reached, rate-limited, too many consecutive errors, interrupted, or target redirected out of scope |
| 3 | Inconclusive — the run completed but no configured indicator ever matched; reconfigure `--success-contains`/`--failure-contains` |

## Development

```bash
pip install -r requirements-dev.txt
python -m pytest -q
```

The test suite spins up a small local Flask app (`tests/mock_app.py`) on
`127.0.0.1` with a real CSRF-token flow, a redirect-on-success login, a
slow endpoint (timeout testing), a 429 endpoint (rate-limit testing) and a
cross-host redirect (scope testing), and drives the real CLI against it —
no attempts are ever sent to a public host or third-party account.

**Actual last run: 45 passed, 0 failed** (`python -m pytest -q`).

## Project layout

```
loginforce/
  cli.py              — argument parsing, terminal UI, run loop, exit codes
  config.py           — RunConfig: validation and safe defaults
  safety.py           — ScopeGuard (authorization scope) and RunController (stop conditions)
  http_client.py      — session, timeouts, scope-checked redirect following
  form_handler.py      — form submission + optional CSRF token fetch
  result_detector.py  — evidence-based success/failure/inconclusive classification
  reporting.py         — redacted JSON + Markdown report generation
tests/
  mock_app.py          — local Flask fixture used only by the test suite
  conftest.py           — spins the fixture up on a real socket for integration tests
  test_*.py             — unit + integration coverage
```

## License

No license has been selected yet — add one deliberately if/when you decide
the terms you want this distributed under.
