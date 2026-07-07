"""Lazy neighbor expansion for BitTrace graph explorer.

Expand a node's k-hop neighborhood up to a budget, pruning by
illicit-class priority to keep interesting nodes first.
"""

from __future__ import annotations

from collections import deque
from typing import Dict, List, Optional, Set, Tuple

import networkx as nx

from src.data.loaders import get_duckdb_connection


def expand_node(
    G: nx.DiGraph,
    node_id: int,
    budget: int = 500,
    max_depth: int = 2,
) -> Dict[str, object]:
    """BFS expansion from *node_id* up to *budget* nodes.

    Nodes are prioritized: illicit (class 1) > licit (class 2) > unknown (class 3),
    so the most interesting nodes are included first within the budget.

    Returns dict with:
      - nodes: list of node IDs
      - edges: list of (src, dst) tuples within the subgraph
      - node_count: int
      - edge_count: int
    """
    if node_id not in G:
        raise ValueError(f"Node {node_id} not in graph")

    # Priority: illicit=0 (highest), licit=1, unknown=2
    def priority(n: int) -> int:
        cls = G.nodes[n].get("class", 3)
        return 0 if cls == 1 else (1 if cls == 2 else 2)

    visited: Set[int] = {node_id}
    queue: deque = deque([(node_id, 0)])

    while queue:
        if len(visited) >= budget:
            break
        cur, depth = queue.popleft()
        if depth >= max_depth:
            continue

        # Collect neighbors and sort by priority
        neighbors = set()
        neighbors.update(G.successors(cur))
        neighbors.update(G.predecessors(cur))
        neighbors -= visited

        for nbr in sorted(neighbors, key=priority):
            if len(visited) >= budget:
                break
            visited.add(nbr)
            queue.append((nbr, depth + 1))

    # Build subgraph
    edges: List[Tuple[int, int]] = []
    for u in visited:
        for v in G.successors(u):
            if v in visited:
                edges.append((u, v))

    return {
        "seed": node_id,
        "nodes": sorted(visited),
        "edges": edges,
        "node_count": len(visited),
        "edge_count": len(edges),
        "budget": budget,
        "max_depth": max_depth,
    }


def expand_bipartite(
    wallet_id: str,
    budget: int = 300,
    db_conn=None,
) -> Dict[str, object]:
    """Expand around a wallet address through the bipartite addr↔tx graph.

    Returns dict with:
      - nodes: list of {id, type, class} dicts
      - edges: list of {source, target, type} dicts
      - node_count: int
    """
    own_db = db_conn is None
    if db_conn is None:
        db_conn = get_duckdb_connection()

    # Start with the wallet
    visited_addrs: Set[str] = {wallet_id}
    visited_txs: Set[int] = set()
    edges_list: List[Tuple[str, int]] = []

    # Hop 1: wallet → transactions
    tx_rows = db_conn.execute(
        f"SELECT txId FROM addr_tx_edges WHERE input_address = '{wallet_id}'"
    ).fetchall()
    for (tx_id,) in tx_rows:
        tx_id = int(tx_id)
        if len(visited_txs) < budget:
            visited_txs.add(tx_id)
            edges_list.append((wallet_id, tx_id))

    # Hop 2: transactions → other wallets (up to budget)
    for tx_id in list(visited_txs):
        if len(visited_addrs) + len(visited_txs) >= budget:
            break
        addr_rows = db_conn.execute(
            f"SELECT output_address FROM tx_addr_edges WHERE txId = {tx_id}"
        ).fetchall()
        for (addr,) in addr_rows:
            if addr not in visited_addrs and len(visited_addrs) + len(visited_txs) < budget:
                visited_addrs.add(addr)
                edges_list.append((tx_id, addr))

    if own_db:
        db_conn.close()

    nodes_out = [
        {"id": a, "type": "address", "class": None} for a in sorted(visited_addrs)
    ] + [
        {"id": t, "type": "transaction", "class": None} for t in sorted(visited_txs)
    ]

    edges_out = [
        {"source": str(s), "target": str(t), "type": "addr-tx"}
        for s, t in edges_list
    ]

    return {
        "seed": wallet_id,
        "seed_type": "address",
        "nodes": nodes_out,
        "edges": edges_out,
        "node_count": len(nodes_out),
        "edge_count": len(edges_out),
    }
