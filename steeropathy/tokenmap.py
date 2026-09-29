"""tokenmap: the model's vocabulary as a map, saved once per model.

vocabmap places our sentence-built sliders on the J-lens token directions
and prints the nearest words. This saves the map itself: every readable
word of the vocabulary as a unit direction at one layer, d_t = J_lᵀ · W_U[t]
(Gurnee, Sofroniew et al. 2026), so that orient can read any vector as
words, turn words into a vector, and walk from a word to its neighbours
without a server. Built on CPU in a minute where the lens and the weights
live (aorus):

    python -m steeropathy.tokenmap --lens lenses/qwen3-4b-instruct-2507.jlens.pt \\
        --unembed ~/.cache/huggingface/hub/models--Qwen--Qwen3-4B-Instruct-2507/snapshots/*/model-00001-of-00003.safetensors \\
        --tokenizer ~/.cache/huggingface/hub/models--Qwen--Qwen3-4B-Instruct-2507/snapshots/*/ \\
        --layer 21 --out data/tokenmap-qwen3-4b-l21.pt

The file holds {"model", "layer", "words": [...], "ids": [...], "D": fp16 [n_words, d]}.
About 180 MB for the 4B; it stays out of git (data/ is ignored).
"""
from __future__ import annotations

import argparse
import glob
import pathlib

import torch

from .vocabmap import load_unembed, word_tokens


def build(lens: str, unembed: str, tokenizer: str, layer: int, model: str | None = None):
    art = torch.load(lens, map_location="cpu", weights_only=True)
    J = art["J"].float()
    if layer >= J.shape[0]:
        raise SystemExit(f"layer {layer} but the lens has {J.shape[0]} layers")
    Jl = J[layer]
    del J
    from transformers import AutoTokenizer
    tok = AutoTokenizer.from_pretrained(glob.glob(tokenizer)[0])
    W = load_unembed(unembed)
    ids, words = word_tokens(tok, W.shape[0])
    D = W[ids] @ Jl                                   # rows W_U[t]ᵀ J_l  = (J_lᵀ W_U[t])ᵀ
    D = D / (D.norm(dim=-1, keepdim=True) + 1e-8)
    return {"model": model or art.get("model") or "", "layer": layer, "words": words,
            "ids": ids.tolist(), "D": D.to(torch.float16)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--lens", required=True)
    ap.add_argument("--unembed", required=True)
    ap.add_argument("--tokenizer", required=True)
    ap.add_argument("--layer", type=int, required=True)
    ap.add_argument("--model", default=None)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    m = build(a.lens, a.unembed, a.tokenizer, a.layer, a.model)
    out = pathlib.Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    torch.save(m, out)
    print(f"{len(m['words'])} words · layer {a.layer} · D {tuple(m['D'].shape)} -> {out}")


if __name__ == "__main__":
    main()
