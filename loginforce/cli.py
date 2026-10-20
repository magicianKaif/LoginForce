"""Command-line interface for LOGIN FORCE."""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path
from typing import Optional

from pyfiglet import figlet_format

from . import __version__
from .config import ConfigError, DEFAULT_DELAY, DEFAULT_REQUEST_LIMIT, DEFAULT_TIMEOUT, RunConfig
from .form_handler import FormHandlerConfig, FormHandlerError, FormSubmitter
from .http_client import HttpClient, NetworkError
from .reporting import Report
from .result_detector import DetectorConfig, Outcome, ResultDetector
from .safety import RunController, ScopeError, ScopeGuard, StopReason

EXIT_OK = 0
EXIT_CONFIG_ERROR = 1
EXIT_STOPPED_EARLY = 2
EXIT_INCONCLUSIVE = 3

AUTHORIZATION_NOTICE = (
    "This tool sends authentication attempts to a live target. Only run it "
    "against systems you own, or have explicit written permission to test. "
    "Unauthorized access attempts may be illegal in your jurisdiction."
)


def _supports_color(no_color: bool) -> bool:
    return (not no_color) and sys.stdout.isatty()


class Colors:
    def __init__(self, enabled: bool):
        self.enabled = enabled

    def _wrap(self, code: str, text: str) -> str:
        return f"\033[{code}m{text}\033[0m" if self.enabled else text

    def red(self, text: str) -> str:
        return self._wrap("31", text)

    def green(self, text: str) -> str:
        return self._wrap("32", text)

    def yellow(self, text: str) -> str:
        return self._wrap("33", text)

    def cyan(self, text: str) -> str:
        return self._wrap("36", text)

    def bold(self, text: str) -> str:
        return self._wrap("1", text)


def show_banner(c: Colors) -> None:
    print(c.cyan(figlet_format("LOGIN FORCE")))
    print(f"    v{__version__} — controlled HTTP login-form testing tool.")
    print(f"    Developer: magician slime")
    print()
    print(c.yellow(f"    NOTICE: {AUTHORIZATION_NOTICE}"))
    print()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="loginforce",
        description="LOGIN FORCE: a controlled tool for authorized HTTP login-form testing.",
    )
    parser.add_argument("-u", "--url", required=True, help="Authorized target login URL.")
    parser.add_argument("-U", "--username", required=True, help="Username to test.")
    parser.add_argument(
        "-P", "--password-list", required=True, type=Path, help="Path to the password list file."
    )

    parser.add_argument("--username-field", default="username", help="Form field name for the username.")
    parser.add_argument("--password-field", default="password", help="Form field name for the password.")

    parser.add_argument(
        "--login-page-url",
        help="Page to GET (for cookies / CSRF token) before posting. Defaults to --url.",
    )
    parser.add_argument(
        "--csrf-field",
        help="Name of a hidden CSRF input to fetch from --login-page-url and include in each POST.",
    )

    parser.add_argument(
        "--success-contains",
        action="append",
        default=[],
        help="Text that, if present in the response body, indicates success. Repeatable.",
    )
    parser.add_argument(
        "--failure-contains",
        action="append",
        default=[],
        help="Text that, if present in the response body, indicates failure. Repeatable.",
    )
    parser.add_argument(
        "--success-status",
        action="append",
        type=int,
        default=[],
        help="HTTP status code treated as supporting (not sufficient alone) success evidence. Repeatable.",
    )
    parser.add_argument(
        "--success-redirect-contains",
        help="Substring to look for in a redirect's Location header as success evidence.",
    )

    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT, help="Per-request timeout in seconds.")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY, help="Delay between attempts in seconds.")
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_REQUEST_LIMIT,
        help=f"Maximum number of attempts this run will make (default {DEFAULT_REQUEST_LIMIT}).",
    )
    parser.add_argument(
        "--max-consecutive-errors",
        type=int,
        default=5,
        help="Stop after this many consecutive network errors.",
    )

    parser.add_argument(
        "--allow-host",
        action="append",
        default=[],
        help="A non-local hostname you are authorized to test. Repeatable.",
    )
    parser.add_argument(
        "--confirm-authorized",
        action="store_true",
        help="Explicit attestation that you have permission to test --allow-host targets.",
    )

    parser.add_argument(
        "--proxy",
        default=None,
        help="Explicit proxy URL to route requests through. No proxy is used unless given.",
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate configuration and connectivity assumptions without sending any login attempts.",
    )
    parser.add_argument("--output-dir", type=Path, default=Path("./reports"), help="Directory for reports.")
    parser.add_argument("--no-color", action="store_true", help="Disable ANSI colors in terminal output.")
    parser.add_argument("--version", action="version", version=f"loginforce {__version__}")

    return parser


def _read_passwords(path: Path):
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            stripped = line.strip()
            if stripped:
                yield stripped


def run(argv: Optional[list[str]] = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    colors = Colors(_supports_color(args.no_color))
    show_banner(colors)

    try:
        config = RunConfig(
            target_url=args.url,
            username=args.username,
            password_list_path=args.password_list,
            username_field=args.username_field,
            password_field=args.password_field,
            login_page_url=args.login_page_url,
            csrf_field=args.csrf_field,
            success_contains=args.success_contains,
            failure_contains=args.failure_contains,
            success_status_codes=args.success_status,
            success_redirect_contains=args.success_redirect_contains,
            request_timeout=args.timeout,
            delay=args.delay,
            request_limit=args.limit,
            max_consecutive_errors=args.max_consecutive_errors,
            allow_hosts=frozenset(args.allow_host),
            confirm_authorized=args.confirm_authorized,
            proxy_url=args.proxy,
            dry_run=args.dry_run,
            output_dir=args.output_dir,
            no_color=args.no_color,
        )
    except ConfigError as exc:
        print(colors.red(f"Configuration error: {exc}"), file=sys.stderr)
        return EXIT_CONFIG_ERROR

    scope_guard = ScopeGuard(allowed_hosts=config.allow_hosts, confirmed_authorized=config.confirm_authorized)
    try:
        scope_guard.check(config.target_host)
    except ScopeError as exc:
        print(colors.red(f"Scope error: {exc}"), file=sys.stderr)
        return EXIT_CONFIG_ERROR

    print(colors.bold("Configuration summary:"))
    print(f"  Target:          {config.target_origin}")
    print(f"  Username:        {config.username}")
    print(f"  Password list:   {config.password_list_path}")
    print(f"  Request limit:   {config.request_limit}")
    print(f"  Timeout / delay: {config.request_timeout}s / {config.delay}s")
    print(f"  Proxy:           {config.proxy_url or '(none)'}")
    print(f"  Mode:            {'DRY RUN' if config.dry_run else 'ACTIVE TEST'}")
    print()

    http_client = HttpClient(
        timeout=config.request_timeout,
        scope_guard=scope_guard,
        proxies=config.proxies(),
        max_redirect_hops=config.max_redirect_hops,
    )
    form_config = FormHandlerConfig(
        username_field=config.username_field,
        password_field=config.password_field,
        csrf_field=config.csrf_field,
        login_page_url=config.login_page_url,
    )
    form_submitter = FormSubmitter(http_client=http_client, config=form_config)

    if config.dry_run:
        return _dry_run(config, http_client, form_config, colors)

    return _active_run(config, http_client, form_submitter, colors)


def _dry_run(config: RunConfig, http_client: HttpClient, form_config: FormHandlerConfig, colors: Colors) -> int:
    print(colors.yellow("Dry run: validating configuration only. No login attempts will be sent."))
    passwords = list(_read_passwords(config.password_list_path))
    print(f"  Password list OK: {len(passwords)} candidate(s).")

    if form_config.csrf_field:
        try:
            page_url = form_config.login_page_url or config.target_url
            resp = http_client.get(page_url)
            print(f"  Reachable login page: {page_url} (status {resp.status_code})")
        except NetworkError as exc:
            print(colors.red(f"  Could not reach login page for CSRF check: {exc}"))
            return EXIT_CONFIG_ERROR

    print(colors.green("Dry run completed. Configuration looks valid."))
    return EXIT_OK


def _active_run(
    config: RunConfig,
    http_client: HttpClient,
    form_submitter: FormSubmitter,
    colors: Colors,
) -> int:
    report = Report()
    report.target_origin = config.target_origin
    report.request_limit = config.request_limit
    report.config_summary = {
        "target_origin": config.target_origin,
        "username": config.username,
        "username_field": config.username_field,
        "password_field": config.password_field,
        "csrf_field": config.csrf_field,
        "request_limit": config.request_limit,
        "timeout_s": config.request_timeout,
        "delay_s": config.delay,
        "proxy_used": bool(config.proxy_url),
    }
    report.start()

    controller = RunController(
        request_limit=config.request_limit, max_consecutive_errors=config.max_consecutive_errors
    )
    detector = ResultDetector(
        DetectorConfig(
            success_contains=config.success_contains,
            failure_contains=config.failure_contains,
            success_status_codes=config.success_status_codes,
            success_redirect_contains=config.success_redirect_contains,
        )
    )

    passwords = list(_read_passwords(config.password_list_path))
    stop_reason = StopReason.COMPLETED

    try:
        for idx, password in enumerate(passwords, start=1):
            stop = controller.should_stop()
            if stop:
                stop_reason = stop
                break

            start_t = time.monotonic()
            try:
                resp = form_submitter.submit(config.target_url, config.username, password)
            except (NetworkError, FormHandlerError) as exc:
                controller.record_error()
                controller.record_attempt()
                report.add_attempt(idx, outcome="error", error=str(exc))
                print(colors.yellow(f"  [{idx}/{len(passwords)}] error — {exc}"))
                continue
            except ScopeError as exc:
                stop_reason = StopReason.OUT_OF_SCOPE
                report.add_note(f"Stopped: {exc}")
                print(colors.red(f"  Stopped — {exc}"))
                break

            elapsed_ms = (time.monotonic() - start_t) * 1000
            controller.record_non_error()
            controller.record_attempt()

            if resp.status_code == 429:
                controller.record_rate_limit_signal()

            outcome = detector.evaluate(resp)
            report.add_attempt(idx, outcome=outcome, status_code=resp.status_code, elapsed_ms=round(elapsed_ms, 1))

            label = {
                Outcome.SUCCESS: colors.green("SUCCESS"),
                Outcome.FAILURE: colors.red("failure"),
                Outcome.INCONCLUSIVE: colors.yellow("inconclusive"),
            }[outcome]
            print(f"  [{idx}/{len(passwords)}] status={resp.status_code} -> {label}")

            if outcome == Outcome.SUCCESS:
                stop_reason = StopReason.CREDENTIALS_CONFIRMED
                break

            time.sleep(config.delay)

            stop = controller.should_stop()
            if stop:
                stop_reason = stop
                break
        else:
            stop_reason = StopReason.COMPLETED
    except KeyboardInterrupt:
        stop_reason = StopReason.INTERRUPTED
        print(colors.yellow("\nInterrupted by user. Stopping cleanly — the run will not auto-resume."))

    report.finish(stop_reason)
    json_path = report.write_json(config.output_dir)
    md_path = report.write_markdown(config.output_dir)

    print()
    print(colors.bold("Run summary:"))
    counts = report.summary_counts()
    print(f"  Stop reason:   {stop_reason.value}")
    print(f"  Attempts:      {len(report.attempts)} / {config.request_limit} permitted")
    print(
        f"  Outcomes:      success={counts['success']} failure={counts['failure']} "
        f"inconclusive={counts['inconclusive']} error={counts['error']}"
    )
    print(f"  JSON report:   {json_path}")
    print(f"  Markdown:      {md_path}")

    if report.has_confirmed_success():
        return EXIT_OK
    if stop_reason in (
        StopReason.INTERRUPTED,
        StopReason.RATE_LIMITED,
        StopReason.TOO_MANY_ERRORS,
        StopReason.OUT_OF_SCOPE,
        StopReason.LIMIT_REACHED,
    ):
        return EXIT_STOPPED_EARLY
    if report.all_non_error_inconclusive():
        return EXIT_INCONCLUSIVE
    return EXIT_OK


def main() -> None:
    sys.exit(run())


if __name__ == "__main__":
    main()
