"""
instruction.py — Core instruction model for ARM32 scheduling.

Defines:
  - ShareType   : enum for masked-cryptography share membership
  - Instruction : immutable dataclass representing one ARM32 instruction
  - build_dependency_graph : extracts RAW (Read-After-Write) data hazards
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Tuple


# ---------------------------------------------------------------------------
# Share types (masking domains)
# ---------------------------------------------------------------------------

class ShareType(Enum):
    """Identifies which cryptographic share an instruction manipulates.

    In a masked implementation a secret is split into (at least) two shares,
    SHARE_A and SHARE_B.  Any compiler output that places instructions from
    different shares within k pipeline cycles of each other risks a timing or
    power side-channel leakage.  NEUTRAL instructions touch neither share.
    """
    SHARE_A = "A"   # Operates on share A (e.g. mask / first keystream word)
    SHARE_B = "B"   # Operates on share B (e.g. complementary mask word)
    NEUTRAL = "N"   # Independent of both shares (address computation, etc.)


# ---------------------------------------------------------------------------
# Instruction model
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Instruction:
    """One ARM32 instruction in the scheduling problem.

    Attributes
    ----------
    idx         : Original position in the unscheduled block (used as unique ID).
    name        : ARM mnemonic (ADD, LDR, EOR, …).
    dest_reg    : Destination register written by this instruction.
    source_regs : Tuple of source registers read by this instruction.
    latency     : Number of pipeline cycles until the result is available
                  (1 for ALU ops, 2 for MUL / LDR).
    share_type  : Cryptographic share membership (SHARE_A, SHARE_B, NEUTRAL).
    """

    idx: int
    name: str
    dest_reg: str
    source_regs: Tuple[str, ...]
    latency: int
    share_type: ShareType

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def reads_reg(self, reg: str) -> bool:
        """Return True if this instruction reads *reg* as a source."""
        return reg in self.source_regs

    def writes_reg(self, reg: str) -> bool:
        """Return True if this instruction writes *reg* as its destination."""
        return self.dest_reg == reg

    def __repr__(self) -> str:
        srcs = ", ".join(self.source_regs) if self.source_regs else "—"
        return (
            f"[{self.idx:2d}] {self.name:<4}  {self.dest_reg} ← {srcs}"
            f"  (share={self.share_type.value}, lat={self.latency})"
        )


# ---------------------------------------------------------------------------
# Dependency graph construction
# ---------------------------------------------------------------------------

def build_dependency_graph(
    instructions: List[Instruction],
) -> Dict[int, List[int]]:
    """Build the RAW (Read-After-Write) data dependency graph.

    For each instruction j, returns the list of instruction indices i < j
    such that i writes a register that j reads AND i is the *most recent*
    writer of that register before j in the original program order.

    Only the latest writer per register is included because it dominates:
    preserving data flow from that writer implies that all earlier writers
    of the same register are already transitively ordered before j.

    Returns
    -------
    predecessors : Dict[int, List[int]]
        predecessors[j] = [i₁, i₂, …] means each iₙ must finish executing
        (i.e., its result must be available) before j can start.
    """
    n = len(instructions)
    predecessors: Dict[int, List[int]] = {i: [] for i in range(n)}

    for j in range(n):
        instr_j = instructions[j]
        seen_regs: set[str] = set()

        # Walk backward from j-1 to 0; take the first (latest) writer per reg
        for i in range(j - 1, -1, -1):
            instr_i = instructions[i]
            if (
                instr_i.dest_reg not in seen_regs
                and instr_j.reads_reg(instr_i.dest_reg)
            ):
                predecessors[j].append(i)
                seen_regs.add(instr_i.dest_reg)

    return predecessors


# ---------------------------------------------------------------------------
# Static validation helpers
# ---------------------------------------------------------------------------

def validate_schedule(
    schedule: List[Tuple[int, "Instruction | None"]],
    instructions: List[Instruction],
    predecessors: Dict[int, List[int]],
    k: int,
) -> Tuple[bool, List[str]]:
    """Statically verify that a schedule is both data-safe and share-secure.

    Parameters
    ----------
    schedule     : List of (cycle, instruction_or_None) pairs (None = NOP).
    instructions : Original instruction list.
    predecessors : Output of build_dependency_graph().
    k            : Required security distance in cycles between shares.

    Returns
    -------
    (ok, errors) where ok=True means zero violations.
    """
    errors: List[str] = []

    # Map idx → (cycle, instruction)
    placement: Dict[int, int] = {}
    for cycle, instr in schedule:
        if instr is not None:
            placement[instr.idx] = cycle

    # 1. RAW constraint check
    for j, preds in predecessors.items():
        instr_j = instructions[j]
        c_j = placement[j]
        for i in preds:
            instr_i = instructions[i]
            c_i = placement[i]
            # j must start no earlier than c_i + latency_i
            if c_j < c_i + instr_i.latency:
                errors.append(
                    f"RAW violation: [{i}]{instr_i.name} (c={c_i}, lat={instr_i.latency})"
                    f" → [{j}]{instr_j.name} (c={c_j}): needs c_j ≥ {c_i + instr_i.latency}"
                )

    # 2. Security distance check
    share_instructions = [
        (cycle, instr)
        for cycle, instr in [(placement[i], instructions[i]) for i in placement]
        if instr.share_type != ShareType.NEUTRAL
    ]
    for idx_a, (ca, ia) in enumerate(share_instructions):
        for cb, ib in share_instructions[idx_a + 1 :]:
            if ia.share_type != ib.share_type:
                if abs(ca - cb) < k:
                    errors.append(
                        f"Security violation (k={k}): [{ia.idx}]{ia.name}"
                        f" (share={ia.share_type.value}, c={ca})"
                        f" ↔ [{ib.idx}]{ib.name}"
                        f" (share={ib.share_type.value}, c={cb})"
                        f": distance={abs(ca - cb)}"
                    )

    return len(errors) == 0, errors
