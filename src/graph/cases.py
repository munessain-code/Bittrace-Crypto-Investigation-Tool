"""Case-study subgraph extraction.

Extracts curated subgraphs for EASY/HARD/AVERAGE difficulty cases
based on the Elliptic++ paper's layering patterns.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

import networkx as nx

from src.data.loaders import get_duckdb_connection
from src.graph.expand import expand_node
from src.graph.export import subgraph_to_cytoscape, subgraph_to_json_file

logger = logging.getLogger(__name__)

# Precomputed subgraphs directory
SUBGRAPHS_DIR = Path(__file__).resolve().parents[2] / "data" / "subgraphs"

# Difficulty selection criteria (documented for reproducibility)
DIFFICULTY_CRITERIA = {
    "easy": {
        "description": "Illicit tx with clear peel chain (>3 hops) and few branches",
        "min_chain_length": 3,
        "max_fan_degree": 2,
    },
    "average": {
        "description": "Illicit tx with moderate fan-out and mixed class neighbors",
        "min_chain_length": 2,
        "max_fan_degree": 5,
    },
    "hard": {
        "description": "Illicit tx deeply embedded in unknown-class nodes with high connectivity",
        "min_chain_length": 1,
        "max_fan_degree": 20,
    },
}


def find_seed_node(
    G: nx.DiGraph,
    difficulty: str = "easy",
) -> int:
    """Select an illicit seed node matching the difficulty criteria.

    Criteria:
    - **easy**: Illicit node at start of a long peel chain (linear, few branches)
    - **average**: Illicit node with moderate fan-out, mixed neighbors
    - **hard**: Illicit node embedded in dense unknown-class subgraph

    Returns the node_id.
    """
    criteria = DIFFICULTY_CRITERIA.get(difficulty, DIFFICULTY_CRITERIA["easy"])
    illicit_nodes = [n for n in G.nodes() if G.nodes[n].get("class") == 1]
    if not illicit_nodes:
        raise ValueError("No illicit nodes found in graph")

    if difficulty == "easy":
        # Find illicit node with out_degree == 1 (start of peel chain)
        candidates = [n for n in illicit_nodes if G.out_degree(n) == 1 and G.in_degree(n) <= 1]
        if not candidates:
            candidates = [n for n in illicit_nodes if G.out_degree(n) <= 2]
        return candidates[0]

    elif difficulty == "average":
        # Find illicit node with moderate connectivity
        candidates = [n for n in illicit_nodes if 2 <= G.out_degree(n) <= 5]
        if not candidates:
            candidates = [n for n in illicit_nodes if 1 <= G.out_degree(n) <= 5]
        if not candidates:
            return illicit_nodes[0]
        # Pick the one with most mixed-class neighbors
        def mixed_score(n):
            neighbors = set(G.successors(n)) | set(G.predecessors(n))
            classes = set(G.nodes[nb].get("class", 3) for nb in neighbors)
            return len(classes)
        return max(candidates, key=mixed_score)

    else:  # hard
        # Find illicit node surrounded by unknown-class nodes
        def unknown_density(n):
            neighbors = set(G.successors(n)) | set(G.predecessors(n))
            if not neighbors:
                return 0
            unknown_count = sum(1 for nb in neighbors if G.nodes[nb].get("class", 3) == 3)
            return unknown_count / len(neighbors)

        candidates = sorted(illicit_nodes, key=unknown_density, reverse=True)
        # Prefer nodes with higher total degree
        if candidates:
            return max(candidates, key=lambda n: G.out_degree(n) + G.in_degree(n))
        return illicit_nodes[0]


def extract_case_subgraph(
    G: nx.DiGraph,
    seed_node: Optional[int] = None,
    difficulty: str = "easy",
    depth: int = 3,
    budget: int = 500,
) -> Dict:
    """Extract a case-study subgraph centered on an illicit node.

    Args:
        G: Transaction graph.
        seed_node: Specific node to start from. If None, auto-selects based on difficulty.
        difficulty: "easy", "average", or "hard".
        depth: BFS expansion depth.
        budget: Maximum nodes to include.

    Returns:
        Cytoscape-compatible dict with metadata.
    """
    if seed_node is None:
        seed_node = find_seed_node(G, difficulty)

    logger.info(f"Extracting {difficulty} case subgraph from seed {seed_node} "
                f"(depth={depth}, budget={budget})")

    expanded = expand_node(G, seed_node, budget=budget, max_depth=depth)

    # Build Cytoscape JSON
    cyto = subgraph_to_cytoscape(G, expanded["nodes"], expanded["edges"])

    # Add metadata
    cls = G.nodes[seed_node].get("class", 3)
    ts = G.nodes[seed_node].get("timestep", None)

    return {
        "metadata": {
            "difficulty": difficulty,
            "seed_node": seed_node,
            "seed_class": cls,
            "seed_timestep": ts,
            "depth": depth,
            "budget": budget,
            "node_count": expanded["node_count"],
            "edge_count": expanded["edge_count"],
            "description": DIFFICULTY_CRITERIA[difficulty]["description"],
        },
        "nodes": cyto["nodes"],
        "edges": cyto["edges"],
    }


def save_case_subgraph(
    case_subgraph: Dict,
    difficulty: str,
    output_dir: Optional[Path] = None,
) -> str:
    """Save a case subgraph to ``data/subgraphs/{difficulty}_case.json``.

    Returns the file path.
    """
    if output_dir is None:
        output_dir = SUBGRAPHS_DIR

    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"{difficulty}_case.json"

    subgraph_to_json_file(case_subgraph, str(path))
    logger.info(f"Saved {difficulty} case to {path}")
    return str(path)


def generate_all_cases(
    G: Optional[nx.DiGraph] = None,
    db=None,
    output_dir: Optional[Path] = None,
    depth: int = 3,
    budget: int = 500,
) -> Dict[str, str]:
    """Generate all three difficulty cases and save them.

    Args:
        G: Transaction graph. Built from DuckDB if not provided.
        db: Existing DuckDB connection (used only if G is None).
        output_dir: Where to save JSON files.
        depth: BFS depth for expansion.
        budget: Max nodes per case.

    Returns:
        Dict mapping difficulty -> file path.
    """
    if G is None:
        from src.graph.builders import build_tx_graph
        own_graph = True
        G = build_tx_graph(db)
    else:
        own_graph = False

    results = {}
    for difficulty in ["easy", "average", "hard"]:
        try:
            case = extract_case_subgraph(G, difficulty=difficulty, depth=depth, budget=budget)
            path = save_case_subgraph(case, difficulty, output_dir)
            results[difficulty] = path
            logger.info(f"  {difficulty}: {case['metadata']['seed_node']} "
                        f"({case['metadata']['node_count']} nodes, "
                        f"{case['metadata']['edge_count']} edges)")
        except Exception as e:
            logger.error(f"Failed to generate {difficulty} case: {e}")

    if own_graph:
        pass  # G was built locally but we don't own the DuckDB connection to close

    return results
