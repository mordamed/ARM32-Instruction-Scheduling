"""
astar.py — Approach A: A* Search + Beam Search for ARM32 instruction scheduling.

Strategy
--------
• For blocks of n ≤ MAX_EXACT  instructions: use A* search, which guarantees
  the *optimal* (minimum-cycle) schedule.  The solution serves as a ground-
  truth baseline for evaluating the other two approaches.

• For blocks of n >  MAX_EXACT  instructions: fall back to Beam Search,
  which is A* restricted to a fixed-width frontier.  Beam search loses the
  optimality guarantee but scales to larger blocks while still using the
  same critical-path heuristic.

State representation
--------------------
A search node encodes:
  - scheduled   : frozenset of (idx, start_cycle) pairs already placed
  - finish_times: frozenset of (idx, finish_cycle) — for RAW readiness
  - last_A      : most recent start cycle of a SHARE_A instruction (−1 if none)
  - last_B      : most recent start cycle of a SHARE_B instruction (−1 if none)
  - cycle       : current time slot

The state key used for duplicate detection is:
  (frozenset_of_idx_with_start, last_A, last_B, cycle)

Heuristic h(n)
--------------
  max critical-path length among remaining instructions.
  Admissible (never overestimates), so A* is optimal.
"""

from __future__ import annotations

import heapq
import time
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, List, Optional, Set, Tuple

from ..core.instruction import Instruction, ShareType
from ..core.pipeline import PipelineState

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
MAX_EXACT = 15        # n ≤ this → A* (exact); n > this → Beam Search
BEAM_WIDTH = 500      # number of frontier nodes kept in Beam Search
MAX_STATES = 200_000  # node-expansion budget for A* (safety cap)
TIME_LIMIT = 120.0    # seconds (wall-clock timeout)


# ---------------------------------------------------------------------------
# Search node
# ---------------------------------------------------------------------------

@dataclass(order=True)
class _Node:
    """Priority-queue node for A* / Beam Search.

    Comparison is by (f_cost, tiebreak) so heapq gives the lowest-f node.
    """

    # --- fields used for priority ---
    f: int = field(compare=True)
    tiebreak: int = field(compare=True)

    # --- actual state --- (excluded from comparison)
    g: int = field(compare=False)                           # cost so far (cycles)
    cycle: int = field(compare=False)                        # current time slot
    scheduled: FrozenSet[Tuple[int, int]] = field(compare=False)   # (idx, start)
    finish_times: FrozenSet[Tuple[int, int]] = field(compare=False) # (idx, finish)
    last_A: int = field(compare=False)                       # last SHARE_A start (−1 = none)
    last_B: int = field(compare=False)                       # last SHARE_B start (−1 = none)
    sequence: List[Optional[Instruction]] = field(compare=False)    # reconstruction list


# ---------------------------------------------------------------------------
# Public solver class
# ---------------------------------------------------------------------------

class AStarScheduler:
    """Schedules an ARM32 instruction block using A* (small n) or Beam Search (large n).

    Parameters
    ----------
    k           : Security distance in cycles between different-share instructions.
    max_states  : Maximum nodes expanded before giving up (A* cap).
    time_limit  : Wall-clock timeout in seconds.
    beam_width  : Frontier width for Beam Search (n > MAX_EXACT).
    """

    def __init__(
        self,
        k: int = 3,
        max_states: int = MAX_STATES,
        time_limit: float = TIME_LIMIT,
        beam_width: int = BEAM_WIDTH,
    ) -> None:
        self.k = k
        self.max_states = max_states
        self.time_limit = time_limit
        self.beam_width = beam_width

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def schedule(
        self,
        instructions: List[Instruction],
    ) -> Tuple[List[Tuple[int, Optional[Instruction]]], int, Dict]:
        """Schedule *instructions* and return the result.

        Returns
        -------
        schedule : List of (cycle, instruction_or_None) — None means NOP.
        total_cycles : Total length of the produced schedule.
        stats : Dict with keys: method, states_explored, total_cycles,
                n_nops, wall_time, optimal.
        """
        t0 = time.perf_counter()
        state = PipelineState(instructions, self.k)

        use_beam = len(instructions) > MAX_EXACT

        if use_beam:
            schedule_out, total, extra = self._beam_search(state, instructions, t0)
            method = "beam_search"
            optimal = False
        else:
            schedule_out, total, extra = self._astar(state, instructions, t0)
            method = "astar"
            optimal = extra.get("optimal", True)

        wall_time = time.perf_counter() - t0
        nops = sum(1 for _, i in schedule_out if i is None)

        stats = {
            "method": method,
            "optimal": optimal,
            "states_explored": extra.get("states_explored", 0),
            "total_cycles": total,
            "n_nops": nops,
            "wall_time": wall_time,
        }
        return schedule_out, total, stats

    # ------------------------------------------------------------------
    # A* (exact, for n ≤ MAX_EXACT)
    # ------------------------------------------------------------------

    def _astar(
        self,
        state: PipelineState,
        instructions: List[Instruction],
        t0: float,
    ) -> Tuple[List, int, Dict]:
        n = len(instructions)
        all_idx = frozenset(instr.idx for instr in instructions)

        # Initial node
        h0 = state.heuristic(all_idx)
        root = _Node(
            f=h0,
            tiebreak=0,
            g=0,
            cycle=0,
            scheduled=frozenset(),
            finish_times=frozenset(),
            last_A=-1,
            last_B=-1,
            sequence=[],
        )

        heap: List[_Node] = [root]
        visited: Dict[tuple, int] = {}   # state_key → best g seen
        counter = 0

        while heap:
            # Timeout / budget check
            if counter >= self.max_states or time.perf_counter() - t0 > self.time_limit:
                # Fall back to greedy
                return self._greedy_fallback(state, instructions), -1, {
                    "states_explored": counter, "optimal": False
                }

            node = heapq.heappop(heap)
            counter += 1

            # Duplicate pruning
            sched_idx = frozenset(idx for idx, _ in node.scheduled)
            state_key = (sched_idx, node.last_A, node.last_B, node.cycle)
            if state_key in visited and visited[state_key] <= node.g:
                continue
            visited[state_key] = node.g

            # Goal check
            if len(sched_idx) == n:
                schedule_out = self._build_output(node.sequence, node.cycle)
                total = schedule_out[-1][0] + 1 if schedule_out else 0
                return schedule_out, total, {"states_explored": counter, "optimal": True}

            # Expand node
            ft_dict: Dict[int, int] = dict(node.finish_times)
            placement: Dict[int, int] = {idx: s for idx, s in node.scheduled}

            ready = state.get_ready_instructions(sched_idx, ft_dict, node.cycle)

            placed_any = False
            for instr in ready:
                if not state.is_security_valid(instr, node.cycle, placement):
                    continue

                new_sched = node.scheduled | {(instr.idx, node.cycle)}
                new_ft = node.finish_times | {(instr.idx, node.cycle + instr.latency)}
                new_last_A = node.last_A
                new_last_B = node.last_B
                if instr.share_type == ShareType.SHARE_A:
                    new_last_A = node.cycle
                elif instr.share_type == ShareType.SHARE_B:
                    new_last_B = node.cycle

                remaining = all_idx - frozenset(idx for idx, _ in new_sched)
                h = state.heuristic(remaining)
                new_g = node.cycle + 1  # each placed instruction costs 1 cycle

                child = _Node(
                    f=new_g + h,
                    tiebreak=counter,
                    g=new_g,
                    cycle=node.cycle + 1,
                    scheduled=new_sched,
                    finish_times=new_ft,
                    last_A=new_last_A,
                    last_B=new_last_B,
                    sequence=node.sequence + [instr],
                )
                heapq.heappush(heap, child)
                placed_any = True

            # NOP branch (always try if nothing could be placed)
            if not placed_any:
                nop_child = _Node(
                    f=node.g + 1 + state.heuristic(all_idx - sched_idx),
                    tiebreak=counter,
                    g=node.g + 1,
                    cycle=node.cycle + 1,
                    scheduled=node.scheduled,
                    finish_times=node.finish_times,
                    last_A=node.last_A,
                    last_B=node.last_B,
                    sequence=node.sequence + [None],
                )
                heapq.heappush(heap, nop_child)

        # Empty heap — should not happen; fall back
        return self._greedy_fallback(state, instructions), -1, {
            "states_explored": counter, "optimal": False
        }

    # ------------------------------------------------------------------
    # Beam Search (for n > MAX_EXACT)
    # ------------------------------------------------------------------

    def _beam_search(
        self,
        state: PipelineState,
        instructions: List[Instruction],
        t0: float,
    ) -> Tuple[List, int, Dict]:
        """Beam Search: A* with a fixed-width frontier.

        Explores the *beam_width* most promising partial schedules at each
        step.  Loses the optimality guarantee of A* but scales to n=50.
        """
        n = len(instructions)
        all_idx = frozenset(instr.idx for instr in instructions)

        h0 = state.heuristic(all_idx)
        root = _Node(
            f=h0, tiebreak=0, g=0, cycle=0,
            scheduled=frozenset(), finish_times=frozenset(),
            last_A=-1, last_B=-1, sequence=[],
        )

        beam: List[_Node] = [root]
        states_explored = 0
        best_solution: Optional[Tuple[List, int]] = None

        for _step in range(n * 4):   # max iterations = 4 * n (generous bound)
            if not beam or time.perf_counter() - t0 > self.time_limit:
                break

            candidates: List[_Node] = []

            for node in beam:
                states_explored += 1
                sched_idx = frozenset(idx for idx, _ in node.scheduled)
                ft_dict: Dict[int, int] = dict(node.finish_times)
                placement: Dict[int, int] = {idx: s for idx, s in node.scheduled}

                # Goal check
                if len(sched_idx) == n:
                    schedule_out = self._build_output(node.sequence, node.cycle)
                    total = schedule_out[-1][0] + 1 if schedule_out else 0
                    if best_solution is None or total < best_solution[1]:
                        best_solution = (schedule_out, total)
                    continue

                # Expand
                ready = state.get_ready_instructions(sched_idx, ft_dict, node.cycle)
                placed_any = False

                for instr in ready:
                    if not state.is_security_valid(instr, node.cycle, placement):
                        continue

                    new_sched = node.scheduled | {(instr.idx, node.cycle)}
                    new_ft = node.finish_times | {(instr.idx, node.cycle + instr.latency)}
                    new_last_A = node.last_A
                    new_last_B = node.last_B
                    if instr.share_type == ShareType.SHARE_A:
                        new_last_A = node.cycle
                    elif instr.share_type == ShareType.SHARE_B:
                        new_last_B = node.cycle

                    remaining = all_idx - frozenset(idx for idx, _ in new_sched)
                    h = state.heuristic(remaining)
                    new_g = node.cycle + 1

                    child = _Node(
                        f=new_g + h, tiebreak=states_explored,
                        g=new_g, cycle=node.cycle + 1,
                        scheduled=new_sched, finish_times=new_ft,
                        last_A=new_last_A, last_B=new_last_B,
                        sequence=node.sequence + [instr],
                    )
                    candidates.append(child)
                    placed_any = True

                if not placed_any:
                    remaining = all_idx - sched_idx
                    nop_child = _Node(
                        f=node.g + 1 + state.heuristic(remaining),
                        tiebreak=states_explored,
                        g=node.g + 1, cycle=node.cycle + 1,
                        scheduled=node.scheduled, finish_times=node.finish_times,
                        last_A=node.last_A, last_B=node.last_B,
                        sequence=node.sequence + [None],
                    )
                    candidates.append(nop_child)

            if not candidates:
                break

            # Keep only the best `beam_width` candidates (lowest f)
            candidates.sort(key=lambda nd: (nd.f, nd.tiebreak))
            beam = candidates[: self.beam_width]

        # Check if any beam node is a complete solution
        for node in beam:
            sched_idx = frozenset(idx for idx, _ in node.scheduled)
            if len(sched_idx) == n:
                schedule_out = self._build_output(node.sequence, node.cycle)
                total = schedule_out[-1][0] + 1 if schedule_out else 0
                if best_solution is None or total < best_solution[1]:
                    best_solution = (schedule_out, total)

        if best_solution is not None:
            return best_solution[0], best_solution[1], {"states_explored": states_explored}

        # Last resort: greedy
        fallback, fc = self._greedy_fallback(state, instructions)
        return fallback, fc, {"states_explored": states_explored}

    # ------------------------------------------------------------------
    # Greedy fallback (used when search times out)
    # ------------------------------------------------------------------

    def _greedy_fallback(
        self,
        state: PipelineState,
        instructions: List[Instruction],
    ) -> Tuple[List[Tuple[int, Optional[Instruction]]], int]:
        """Simple list-scheduling greedy (highest critical path first)."""
        n = len(instructions)
        scheduled: Set[int] = set()
        finish_times: Dict[int, int] = {}
        placement: Dict[int, int] = {}
        sequence: List[Tuple[int, Optional[Instruction]]] = []
        cycle = 0

        while len(scheduled) < n:
            ready = state.get_ready_instructions(scheduled, finish_times, cycle)
            # Filter by security
            valid = [
                instr for instr in ready
                if state.is_security_valid(instr, cycle, placement)
            ]
            if valid:
                # Pick the one with the highest critical-path weight
                chosen = max(valid, key=lambda i: state._critical_path[i.idx])
                scheduled.add(chosen.idx)
                finish_times[chosen.idx] = cycle + chosen.latency
                placement[chosen.idx] = cycle
                sequence.append((cycle, chosen))
            else:
                sequence.append((cycle, None))   # NOP
            cycle += 1

        total = cycle
        return sequence, total

    # ------------------------------------------------------------------
    # Output reconstruction
    # ------------------------------------------------------------------

    @staticmethod
    def _build_output(
        sequence: List[Optional[Instruction]],
        final_cycle: int,
    ) -> List[Tuple[int, Optional[Instruction]]]:
        """Convert a flat sequence list into (cycle, instruction_or_None) pairs."""
        return [(i, instr) for i, instr in enumerate(sequence)]
