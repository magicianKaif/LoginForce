from __future__ import annotations

import socket
import threading

import pytest
from werkzeug.serving import make_server

from .mock_app import create_app


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class _ServerThread(threading.Thread):
    def __init__(self, app, host, port):
        super().__init__(daemon=True)
        self.server = make_server(host, port, app)

    def run(self):
        self.server.serve_forever()

    def shutdown(self):
        self.server.shutdown()


@pytest.fixture(scope="session")
def live_server():
    app = create_app()
    port = _free_port()
    thread = _ServerThread(app, "127.0.0.1", port)
    thread.start()
    base_url = f"http://127.0.0.1:{port}"
    yield base_url
    thread.shutdown()
    thread.join(timeout=5)
