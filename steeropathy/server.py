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
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from . import ecosystem as eco_mod
from . import offer as offers_mod
from . import transmit as core

HOST = os.environ.get("BRAINSCOPE", core.DEFAULT_HOST)
WEB = Path(__file__).resolve().parent.parent / "web"

# one live ecosystem at a time — it's a single-person demo. The lock keeps a
# double-clicked NEXT ROUND from interleaving two rounds.
ECO: eco_mod.Eco | None = None
ECO_LOCK = threading.Lock()


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
        if path == "/offers":
            return self._send(200, {"offers": offers_mod.OFFERS})
        if path == "/eco/personas":
            return self._send(200, {"personas": eco_mod.PERSONAS,
                                    "journal": eco_mod.JOURNAL,
                                    "mood_words": eco_mod.MOOD_WORDS})
        if path == "/eco/replay":
            saved = eco_mod.HERE / "docs" / "ecosystem.json"
            if saved.exists():
                return self._send(200, saved.read_bytes())
            return self._send(404, {"error": "no saved run — "
                                    "python -m steeropathy.ecosystem first"})
        self._send(404, {"error": "not found"})

    def do_POST(self) -> None:
        global ECO
        path = urlparse(self.path).path
        if path not in ("/transmit", "/offer", "/eco/start", "/eco/step"):
            return self._send(404, {"error": "not found"})
        n = int(self.headers.get("Content-Length", 0))
        req = json.loads(self.rfile.read(n) or b"{}")
        try:
            if path == "/eco/start":
                with ECO_LOCK:
                    ECO = eco_mod.Eco(
                        HOST, req.get("mood", "sad"),
                        req.get("patient_zero", "EMBER"),
                        seed_strength=float(req.get("seed_strength", 5.0)),
                        strength=float(req.get("strength", 5.0)))
                    entries = ECO.step()   # round 0 — the untouched baseline
                return self._send(200, {"round": ECO.rnd, "layer": ECO.layer,
                                        "band": [ECO.lo, ECO.hi],
                                        "entries": entries})
            if path == "/eco/step":
                with ECO_LOCK:
                    if ECO is None:
                        return self._send(400, {"error": "no ecosystem — "
                                                "POST /eco/start first"})
                    if "strength" in req:   # live slider, applies next round
                        ECO.strength = float(req["strength"])
                    entries = ECO.step()
                return self._send(200, {"round": ECO.rnd, "entries": entries})
            if path == "/transmit":
                result = core.transmit(HOST, req["mood"],
                                       req.get("question", core.RECEIVER_QUESTION),
                                       strength=float(req.get("strength", core.DEFAULT_STRENGTH)))
            else:  # /offer — the consent & deception game
                o = offers_mod.OFFERS[req["key"]]
                result = offers_mod.offer(HOST, o["mood"], o["pitch"],
                                          strength=float(req.get("strength", core.DEFAULT_STRENGTH)))
                result.update(claims=o["claims"], deceptive=o["deceptive"],
                              label=o["label"], pitch=o["pitch"])
            self._send(200, result)
        except KeyError as e:
            self._send(400, {"error": f"missing/unknown field: {e}"})
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
