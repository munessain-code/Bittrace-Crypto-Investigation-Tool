#!/usr/bin/env python3
"""k-hop subgraph extraction for flagged nodes.

Given a transaction ID and the tx→tx NetworkX graph, extracts a subgraph
of depth k centered on the target node and returns it in Cytoscape format
ready for frontend rendering.

Usage:
    from src.explain.subgraph_explainer import extract_k_hop_subgraph

    subgraph = extract_k_hop_subgraph(G, tx_id=272145560, k=2)
    # subgraph is Cytoscape-ready JSON dict
"""

from __future__ import annotations

from collections import deque
from typing import Any, Dict, List, Optional, Set, Tuple

import networkx as nx

from src.graph.export import CLASS_COLORS, CLASS_LABELS, subgraph_to_cytoscape


def extract_k_hop_subgraph(
    G: nx.DiGraph,
    node_id: int,
    k: int = 2,
    max_nodes: int = 500,
) -> Dict[str, Any]:
    """Extract a k-hop subgraph centered on *node_id*.

    Performs bidirectional BFS from the target node, collecting both
    upstream (predecessors) and downstream (successors) neighbors up to
    depth k. Stops early if *max_nodes* is reached.

    Parameters
    ----------
    G : nx.DiGraph
        The full tx→tx graph.
    node_id : int
        The transaction ID to center the subgraph on.
    k : int
        Maximum hop depth (default 2).
    max_nodes : int
        Hard cap on subgraph size (default 500).

    Returns
    -------
    Dict with:
        - "nodes": list of node IDs in the subgraph
        - "edges": list of (src, dst) edge tuples
        - "cytoscape": Cytoscape.js-compatible JSON
        - "stats": dict with node/edge counts, class breakdown
    """
    if node_id not in G:
        raise ValueError(f"Node {node_id} not in graph")

    # Bidirectional BFS
    visited: Set[int] = {node_id}
    hops: Dict[int, int] = {node_id: 0}
    edges: List[Tuple[int, int]] = []

    # BFS frontier: list of (node, depth, direction)
    queue: deque = deque([(node_id, 0, "seed")])

    while queue:
        cur, depth, _ = queue.popleft()
        if depth >= k:
            continue

        # Downstream successors
        for succ in G.successors(cur):
            if succ in visited:
                continue
            if len(visited) >= max_nodes:
                break
            visited.add(succ)
            hops[succ] = depth + 1
            edges.append((cur, succ))
            queue.append((succ, depth + 1, "downstream"))

        # Upstream predecessors
        for pred in G.predecessors(cur):
            if pred in visited:
                continue
            if len(visited) >= max_nodes:
                break
            visited.add(pred)
            hops[pred] = depth + 1
            edges.append((pred, cur))
            queue.append((pred, depth + 1, "upstream"))

    # Build subgraph stats
    class_counts: Dict[str, int] = {}
    for nid in visited:
        cls = G.nodes[nid].get("class", 3)
        label = CLASS_LABELS.get(cls, "unknown")
        class_counts[label] = class_counts.get(label, 0) + 1

    seed_attrs = G.nodes[node_id]
    seed_class = seed_attrs.get("class", 3)

    # Cytoscape export
    cytoscape = subgraph_to_cytoscape(
        G,
        subgraph_nodes=list(visited),
        subgraph_edges=edges,
    )

    # Add hop info to cytoscape nodes
    for node_data in cytoscape["nodes"]:
        nid = int(node_data["data"]["id"])
        node_data["data"]["hop"] = hops.get(nid, 0)
        is_seed = nid == node_id
        node_data["data"]["is_seed"] = is_seed
        if is_seed:
            node_data["data"]["shape"] = "diamond"
            node_data["data"]["size"] = 20
        else:
            hop = hops.get(nid, 0)
            node_data["data"]["size"] = max(6, 14 - hop * 3)

    return {
        "seed": node_id,
        "seed_class": CLASS_LABELS.get(seed_class, "unknown"),
        "seed_color": CLASS_COLORS.get(seed_class, CLASS_COLORS[3]),
        "k": k,
        "nodes": sorted(visited),
        "edges": edges,
        "hops": hops,
        "cytoscape": cytoscape,
        "stats": {
            "node_count": len(visited),
            "edge_count": len(edges),
            "max_hop": max(hops.values()) if hops else 0,
            "class_counts": class_counts,
        },
    }


def get_subgraph_path(
    G: nx.DiGraph,
    source_id: int,
    target_id: int,
    max_path_length: int = 10,
) -> Optional[List[int]]:
    """Find shortest path between two transaction nodes.

    Returns None if no path exists within max_path_length.
    """
    try:
        path = nx.shortest_path(G, source_id, target_id)
        if len(path) <= max_path_length:
            return path
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        pass
    return None
