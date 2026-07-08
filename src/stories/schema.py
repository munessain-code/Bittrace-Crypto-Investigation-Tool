#!/usr/bin/env python3
"""Data schema for BitTrace investigation stories.

Each story is a curated, step-by-step tracing narrative designed to
guide an analyst through a real money-layering pattern in the Elliptic++
transaction graph.

Difficulty tiers follow the KDD paper's EASY / AVERAGE / HARD case study
framework, where EASY patterns have strong structural signals (e.g.
long peel chains) and HARD cases require deeper context (e.g.
multi-hop fan-in mixed with licit traffic).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class Difficulty(str, Enum):
    """Story difficulty aligned with KDD paper case tiers."""
    EASY = "EASY"
    AVERAGE = "AVERAGE"
    HARD = "HARD"


class TraceDirection(str, Enum):
    """Direction of graph traversal for the step."""
    DOWNSTREAM = "downstream"
    UPSTREAM = "upstream"
    BIDIRECTIONAL = "bidirectional"


@dataclass
class StoryStep:
    """Single step within an investigation story.

    Each step focuses the analyst on a specific part of the traced
    subgraph and highlights nodes / edges relevant to the narrative.
    """
    step_num: int
    title: str
    description: str
    highlight_nodes: List[int] = field(default_factory=list)
    highlight_edges: List[List[int]] = field(default_factory=list)
    trace_direction: str = "downstream"  # TraceDirection value as string


@dataclass
class Story:
    """A complete investigation story with metadata and steps.

    Attributes:
        id: Unique story identifier (lowercase-with-hyphens).
        title: Human-readable title shown in the notebook / UI.
        difficulty: One of EASY, AVERAGE, HARD.
        seed_node_id: Transaction ID to start the trace from.
        pattern: Structural pattern this story illustrates
            (peel_chain, fan_out, fan_in, etc.).
        narrative: One-paragraph summary of the investigation storyline.
        steps: Ordered list of StoryStep objects.
        source_file: Path to the YAML file this story was loaded from.
    """
    id: str
    title: str
    difficulty: Difficulty
    seed_node_id: int
    pattern: str
    narrative: str
    steps: List[StoryStep] = field(default_factory=list)
    source_file: Optional[str] = None

    # ---------- convenience ----------

    def seed_node(self) -> int:
        """Return the seed node ID as a plain int."""
        return self.seed_node_id

    def all_highlight_nodes(self) -> List[int]:
        """Flatten every step's highlight_nodes into one list."""
        nodes: List[int] = []
        for step in self.steps:
            nodes.extend(step.highlight_nodes)
        return nodes

    def to_dict(self) -> Dict[str, Any]:
        """Serialisable representation (for export / API)."""
        return {
            "id": self.id,
            "title": self.title,
            "difficulty": self.difficulty.value,
            "seed_node_id": self.seed_node_id,
            "pattern": self.pattern,
            "narrative": self.narrative,
            "steps": [
                {
                    "step_num": s.step_num,
                    "title": s.title,
                    "description": s.description,
                    "highlight_nodes": s.highlight_nodes,
                    "highlight_edges": s.highlight_edges,
                    "trace_direction": s.trace_direction,
                }
                for s in self.steps
            ],
        }
