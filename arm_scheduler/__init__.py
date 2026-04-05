"""
arm_scheduler — ARM32 Instruction Scheduler for Masked Cryptography
====================================================================
INFO-H410 Artificial Intelligence Project

Three scheduling approaches:
  - A*  : Exact search (n≤15) + Beam Search fallback (n>15)
  - CSP : Constraint Satisfaction Problem via python-constraint
  - MDP : Q-Learning Reinforcement Learning agent
"""

from .core.instruction import Instruction, ShareType, build_dependency_graph
from .core.pipeline import PipelineState
from .core.generator import generate_block

__version__ = "1.0.0"
__all__ = [
    "Instruction",
    "ShareType",
    "build_dependency_graph",
    "PipelineState",
    "generate_block",
]
