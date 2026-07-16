"""The resonance web routes: replay serves the saved run as-is (no model needed),
and start/step drive one live Reso room behind a lock. Brainscope is mocked for the
live routes — these test the HTTP wiring, not the experiment."""
import json
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from steeropathy import server


def _serve():
    """A real server on an ephemeral port, torn down by the test."""
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}"


def _get(url):
    with urllib.request.urlopen(url) as r:
        return r.status, json.loads(r.read())


def _post(url, body):
    req = urllib.request.Request(url, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


class FakeReso:
    """Stands in for Reso: no network, deterministic rounds."""
    def __init__(self, url, mood, zero, **kw):
        self.args = (url, mood, zero, kw)
        self.rnd, self.layer, self.lo, self.hi = -1, 21, 17, 25
        self.jlens, self.strength = True, kw.get("strength", 5.0)

    def step(self):
        self.rnd += 1
        return [{"round": self.rnd, "agent": n, "text": "…", "sad_score": 0,
                 "mind": None, "inbound": [], "touch": None}
                for n in ("NOVA", "EMBER", "ATLAS", "QUILL")]


class TestResonanceRoutes(unittest.TestCase):
    def setUp(self):
        self.httpd, self.base = _serve()
        server.RESO = None            # each test starts with no live room

    def tearDown(self):
        self.httpd.shutdown()

    def test_replay_serves_the_saved_run(self):
        status, d = _get(self.base + "/resonance/replay")
        self.assertEqual(status, 200)
        self.assertIn("params", d)
        self.assertIn("log", d)
        # the canonical run: every entry has the fields the UI paints
        for k in ("round", "agent", "sad_score", "text"):
            self.assertIn(k, d["log"][0])

    def test_step_without_start_is_a_400(self):
        status, d = _post(self.base + "/resonance/step", {})
        self.assertEqual(status, 400)
        self.assertIn("start first", d["error"])

    def test_start_then_step_round_trips(self):
        with patch.object(server.reso_mod, "Reso", FakeReso):
            status, d = _post(self.base + "/resonance/start",
                              {"mood": "sad", "patient_zero": "QUILL",
                               "strength": 3.0})
            self.assertEqual(status, 200)
            self.assertEqual(d["round"], 0)          # round 0 = baseline
            self.assertEqual(d["band"], [17, 25])
            self.assertEqual(len(d["entries"]), 4)
            # the requested config reached the constructor
            self.assertEqual(server.RESO.args[1:3], ("sad", "QUILL"))
            self.assertEqual(server.RESO.args[3]["strength"], 3.0)

            status, d = _post(self.base + "/resonance/step", {"strength": 7.0})
            self.assertEqual(status, 200)
            self.assertEqual(d["round"], 1)
            self.assertEqual(server.RESO.strength, 7.0)   # live slider applied

    def test_start_uses_the_canonical_config(self):
        # the tab must run the same experiment as docs/resonance.json:
        # bipolar axis, moods baseline, memory off, conserved transfer
        with patch.object(server.reso_mod, "Reso", FakeReso):
            _post(self.base + "/resonance/start", {})
            kw = server.RESO.args[3]
            self.assertTrue(kw["bipolar"])
            self.assertEqual(kw["baseline"], "moods")
            self.assertFalse(kw["memory"])
            self.assertTrue(kw["transfer"])
            self.assertEqual(kw["give"], 0.5)


if __name__ == "__main__":
    unittest.main()
