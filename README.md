# ARM32 Instruction Scheduler for Masked Cryptography

**INFO-H410 — Artificial Intelligence | ULB**

A Python post-processor that reorders ARM32 instruction blocks to guarantee a **security distance of k cycles** between instructions manipulating different cryptographic shares, thereby mitigating power/timing side-channel leakages in masked implementations.

---

## Problem Statement

In **masked cryptography** (e.g., Boolean masking), a secret s is split into shares A and B such that s = A XOR B. If the compiler places instructions operating on A and B within k pipeline cycles of each other, a power-analysis adversary can recover s through Hamming-distance leakage.

This project implements and compares **three AI scheduling approaches** that reorganise a basic block of ARM32 instructions to enforce the k-cycle security property while minimising total execution time.

---

## Three Approaches

| | **A* Search** | **CSP** | **MDP (Q-Learning)** |
|---|---|---|---|
| **n<=15** | A* exact (optimal) | backtracking + AC-3 | Tabular Q-Learning |
| **n>15** | Beam Search (width=500) | iterative T_max | feature-based policy |
| **Optimal?** | Yes (A* phase) | Yes | Heuristic |
| **Stochastic?** | No | No | Yes (latency +/-1) |

---

## Project Structure

```
arm_scheduler/
    core/           instruction.py, pipeline.py, generator.py
    solvers/        astar.py, csp.py, mdp.py
    evaluation/     benchmark.py, visualizer.py
experiments/        run_all.py
tests/              test_core.py, test_solvers.py
Dockerfile
requirements.txt
```

---

## Quick Start

### Docker (Recommended)
```bash
docker build -t arm-scheduler .
docker run --rm -v "C:\Users\tajani\Cours\AI\Project/experiments:/app/experiments" arm-scheduler
```

### Local Python
```bash
pip install -r requirements.txt
pip install -e .
python experiments/run_all.py --k 3 --sizes 10 30 50 --seeds 42 43 44
```

### Quick Smoke Test
```bash
python experiments/run_all.py --quick
```

### Run Tests
```bash
pytest tests/ -v
```

---

## CLI Reference

```
python experiments/run_all.py [OPTIONS]

--k INT           Security distance in cycles (default: 3)
--sizes INT...    Block sizes (default: 10 30 50)
--seeds INT...    Random seeds (default: 42 43 44)
--episodes INT    MDP training episodes (default: 5000)
--stochastic      Enable stochastic latency in MDP
--methods STR...  astar csp mdp (default: all)
--quick           Smoke test: n=10, seed=42, episodes=300
--no-plots        Skip figure generation
```

---

## Security Model

- In-order ARM Cortex-M pipeline (1 instruction/cycle)
- Constraint: |start(i) - start(j)| >= k for pairs with share(i) != share(j)
- k is a configurable parameter (default k=3)
- Static validation applied to every produced schedule

---

*INFO-H410 — Intelligence Artificielle, ULB, 2025-2026*
