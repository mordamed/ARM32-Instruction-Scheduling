"""
pipeline.py — Pipeline state and scheduling utilities.

Provides PipelineState, which encapsulates:
  - The full instruction list and their RAW dependencies
  - Critical-path lengths (for A* heuristic)
  - Helpers for determining ready instructions and security validity
"""

from __future__ import annotations

from typing import Dict, FrozenSet, List, Optional, Set, Tuple

from .instruction import Instruction, ShareType, build_dependency_graph

# Sentinel for "no share instruction placed yet"
_NOT_PLACED = -1


class PipelineState:
    """Pre-computed structural information about a scheduling problem instance.

    This object is created once per problem instance and shared across all
    solver calls.  It is *read-only* (no mutable state).

    Parameters
    ----------
    instructions : List of Instruction objects in their original program order.
    k            : Minimum cycle distance required between instructions of
                   different (non-NEUTRAL) share types.
    """

    def __init__(self, instructions: List[Instruction], k: int = 3) -> None:
        self.instructions: List[Instruction] = instructions
        self.k: int = k
        self.n: int = len(instructions)

        # Dependency graph: predecessors[j] = [i, ...] (i must finish before j)
        self.predecessors: Dict[int, List[int]] = build_dependency_graph(instructions)

        # Successors: successors[i] = [j, ...] (j depends on i)
        self.successors: Dict[int, List[int]] = {i: [] for i in range(self.n)}
        for j, preds in self.predecessors.items():
            for i in preds:
                self.successors[i].append(j)

        # Index map for fast lookup: idx → Instruction
        self.idx_map: Dict[int, Instruction] = {instr.idx: instr for instr in instructions}

        # Critical-path lengths (cycles from each node to schedule end)
        # Used as an admissible A* heuristic (never overestimates remaining work)
        self._critical_path: Dict[int, int] = self._compute_critical_paths()

    # ------------------------------------------------------------------
    # Critical path (for A* heuristic)
    # ------------------------------------------------------------------

    def _compute_critical_paths(self) -> Dict[int, int]:
        """Compute the critical path length from each instruction to the end.

        cp[i] = latency(i) + max(cp[j] for j in successors[i])
              = longest execution path starting at i.

        Computed via dynamic programming in reverse topological order.
        """
        # Topological sort (Kahn's algorithm)
        in_degree = {i: len(self.predecessors[i]) for i in range(self.n)}
        queue = [i for i, d in in_degree.items() if d == 0]
        topo: List[int] = []
        temp = dict(in_degree)
        while queue:
            node = queue.pop(0)
            topo.append(node)
            for succ in self.successors[node]:
                temp[succ] -= 1
                if temp[succ] == 0:
                    queue.append(succ)

        # DP bottom-up
        cp: Dict[int, int] = {}
        for idx in reversed(topo):
            instr = self.idx_map[idx]
            if not self.successors[idx]:
                cp[idx] = instr.latency
            else:
                cp[idx] = instr.latency + max(cp[s] for s in self.successors[idx])
        return cp

    def heuristic(self, remaining: FrozenSet[int]) -> int:
        """Lower bound on cycles needed to schedule *remaining* instructions.

        Equals the maximum critical-path length among remaining instructions.
        This is admissible: no valid schedule can do better.
        """
        if not remaining:
            return 0
        return max(self._critical_path[idx] for idx in remaining)

    # ------------------------------------------------------------------
    # Ready instruction query
    # ------------------------------------------------------------------

    def get_ready_instructions(
        self,
        scheduled: Set[int],
        finish_times: Dict[int, int],
        current_cycle: int,
    ) -> List[Instruction]:
        """Return instructions that can START at *current_cycle*.

        An instruction is ready when:
          1. It has not yet been scheduled.
          2. All its predecessors have FINISHED (finish_time ≤ current_cycle).

        Parameters
        ----------
        scheduled     : Set of already-scheduled instruction indices.
        finish_times  : {idx: finish_cycle} for all scheduled instructions.
        current_cycle : The cycle under consideration.
        """
        ready: List[Instruction] = []
        for instr in self.instructions:
            if instr.idx in scheduled:
                continue
            preds = self.predecessors[instr.idx]
            if all(
                p in finish_times and finish_times[p] <= current_cycle
                for p in preds
            ):
                ready.append(instr)
        return ready

    # ------------------------------------------------------------------
    # Security constraint check
    # ------------------------------------------------------------------

    def is_security_valid(
        self,
        instr: Instruction,
        cycle: int,
        placement: Dict[int, int],     # {idx: start_cycle} of already placed instrs
    ) -> bool:
        """Return True if placing *instr* at *cycle* satisfies the k-distance rule.

        The rule: for any pair of instructions (i, j) where share_type(i) ≠
        share_type(j) and both are non-NEUTRAL, |start(i) − start(j)| ≥ k.
        """
        if instr.share_type == ShareType.NEUTRAL:
            return True  # NEUTRAL instructions never cause violations

        for idx, start in placement.items():
            other = self.idx_map[idx]
            if other.share_type == ShareType.NEUTRAL:
                continue
            if other.share_type != instr.share_type:
                if abs(start - cycle) < self.k:
                    return False
        return True

    # ------------------------------------------------------------------
    # Convenience: earliest possible start for each instruction
    # ------------------------------------------------------------------

    def earliest_starts(self, finish_times: Dict[int, int]) -> Dict[int, int]:
        """Compute the earliest cycle each unscheduled instruction can start.

        Used as a planning aid by the CSP and beam search solvers.

        earliest_start[j] = max(finish_times[i] for i in predecessors[j])
                            (or 0 if no predecessors).
        """
        result: Dict[int, int] = {}
        for instr in self.instructions:
            preds = self.predecessors[instr.idx]
            if not preds:
                result[instr.idx] = 0
            else:
                result[instr.idx] = max(
                    finish_times.get(p, 0) for p in preds
                )
        return result

    # ------------------------------------------------------------------
    # Pretty-print helpers
    # ------------------------------------------------------------------

    def print_schedule(
        self,
        schedule: List[Tuple[int, Optional[Instruction]]],
    ) -> None:
        """Print a schedule to stdout (cycle | content format)."""
        print(f"\n{'Cycle':>5}  {'Instruction'}")
        print("—" * 50)
        for cycle, instr in schedule:
            label = str(instr) if instr is not None else "NOP"
            print(f"{cycle:>5}  {label}")
        print("—" * 50)
        total = schedule[-1][0] + 1 if schedule else 0
        nops = sum(1 for _, i in schedule if i is None)
        print(f"Total cycles: {total}  |  NOPs: {nops}\n")
