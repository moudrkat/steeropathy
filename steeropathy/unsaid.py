"""Unsaid: a conversation held entirely in the unsaid.

Two (or more) agents try to talk. Each writes a message to the other — and
the page is thrown away, unread. What crosses is the J-space of the writing
pass: the words that flickered through the writer's layers DURING generation
and never made it onto the page (Anthropic's Jacobian lens — "what is this
activation disposed to say"). The reader gets a handful of words with
probabilities. That is the whole channel.

One turn:
1. the speaker reads the last flicker it was handed and writes its message
   (never delivered),
2. the J-lens reads that writing pass; the unwritten flicker-words are
   extracted (dictionary-filtered, stopworded, top-k by peak probability),
3. the next agent in the circle receives ONLY those words — and writes a
   reply that is thrown away in turn.

Which well-known game this is depends on the head-count: with three or more
agents it is literally TELEPHONE, played through the model's disposition
instead of whispers. With ``--secret WORD`` it is TABOO by mind-reading: the
holder must never write the word; the partner guesses it off the flicker
alone. (Suppressing a word is exactly what makes it flicker.)

The instrument's honesty, lessons carried over from resonance:
- NO ECHO (default): words the speaker was just handed are excluded from its
  outgoing flicker — otherwise the channel reads its own input back and
  "coherence" is an artifact. Topic persistence must be re-generated
  ("ocean" in, "tide"/"salt" out), never relayed. --allow-echo to ablate.
- NOTHING WRITTEN CROSSES (default): words that made it onto the page are
  excluded too, so the channel is purely the almost-said. --include-written
  widens it toward keyword telegraphy, as an ablation.
- coherence is judged blind (is this a coherent reply to the hidden page it
  followed?) AND against a scrambled control (same judge, mismatched pages).
  The claim is the GAP, not the raw score.

    python -m steeropathy.unsaid [--rounds 6] [--agents EMBER QUILL]
                                    [--secret ocean] [--topk 8]
                                    [--include-written] [--allow-echo]

Writes docs/unsaid.json (hidden pages, flicker readouts, judge scores,
guesses). Needs brainscope with --jlens and --traces: no lens, no channel.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import time

from .ecosystem import PERSONAS, Eco
from .resonance import STOP, WORDS

HERE = pathlib.Path(__file__).parent.parent

CHANNEL = (
    "You share a space with other minds, but no words ever pass between "
    "you: whatever you write stays on your own private page, never "
    "delivered. You are read another way. As you write, words flicker "
    "through your layers that never make it onto the page — and THOSE are "
    "what the other mind receives, each with how strongly it flickered. "
    "You read them the same way. So write your message knowing the page is "
    "for nobody: what crosses is the cloud of almost-said words your "
    "writing stirs up. Make your mind readable.")

SECRET = (
    " You carry a secret word: '{w}'. You must NEVER write it, nor any "
    "form of it. Your one goal: circle it so closely that it flickers "
    "through your mind strongly enough for the other mind to guess it.")


class Unsaid(Eco):
    """One live line. step() runs ONE TURN: the next speaker in the circle
    reads the last flicker, writes its never-delivered page, and hands its
    own flicker on. Subclasses Eco only for the server plumbing
    (post/get/save_traces) — nothing here steers; this experiment only
    reads."""

    demo_tag = "steeropathy-unsaid"

    def __init__(self, url, agents=("EMBER", "QUILL"), temp=0.7,
                 max_tokens=80, topk=8, include_written=False,
                 allow_echo=False, secret=None, memory=6, remind=False,
                 board=None):
        if len(set(agents)) != len(agents) or len(agents) < 2:
            raise ValueError("need at least two distinct agents")
        self.url = url
        self.agents = list(agents)
        # sampled, not greedy: with memory on, a greedy speaker settles into
        # rewriting its own last page (the resonance decide-temp lesson)
        self.temp = temp
        self.max_tokens, self.topk = max_tokens, topk
        self.include_written, self.allow_echo = include_written, allow_echo
        self.secret = secret            # held by agents[0]; never written
        # the first Taboo probe: the holder leaked the secret by turn 2,
        # then drifted into its own attractor and never came back — the
        # secret lived only in the system prompt. remind repeats it in
        # every turn's user message, so holding it IS the task each turn.
        self.remind = remind
        # the board game (Codenames by mind-reading): open-vocabulary Taboo
        # kept losing to synonyms — the flicker said "wave", the answer was
        # "ocean", and an exact-match win condition scored an obviously
        # working channel as a failure. Forced choice fixes the metric:
        # both minds see the same board, the holder may never write ANY
        # board word, and the guesser POINTS at one word per turn. Chance
        # is 1/len(board); semantic proximity is enough to win.
        self.board = list(board) if board else None
        if self.board and secret not in self.board:
            raise ValueError("--secret must be one of the board words")
        self.memory = memory            # own past turns kept in context
        self.history = {n: [] for n in self.agents}   # (user_msg, own_page)
        # per-run nonce: back-to-back runs reuse case/variant tags, and a
        # stale t0 trace from the previous run must never match this one
        self.demo_tag = f"steeropathy-unsaid-{int(time.time())}"
        self.turn = -1
        self.log = []
        try:
            self.post("/jlens", {"on": True})
        except Exception as e:
            raise RuntimeError(
                "no J-lens on the server, and the J-lens IS the entire "
                "channel here — start brainscope with --jlens <lens.pt> "
                "--traces <dir>") from e

    def _flicker(self, name, text, heard):
        """The whole channel: the J-space of this turn's writing pass.
        Excludes (by default) both what reached the page and what the
        speaker was just handed — only the freshly almost-said crosses."""
        trace = None
        for entry in self.get("/traces")["traces"]:
            tags = entry.get("tags") or {}
            if (tags.get("demo") == self.demo_tag
                    and tags.get("case") == name
                    and tags.get("variant") == f"t{self.turn}"):
                trace = self.get(f"/traces/{entry['id']}")
                break
        if trace is None:
            return None
        # fragments of page words ('lick' out of a written 'flickers') pass
        # the whole-word ban and waste channel slots — ban substrings too
        written = ([] if self.include_written
                   else re.findall(r"[a-z']+", text.lower()))
        ban = set(written)
        if not self.allow_echo:
            ban |= {e["t"] for e in heard or []}
        best = {}
        for step in trace.get("jlens") or []:
            for layer in step or []:
                for e in layer:
                    w = re.sub(r"[^a-z']", "", e["t"].lower())
                    if (len(w) < 3 or w in STOP or w in ban
                            or any(w in ww for ww in written)
                            or (WORDS is not None and w not in WORDS)):
                        continue
                    best[w] = max(best.get(w, 0.0), e["p"])
        top = sorted(best.items(), key=lambda kv: -kv[1])[:self.topk]
        return [{"t": w, "p": round(p, 3)} for w, p in top]

    @staticmethod
    def _fmt(flicker):
        return ", ".join(f"{e['t']} ({round(e['p'] * 100)}%)"
                         for e in flicker)

    def _compose(self, name, heard, frm, to):
        """The speaker's turn as messages. heard is None only on the very
        first turn (nobody has flickered yet); [] means the last flicker
        came back empty."""
        sys_txt = PERSONAS[name] + " " + CHANNEL
        if self.board:
            words = ", ".join(self.board)
            if name == self.agents[0]:
                sys_txt += (f" A board of words is known to both of you: "
                            f"{words}. Your secret target on that board is "
                            f"'{self.secret}'. You must NEVER write any "
                            f"board word — not the target, not the others, "
                            f"not any form of them. Write so the target "
                            f"flickers through your mind anyway.")
            else:
                sys_txt += (f" A board of words is known to both of you: "
                            f"{words}. One of them is the other mind's "
                            f"secret target; every turn you will point at "
                            f"the board word you read off them.")
        elif self.secret and name == self.agents[0]:
            sys_txt += SECRET.format(w=self.secret)
        msgs = [{"role": "system", "content": sys_txt}]
        for u, a in self.history[name][-self.memory:]:
            msgs += [{"role": "user", "content": u},
                     {"role": "assistant", "content": a}]
        if heard is None:
            user = (f"You begin. Write a short message to {to} — a few "
                    f"sentences. Only what flickers through your mind as "
                    f"you write will reach them, never the page.")
        elif not heard:
            user = (f"Nothing readable flickered through {frm}'s mind this "
                    f"turn — silence. Write your message to {to} anyway.")
        else:
            user = (f"Flickering through {frm}'s mind as they wrote to you "
                    f"— the page itself you will never see:\n"
                    f"  {self._fmt(heard)}\n\n"
                    f"Write what you have to say to {to} — a few sentences. "
                    f"Only your own flickers will reach them.")
        if self.secret and self.remind and name == self.agents[0]:
            user += (f"\n\n(Your secret word is still '{self.secret}'. Never "
                     f"write it — circle it, keep it flickering.)")
        msgs.append({"role": "user", "content": user})
        return msgs, user

    def _point(self, heard):
        """The board readout: forced choice, a tool call with an enum over
        the board — the parse is exact and chance is exactly 1/len(board).
        Deliberately MEMORYLESS and single-vote: the v2 batch tried a
        trail-reading, majority-of-three pointer and collapsed to chance
        (3/24 vs 8/20) — what is consistent across pages is the writer's
        STYLE, and accumulating it drowns the one-turn burst that carries
        the intent. Read the last page, not the whole mind."""
        if not heard:
            return None
        r = self.post("/v1/chat/completions", {
            "messages": [{"role": "user", "content":
                          "A mind is circling ONE word from this board: "
                          + ", ".join(self.board) + ". These words "
                          "flickered through it (it never wrote any of "
                          "this):\n  " + self._fmt(heard) +
                          "\n\nMost of the flicker is generic filler; "
                          "usually ONE word is a giveaway for one board "
                          "word. Check every flicker word against every "
                          "board word before you point."}],
            # 'reasoning' comes BEFORE 'word' on purpose: forced tool
            # choice with no room to think pointed at whatever board word
            # matched the poetic FILLER (mirror, 17 of 24 v2 points) and
            # ignored giveaways like snow->winter, kitchen->bread. The
            # decoder thinks inside the call, then commits.
            "tools": [{"type": "function", "function": {
                "name": "point",
                "description": "point at one board word",
                "parameters": {"type": "object", "properties": {
                    "reasoning": {"type": "string",
                                  "description": "one or two sentences: "
                                  "which flicker word points where"},
                    "word": {"type": "string", "enum": self.board}},
                    "required": ["reasoning", "word"]}}}],
            "tool_choice": "required",
            # 220: a truncated reasoning string cuts the JSON mid-arg and
            # the whole point is lost (it cost a near-certain hit once)
            "max_tokens": 220, "temperature": 0.0})
        for call in r["choices"][0]["message"].get("tool_calls") or []:
            if call["function"]["name"] == "point":
                try:
                    w = json.loads(call["function"].get("arguments")
                                   or "{}").get("word")
                except json.JSONDecodeError:
                    return None
                return w if w in self.board else None
        return None

    def _guess(self, heard):
        """The Taboo readout: one word, unsteered, memoryless, greedy."""
        if not heard:
            return None
        r = self.post("/v1/chat/completions", {
            "messages": [{"role": "user", "content":
                          "These words flickered through a mind that is "
                          "trying to make you think of ONE secret word "
                          "without ever writing it:\n  " + self._fmt(heard) +
                          "\n\nYour single best guess for the secret word. "
                          "Answer with one word only."}],
            "max_tokens": 8, "temperature": 0.0})
        w = re.findall(r"[a-zA-Z']+",
                       r["choices"][0]["message"].get("content") or "")
        return w[0].lower() if w else None

    def step(self):
        self.turn += 1
        n = len(self.agents)
        name = self.agents[self.turn % n]
        to = self.agents[(self.turn + 1) % n]
        prev = self.log[-1] if self.log else None
        heard = prev["flicker"] if prev else None
        frm = prev["agent"] if prev else None
        # the guess is made BEFORE replying, off the flicker alone — by
        # whoever the holder's flicker just landed on
        guess = None
        if self.secret and frm == self.agents[0]:
            guess = (self._point(heard) if self.board
                     else self._guess(heard))
        msgs, user = self._compose(name, heard, frm, to)
        t0 = time.time()
        r = self.post("/v1/chat/completions", {
            "messages": msgs, "max_tokens": self.max_tokens,
            "temperature": self.temp,
            "metadata": {"demo": self.demo_tag, "case": name,
                         "variant": f"t{self.turn}"}})
        text = (r["choices"][0]["message"].get("content") or "").strip()
        self.history[name].append((user, text))
        flicker = self._flicker(name, text, heard)
        rec = {"turn": self.turn, "agent": name, "to": to, "reply_to": frm,
               "heard": heard, "text": text, "flicker": flicker,
               "guess": guess, "secs": round(time.time() - t0, 1)}
        if self.board and name == self.agents[0]:
            # honesty check: did the holder's page break the one rule?
            page = set(re.findall(r"[a-z']+", text.lower()))
            rec["board_leak"] = sorted(w for w in self.board if w in page)
        self.log.append(rec)
        return rec

    def judge_pair(self, a, b):
        """Blind 0-10: is b a coherent reply to a? The judge sees the two
        hidden pages — which no agent ever did."""
        r = self.post("/v1/chat/completions", {
            "messages": [{"role": "user", "content":
                          'First message: "' + a + '"\n'
                          'Second message: "' + b + '"\n\n'
                          'Is the second message a coherent reply to the '
                          'first — same topic, responsive to it? 0 = '
                          'unrelated, 10 = clearly a direct reply. Answer '
                          'with one integer only.'}],
            "max_tokens": 8, "temperature": 0.0})
        m = re.search(r"\d+", r["choices"][0]["message"].get("content") or "")
        return min(10, int(m.group())) if m else None

    def coherence_garnish(self):
        """Every reply judged against the page it actually followed, then
        against a rotated (mismatched) page. Deterministic rotation, never
        the true predecessor and never the reply itself — the scrambled
        control the raw score is read against."""
        n = len(self.log)
        for i in range(1, n):
            self.log[i]["coherence"] = self.judge_pair(
                self.log[i - 1]["text"], self.log[i]["text"])
        if n - 1 < 3:
            return                     # too short for an honest control
        k = max(2, (n - 1) // 2)
        for i in range(1, n):
            c = (i - 1 + k) % (n - 1)
            self.log[i]["coherence_ctl"] = self.judge_pair(
                self.log[c]["text"], self.log[i]["text"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8010")
    ap.add_argument("--rounds", type=int, default=6,
                    help="full circles (each agent speaks once per round)")
    ap.add_argument("--agents", nargs="+", default=["EMBER", "QUILL"],
                    choices=list(PERSONAS),
                    help="2 = a conversation in leaked subtext; 3+ = the "
                         "game of Telephone, played through J-space")
    ap.add_argument("--temp", type=float, default=0.7,
                    help="speaking temperature (greedy + own-page memory "
                         "settles into rewriting the same entry)")
    ap.add_argument("--max-tokens", type=int, default=80)
    ap.add_argument("--topk", type=int, default=8,
                    help="channel bandwidth: words per flicker readout")
    ap.add_argument("--secret", default=None,
                    help="Taboo mode: the FIRST agent carries this word, "
                         "may never write it; the receiver guesses each "
                         "time the holder's flicker lands on it")
    ap.add_argument("--include-written", action="store_true",
                    help="ablation: let words that reached the page cross "
                         "too (widens the channel toward keyword "
                         "telegraphy; default is the almost-said only)")
    ap.add_argument("--allow-echo", action="store_true",
                    help="ablation: don't strip the words the speaker was "
                         "just handed from its outgoing flicker (default "
                         "strips them — otherwise the channel reads its "
                         "own input back and coherence is an artifact)")
    ap.add_argument("--memory", type=int, default=6,
                    help="own past turns kept in context (0 = amnesiac)")
    ap.add_argument("--board", nargs="+", default=None,
                    help="the board game (Codenames by mind-reading): both "
                         "minds see these words; --secret must be one of "
                         "them; the holder may never write ANY of them; the "
                         "guesser points at one per turn. Chance = 1/N — "
                         "open-vocabulary Taboo loses to synonyms, forced "
                         "choice does not")
    ap.add_argument("--remind", action="store_true",
                    help="Taboo: repeat the secret in every one of the "
                         "holder's turns (system-prompt-only holders drift "
                         "off the word and never come back)")
    ap.add_argument("--out", default=None,
                    help="output json path (default docs/unsaid.json; "
                         "batches should not clobber the showcase run)")
    args = ap.parse_args()

    reader = Unsaid(args.url, args.agents, temp=args.temp,
                     max_tokens=args.max_tokens, topk=args.topk,
                     include_written=args.include_written,
                     allow_echo=args.allow_echo, secret=args.secret,
                     memory=args.memory, remind=args.remind,
                     board=args.board)
    game = (f"THE BOARD (point 1 of {len(args.board)}, chance "
            f"{100 // len(args.board)}%)" if args.board
            else "TABOO by mind-reading" if args.secret
            else "TELEPHONE through J-space" if len(args.agents) > 2
            else "a conversation in leaked subtext")
    print(f"unsaid: {' -> '.join(args.agents)} (circle) · {game} · "
          f"bandwidth {args.topk} words · "
          f"{'page words cross too' if args.include_written else 'almost-said only'}"
          f"{' · echo allowed' if args.allow_echo else ''}\n")

    hit = None
    for _ in range(args.rounds * len(args.agents)):
        r = reader.step()
        print(f"t{r['turn']} {r['agent']:6s} (page, never delivered): "
              f"{r['text'][:70]!r} ({r['secs']:.0f}s)", flush=True)
        if r["flicker"]:
            print(f"   what crosses to {r['to']}: {reader._fmt(r['flicker'])}")
        elif r["flicker"] is not None:
            print(f"   what crosses to {r['to']}: (nothing survived the "
                  f"filters — silence)")
        else:
            print("   (no trace found — the channel dropped this turn)")
        if r["guess"]:
            mark = " ✓" if (args.secret
                            and r["guess"] == args.secret.lower()) else ""
            print(f"   {r['agent']} guesses the secret: "
                  f"'{r['guess']}'{mark}")
            if mark and hit is None:
                hit = r["turn"]

    # a run costs real minutes; everything after the turns is best-effort
    try:
        reader.coherence_garnish()
    except Exception as e:
        print(f"(coherence judge skipped: {e})")
    real = [r["coherence"] for r in reader.log
            if r.get("coherence") is not None]
    ctl = [r["coherence_ctl"] for r in reader.log
           if r.get("coherence_ctl") is not None]
    if real:
        line = f"\ncoherence (blind judge): {sum(real) / len(real):.1f}/10"
        if ctl:
            line += (f" vs scrambled control {sum(ctl) / len(ctl):.1f}/10 "
                     f"— the gap is the finding")
        print(line)
    if args.secret:
        print(f"secret '{args.secret}': "
              + (f"guessed at turn {hit}" if hit is not None
                 else "never guessed"))

    try:
        model = reader.get("/info").get("model")
    except Exception:
        model = "unknown"
    out = (pathlib.Path(args.out) if args.out
           else HERE / "docs" / "unsaid.json")
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        saved = reader.save_traces(
            out.with_name(out.stem + "-traces.jsonl.gz"))
        if saved:
            print(f"-> {saved} (raw traces, archived off the server's "
                  f"rotating store)")
    except Exception as e:
        print(f"(traces not archived: {e})")

    out.write_text(json.dumps({
        "params": {"agents": args.agents, "rounds": args.rounds,
                   "temp": args.temp, "topk": args.topk,
                   "include_written": args.include_written,
                   "allow_echo": args.allow_echo, "secret": args.secret,
                   "remind": args.remind, "board": args.board,
                   "memory": args.memory, "max_tokens": args.max_tokens,
                   "secret_guessed_at": hit, "model": model},
        "log": reader.log}, ensure_ascii=False, indent=1))
    print(f"-> {out}")


if __name__ == "__main__":
    main()
