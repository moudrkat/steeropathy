"""vocabmap: name the sliders with the model's own vocabulary.

brainscope's J-lens gives every vocabulary token a steering direction,
d_t = J_lᵀ · W_U[t]: the activation pattern at layer l whose growth most
raises the token's *future* logit (Gurnee, Sofroniew et al. 2026). That is
a map with thousands of named points, built from no sentences at all. A
slider we built from sentences (crowded − empty, at layer l) can be placed
on it: its cosine with every token direction, and the words at the top are
what the model calls the slider. Read the other way, the top words are
the direct-logit reading of the transported vector, W_U · (J_l v).

Runs where the lens and the unembedding live (aorus), on CPU, in a minute:

    python -m steeropathy.vocabmap docs/runs/directions-qwen3-4b-instruct-2507.json \\
        --lens lenses/qwen3-4b-instruct-2507.jlens.pt \\
        --unembed ~/.cache/huggingface/hub/models--Qwen--Qwen3-4B-Instruct-2507/snapshots/*/model-00001-of-00003.safetensors \\
        --tokenizer ~/.cache/huggingface/hub/models--Qwen--Qwen3-4B-Instruct-2507/snapshots/*/ \\
        --out docs/runs/vocabmap-qwen3-4b.json

No server, no generation: the sliders' vectors come from the json that
fig/plot_directions.py wrote when it captured them on the same model.

The honesty: the map is first-order (a Jacobian), the tokens are single
pieces, and a slider's nearest words say what the model is disposed to
*say* under it, which is not the same as what it draws. The page stays the
readout; this names the axes.
"""
from __future__ import annotations

import argparse
import glob
import json
import pathlib
import re

import torch


def load_unembed(path: str) -> torch.Tensor:
    from safetensors import safe_open
    path = glob.glob(path)[0]
    with safe_open(path, framework="pt", device="cpu") as f:
        for key in ("lm_head.weight", "model.embed_tokens.weight"):
            if key in f.keys():
                return f.get_tensor(key).float()
    raise SystemExit(f"no unembedding in {path}")


def word_tokens(tok, vocab_size: int):
    """The tokens that are a plain word with a leading space, three letters or more: the readable part of the vocabulary."""
    ids, words = [], []
    for i in range(vocab_size):
        s = tok.decode([i])
        if re.fullmatch(r" [A-Za-z][a-z]{2,}", s):
            ids.append(i)
            words.append(s.strip().lower())
    return torch.tensor(ids), words


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("directions", help="json from fig/plot_directions.py: {model, layer, directions: {name: [d]}}")
    ap.add_argument("--lens", required=True)
    ap.add_argument("--unembed", required=True, help="safetensors shard holding lm_head.weight or the tied embed_tokens")
    ap.add_argument("--tokenizer", required=True)
    ap.add_argument("--layer", type=int, default=None, help="lens layer to place the sliders at (default: the json's layer)")
    ap.add_argument("--top", type=int, default=25)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    d = json.loads(pathlib.Path(a.directions).read_text())
    layer = a.layer if a.layer is not None else int(d["layer"])
    names = list(d["directions"])
    V = torch.tensor([d["directions"][n] for n in names], dtype=torch.float32)   # [k, d]
    V = V / V.norm(dim=-1, keepdim=True)

    art = torch.load(a.lens, map_location="cpu", weights_only=True)
    J = art["J"].float()                                                          # [n_layers, d, d]
    if layer >= J.shape[0]:
        raise SystemExit(f"layer {layer} but the lens has {J.shape[0]} layers")
    Jl = J[layer]
    del J

    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(glob.glob(a.tokenizer)[0])
    W = load_unembed(a.unembed)                                                   # [vocab, d]
    ids, words = word_tokens(tok, W.shape[0])
    Ww = W[ids]                                                                   # [n_words, d]
    print(f"{len(names)} sliders · layer {layer} · {len(words)} word tokens · lens {tuple(Jl.shape)}", flush=True)

    # token directions at this layer: d_t = J_lᵀ W_U[t], unit-normed
    D = Ww @ Jl                                                                   # [n_words, d]  (rows: W_U[t]ᵀ J_l)
    Dn = D / (D.norm(dim=-1, keepdim=True) + 1e-8)
    cos = V @ Dn.T                                                                # [k, n_words]
    # and the direct reading: W_U · (J_l v)
    logit = (V @ Jl.T) @ Ww.T                                                     # [k, n_words]

    out = {"model": d.get("model"), "layer": layer, "n_words": len(words), "sliders": {}}
    for i, n in enumerate(names):
        top = torch.topk(cos[i], a.top)
        bot = torch.topk(-cos[i], a.top)
        up = torch.topk(logit[i], a.top)
        out["sliders"][n] = {
            "nearest": [(words[j], round(float(c), 3)) for c, j in zip(top.values, top.indices)],
            "farthest": [(words[j], round(-float(c), 3)) for c, j in zip(bot.values, bot.indices)],
            "says": [(words[j], round(float(c), 2)) for c, j in zip(up.values, up.indices)],
        }
        print(f"\n{n}")
        print("  nearest  " + ", ".join(f"{w} {c:+.2f}" for w, c in out["sliders"][n]["nearest"][:12]))
        print("  farthest " + ", ".join(f"{w} {c:+.2f}" for w, c in out["sliders"][n]["farthest"][:8]))
        print("  says     " + ", ".join(w for w, _ in out["sliders"][n]["says"][:12]))
    # the sliders against each other on the map: cosine of their word-profiles
    P = cos / (cos.norm(dim=-1, keepdim=True) + 1e-8)
    out["profile_cos"] = {n: {m: round(float((P[i] * P[j]).sum()), 3) for j, m in enumerate(names)} for i, n in enumerate(names)}
    if a.out:
        pathlib.Path(a.out).write_text(json.dumps(out, ensure_ascii=False, indent=1))
        print(f"\n-> {a.out}")


if __name__ == "__main__":
    main()
