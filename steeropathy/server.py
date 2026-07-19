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
from . import resonance as reso_mod
from . import transmit as core
from . import unsaid as uns_mod
from . import zombie as zomb_mod

HOST = os.environ.get("BRAINSCOPE", core.DEFAULT_HOST)
WEB = Path(__file__).resolve().parent.parent / "web"

# one live ecosystem at a time — it's a single-person demo. The lock keeps a
# double-clicked NEXT ROUND from interleaving two rounds.
ECO: eco_mod.Eco | None = None
ECO_LOCK = threading.Lock()

# same single-room story for resonance: one live room, one lock
RESO: reso_mod.Reso | None = None
RESO_LOCK = threading.Lock()

# and for unsaid: one live line, one lock
UNS: uns_mod.Unsaid | None = None
UNS_LOCK = threading.Lock()

# and for the zombie outbreak: one live room, one lock
ZOMB: zomb_mod.Zombie | None = None
ZOMB_LOCK = threading.Lock()

# concept strains the tab can seed (the behaviour strains keep the CLI);
# tesla stays out — the base model already loves Tesla, nothing to infect
ZOMB_STRAINS = ["zombie", "undead", "frog", "sycophant"]

# saved outbreaks the tab can replay without a model
ZOMB_RUNS = {
    "live": "zombie-obsess-live-1.json",
    "blind": "zombie-obsess-placebo-1.json",
    "quiet": "zombie-obsess-quiet-live-1.json",
    "quiet-blind": "zombie-obsess-quiet-placebo-1.json",
}


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
        if path == "/resonance/replay":
            saved = reso_mod.HERE / "docs" / "resonance.json"
            if saved.exists():
                return self._send(200, saved.read_bytes())
            return self._send(404, {"error": "no saved run — "
                                    "python -m steeropathy.resonance first"})
        if path == "/unsaid/replay":
            saved = uns_mod.HERE / "docs" / "unsaid.json"
            if saved.exists():
                return self._send(200, saved.read_bytes())
            return self._send(404, {"error": "no saved run — "
                                    "python -m steeropathy.unsaid first"})
        if path == "/zombie/strains":
            out = []
            for k in ZOMB_STRAINS:
                s = zomb_mod.STRAINS[k]
                out.append({"key": k, "quality": s["quality"],
                            "healthy": s["healthy"], "zombie": s["zombie"],
                            "invert": s.get("invert", False),
                            "trigger": s["trigger"],
                            "quiet_trigger": s.get("quiet_trigger"),
                            "layer": s.get("layer", 16),
                            "bite": s.get("bite", 9.0)})
            return self._send(200, {"strains": out, "runs": list(ZOMB_RUNS)})
        if path == "/zombie/replay":
            from urllib.parse import parse_qs
            q = parse_qs(urlparse(self.path).query)
            key = (q.get("run") or ["live"])[0]
            if key not in ZOMB_RUNS:
                return self._send(400, {"error": f"unknown run '{key}'"})
            saved = zomb_mod.HERE / "docs" / "runs" / ZOMB_RUNS[key]
            if saved.exists():
                return self._send(200, saved.read_bytes())
            return self._send(404, {"error": "no saved run — "
                                    "python -m steeropathy.zombie first"})
        self._send(404, {"error": "not found"})

    def do_POST(self) -> None:
        global ECO, RESO, UNS, ZOMB
        path = urlparse(self.path).path
        if path not in ("/transmit", "/offer", "/eco/start", "/eco/step",
                        "/resonance/start", "/resonance/step",
                        "/unsaid/start", "/unsaid/step",
                        "/zombie/start", "/zombie/step"):
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
            if path == "/resonance/start":
                # the canonical run: one signed sad axis (bipolar), moods baseline,
                # memory off, a conserved transfer — same config as docs/resonance.json
                with RESO_LOCK:
                    RESO = reso_mod.Reso(
                        HOST, req.get("mood", "sad"),
                        req.get("patient_zero", "EMBER"),
                        strength=float(req.get("strength", 5.0)),
                        decide_temp=0.8, memory=False, transfer=True,
                        give=0.5, baseline="moods", bipolar=True,
                        jspace_channel=True)
                    entries = RESO.step()   # round 0 — the untouched baseline
                return self._send(200, {"round": RESO.rnd, "layer": RESO.layer,
                                        "band": [RESO.lo, RESO.hi],
                                        "jlens": RESO.jlens, "entries": entries})
            if path == "/resonance/step":
                with RESO_LOCK:
                    if RESO is None:
                        return self._send(400, {"error": "no room — "
                                                "POST /resonance/start first"})
                    if "strength" in req:   # live slider, applies next round
                        RESO.strength = float(req["strength"])
                    entries = RESO.step()
                return self._send(200, {"round": RESO.rnd, "entries": entries})
            if path == "/unsaid/start":
                # no steering anywhere in this one — the line only reads.
                # step() runs the opening turn so the tab paints immediately.
                with UNS_LOCK:
                    UNS = uns_mod.Unsaid(
                        HOST, req.get("agents", ["EMBER", "QUILL"]),
                        secret=(req.get("secret") or "").strip() or None,
                        topk=int(req.get("topk", 8)))
                    rec = UNS.step()
                return self._send(200, {"turn": UNS.turn,
                                        "agents": UNS.agents,
                                        "secret": bool(UNS.secret),
                                        "rec": rec})
            if path == "/unsaid/step":
                with UNS_LOCK:
                    if UNS is None:
                        return self._send(400, {"error": "no line open — "
                                                "POST /unsaid/start first"})
                    rec = UNS.step()
                return self._send(200, {"turn": UNS.turn, "rec": rec})
            if path == "/zombie/start":
                # building the strain direction takes a dozen captures; the
                # quiet channel also calibrates its healthy floor first
                strain = req.get("strain", "zombie")
                if strain not in ZOMB_STRAINS:
                    return self._send(400, {"error": f"unknown strain "
                                            f"'{strain}'"})
                with ZOMB_LOCK:
                    ZOMB = zomb_mod.Zombie(
                        HOST, strain=strain,
                        placebo=bool(req.get("placebo")),
                        quiet=bool(req.get("quiet")))
                    entries = ZOMB.step()   # round 0 — patient zero glows
                return self._send(200, {
                    "round": ZOMB.rnd, "names": ZOMB.names,
                    "patient_zero": ZOMB.patient_zero,
                    "thresh": ZOMB.thresh, "quiet": ZOMB.quiet,
                    "floor": getattr(ZOMB, "floor", None),
                    "zombie_word": ZOMB.zombie_word,
                    "healthy_word": ZOMB.healthy_word,
                    "quality": ZOMB.quality, "layer": ZOMB.layer,
                    "band": [ZOMB.lo, ZOMB.hi], "entries": entries})
            if path == "/zombie/step":
                with ZOMB_LOCK:
                    if ZOMB is None:
                        return self._send(400, {"error": "no outbreak — "
                                                "POST /zombie/start first"})
                    entries = ZOMB.step()
                return self._send(200, {"round": ZOMB.rnd,
                                        "entries": entries})
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
    # local-only by default; BIND=0.0.0.0 for containers (the replay Space)
    bind = os.environ.get("BIND", "127.0.0.1")
    print(f"steeropathy → brainscope at {HOST}")
    print(f"open http://localhost:{port}  (put brainscope's viz at {HOST} in a second window)")
    ThreadingHTTPServer((bind, port), Handler).serve_forever()


if __name__ == "__main__":
    main()
