#!/usr/bin/env python3
"""Example: run LOGIN FORCE end-to-end against the test suite's own local
mock app. Starts the fixture on 127.0.0.1 (a random free port), runs a
dry-run and then an active test that includes the real password so you can
see a confirmed SUCCESS outcome, then shuts the fixture down.

Safe to run anywhere — every request stays on 127.0.0.1.

Usage: python3 examples/run_against_local_mock.py
"""

from __future__ import annotations

import socket
import sys
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.mock_app import VALID_PASSWORD, create_app  # noqa: E402
from werkzeug.serving import make_server  # noqa: E402

from loginforce import cli  # noqa: E402


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def main() -> None:
    app = create_app()
    port = free_port()
    server = make_server("127.0.0.1", port, app)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{port}"

    wordlist = Path(__file__).parent / "wordlist.example.txt"
    tmp_wordlist = Path("/tmp/loginforce_example_wordlist.txt")
    tmp_wordlist.write_text(wordlist.read_text() + f"\n{VALID_PASSWORD}\n")

    common = [
        "-u", f"{base}/login",
        "-U", "admin",
        "-P", str(tmp_wordlist),
        "--login-page-url", f"{base}/login",
        "--csrf-field", "csrf_token",
        "--success-redirect-contains", "/dashboard",
        "--failure-contains", "Invalid username or password",
        "--delay", "0.1",
        "--output-dir", "/tmp/loginforce_example_reports",
    ]

    print("=== dry run ===")
    cli.run(common + ["--dry-run"])

    print("\n=== active run ===")
    cli.run(common)

    server.shutdown()
    thread.join(timeout=5)


if __name__ == "__main__":
    main()
