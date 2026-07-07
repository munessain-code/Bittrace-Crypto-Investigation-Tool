"""Batch-generate subgraph JSON files for precomputed case studies.

Generates EASY/HARD/AVERAGE subgraph files from 3 seed illicit nodes.
Selection criteria are documented below.

Seed Selection Criteria
======================
- **Easy case**: Illicit transaction with a long peel chain (linear flow,
  easy to trace). Selected by finding an illicit node with out_degree==1
  that starts a chain >= 3 hops.

- **Hard case**: Illicit transaction deeply embedded in unknown-class nodes
  with high connectivity. Selected by finding the illicit node with highest
  "unknown neighbor density" and total degree.

- **Average case**: Illicit transaction with moderate fan-out and mixed
  class neighbors. Selected by finding an illicit node with 2-5 out_degree
  and the most diverse neighbor classes.
"""

import logging
from pathlib import Path
from typing import Optional

import networkx as nx

from src.graph.builders import build_tx_graph
from src.graph.cases import (
    DIFFICULTY_CRITERIA,
    SUBGRAPHS_DIR,
    extract_case_subgraph,
    find_seed_node,
    save_case_subgraph,
)

logger = logging.getLogger(__name__)


def precompute_subgraphs(
    G: Optional[nx.DiGraph] = None,
    output_dir: Optional[Path] = None,
    depth: int = 3,
    budget: int = 500,
) -> dict:
    """Generate and save subgraph JSON files for all three difficulty cases.

    Args:
        G: Transaction graph. Built from DuckDB if not provided.
        output_dir: Directory for output JSON files.
        depth: BFS expansion depth.
        budget: Maximum nodes per subgraph.

    Returns:
        Dict mapping difficulty -> file path.
    """
    if G is None:
        logger.info("Building full tx graph...")
        G = build_tx_graph()

    logger.info(f"Graph loaded: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

    if output_dir is None:
        output_dir = SUBGRAPHS_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    results = {}

    for difficulty in ["easy", "average", "hard"]:
        logger.info(f"\n--- Generating {difficulty.upper()} case ---")
        seed = find_seed_node(G, difficulty)
        seed_cls = G.nodes[seed].get("class", "?")
        seed_ts = G.nodes[seed].get("timestep", "?")
        logger.info(f"  Seed: {seed} (class={seed_cls}, timestep={seed_ts})")
        logger.info(f"  Criteria: {DIFFICULTY_CRITERIA[difficulty]['description']}")

        case = extract_case_subgraph(G, seed_node=seed, difficulty=difficulty, depth=depth, budget=budget)
        path = save_case_subgraph(case, difficulty, output_dir)
        results[difficulty] = path

        meta = case["metadata"]
        logger.info(f"  Output: {meta['node_count']} nodes, {meta['edge_count']} edges -> {path}")

    # Write a README documenting the subgraphs
    readme_path = output_dir / "README.md"
    readme_path.write_text(_generate_readme(results))
    logger.info(f"\nREADME written to {readme_path}")

    return results


def _generate_readme(results: dict) -> str:
    """Generate a README for the subgraphs directory."""
    lines = [
        "# Precomputed Subgraphs\n\n"
        "These subgraph files are Cytoscape.js-compatible JSON exports of "
        "case-study transactions from the Elliptic++ dataset.\n\n"
        "## Files\n\n",
    ]
    for diff, path in results.items():
        lines.append(f"- **{diff}_case.json** — {diff.capitalize()} difficulty case\n")
    lines.extend([
        "\n## Selection Criteria\n\n",
        "| Difficulty | Criteria |\n",
        "|---|---|\n",
    ])
    for diff, criteria in DIFFICULTY_CRITERIA.items():
        lines.append(f"| {diff.capitalize()} | {criteria['description']} |\n")
    lines.extend([
        "\n## Schema\n\n"
        "Each file contains:\n"
        "- `metadata`: difficulty, seed_node, seed_class, depth, node_count, edge_count\n"
        "- `nodes`: [{data: {id, label, class, class_label, color, hop, timestep}}]\n"
        "- `edges`: [{data: {id, source, target}}]\n\n"
        "## Generation\n\n"
        "```python\n"
        "from src.viz.precompute import precompute_subgraphs\n"
        "precompute_subgraphs(depth=3, budget=500)\n"
        "```\n",
    ])
    return "".join(lines)


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Precompute subgraph JSON files")
    parser.add_argument("--output-dir", type=Path, default=SUBGRAPHS_DIR)
    parser.add_argument("--depth", type=int, default=3)
    parser.add_argument("--budget", type=int, default=500)
    args = parser.parse_args()

    precompute_subgraphs(output_dir=args.output_dir, depth=args.depth, budget=args.budget)
