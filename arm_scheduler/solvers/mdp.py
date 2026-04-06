"""
mdp.py — Approach C: MDP with Deep Q-Network (DQN) using PyTorch.

GPU Acceleration
----------------
The DQN uses PyTorch and runs on the best available device:
  - NVIDIA GPU (CUDA) if available → fastest
  - CPU otherwise → still much faster than tabular Q-learning for large n

To enable GPU:
  1. Install CUDA Toolkit 12.x from https://developer.nvidia.com/cuda-downloads
  2. pip install torch --index-url https://download.pytorch.org/whl/cu124

Architecture
------------
We use a paired (state, action) Q-function:

  Q(s, a) = MLP( concat(state_features, action_features) ) → scalar

State features (fixed-size, n-independent):
  - remaining_ratio       : (n - |scheduled|) / n
  - since_A_norm          : min(Δ_A, k+1) / (k+1)   (cycles since last SHARE_A)
  - since_B_norm          : min(Δ_B, k+1) / (k+1)
  - n_ready_norm          : |ready| / n
  - cp_remaining_norm     : max_critical_path / n
  - current_cycle_norm    : cycle / (3n)

Action features (per instruction, fixed-size):
  - share_A               : binary
  - share_B               : binary
  - share_N               : binary
  - latency_norm          : latency / max_latency
  - cp_norm               : critical_path / max_cp

Training uses Experience Replay + Target Network (Double DQN style).

MDP Formulation
---------------
State  S : compact feature vector (6-dim, invariant to block size)
Action A : choose one ready instruction (or NOP if none valid)
Reward R :
  -1    per cycle elapsed
  -10   per security violation
  +50   on full completion
"""

from __future__ import annotations

import random
import time
from collections import deque
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
from tqdm import tqdm

# ---------------------------------------------------------------------------
# PyTorch detection + device selection
# ---------------------------------------------------------------------------
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    _TORCH = True
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
except ImportError:
    _TORCH = False
    DEVICE = None

from ..core.instruction import Instruction, ShareType
from ..core.pipeline import PipelineState
from ..core.generator import generate_block

# ---------------------------------------------------------------------------
# Hyper-parameters
# ---------------------------------------------------------------------------
# DQN
DQN_HIDDEN = 128
DQN_LR = 1e-3
DQN_BATCH = 64
DQN_REPLAY_SIZE = 10_000
DQN_TARGET_UPDATE = 200   # steps between target-net sync
DQN_GAMMA = 0.95
DQN_EPSILON_START = 1.0
DQN_EPSILON_END = 0.05
DQN_EPSILON_DECAY = 0.997
DQN_EPISODES = 5_000

# Tabular fallback (Python 3.14 / no torch)
TABULAR_ALPHA = 0.1
TABULAR_GAMMA = 0.95
TABULAR_EPSILON_START = 1.0
TABULAR_EPSILON_END = 0.05
TABULAR_EPSILON_DECAY = 0.995
TABULAR_EPISODES = 5_000

STOCHASTIC_PROB = 0.2

# State / action feature dimensions (fixed)
STATE_DIM = 6
ACTION_DIM = 5


# ===========================================================================
# Scheduling Environment (shared by both DQN and tabular)
# ===========================================================================

class SchedulerEnv:
    """Gym-like scheduling environment for one instruction block."""

    def __init__(
        self,
        instructions: List[Instruction],
        k: int = 3,
        stochastic: bool = False,
    ) -> None:
        self.instructions = instructions
        self.k = k
        self.stochastic = stochastic
        self.n = len(instructions)
        self.pipeline_state = PipelineState(instructions, k)
        self._max_cp = max(self.pipeline_state._critical_path.values()) if instructions else 1
        self._max_lat = max(i.latency for i in instructions) if instructions else 1
        self.reset()

    def reset(self) -> np.ndarray:
        self.cycle = 0
        self.scheduled: Set[int] = set()
        self.finish_times: Dict[int, int] = {}
        self.placement: Dict[int, int] = {}
        self.last_A = -1
        self.last_B = -1
        self.done = False
        self.total_reward = 0.0
        self.n_violations = 0
        self._eff_lat = {
            i.idx: i.latency + (1 if self.stochastic and random.random() < STOCHASTIC_PROB else 0)
            for i in self.instructions
        }
        return self._state_features()

    def get_actions(self) -> List[Instruction]:
        return self.pipeline_state.get_ready_instructions(
            self.scheduled, self.finish_times, self.cycle
        )

    def get_valid_actions(self) -> List[Instruction]:
        return [
            i for i in self.get_actions()
            if self.pipeline_state.is_security_valid(i, self.cycle, self.placement)
        ]

    def step(self, action_instr: Optional[Instruction]) -> Tuple[np.ndarray, float, bool]:
        assert not self.done
        reward = -1.0

        if action_instr is None:
            self.cycle += 1
        else:
            violated = not self.pipeline_state.is_security_valid(
                action_instr, self.cycle, self.placement
            )
            if violated:
                reward -= 10.0
                self.n_violations += 1
            self.scheduled.add(action_instr.idx)
            self.finish_times[action_instr.idx] = self.cycle + self._eff_lat[action_instr.idx]
            self.placement[action_instr.idx] = self.cycle
            if action_instr.share_type == ShareType.SHARE_A:
                self.last_A = self.cycle
            elif action_instr.share_type == ShareType.SHARE_B:
                self.last_B = self.cycle
            self.cycle += 1

        if len(self.scheduled) == self.n:
            reward += 50.0
            self.done = True

        self.total_reward += reward
        return self._state_features(), reward, self.done

    # ---- Feature encoders ----

    def _state_features(self) -> np.ndarray:
        remaining = self.n - len(self.scheduled)
        since_A = min(self.cycle - self.last_A, self.k + 1) if self.last_A >= 0 else self.k + 1
        since_B = min(self.cycle - self.last_B, self.k + 1) if self.last_B >= 0 else self.k + 1
        n_ready = len(self.get_actions())
        rem_ids = frozenset(
            i.idx for i in self.instructions if i.idx not in self.scheduled
        )
        cp = self.pipeline_state.heuristic(rem_ids)
        norm_cycle = min(self.cycle / max(3 * self.n, 1), 1.0)
        return np.array([
            remaining / max(self.n, 1),
            since_A / max(self.k + 1, 1),
            since_B / max(self.k + 1, 1),
            min(n_ready / max(self.n, 1), 1.0),
            cp / max(self._max_cp, 1),
            norm_cycle,
        ], dtype=np.float32)

    def action_features(self, instr: Instruction) -> np.ndarray:
        share = instr.share_type
        cp = self.pipeline_state._critical_path[instr.idx]
        return np.array([
            float(share == ShareType.SHARE_A),
            float(share == ShareType.SHARE_B),
            float(share == ShareType.NEUTRAL),
            instr.latency / max(self._max_lat, 1),
            cp / max(self._max_cp, 1),
        ], dtype=np.float32)

    # Compact tabular state key (for fallback)
    def _tabular_key(self) -> Tuple:
        remaining = self.n - len(self.scheduled)
        since_A = min(self.cycle - self.last_A, self.k + 1) if self.last_A >= 0 else self.k + 1
        since_B = min(self.cycle - self.last_B, self.k + 1) if self.last_B >= 0 else self.k + 1
        n_ready = min(len(self.get_actions()), 8)
        if self.n <= 20:
            mask = sum(1 << i for i, instr in enumerate(self.instructions)
                       if instr.idx not in self.scheduled)
        else:
            mask = remaining // 5
        return (mask, since_A, since_B, n_ready)


# ===========================================================================
# DQN Network (PyTorch)
# ===========================================================================

if _TORCH:
    class _QNetwork(nn.Module):
        """Q(s, a) = MLP(state_features ∥ action_features) → scalar."""

        def __init__(self, hidden: int = DQN_HIDDEN):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(STATE_DIM + ACTION_DIM, hidden),
                nn.LayerNorm(hidden),
                nn.ReLU(),
                nn.Linear(hidden, hidden // 2),
                nn.ReLU(),
                nn.Linear(hidden // 2, 1),
            )

        def forward(self, state: torch.Tensor, action: torch.Tensor) -> torch.Tensor:
            x = torch.cat([state, action], dim=-1)
            return self.net(x).squeeze(-1)


# ===========================================================================
# DQN Agent (GPU-accelerated when available)
# ===========================================================================

class DQNAgent:
    """Deep Q-Learning agent for the instruction scheduling MDP.

    Uses GPU if torch.cuda.is_available(), otherwise CPU.
    """

    def __init__(
        self,
        k: int = 3,
        hidden: int = DQN_HIDDEN,
        lr: float = DQN_LR,
        gamma: float = DQN_GAMMA,
        batch_size: int = DQN_BATCH,
        replay_size: int = DQN_REPLAY_SIZE,
        target_update: int = DQN_TARGET_UPDATE,
        stochastic: bool = False,
    ) -> None:
        if not _TORCH:
            raise RuntimeError("PyTorch is required for DQNAgent. pip install torch")
        self.k = k
        self.gamma = gamma
        self.batch_size = batch_size
        self.target_update = target_update
        self.stochastic = stochastic
        self.device = DEVICE

        self.q_net = _QNetwork(hidden).to(self.device)
        self.target_net = _QNetwork(hidden).to(self.device)
        self.target_net.load_state_dict(self.q_net.state_dict())
        self.target_net.eval()

        self.optimizer = optim.Adam(self.q_net.parameters(), lr=lr)
        self.loss_fn = nn.HuberLoss()
        self.replay: deque = deque(maxlen=replay_size)
        self._steps = 0

    # ---- Training ----

    def train(
        self,
        instructions: List[Instruction],
        n_episodes: int = DQN_EPISODES,
        verbose: bool = False,
        run_id: str = None,
    ) -> List[float]:
        env = SchedulerEnv(instructions, self.k, self.stochastic)
        episode_rewards: List[float] = []
        eps = DQN_EPSILON_START
        start_episode = 0

        # --- Load Checkpoint ---
        checkpoint_path = None
        if run_id:
            os.makedirs("experiments/checkpoints", exist_ok=True)
            checkpoint_path = f"experiments/checkpoints/mdp_{run_id}.pt"
            if os.path.exists(checkpoint_path):
                try:
                    checkpoint = torch.load(checkpoint_path, map_location=self.device)
                    self.model.load_state_dict(checkpoint['model_state_dict'])
                    self.target_model.load_state_dict(checkpoint['model_state_dict'])
                    self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
                    episode_rewards = checkpoint.get('episode_rewards', [])
                    eps = checkpoint.get('epsilon', DQN_EPSILON_START)
                    start_episode = checkpoint.get('episode', 0) + 1
                    if verbose:
                        print(f"\n[Checkpoint] Resuming '{run_id}' from episode {start_episode}")
                except Exception as e:
                    if verbose:
                        print(f"\n[Checkpoint] Error loading {checkpoint_path}: {e}. Starting from scratch.")

        if start_episode >= n_episodes:
            return episode_rewards

        pbar = tqdm(range(start_episode, n_episodes), desc="  DQN Training", leave=False, disable=not verbose, miniters=20)
        for ep in pbar:
            state_feat = env.reset()
            done = False
            ep_reward = 0.0

            while not done:
                actions = env.get_actions()
                valid = env.get_valid_actions()
                chosen_action = self._select_action(
                    state_feat, env, actions, valid, eps
                )

                next_feat, reward, done = env.step(chosen_action)
                next_actions = env.get_actions()

                # Store transition
                if chosen_action is not None:
                    a_feat = env.action_features(chosen_action)
                    next_a_feats = [env.action_features(a) for a in next_actions] if next_actions else []
                    self.replay.append((
                        state_feat.copy(), a_feat,
                        reward, next_feat.copy(), next_a_feats, done
                    ))

                # Learn
                if len(self.replay) >= self.batch_size:
                    self._update()

                state_feat = next_feat
                ep_reward += reward

            eps = max(DQN_EPSILON_END, eps * DQN_EPSILON_DECAY)
            episode_rewards.append(ep_reward)

            if (ep + 1) % 20 == 0:
                avg = np.mean(episode_rewards[-100:]) if len(episode_rewards) >= 100 else np.mean(episode_rewards)
                pbar.set_postfix(avg_rew=f"{avg:.1f}", eps=f"{eps:.3f}", dev=str(self.device))

            # --- Save Checkpoint ---
            if checkpoint_path and (ep + 1) % 500 == 0:
                torch.save({
                    'episode': ep,
                    'model_state_dict': self.model.state_dict(),
                    'optimizer_state_dict': self.optimizer.state_dict(),
                    'epsilon': eps,
                    'episode_rewards': episode_rewards,
                }, checkpoint_path)

        return episode_rewards

    def _select_action(
        self,
        state_feat: np.ndarray,
        env: SchedulerEnv,
        actions: List[Instruction],
        valid: List[Instruction],
        eps: float,
    ) -> Optional[Instruction]:
        if not actions:
            return None
        if random.random() < eps:
            pool = valid if valid else actions
            return random.choice(pool)
        # Greedy: score all valid (or any) actions
        candidates = valid if valid else actions
        return self._best_action(state_feat, env, candidates)

    @torch.no_grad()
    def _best_action(
        self,
        state_feat: np.ndarray,
        env: SchedulerEnv,
        candidates: List[Instruction],
    ) -> Optional[Instruction]:
        if not candidates:
            return None
        s = torch.tensor(state_feat, dtype=torch.float32, device=self.device).unsqueeze(0)
        s_rep = s.expand(len(candidates), -1)
        a_batch = torch.tensor(
            np.stack([env.action_features(a) for a in candidates]),
            dtype=torch.float32, device=self.device
        )
        q_vals = self.q_net(s_rep, a_batch)
        best = int(q_vals.argmax().item())
        return candidates[best]

    def _update(self) -> None:
        batch = random.sample(self.replay, self.batch_size)
        states, a_feats, rewards, next_states, next_a_feats_list, dones = zip(*batch)

        s = torch.tensor(np.array(states), dtype=torch.float32, device=self.device)
        a = torch.tensor(np.array(a_feats), dtype=torch.float32, device=self.device)
        r = torch.tensor(rewards, dtype=torch.float32, device=self.device)
        done_t = torch.tensor(dones, dtype=torch.float32, device=self.device)

        # Current Q values
        q_current = self.q_net(s, a)

        # Target Q values
        with torch.no_grad():
            max_next_q = torch.zeros(self.batch_size, device=self.device)
            for i, next_a_feats in enumerate(next_a_feats_list):
                if next_a_feats:
                    ns = torch.tensor(next_states[i], dtype=torch.float32, device=self.device)
                    ns_rep = ns.unsqueeze(0).expand(len(next_a_feats), -1)
                    na_batch = torch.tensor(
                        np.array(next_a_feats), dtype=torch.float32, device=self.device
                    )
                    max_next_q[i] = self.target_net(ns_rep, na_batch).max()

            targets = r + self.gamma * max_next_q * (1 - done_t)

        loss = self.loss_fn(q_current, targets)
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.q_net.parameters(), 1.0)
        self.optimizer.step()

        self._steps += 1
        if self._steps % self.target_update == 0:
            self.target_net.load_state_dict(self.q_net.state_dict())

    # ---- Inference ----

    def schedule_greedy(
        self,
        instructions: List[Instruction],
    ) -> Tuple[List[Tuple[int, Optional[Instruction]]], int, Dict]:
        t0 = time.perf_counter()
        env = SchedulerEnv(instructions, self.k, stochastic=False)
        state_feat = env.reset()
        schedule_out: List[Tuple[int, Optional[Instruction]]] = []

        while not env.done:
            valid = env.get_valid_actions()
            actions = env.get_actions()
            if valid:
                chosen = self._best_action(state_feat, env, valid)
            elif actions:
                chosen = self._best_action(state_feat, env, actions)
            else:
                chosen = None

            schedule_out.append((env.cycle, chosen))
            state_feat, _, _ = env.step(chosen)

        nops = sum(1 for _, i in schedule_out if i is None)
        return schedule_out, env.cycle, {
            "method": "dqn",
            "backend": str(self.device),
            "optimal": False,
            "total_cycles": env.cycle,
            "n_nops": nops,
            "n_violations": env.n_violations,
            "wall_time": time.perf_counter() - t0,
        }


# ===========================================================================
# Tabular Q-Learning Agent (fallback when torch is not available)
# ===========================================================================

class QLearningAgent:
    """Tabular Q-Learning fallback (no GPU, works on any Python version)."""

    def __init__(
        self,
        k: int = 3,
        alpha: float = TABULAR_ALPHA,
        gamma: float = TABULAR_GAMMA,
        stochastic: bool = False,
    ) -> None:
        from collections import defaultdict
        self.k = k
        self.alpha = alpha
        self.gamma = gamma
        self.stochastic = stochastic
        self.Q: Dict = defaultdict(lambda: defaultdict(float))

    def train(
        self,
        instructions: List[Instruction],
        n_episodes: int = TABULAR_EPISODES,
        verbose: bool = False,
    ) -> List[float]:
        env = SchedulerEnv(instructions, self.k, self.stochastic)
        episode_rewards: List[float] = []
        eps = TABULAR_EPSILON_START

        for ep in range(n_episodes):
            state = env.reset()
            state_key = env._tabular_key()
            done = False
            ep_reward = 0.0

            while not done:
                actions = env.get_actions()
                n_a = len(actions)
                if random.random() < eps or n_a == 0:
                    action_idx = random.randint(0, n_a - 1) if n_a else None
                else:
                    action_idx = max(range(n_a), key=lambda a: self.Q[state_key][a])

                chosen = actions[action_idx] if action_idx is not None and action_idx < n_a else None
                next_feat, reward, done = env.step(chosen)
                next_key = env._tabular_key()
                n_next = len(env.get_actions())

                if action_idx is not None:
                    max_next = max((self.Q[next_key][a] for a in range(n_next)), default=0.0)
                    old = self.Q[state_key][action_idx]
                    self.Q[state_key][action_idx] = old + self.alpha * (
                        reward + self.gamma * max_next - old
                    )

                state_key = next_key
                ep_reward += reward

            eps = max(TABULAR_EPSILON_END, eps * TABULAR_EPSILON_DECAY)
            episode_rewards.append(ep_reward)

            if verbose and (ep + 1) % 500 == 0:
                avg = np.mean(episode_rewards[-500:])
                print(f"  Ep {ep+1:5d}/{n_episodes}  avg={avg:7.1f}  ε={eps:.3f}  (tabular)")

        return episode_rewards

    def schedule_greedy(
        self,
        instructions: List[Instruction],
    ) -> Tuple[List, int, Dict]:
        t0 = time.perf_counter()
        env = SchedulerEnv(instructions, self.k)
        env.reset()
        schedule_out: List = []

        while not env.done:
            valid = env.get_valid_actions()
            actions = env.get_actions()
            state_key = env._tabular_key()
            pool = valid if valid else actions
            n_a = len(pool)

            if n_a > 0:
                action_idx = max(range(n_a), key=lambda a: self.Q[state_key][a])
                chosen = pool[action_idx]
            else:
                chosen = None

            schedule_out.append((env.cycle, chosen))
            env.step(chosen)

        nops = sum(1 for _, i in schedule_out if i is None)
        return schedule_out, env.cycle, {
            "method": "mdp_tabular",
            "device": "cpu",
            "total_cycles": env.cycle,
            "n_nops": nops,
            "n_violations": env.n_violations,
            "wall_time": time.perf_counter() - t0,
        }


# ===========================================================================
# High-level MDPScheduler wrapper (auto-selects DQN vs tabular)
# ===========================================================================

class MDPScheduler:
    """High-level wrapper that auto-selects DQN (GPU) or tabular Q-Learning.

    Parameters
    ----------
    k          : Security distance.
    n_episodes : Training episodes.
    stochastic : Enable stochastic latency during training.
    force_tabular : Force tabular Q-Learning even if PyTorch is available.
    """

    def __init__(
        self,
        k: int = 3,
        n_episodes: int = DQN_EPISODES,
        stochastic: bool = False,
        force_tabular: bool = False,
    ) -> None:
        self.k = k
        self.n_episodes = n_episodes
        self.stochastic = stochastic
        self.use_dqn = _TORCH and not force_tabular
        self._agent = None

    @property
    def backend(self) -> str:
        if self.use_dqn:
            return f"DQN ({DEVICE})"
        return "Tabular Q-Learning (CPU)"

    def train(
        self,
        instructions: List[Instruction],
        verbose: bool = False,
        run_id: str = None,
    ) -> List[float]:
        """Train the agent on *instructions*. Returns episode reward list."""
        if self._agent is None:
            if self.use_dqn:
                self._agent = DQNAgent(k=self.k, stochastic=self.stochastic)
            else:
                self._agent = QLearningAgent(k=self.k, stochastic=self.stochastic)
        
        if self.use_dqn:
            return self._agent.train(instructions, self.n_episodes, verbose=verbose, run_id=run_id)
        else:
            return self._agent.train(instructions, self.n_episodes, verbose=verbose)

    def schedule(
        self,
        instructions: List[Instruction],
    ) -> Tuple[List[Tuple[int, Optional[Instruction]]], int, Dict]:
        """Train (if needed) then schedule. Includes train_time in stats."""
        t_train_start = time.perf_counter()
        if self._agent is None:
            self.train(instructions)
        train_time = time.perf_counter() - t_train_start

        sched, total, stats = self._agent.schedule_greedy(instructions)
        stats["train_time"] = train_time
        stats["method"] = "mdp_dqn" if self.use_dqn else "mdp_tabular"
        stats["backend"] = self.backend
        return sched, total, stats
