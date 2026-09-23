# Novelty search — secondhand, ghosts, worldof (2026-09-23)

A search over arXiv, ACL/ICML/ICLR/COLM/NeurIPS, LessWrong, the HF blog and
GitHub for anything close to: rendering a latent message or a steering vector
as a typed, scored world; runner-up transfer across agents; steering inside
constrained decoding; two models steering each other live. Distances:
identical / very close / related / superficial.

## Closest work, by family

**Rendering internal state as a legible artifact**
- Anthropic, *Visual Features Across Modalities* (Circuits update, Oct 2025) — steering cross-modal SAE features while the model emits SVG/ASCII art changes the drawing. *Related*: a steered model draws, but free-form, no fixed spec, no field scoring, no second mind. https://transformer-circuits.pub/2025/october-update/index.html
- Patchscopes (Ghandeharioun et al., ICML 2024, 2401.06102), SelfIE (2403.10949), LatentQA (2412.08686), Predictive Concept Decoders (2512.15712) — a hidden state verbalised in text. *Related*: secondhand is a Patchscope whose target prompt is a world form and whose "verbalisation" is a page.
- Lindsey, *Emergent Introspective Awareness* (Anthropic, Oct 2025) + Vogel, *Small Models Can Introspect, Too*; *Steering Awareness* (2511.21399); *Mechanisms of Introspective Awareness* (2603.21396); *Can LLMs Introspect? A Reality Check* (2605.26242) — inject a concept vector, ask the model what it notices. *Related to worldof*: same primitive, yes/no or a name as the readout, not a drawn world.
- Black & Bloom, *Machinic Psychopharmacology* (LessWrong, Jun 2026) — models given steering vectors as tools, steering themselves. *Related to brave-new-world's own control panel.*

**Latent / activation communication between agents**
- Ramesh & Li, *Communicating Activations Between LM Agents* (ICML 2025, 2501.14082) — *very close in mechanism*; accuracy readout.
- Interlat (2511.09149), Cache-to-Cache (2510.03215, ICLR 2026), LatentMAS (2511.20639, ICML 2026), StateBridge (2608.13317, COLM 2026), Vision Wormhole (2602.15382), XKV (2608.20617), See What I See (2606.13594) — channel designs, all accuracy readouts.
- Wenzel 2026 (2607.14103) — dense/SAE/text channels; a side test injects SAE-decoded vectors and scores concept *naming* (39.3 %). *Closest on "what does text lose"*; readout still a label.
- Zhang & Emu, *Do Latent Channels Actually Communicate?* (2607.26773) and Cheng, Das & Ramnath, *When Does Latent Communication Pay?* (2608.04893) — mismatched / random / absent-message controls; gains vanish when the receiver does not need the sender's private information. *Very close in control design*: secondhand's `none / rot / crosstask` are these controls per field of a rendered spec, and the `none` prior + `m:` columns are the answer to Cheng et al.
- Kaur et al., *Beyond the Transcript* (2608.19161) — monitor for covert latent coordination. *Related* in motivation.
- Liu's survey (2606.05711) and the living atlas github.com/edzq/LatentAgentComm — no method with a generated-artifact readout or runner-up transfer.
- Wu & Zhu, *Post-Hoc Sparse Coding of Latent Communication* (2608.10198) — SAE on latent messages, explicitly not decoded to legible form.

**Steering meets structured generation**
- Panahi, *From Golden Gate Bridge to Broken JSON* (HF blog, Feb 2026) — steering a Qwen2.5-0.5B yields 24.4 % valid JSON; "steering is semantic, JSON is a state machine"; fixed with an FSM logits processor, never tries steering only inside values. *Related*: the split brave-new-world/secondhand use (grammar owns syntax, vector owns semantics, every token is a field) is the untested half of his conclusion.
- Gao et al., *What Does Activation Steering Control?* (2608.22985) — CAA often tracks the answer-identifier position, not meaning. *A reason to report the moved-only columns, and a risk for enum-token steering.*
- No paper found on muting steering over scaffolding tokens or steering only in string values.

**Runner-up / alternatives across agents**
- Mixture of Inputs (2505.14827, NeurIPS 2025), Soft Thinking (2505.15778), Coconut (2412.06769) — keep discarded alternatives alive inside *one* model. Nobody measures whether a specific runner-up of A reappears in B.

**Closed-loop two-model coupling**
- *The Bicameral Model* (2605.11167, May 2026) — two frozen LMs in lockstep, bidirectional hidden-state coupling at every step through a trained interface. *Very close to duet* in shape; trained, task-driven, accuracy readout.

**Small model fills a typed spec, engine renders**
- SpatialGrammar (2604.27555), *From Text to DSL* (2605.15865), generative-UI practice (A2UI, Open-JSON-UI, json-render). *Related*: the pattern is not new; brave-new-world's framing (a world with a poem and its own panel, 0.5B in the browser) is its own.

## Verdict

Not new, and to be framed as such: activation-level communication between copies of a model; "text collapses alternatives" as a thesis; mismatched/random/absent controls; inject-a-vector-and-read-the-report; LLM-fills-spec-engine-renders; steering changing a drawn artifact.

New, as far as this search can tell:
1. **The rendered spec as the readout of a latent channel**, scored field by field with per-field controls, and the decomposition of *which* fields text loses.
2. **Ghosts** — A's runner-up (from logprobs at the kind token) reappearing in B via the vector and not via A's text.
3. **worldof** — a catalogue steering vector drawn as a world under a grammar, with placebos.
4. **Steering inside constrained decoding** where every token is a semantic field, dissolving the broken-JSON problem instead of patching it.

Reviewer will raise: same-model judge (answered partly by the cross-model pick); small N; Gao et al. (position tracking); Cheng et al. (gains vanish when B needs nothing from A — say the `none` prior and `m:` columns are exactly that check); Bicameral already couples two models live, so duet must be positioned against it.

Must cite: Ramesh & Li 2025; Zhang & Emu 2026; Cheng, Das & Ramnath 2026; Wenzel 2026; Lindsey 2025. Strongly recommended: Interlat, Liu's survey, Panahi's post, the Anthropic SVG note, Bicameral, Mixture of Inputs.
