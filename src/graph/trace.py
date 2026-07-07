"""Money-flow tracing on the BitTrace transaction graph.

Provides upstream/downstream BFS traces on the tx→tx directed graph,
and bipartite addr↔tx traces via DuckDB.
"""

from __future__ import annotations

from collections import deque
from typing import Dict, List, Optional, Set, Tuple

import duckdb
import networkx as nx
import pandas as pd

from src.data.loaders import get_duckdb_connection

# ---------------------------------------------------------------------------
# Return type aliases
# ---------------------------------------------------------------------------
TraceResult = Dict[str, object]


def trace_downstream(
    G: nx.DiGraph,
    node_id: int,
    max_hops: int = 10,
    class_filter: Optional[List[int]] = None,
) -> TraceResult:
    """BFS downstream (following money flow) from *node_id*.

    Returns dict with:
      - nodes: list of visited node IDs
      - edges: list of (src, dst) tuples
      - hops: dict mapping node_id -> hop_distance
      - max_reached: int (actual max hop reached)
    """
    if node_id not in G:
        raise ValueError(f"Node {node_id} not in graph")

    visited: Set[int] = {node_id}
    hops: Dict[int, int] = {node_id: 0}
    edges: List[Tuple[int, int]] = []

    queue: deque = deque([(node_id, 0)])
    while queue:
        cur, depth = queue.popleft()
        if depth >= max_hops:
            continue
        for succ in G.successors(cur):
            if succ in visited:
                continue
            # Apply class filter (exclude unknown unless explicitly included)
            if class_filter is not None:
                cls = G.nodes[succ].get("class", 3)
                if cls not in class_filter:
                    continue
            visited.add(succ)
            hops[succ] = depth + 1
            edges.append((cur, succ))
            queue.append((succ, depth + 1))

    return {
        "seed": node_id,
        "direction": "downstream",
        "max_hops": max_hops,
        "nodes": sorted(visited),
        "edges": edges,
        "hops": hops,
        "max_reached": max(hops.values()) if hops else 0,
        "node_count": len(visited),
        "edge_count": len(edges),
    }


def trace_upstream(
    G: nx.DiGraph,
    node_id: int,
    max_hops: int = 10,
    class_filter: Optional[List[int]] = None,
) -> TraceResult:
    """BFS upstream (reverse money flow) from *node_id*.

    Returns the same dict shape as ``trace_downstream``.
    """
    if node_id not in G:
        raise ValueError(f"Node {node_id} not in graph")

    visited: Set[int] = {node_id}
    hops: Dict[int, int] = {node_id: 0}
    edges: List[Tuple[int, int]] = []

    queue: deque = deque([(node_id, 0)])
    while queue:
        cur, depth = queue.popleft()
        if depth >= max_hops:
            continue
        for pred in G.predecessors(cur):
            if pred in visited:
                continue
            if class_filter is not None:
                cls = G.nodes[pred].get("class", 3)
                if cls not in class_filter:
                    continue
            visited.add(pred)
            hops[pred] = depth + 1
            edges.append((pred, cur))
            queue.append((pred, depth + 1))

    return {
        "seed": node_id,
        "direction": "upstream",
        "max_hops": max_hops,
        "nodes": sorted(visited),
        "edges": edges,
        "hops": hops,
        "max_reached": max(hops.values()) if hops else 0,
        "node_count": len(visited),
        "edge_count": len(edges),
    }


def trace_bipartite(
    wallet_or_tx_id: object,
    db: Optional[duckdb.DuckDBPyConnection] = None,
    max_hops: int = 5,
) -> TraceResult:
    """BFS on the bipartite addr↔tx graph starting from a wallet or tx.

    Alternates address → transaction → address … up to *max_hops*.

    Returns dict with:
      - nodes: list of {id, type} dicts
      - edges: list of {source, target} dicts
      - hops: dict mapping node_id -> hop_distance
    """
    own_db = db is None
    if db is None:
        db = get_duckdb_connection()

    # Determine starting node type
    try:
        check_tx = db.execute(
            f"SELECT COUNT(*) FROM tx_classes WHERE txId = {int(wallet_or_tx_id)}"
        ).fetchone()[0]
        start_type = "transaction" if check_tx > 0 else "address"
    except (ValueError, TypeError):
        start_type = "address"

    visited: Set[object] = {wallet_or_tx_id}
    node_types: Dict[object, str] = {wallet_or_tx_id: start_type}
    hops: Dict[object, int] = {wallet_or_tx_id: 0}
    edges_list: List[Tuple[object, object]] = []

    node_id = wallet_or_tx_id
    for depth in range(max_hops):
        if node_types[node_id] == "transaction":
            # tx → addresses (both input and output)
            try:
                tx_id = int(node_id)
                rows = db.execute(
                    f"SELECT output_address FROM tx_addr_edges WHERE txId = {tx_id}"
                ).fetchall()
                for (addr,) in rows:
                    if addr not in visited:
                        visited.add(addr)
                        node_types[addr] = "address"
                        hops[addr] = depth + 1
                        edges_list.append((node_id, addr))
                # Also check addr_tx_edges for inputs to this tx
                rows2 = db.execute(
                    f"SELECT input_address FROM addr_tx_edges WHERE txId = {tx_id}"
                ).fetchall()
                for (addr,) in rows2:
                    if addr not in visited:
                        visited.add(addr)
                        node_types[addr] = "address"
                        hops[addr] = depth + 1
                        edges_list.append((addr, node_id))
            except (ValueError, TypeError):
                break
        else:
            # address → transactions
            addr = node_id
            try:
                rows = db.execute(
                    f"SELECT txId FROM addr_tx_edges WHERE input_address = '{addr}'"
                ).fetchall()
                for (tx_id,) in rows:
                    tx_id = int(tx_id)
                    if tx_id not in visited:
                        visited.add(tx_id)
                        node_types[tx_id] = "transaction"
                        hops[tx_id] = depth + 1
                        edges_list.append((addr, tx_id))
            except Exception:
                break

        if not visited or len(visited) <= 1:
            break
        # Pick the most recent unexpanded node for next hop
        node_id = None
        for v in visited:
            if hops.get(v, 0) == depth and v in node_types:
                # Expand all nodes at this depth for true BFS
                break
        # Actually do proper BFS: collect all nodes at current depth
        if depth + 1 in hops.values():
            node_id = None
            for v, h in hops.items():
                if h == depth + 1:
                    node_id = v
                    break
        else:
            break
        if node_id is None:
            break

    if own_db:
        db.close()

    # Build output
    nodes_out = [
        {"id": n, "type": node_types[n], "hop": hops[n]} for n in sorted(visited, key=lambda x: hops.get(x, 0))
    ]
    edges_out = [
        {"source": str(s), "target": str(t)} for s, t in edges_list
    ]

    return {
        "seed": wallet_or_tx_id,
        "seed_type": start_type,
        "max_hops": max_hops,
        "nodes": nodes_out,
        "edges": edges_out,
        "hops": {str(k): v for k, v in hops.items()},
        "max_reached": max(hops.values()) if hops else 0,
        "node_count": len(visited),
        "edge_count": len(edges_list),
    }
