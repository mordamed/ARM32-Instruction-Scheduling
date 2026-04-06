# ARM32 Instruction Scheduler for Masked Cryptography

**INFO-H410 — Artificial Intelligence | ULB**

A Python tool that reorders ARM32 instruction blocks to mitigate power/timing side-channel leakages in masked implementations. It balances execution speed with a security risk model.

---

## Three Scheduling Approaches

This project compares three distinct AI methodologies:

| | **A: Bayesian Inference** | **B: CSP (OR-Tools)** | **C: MDP (Deep Q-Learning)** |
|---|---|---|---|
| **Paradigm** | Probabilistic Risk Model | Combinatorial Optimization | Reinforcement Learning |
| **Logic** | Greedy + Risk Threshold ($\tau$) | Constraint Programming (SAT) | Neural Policy (DQN on GPU) |
| **Security** | Expected Leakage $E(L)$ | Hard Distance $k$ (Safe) | Reward-driven (Heuristic) |
| **Speed** | Instant (<1ms) | Optimal (~1s) | Real-time Inference (<1ms) |

- **Bayesian**: Models the physical "capacitor discharge" in the pipeline. Injects NOPs only when cumulative risk exceeds $\tau$.
- **CSP**: Guarantees a strict cycle distance $k$ between different shares. Finds the mathematically shortest possible valid schedule.
- **MDP**: Trains a neural network to "play" the scheduling game. Learns complex heuristics through thousands of self-play episodes.

---

## Quick Start

### Windows (GPU Enabled)
If you have an NVIDIA GPU, use the provided batch file for an optimized environment:
```powershell
./run_gpu_windows.bat
```

### Docker
```bash
docker build -t arm-scheduler .
docker run --rm -v "$(pwd)/experiments:/app/experiments" arm-scheduler
```

### Manual Install
```bash
pip install -r requirements.txt
pip install -e .
python experiments/run_all.py --methods bayesian csp mdp --k 3
```

---

## Project Structure

```
arm_scheduler/
    core/           instruction.py (ARM32 ISA), pipeline.py (RAW/Security Logic)
    solvers/        bayesian.py, csp.py, mdp.py
    evaluation/     benchmark.py, visualizer.py (Graphics)
experiments/        run_all.py (CLI entry point)
report/             main.tex (Academic Report)
```

---

## Security Model

We model an in-order ARM Cortex-M pipeline. The primary security constraint is the **Temporal Distance** between instructions manipulating different shares (e.g. Share A and Share B).
- **Strict Model**: $|t_i - t_j| \ge k$.
- **Probabilistic Model**: $P(Leakage) = f(\Delta t)$, total risk $\sum P < \tau$.

---

*INFO-H410 — Intelligence Artificielle, ULB, 2025-2026*
