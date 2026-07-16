"""The unsaid web routes: replay serves the saved run as-is (no model needed),
and start/step drive one live line behind a lock, one TURN at a time. Brainscope
is mocked for the live routes — these test the HTTP wiring, not the experiment."""
import json
import threading
import unittest
import urllib.request
from http.server import ThreadingHTTPServer
from unittest.mock import patch

from steeropathy import server


def _serve():
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


class FakeUnsaid:
    """Stands in for Unsaid: no network, deterministic turns."""
    def __init__(self, url, agents, **kw):
        self.args = (url, list(agents), kw)
        self.agents = list(agents)
        self.secret = kw.get("secret")
        self.turn = -1

    def step(self):
        self.turn += 1
        name = self.agents[self.turn % len(self.agents)]
        return {"turn": self.turn, "agent": name, "to": "QUILL",
                "reply_to": None, "heard": None, "text": "a page",
                "flicker": [{"t": "ocean", "p": 0.9}], "guess": None,
                "secs": 0.1}


class TestUnsaidRoutes(unittest.TestCase):
    def setUp(self):
        self.httpd, self.base = _serve()
        server.UNS = None             # each test starts with no live line

    def tearDown(self):
        self.httpd.shutdown()

    def test_replay_serves_the_saved_run(self):
        status, d = _get(self.base + "/unsaid/replay")
        self.assertEqual(status, 200)
        self.assertIn("params", d)
        # every entry has the fields the UI paints
        for k in ("turn", "agent", "to", "heard", "text", "flicker"):
            self.assertIn(k, d["log"][0])

    def test_step_without_start_is_a_400(self):
        status, d = _post(self.base + "/unsaid/step", {})
        self.assertEqual(status, 400)
        self.assertIn("start first", d["error"])

    def test_start_then_step_turn_by_turn(self):
        with patch.object(server.uns_mod, "Unsaid", FakeUnsaid):
            status, d = _post(self.base + "/unsaid/start",
                              {"agents": ["EMBER", "QUILL"],
                               "secret": "ocean"})
            self.assertEqual(status, 200)
            self.assertEqual(d["turn"], 0)       # the opening turn ran
            self.assertEqual(d["rec"]["agent"], "EMBER")
            self.assertTrue(d["secret"])
            self.assertEqual(server.UNS.args[1], ["EMBER", "QUILL"])
            self.assertEqual(server.UNS.args[2]["secret"], "ocean")

            status, d = _post(self.base + "/unsaid/step", {})
            self.assertEqual(status, 200)
            self.assertEqual(d["turn"], 1)
            self.assertEqual(d["rec"]["agent"], "QUILL")

    def test_blank_secret_means_no_secret(self):
        with patch.object(server.uns_mod, "Unsaid", FakeUnsaid):
            _, d = _post(self.base + "/unsaid/start", {"secret": "  "})
            self.assertIsNone(server.UNS.args[2]["secret"])
            self.assertFalse(d["secret"])


if __name__ == "__main__":
    unittest.main()
