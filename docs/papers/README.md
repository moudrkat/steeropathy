# Reading notes — latent communication & steering (Sept 2026)

[← back to the lab](../../README.md)

Five papers, one summary each, and what they add up to for this lab. The
full corpus of the field, coded on Liu's axes, is in [related-work.md](related-work.md). The
experiment they suggest is built: [experiments/runnerup.md](../../experiments/runnerup.md)
(the original proposal is in [PROPOSAL-runnerup.md](PROPOSAL-runnerup.md)).

| paper | one line | file |
|---|---|---|
| Singh et al. 2024, *Representation Surgery* (ICML) | the L2-optimal affine steer is a mean-difference translation; covariance matching (MiMiC) does better; push selectively, judge by linear guardedness | [singh-2024-affine-steering.md](singh-2024-affine-steering.md) |
| Zhang et al. 2026, *Locate, Steer, and Improve* (ACL Findings) | mech-interp as Locate → Steer → Improve; J-lens = vocabulary projection with a basis caveat; side effects are a mandatory metric; **no agents anywhere** | [zhang-2026-locate-steer-improve.md](zhang-2026-locate-steer-improve.md) |
| Du et al. 2026, *Interlat* (ACL) | trained channel of last-layer state sequences; beats text on ALFWorld and MATH L5; "text causes premature collapse of the hypotheses" | [du-2026-interlat.md](du-2026-interlat.md) |
| Liu 2026, *Beyond Tokens* (survey) | WHAT / WHICH / HOW taxonomy of 18 latent-comm methods; latent wins only conditionally; auditability and integrity are protocol properties | [liu-2026-beyond-tokens.md](liu-2026-beyond-tokens.md) |
| Wenzel 2026, *Latent Communication…Limits of Text* | text destroys 88% of SAE features but they are surface form; **text ≥ latent on every text-expressible task**; latent can only win on what text can't say | [wenzel-2026-latent-communication.md](wenzel-2026-latent-communication.md) |

## What they add up to

**1. The field has a null we have never run.** Every bench here compares the
vector channel against *nothing* or against a *scrambled vector*. Wenzel
compares latent against **the sender's own text** and finds text wins or ties
on everything he tried. Until a steeropathy bench includes the text channel as
a condition, "they communicate through what they never said" is unfalsified
against the obvious alternative: they'd have done as well saying it.

**2. The field also says where latent should win, and nobody has tested it
directly.** Liu (§4.1.2): a hidden state "encodes not just which token to say
next, but also the alternatives considered, their relative probabilities … all
of this is lost the moment we sample a single token." Du: text forces a
"premature collapse" of the reasoning distribution; latents keep parallel
hypotheses — inferred from a MATH Level-5 accuracy inversion, never measured.
Wenzel: latent wins only on "information that text cannot express". The
alternatives the sampler threw away are exactly that, and exactly what the
J-lens reads. This is the experiment: [runner-up](../../experiments/runnerup.md).

**3. Our recipe has a theorem now.** Singh: `mean(lines) − neutral` is the
L2-optimal linear-guarding steer. It also says what the recipe cannot do: it
moves the mean and leaves the covariance alone, which is why every mood vector
carries the shared intensity component (resonance). Two cheap upgrades:
a distance-gated push (steer only when the receiver sits on the source side)
and **guardedness as the success metric** (after the push, can a linear probe
still separate the receiver's pages from target-class pages?).

**4. Better placebos.** Du's control ladder — cross-task latents, Gaussian with
matched mean+covariance, random orthogonal rotation of the real vector — is
stronger than a random matched-norm vector: the rotation keeps norm and
spectrum and destroys meaning. Adopt `--control rot`.

**5. The J-lens is a vocabulary projection, with that method's caveat**
(Zhang §3.5): it reads what is linearly decodable by the final layer, weaker
mid-depth. Any claim that rests on it should race the plain logit lens (house
rule already) and say which layer was read.

**6. Injection has structural barriers in chat models** (Wenzel §4.4): the BOS
position is an attention sink (35× norm), injection there is ≤3%; tokens
outside the chat template are treated as positional noise. brainscope pushes
at generated positions inside the template, which is the right place; say so
in the docs.

**7. Where we sit on Liu's map:** training-free, same model, one contrast
*direction* as payload (nearest neighbour: SDE's state delta), fused by
addition into the residual stream, with an auditing channel (J-lens) bolted
on. His security section is the offer experiment in protocol language: a
visible commitment that does not match the latent payload, and a receiver
that cannot check. Worth one sentence in "Where this sits".

**8. Side effects are a metric, not a footnote** (Zhang §6). A mood push should
ship with a coherence / over-refusal line. "Does a grieving mind still soothe"
is that line for resonance.

## Small TODOs that fall out (not the experiment)

- README references: add Singh 2024 (theory for the recipe), Wenzel 2026 and
  Du 2026 (the two sides of the latent-vs-text argument), Liu 2026 (map).
- README "Honest notes": one line that the text channel has not yet been run
  as a control, and that runner-up is where it happens.
- `steeropathy/transmit.py`: optional `gate="distance"` (Singh) — push only
  when cos(receiver state − baseline, direction) < 0.
- zombie / resonance: `--control rot` (random orthogonal rotation of the
  real vector), next to the existing placebo.
