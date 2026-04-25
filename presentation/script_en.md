# Presentation script — Side-Channel-Secure ARM32 Instruction Scheduling

**Target:** ~10 min oral defense (INFO-H410, ULB)
**Speaker:** Mohamed Tajani
**Deck:** `INFO-H410_presentation.pptx` (12 slides)

---

## Timing budget

| # | Slide                       | Budget | Cumulative |
|---|-----------------------------|--------|------------|
| 1 | Title                       | 0:30   | 0:30       |
| 2 | The problem                 | 1:10   | 1:40       |
| 3 | Formal problem              | 1:00   | 2:40       |
| 4 | Why three AI techniques?    | 0:50   | 3:30       |
| 5 | Approach A — Bayesian       | 1:30   | 5:00       |
| 6 | Approach B — CSP            | 1:30   | 6:30       |
| 7 | Approach C — MDP (brief)    | 0:50   | 7:20       |
| 8 | Experimental setup          | 0:40   | 8:00       |
| 9 | Results                     | 1:10   | 9:10       |
| 10 | Trade-offs                 | 0:40   | 9:50       |
| 11 | Conclusion                 | 0:50   | 10:40      |
| 12 | Q&A                        | —      | —          |

If running long: cut slide 8 to 20 s and skip the second example on slide 5.

---

## Slide 1 — Title (0:30)

Good morning. My INFO-H410 project is on **ARM32 instruction scheduling resistant to side-channel attacks**. The one-line summary: a naive compiler can destroy masked cryptographic protections simply by placing two instructions too close in the pipeline. I compare three AI families to fix this: Bayesian inference, constraint satisfaction, and reinforcement learning.

---

## Slide 2 — The problem (1:10)

Boolean masking is a classic shield in embedded crypto. We split a secret `s` into two shares `A` and `B` such that `s = A ⊕ B`. As long as we never manipulate `A` and `B` at the same time, an attacker measuring the power consumption only sees noise.

**The catch**: on a Cortex-M3 or M4, the pipeline is in-order, single-issue. If two instructions touching `A` and then `B` are separated by less than `k` cycles, the register file holds both intermediates simultaneously. The Hamming distance between them leaks into the power trace — protection broken.

[*Point at the schematic*] Here, a 6-cycle block. The orange and blue boxes are the two shares. On the left they're adjacent: leakage. On the right, two NOPs have been inserted — `Δt ≥ k`, safe.

The practical cost: Kocher 1999 and 25 years of follow-up literature show that a masked AES key can be recovered in minutes if the scheduler did nothing for us.

---

## Slide 3 — Formal problem (1:00)

We can frame this as a constrained optimization problem. We have a block of `n` instructions, and we want to assign a start cycle `tᵢ` to each, under three families of constraints:

- **RAW** — Read-After-Write. If `j` depends on `i`, then `j` cannot start before `i` finishes. Standard.
- **SEC** — the masking-specific constraint: for two instructions touching different shares, `|tᵢ − tⱼ| ≥ k`.
- **SLOT** — one slot per cycle. In-order pipeline.

The objective is to **minimize the makespan**: total cycle count. Practically, this is equivalent to minimizing the number of injected NOPs, because a NOP is a wasted cycle.

And to be precise — this is **NP-hard**. Polynomial reduction from scheduling-with-delays, which is itself NP-hard. So no guaranteed polynomial algorithm — which is exactly the kind of problem AI techniques are designed for.

---

## Slide 4 — Why three AI techniques? (0:50)

Three paradigms, because the problem touches three different facets of AI:

1. **Bayesian** — leakage is not binary. At `Δt = 1` cycle, leakage is near-certain. At `Δt = 4`, negligible. Continuous, *soft* model. Exactly what a Bayesian network encodes well.

2. **CSP** — when you want a *hard*, optimal guarantee, you encode RAW + SEC + SLOT as constraints and let a modern SAT solver (CP-SAT) do the work. No learning, declarative reasoning.

3. **MDP / DQN** — choosing which instruction to issue at each cycle is exactly a sequential decision problem: an MDP. We learn a *policy* that potentially generalizes to new block distributions.

Three angles, three different trade-offs. That's what makes the comparison interesting.

---

## Slide 5 — Approach A: Bayesian (1:30)

**Core idea**: safety is not binary. The pipeline behaves like a discharging capacitor — correlation between two registers decays gradually with temporal distance.

[*Point at the CPT*] I encode this as a **conditional probability table**. At `Δt = 1`, the leakage probability is ≈ 0.95. At `Δt = 2`, 0.50. At `Δt = 3`, 0.10. Beyond 4, negligible. These values come from the Hamming-distance leakage literature — they can be recalibrated on real hardware.

[*Point at the algorithm on the right*] At each cycle, the scheduler:
1. Computes the **marginal expected leakage** `E[L]` for every data-ready candidate.
2. Picks the candidate that minimizes `E[L]`.
3. If even the best candidate exceeds a threshold τ — typically 0.15 — we inject a NOP. The time gap grows, the risk falls back below τ.

Cost: `O(n²)` per block, **no training**. Immediately deployable. And the threshold τ gives the compiler a knob to trade security against code density.

---

## Slide 6 — Approach B: CSP (1:30)

CSP is the most *honest* approach: we tell the solver exactly what we want.

[*Point at encoding on the left*] **Variables**: one integer `tᵢ` per instruction, bounded by `T_max`. `T_max` comes from a greedy warm-start, so it's a tight upper bound — the solver doesn't explore a ridiculous space.

The interesting constraint is **SEC**. A minimum distance `|tᵢ − tⱼ| ≥ k` is not linear — it's a disjunction. CP-SAT supports this natively via a **reified disjunction**:

`(t_A − t_B ≥ k) ∨ (t_B − t_A ≥ k)`

The solver introduces a Boolean variable that picks the branch and propagates.

[*Point at the solver on the right*] Backend: **Google OR-Tools CP-SAT**. Modern SAT, propagation, CDCL clause learning, 4 parallel workers. For `n = 10`, we prove optimality in tens of ms. At `n ≥ 30`, we hit a 15-second timeout — the returned solution is feasible but optimality is not proven. Important methodological honesty.

Fallback: `python-constraint`, pure backtracking, for environments without OR-Tools — usable up to `n ≈ 15`.

---

## Slide 7 — Approach C: MDP / DQN (0:50)

Scheduling at a given cycle is an **MDP**: *state*, *action*, *reward*.

- **State**: a 6-D feature vector invariant to block size — fraction of remaining work, distances to last `A` and `B`, ready-queue size, critical-path length. Crucially: invariant to `n`, so a single policy can serve all block sizes.
- **Action**: pick a *ready* instruction or insert a NOP.
- **Reward**: `−1` per cycle, **`−100`** per violation (rescaled), `+50` on completion.

Training stack: MLP Q-network on PyTorch, replay buffer 10 000, target network refreshed every 200 steps, decaying ε-greedy, Huber loss with gradient clipping.

[*Point at the green banner*] **Reward-shaping story** — the original penalty (`−10` / violation) was a trap: at large `n`, the cumulative NOP cost (`−1` per cycle, ≥ `k` cycles per pair) exceeded the per-violation penalty, so the agent rationally tolerated leakage. Rescaling the penalty to `−100` restores **100 % valid schedules at `n = 10`, within 6 % of the CSP optimum**. The ablation is in the report — it's a clean negative-then-positive result, and a reminder that reward shaping is half the work in RL.

---

## Slide 8 — Experimental setup (0:40)

Simple, reproducible setup:

- **Sizes**: `n ∈ {10, 30, 50}` instructions per block.
- **k = 3** — standard security distance for Cortex-M pipelines.
- **3 seeds**: 42, 43, 44. Each `(n, seed)` generates exactly the same block for all three solvers — strictly fair comparison.
- **Metrics**: makespan in cycles, NOP count, expected leakage `E[L]`, wall-clock time. For the MDP, training time is reported separately.

---

## Slide 9 — Results (1:10)

[*Read the table left-to-right, top-to-bottom*]

For `n = 10`, the three valid approaches are essentially tied. Bayesian and CSP both land at `11.0` cycles with `1.0` NOP. The MDP **with rescaled reward** (`★`) lands at `11.7` cycles — within 6 % of the CSP optimum, and 100 % valid. Same row, the MDP **with default reward** (`†`): looks great on cycles (`10.3`!) but `0 %` valid — it cheated by violating SEC.

For `n = 30` and `n = 50`:

- **CSP** finds the tightest makespan — `30.0` and `50.0` cycles — with zero NOPs. But it hits the 15-second timeout for large blocks (asterisk on the cycle column): solution feasible, optimality not proven.
- **Bayesian** is sub-millisecond, inserts a few more NOPs (`1.7` to `3.0`), keeps `E[L]` controlled by τ, 100 % valid throughout.
- **MDP † (default reward)**: still `0 %` valid — same pathology as at `n = 10`, just worse. The tuned MDP rerun at `n = 30 / 50` is in the future-work section: ~9 GPU-hours end-to-end.

[*Point at the three callouts*] **Bayesian** — fast heuristic. **CSP** — formal guarantee. **MDP ★** — a learnable scheduler, *once you fix the reward*.

---

## Slide 10 — Trade-offs (0:40)

Direct read-out:

- If you need a **strict guarantee** — `k` non-negotiable — CSP. Bayesian is *soft* by construction.
- If you want the **densest code** — minimum NOPs — CSP again.
- If you need **sub-ms inference** in a compiler — Bayesian, no question. CSP times out at `n ≥ 30`.
- **Probabilistic threat model** — bounded residual risk acceptable — Bayesian, because τ is precisely that knob.
- **Adding a new business rule** — say a resource constraint on certain slots — CSP, one line of model. Bayesian, you'd need to re-derive the CPT.

So no absolute winner. That's the position defended in the report — these two tools are **complementary**, not competing.

---

## Slide 11 — Conclusion (0:50)

Three takeaways:

1. **Three approaches, three regimes**, validated experimentally. Bayesian for probabilistic threat models and sub-ms inference; CSP for strict guarantees and tight makespans; MDP/DQN as a learnable scheduler **once the reward is correctly shaped**.

2. **Reward-shaping is the lesson**. With the default penalty (`−10` / violation), the agent rationally ignored security at large `n`. Rescaling to `−100` restores 100 % valid schedules at `n = 10`, within 6 % of the CSP optimum. A clean negative-then-positive ablation — the kind of result that's only worth telling because the failure was diagnosed, not papered over.

3. **Logical next steps**: extend the tuned MDP rerun to `n = 30 / 50`; extract CPTs from real Cortex-M4 power traces rather than from the literature; explore a **CSP + RL hybrid** where CSP acts as a feasibility oracle for the agent. Active research area (NeurIPS 2023 on neuro-symbolic scheduling).

Thank you.

---

## Slide 12 — Q&A

(See cheatsheet below.)

---

# Q&A cheatsheet — likely jury questions

> Answer style: short, factual, cite the code or the literature. If I don't know, I say so.

### 1. Why NP-hard? Reduction from what?

Reduction from **single-machine scheduling with precedence and minimum delays** (Garey & Johnson). Each precedence arc encodes a RAW constraint; each `(A, B)` pair to isolate encodes a SEC constraint. The original problem becomes an instance of mine.

### 2. Why DQN rather than policy gradient (REINFORCE / PPO)?

Three reasons:
1. The action space is **discrete and small** (n_ready ≤ 6 typically) — DQN is a natural fit; policy gradient shines with many or continuous actions.
2. **Sample reuse** via the replay buffer — important under a limited episode budget.
3. More stable, well-documented implementation for a course project.

PPO would be the natural next step if we want to generalize to more diverse block distributions.

### 3. How were the CPT values calibrated?

Initial values from the Hamming-distance leakage literature on Cortex-M pipelines (Mangard, Oswald, Popp 2007; more recent studies on masked AES). These values are **a starting point** — in practice, an industrial user would recalibrate on their target platform with a ChipWhisperer or equivalent.

### 4. What does `k = 3` represent physically?

`k = 3` cycles. On a Cortex-M3/M4 with a 3-stage pipeline (Fetch, Decode, Execute), an instruction sits in the register file for ≈ 1 cycle before the next one reuses it. With `k = 3`, both shares are guaranteed never to be simultaneously in the pipeline or in the forwarding network. Conservative, standard value in the defensive literature.

### 5. Why does CSP time out at 15 s? Just a slow solver?

No. **NP-hard**: at `n = 30`, the brute-force search space is `30!` configurations (~`2.6 × 10³²`). CP-SAT explores this with propagation and clause learning, but worst case stays exponential. The timeout is a practical trade-off: we accept a feasible solution bounded by the warm-start. Beyond that, marginal cost is not worth it.

### 6. Why use *expected leakage* `Σ P(L=1)` rather than an exact metric?

Because real leakage depends on the hardware, the noise, the attack model. `Σ P(L=1)` is a **device-independent expected upper bound**, computable in `O(n²)` from the CPT. Sufficient for comparing schedules against each other. For real deployment, we'd replace it with an MTD (Measurements To Disclosure) on real traces.

### 7. What's the exact MDP status?

The current `benchmark_results.csv` shows the agent ignored the SEC constraint at large `n` (up to 7 violations at `n = 50`, zero NOPs). It's a **diagnosed** failure — not a mystery. Penalty `−10` per violation against a cumulative `−n` cost per NOP cycle: at `n ≥ 10`, the agent correctly computes that violating is cheaper. Trivial fix — penalty rescaled to `−100` — and the rerun is in progress on GPU. The ablation will go into the report.

### 8. Why not a more expressive model than CPT — e.g. a GP, a multi-variable Bayesian network?

Good question. For a single `(A, B)` pair, the marginal CPT suffices because we condition only on `Δt`. To model **correlations across multiple pairs** simultaneously, we'd need a *full Bayesian network* or a GP, and inference becomes more expensive. Conscious trade-off to stay in `O(n²)`.

### 9. How do you validate that solutions are *actually* secure?

Three levels:
1. **Feasibility test**: `validate_schedule()` checks RAW + SEC + SLOT — a *necessary* condition.
2. **Metric `E[L]`** compared across approaches.
3. **Ideally**, empirical validation on hardware (ChipWhisperer + masked AES + DPA / TVLA) — out of scope here, but the natural next step.

### 10. Why not A\* / IDA\* / ILP?

A\* was considered in the early drafts but dropped: no obvious admissible heuristic on SEC, so the branching factor is unmanageable beyond `n ≈ 15`. Pure ILP behaves similarly to CSP — Gurobi could replace CP-SAT, but OR-Tools is free and CP-SAT is already state-of-the-art on MiniZinc benchmarks for this kind of constraint mix (booleans + integers).

### 11. Reproducibility?

`seed = 42, 43, 44`, deterministic blocks per `(n, seed)`, GitHub repo with `Dockerfile`. Environment table in the *Reproducibility* section of the report (precise versions of `ortools`, `pytorch`, etc.). The full pipeline runs as `python experiments/run_all.py`.

### 12. Limitations?

Honestly:
- No validation on real power traces.
- CPT from the literature, not calibrated on a device.
- MDP still in reward-shaping ablation at submission time.
- CSP timeout at large `n` — optimality unproven for `n ≥ 30`.
- Only one `k` tested (`k = 3`) — a sweep over `k ∈ {2, 3, 4, 5}` would be informative.

### 13. If you started over, what would you change?

Start with the MDP reward shaping. That's the part that cost the most wasted compute. And probably implement the CSP + RL hybrid rather than three siloed approaches — that's where current research is heading.

### 14. Is the application context defensive or offensive?

**Strictly defensive**. The project helps a compiler produce masked code that is *more resistant* to side-channel attacks. Nothing here is used to attack.

---

# Speaker notes

- **Breathe** between slides 5–6 (the technical approaches) — they're the densest.
- If a question is very open-ended ("What do you think of …"), take 2 seconds of silence before answering.
- The strongest card is **methodological honesty** about the MDP and the CSP timeout — showing you know the limits beats pretending everything works perfectly.
- In case of demo failure: code is in the GitHub repo, `python experiments/run_all.py --quick` finishes in 2 minutes.
