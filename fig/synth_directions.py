"""New vectors from the geometry of the old ones, no sentences involved.
From the saved directions (fig/plot_directions.py): the principal
components of the set (pc1 is the hidden slider the matrix showed, more vs
less), the mean of the three moods (emotional at all), and sad with its
projection on pc1 removed (pure sad, if there is such a thing). Written as
a direction dict worldof can steer by (`--dict`).

    python fig/synth_directions.py docs/runs/directions-qwen2.5-1.5b-instruct.json
    python -m steeropathy.worldof --dict docs/runs/synth-qwen2.5-1.5b-instruct.json pc1 pc2 emotion sad_pure --strength 3 --placebo --n 8
"""
import json
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).parent.parent


def unit(v):
    v = np.asarray(v, dtype=float)
    return (v / (np.linalg.norm(v) or 1.0)).tolist()


def main():
    src = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else HERE / "docs/runs/directions-qwen2.5-1.5b-instruct.json")
    d = json.loads(src.read_text())
    names = list(d["directions"])
    X = np.array([d["directions"][n] for n in names])            # unit rows
    Xc = X - X.mean(axis=0)
    U, S, Vt = np.linalg.svd(Xc, full_matrices=False)
    pcs = Vt[:3]
    var = (S ** 2 / (S ** 2).sum())[:3]
    # orient pc1 so that "crowded" is positive (more), pc2 so that "sad" is positive
    def orient(pc, anchor):
        return pc if np.dot(pc, X[names.index(anchor)]) >= 0 else -pc
    pc1, pc2, pc3 = orient(pcs[0], "crowded"), orient(pcs[1], "sad"), pcs[2]
    loadings = {n: {"pc1": round(float(np.dot(X[i], pc1)), 2), "pc2": round(float(np.dot(X[i], pc2)), 2)}
                for i, n in enumerate(names)}
    moods = [X[names.index(n)] for n in ("sad", "calm", "angry") if n in names]
    emotion = unit(np.mean(moods, axis=0))
    sad = X[names.index("sad")]
    sad_pure = unit(sad - np.dot(sad, pc1) * pc1)
    crowded = X[names.index("crowded")]
    crowded_pure = unit(crowded - np.dot(crowded, pc1) * pc1)
    out = {"model": d["model"], "layer": d["layer"], "from": str(src.name),
           "explained": [round(float(v), 3) for v in var], "loadings": loadings,
           "directions": {"pc1": unit(pc1), "pc2": unit(pc2), "pc3": unit(pc3),
                          "emotion": emotion, "sad_pure": sad_pure, "crowded_pure": crowded_pure}}
    dst = HERE / "docs/runs" / src.name.replace("directions-", "synth-")
    dst.write_text(json.dumps(out))
    print("explained variance pc1..3:", out["explained"])
    for k in ("pc1", "pc2"):
        top = sorted(loadings.items(), key=lambda kv: -kv[1][k])
        print(f"{k}: + " + ", ".join(f"{n} {v[k]}" for n, v in top[:5]) + "   | − " + ", ".join(f"{n} {v[k]}" for n, v in top[-5:]))
    print("sad·pc1", round(float(np.dot(sad, pc1)), 2), "· sad_pure·sad", round(float(np.dot(sad_pure, sad)), 2))
    print(dst)


if __name__ == "__main__":
    main()
