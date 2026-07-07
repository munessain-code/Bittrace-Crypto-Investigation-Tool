"""Layering pattern detection for BitTrace transaction graphs.

Detects peel chains, fan-in/fan-out, and path-length statistics
that are common indicators of money-layering behaviour.
"""

import logging
from typing import List, Optional, Tuple

import networkx as nx
import numpy as np

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Peel-chain detection
# ---------------------------------------------------------------------------
def detect_peel_chains(
    G: nx.DiGraph,
    min_length: int = 3,
    max_chains: int = 10000,
) -> List[List]:
    """Find peel chains — linear paths through degree-(1,1) nodes.

    A peel chain is a path where every intermediate node has in-degree == 1
    and out-degree == 1.  The chain starts at a node whose in-degree != 1
    (typically a fan-in or a source) and ends when a node's out-degree != 1.
    """
    chains: List[List] = []
    visited: set = set()

    # Candidates: nodes with out_degree == 1 that can start or continue a chain
    for node in G.nodes():
        in_d = G.in_degree(node)
        out_d = G.out_degree(node)
        # A chain start is any node with out_degree==1 whose predecessor
        # does NOT have out_degree==1 (i.e. it's a branching point or source)
        is_start = (out_d == 1) and (
            in_d == 0  # true source
            or in_d > 1  # fan-in node
            or (in_d == 1 and G.predecessors(node).__next__().__hash__  # has predecessor
                and G.out_degree(list(G.predecessors(node))[0]) != 1)  # predecessor branches
        )
        # Simpler: just start from any node with out_degree==1 and in_degree<=1
        # that hasn't been consumed by a longer chain yet
        if out_d != 1 or node in visited:
            continue

        # Trace forward
        chain = [node]
        cur = node
        while True:
            successors = list(G.successors(cur))
            if not successors:
                break
            nxt = successors[0]
            if G.out_degree(nxt) != 1:
                # Last node in chain (it fans out or is a sink)
                chain.append(nxt)
                break
            chain.append(nxt)
            cur = nxt
            if len(chain) > 5000:
                # Safety cap on a single chain
                break

        if len(chain) >= min_length:
            chains.append(chain)
            visited.update(chain[:-1])  # Don't block the fan node

        if len(chains) >= max_chains:
            break

    return chains


def get_longest_peel_chains(
    G: nx.DiGraph,
    top_k: int = 10,
    min_length: int = 3,
) -> List[List]:
    """Return the *top_k* longest peel chains."""
    chains = detect_peel_chains(G, min_length=min_length)
    chains.sort(key=len, reverse=True)
    return chains[:top_k]


# ---------------------------------------------------------------------------
# Fan-in / Fan-out
# ---------------------------------------------------------------------------
def detect_fan_out(
    G: nx.DiGraph,
    min_degree: int = 3,
) -> List[Tuple]:
    """Nodes whose out-degree >= *min_degree*."""
    return [
        (n, d, list(G.successors(n)))
        for n, d in G.out_degree()
        if d >= min_degree
    ]


def detect_fan_in(
    G: nx.DiGraph,
    min_degree: int = 3,
) -> List[Tuple]:
    """Nodes whose in-degree >= *min_degree*."""
    return [
        (n, d, list(G.predecessors(n)))
        for n, d in G.in_degree()
        if d >= min_degree
    ]


def get_fan_illicit_counts(
    G: nx.DiGraph,
    min_degree: int = 3,
) -> dict:
    """Count how many fan-in/fan-out nodes are illicit (class == 1)."""
    fan_out = detect_fan_out(G, min_degree)
    fan_in = detect_fan_in(G, min_degree)

    def count_illicit(nodes_info):
        total = len(nodes_info)
        illicit = 0
        for n, *_ in nodes_info:
            cls = G.nodes[n].get("class")
            if cls == 1:
                illicit += 1
        ratio = illicit / total if total > 0 else 0.0
        return total, illicit, ratio

    fo_total, fo_illicit, fo_ratio = count_illicit(fan_out)
    fi_total, fi_illicit, fi_ratio = count_illicit(fan_in)

    return {
        "fan_out_total": fo_total,
        "fan_out_illicit": fo_illicit,
        "illicit_ratio_out": fo_ratio,
        "fan_in_total": fi_total,
        "fan_in_illicit": fi_illicit,
        "illicit_ratio_in": fi_ratio,
    }


# ---------------------------------------------------------------------------
# Path-length distribution
# ---------------------------------------------------------------------------
def path_length_distribution(
    G: nx.DiGraph,
    max_samples: int = 1000,
    max_depth: int = 50,
) -> dict:
    """BFS shortest-path lengths from sampled source nodes.

    Returns dict with ``path_lengths`` (flat list), ``hist_bins``, ``hist_counts``.
    """
    # Prefer source nodes (in-degree == 0), fall back to random
    sources = [n for n, d in G.in_degree() if d == 0]
    if not sources:
        sources = list(G.nodes())
    np.random.shuffle(sources)
    sources = sources[:max_samples]

    all_lengths: list[int] = []
    for src in sources:
        try:
            lengths = nx.single_source_shortest_path_length(G, src, cutoff=max_depth)
            for l in lengths.values():
                if l > 0:
                    all_lengths.append(l)
        except nx.NetworkXUnbounded:
            continue

    all_lengths = sorted(all_lengths)
    if all_lengths:
        bins = np.logspace(0, np.ceil(np.log10(max(all_lengths))), 30).astype(int)
        hist_counts, hist_edges = np.histogram(all_lengths, bins=bins)
    else:
        hist_counts = np.array([], dtype=int)
        hist_edges = np.array([])

    return {
        "path_lengths": all_lengths,
        "hist_counts": hist_counts,
        "hist_edges": hist_edges,
    }


# ---------------------------------------------------------------------------
# Combined summary
# ---------------------------------------------------------------------------
def summarize_layering_patterns(
    G: nx.DiGraph,
    min_length: int = 3,
    min_degree: int = 3,
    max_samples: int = 1000,
) -> dict:
    """One-call summary of all layering patterns."""
    logger.info("Summarizing layering patterns...")

    chains = detect_peel_chains(G, min_length=min_length, max_chains=10000)
    longest = max((len(c) for c in chains), default=0)

    fan_out = detect_fan_out(G, min_degree=min_degree)
    fan_in = detect_fan_in(G, min_degree=min_degree)

    illicit = get_fan_illicit_counts(G, min_degree=min_degree)

    pl = path_length_distribution(G, max_samples=max_samples)
    lengths = pl["path_lengths"]

    return {
        "peel_chains": len(chains),
        "longest_peel_chain": longest,
        "fan_out_nodes": len(fan_out),
        "fan_in_nodes": len(fan_in),
        "fan_illicit": illicit,
        "avg_path_length": float(np.mean(lengths)) if lengths else 0.0,
        "max_path_length": float(max(lengths)) if lengths else 0.0,
    }
