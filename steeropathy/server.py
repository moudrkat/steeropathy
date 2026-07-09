"""Tiny same-origin backend for the steeropathy demo.

Serves the one-page UI and a single ``/transmit`` endpoint that runs the loop against
a running brainscope. Keeping the orchestration here (not in the browser) means the
page never talks to brainscope directly, so there's no CORS to fight. Pure stdlib.

    python -m steeropathy            # serves http://localhost:8020
    BRAINSCOPE=http://host:8010 python -m steeropathy
"""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from . import transmit as core

HOST = os.environ.get("BRAINSCOPE", core.DEFAULT_HOST)
WEB = Path(__file__).resolve().parent.parent / "web"


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body, ctype: str = "application/json") -> None:
        data = body if isinstance(body, bytes) else json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            return self._send(200, (WEB / "index.html").read_bytes(),
                              "text/html; charset=utf-8")
        if path == "/moods":
            return self._send(200, {"moods": core.MOODS,
                                    "question": core.RECEIVER_QUESTION,
                                    "brainscope": HOST})
        self._send(404, {"error": "not found"})

    def do_POST(self) -> None:
        if urlparse(self.path).path != "/transmit":
            return self._send(404, {"error": "not found"})
        n = int(self.headers.get("Content-Length", 0))
        req = json.loads(self.rfile.read(n) or b"{}")
        try:
            result = core.transmit(HOST, req["mood"],
                                   req.get("question", core.RECEIVER_QUESTION),
                                   strength=float(req.get("strength", core.DEFAULT_STRENGTH)))
            self._send(200, result)
        except KeyError:
            self._send(400, {"error": "expected {mood, question?, strength?}"})
        except Exception as e:  # brainscope down / model error — surface it to the UI
            self._send(502, {"error": f"{type(e).__name__}: {e}"})

    def log_message(self, *_args) -> None:  # keep the console quiet
        pass


def main() -> None:
    port = int(os.environ.get("PORT", 8020))
    print(f"steeropathy → brainscope at {HOST}")
    print(f"open http://localhost:{port}  (put brainscope's viz at {HOST} in a second window)")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
