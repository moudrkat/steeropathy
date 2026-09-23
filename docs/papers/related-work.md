# Related work — latent communication between LLM agents

The corpus of Liu's *Beyond Tokens* survey ([2606.05711](https://arxiv.org/abs/2606.05711))
and its companion list [enochliu98/Awesome-Latent-Communication](https://github.com/enochliu98/Awesome-Latent-Communication),
checked 2026-09-23 (the list and the survey hold the same 18 entries), plus the
adjacent lists [EIT-NLP/Awesome-Latent-CoT](https://github.com/EIT-NLP/Awesome-Latent-CoT)
and [YU-deep/Awesome-Latent-Space](https://github.com/YU-deep/Awesome-Latent-Space).
Coded on Liu's axes. Where steeropathy sits is the last row.

| method | WHAT | WHICH | HOW | trained? | link |
|---|---|---|---|---|---|
| CIPHER (ICLR 2024) | logit-weighted embedding | last→first | concat | no | [2310.06272](https://arxiv.org/abs/2310.06272) |
| AC — Communicating Activations (ICML 2025) | hidden state, selected layer, last token | same layer | addition | no | [2501.14082](https://arxiv.org/abs/2501.14082) |
| Interlat (ACL 2026) | last-layer state sequence | last→first (+proj.) | concat + adapter | yes | [2511.09149](https://arxiv.org/abs/2511.09149) |
| SDE — State Delta Trajectory | per-layer state delta | all→corresponding | addition | no | [2506.19209](https://arxiv.org/abs/2506.19209) |
| ThoughtComm | hidden state | corresponding | gated combination | — | [2510.20733](https://arxiv.org/abs/2510.20733) |
| Mixture of Thoughts | projected hidden states | learned interaction layers | cross-attention | yes | [2509.21164](https://arxiv.org/abs/2509.21164) |
| KVComm (ICLR 2026) | KV-cache, selected layers | selected→selected | prepend | no | [2510.03346](https://arxiv.org/abs/2510.03346) |
| Cache-to-Cache | KV-cache, all layers | all→corresponding | learned fuser | yes | [2510.03215](https://arxiv.org/abs/2510.03215) |
| LatentMAS | KV-cache, prefill+decode | all→corresponding | prepend | no | [2511.20639](https://arxiv.org/abs/2511.20639) |
| Q-KVComm | compressed KV-cache | all→corresponding | prepend | no | [2512.17914](https://arxiv.org/abs/2512.17914) |
| LRAgent (ICML 2026) | KV base + low-rank adapter | same backbone | additive in kernel | no | [2602.01053](https://arxiv.org/abs/2602.01053) |
| RelayCaching | decoding-phase KV | same model | cache restoration | no | [2603.13289](https://arxiv.org/abs/2603.13289) |
| Agent Memory | Q4 KV on disk | same agent | cache restoration | no | [2603.04428](https://arxiv.org/abs/2603.04428) |
| Agent Primitives | inter-primitive KV | same backbone | chaining | no | [2602.03695](https://arxiv.org/abs/2602.03695) |
| Edge LLM Handover | KV over backhaul | same edge LLM | partial re-prefill | no | [2603.28018](https://arxiv.org/abs/2603.28018) |
| Vision Wormhole | hidden state in a visual codec | hub-and-spoke | visual injection | yes | [2602.15382](https://arxiv.org/abs/2602.15382) |
| BIGMAS | shared workspace | common contract | workspace fusion | — | [2603.15371](https://arxiv.org/abs/2603.15371) |
| Five Ws survey (TMLR 2026) | taxonomy | — | — | — | [2602.11583](https://arxiv.org/abs/2602.11583) |
| *boundary:* When Latent Agents Lie | KV + visible text | same checkpoint | injection + integrity | no | [2606.28958](https://arxiv.org/abs/2606.28958) |
| *boundary:* Latent Agents (ACL 2026) | activation subspaces | intra-model | internalised | yes | [ACL](https://aclanthology.org/2026.acl-long.709/) |
| **steeropathy** | one contrast **direction** at one layer (transmit, ecosystem, resonance, zombie, runner-up); **J-space word cloud** read-only (unsaid, warmer); **J-space word directions** written back live (duet) | same model, same layer ± band | addition into the residual stream; live lockstep loop (duet) | no | this repo |

What nobody in the table does, and the benches here do: compare the latent
channel against the sender's own text ([runner-up](../../experiments/runnerup.md));
read the other agent off a vocabulary projection of its layers rather than
its raw state (unsaid, zombie); and close the loop at token level with no
turns ([duet](../../experiments/duet.md)). Whether any of it beats text is
exactly the open question; see [Wenzel 2026](wenzel-2026-latent-communication.md)
for the negative result to beat.
