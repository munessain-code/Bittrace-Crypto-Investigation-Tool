#!/usr/bin/env python3
"""CLI for manual testing of BitTrace graph operations.

Usage:
  python scripts/graph_cli.py trace --node-id 272145560 --direction downstream
  python scripts/graph_cli.py expand --node-id 272145560
  python scripts/graph_cli.py export --node-id 272145560 --output out.json
  python scripts/graph_cli.py case --difficulty easy --output case.json
"""

import argparse
import json
import sys
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.graph.builders import build_tx_graph
from src.graph.trace import trace_downstream, trace_upstream
from src.graph.expand import expand_node
from src.graph.export import subgraph_to_cytoscape, subgraph_to_json_file
from src.graph.cases import extract_case_subgraph, save_case_subgraph


def cmd_trace(args, G):
    """Trace money flow upstream or downstream from a node."""
    direction = args.direction.lower()
    max_hops = getattr(args, "max_hops", 10) or 10

    if direction == "downstream":
        result = trace_downstream(G, args.node_id, max_hops=max_hops)
    elif direction == "upstream":
        result = trace_upstream(G, args.node_id, max_hops=max_hops)
    else:
        print(f"Error: direction must be 'upstream' or 'downstream', got '{direction}'", file=sys.stderr)
        sys.exit(1)

    print(f"Trace: {direction} from node {args.node_id}")
    print(f"  Hops reached: {result['max_reached']}")
    print(f"  Nodes: {result['node_count']}")
    print(f"  Edges: {result['edge_count']}")

    if args.output:
        cyto = subgraph_to_cytoscape(G, result["nodes"], result["edges"])
        subgraph_to_json_file(cyto, args.output)
        print(f"  Exported to: {args.output}")


def cmd_expand(args, G):
    """Expand k-hop neighborhood around a node."""
    budget = getattr(args, "budget", 500) or 500
    depth = getattr(args, "depth", 2) or 2

    result = expand_node(G, args.node_id, budget=budget, max_depth=depth)

    print(f"Expand: node {args.node_id} (budget={budget}, depth={depth})")
    print(f"  Nodes: {result['node_count']}")
    print(f"  Edges: {result['edge_count']}")

    if args.output:
        cyto = subgraph_to_cytoscape(G, result["nodes"], result["edges"])
        subgraph_to_json_file(cyto, args.output)
        print(f"  Exported to: {args.output}")


def cmd_export(args, G):
    """Export a node's subgraph to JSON."""
    # Default to 1-hop expansion
    result = expand_node(G, args.node_id, budget=500, max_depth=1)
    cyto = subgraph_to_cytoscape(G, result["nodes"], result["edges"])
    out_path = subgraph_to_json_file(cyto, args.output)
    print(f"Exported {result['node_count']} nodes, {result['edge_count']} edges -> {out_path}")


def cmd_case(args, G):
    """Extract a case-study subgraph."""
    difficulty = getattr(args, "difficulty", "easy") or "easy"
    depth = getattr(args, "depth", 3) or 3
    budget = getattr(args, "budget", 500) or 500

    seed = args.node_id if hasattr(args, "node_id") and args.node_id else None
    case = extract_case_subgraph(G, seed_node=seed, difficulty=difficulty, depth=depth, budget=budget)

    if args.output:
        path = subgraph_to_json_file(case, args.output)
        print(f"Saved {difficulty} case -> {path}")
    else:
        path = save_case_subgraph(case, difficulty)
        print(f"Saved {difficulty} case -> {path}")

    meta = case["metadata"]
    print(f"  Seed: {meta['seed_node']} (class={meta['seed_class']}, timestep={meta['seed_timestep']})")
    print(f"  Nodes: {meta['node_count']}, Edges: {meta['edge_count']}")


def main():
    parser = argparse.ArgumentParser(
        description="BitTrace Graph CLI — trace, expand, and export subgraphs"
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # --- trace ---
    p_trace = subparsers.add_parser("trace", help="Trace money flow")
    p_trace.add_argument("--node-id", type=int, required=True, help="Seed node ID")
    p_trace.add_argument("--direction", type=str, required=True, choices=["upstream", "downstream"])
    p_trace.add_argument("--max-hops", type=int, default=10, help="Max hops to trace (default: 10)")
    p_trace.add_argument("--output", type=str, default=None, help="Export to JSON file")

    # --- expand ---
    p_expand = subparsers.add_parser("expand", help="Expand neighborhood")
    p_expand.add_argument("--node-id", type=int, required=True, help="Seed node ID")
    p_expand.add_argument("--budget", type=int, default=500, help="Max nodes (default: 500)")
    p_expand.add_argument("--depth", type=int, default=2, help="Max depth (default: 2)")
    p_expand.add_argument("--output", type=str, default=None, help="Export to JSON file")

    # --- export ---
    p_export = subparsers.add_parser("export", help="Export subgraph to JSON")
    p_export.add_argument("--node-id", type=int, required=True, help="Seed node ID")
    p_export.add_argument("--output", type=str, required=True, help="Output JSON file")

    # --- case ---
    p_case = subparsers.add_parser("case", help="Extract case-study subgraph")
    p_case.add_argument("--difficulty", type=str, default="easy", choices=["easy", "average", "hard"])
    p_case.add_argument("--node-id", type=int, default=None, help="Seed node (auto-selected if omitted)")
    p_case.add_argument("--depth", type=int, default=3, help="Expansion depth")
    p_case.add_argument("--budget", type=int, default=500, help="Max nodes")
    p_case.add_argument("--output", type=str, default=None, help="Output JSON file")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    print("Loading transaction graph...")
    G = build_tx_graph()
    print(f"Loaded: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges\n")

    commands = {
        "trace": cmd_trace,
        "expand": cmd_expand,
        "export": cmd_export,
        "case": cmd_case,
    }

    commands[args.command](args, G)


if __name__ == "__main__":
    main()
