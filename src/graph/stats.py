"""Graph statistics for NetworkX graphs."""

import logging
from typing import Tuple

import networkx as nx
import numpy as np

logger = logging.getLogger(__name__)


def compute_stats(G: nx.Graph) -> dict:
    """Compute basic graph statistics."""
    is_directed = G.is_directed()
    n_nodes = G.number_of_nodes()
    n_edges = G.number_of_edges()

    logger.info("Computing connected components (%d nodes, %d edges)...", n_nodes, n_edges)
    if is_directed:
        components = list(nx.weakly_connected_components(G))
    else:
        components = list(nx.connected_components(G))

    sizes = sorted([len(c) for c in components], reverse=True)
    degrees = [d for _, d in G.degree()]
    in_degrees = [d for _, d in G.in_degree()] if is_directed else degrees
    out_degrees = [d for _, d in G.out_degree()] if is_directed else degrees

    return {
        "num_nodes": n_nodes,
        "num_edges": n_edges,
        "density": nx.density(G),
        "num_connected_components": len(components),
        "largest_cc_size": sizes[0] if sizes else 0,
        "avg_degree": float(np.mean(degrees)) if degrees else 0.0,
        "max_degree": max(degrees) if degrees else 0,
        "max_in_degree": max(in_degrees) if in_degrees else 0,
        "max_out_degree": max(out_degrees) if out_degrees else 0,
    }


def degree_distribution(
    G: nx.Graph, mode: str = "in"
) -> Tuple[np.ndarray, np.ndarray]:
    """Compute in-degree (for DiGraph) or degree (for Graph) distribution.

    Parameters
    ----------
    mode : 'in', 'out', or 'degree'
    """
    if G.is_directed() and mode == "in":
        degs = [d for _, d in G.in_degree()]
    elif G.is_directed() and mode == "out":
        degs = [d for _, d in G.out_degree()]
    else:
        degs = [d for _, d in G.degree()]

    counts = np.bincount(degs)
    nonzero = np.where(counts > 0)
    return nonzero[0], counts[nonzero[0]]


def get_degree_histogram_data(
    G: nx.Graph, bins: int = 50, mode: str = "in"
) -> Tuple[np.ndarray, np.ndarray]:
    """Return (counts, bin_centers) for plotting degree distribution."""
    degs = np.array(
        [d for _, d in G.in_degree()]
        if G.is_directed() and mode == "in"
        else [d for _, d in G.degree()]
    )

    hist, edges = np.histogram(degs, bins=bins)
    centers = 0.5 * (edges[:-1] + edges[1:])
    return hist, centers


def connected_components_summary(G: nx.Graph) -> dict:
    """Summarize connected-component structure."""
    is_directed = G.is_directed()
    if is_directed:
        components = list(nx.weakly_connected_components(G))
    else:
        components = list(nx.connected_components(G))

    sizes = sorted([len(c) for c in components], reverse=True)
    total_nodes = G.number_of_nodes()

    return {
        "total": len(components),
        "sizes": sizes,
        "top_10": sizes[:10],
        "giant_fraction": sizes[0] / total_nodes if total_nodes > 0 else 0.0,
    }


def density_summary(G: nx.Graph) -> dict:
    """Density, clustering, and reciprocity summary."""
    s = {"density": nx.density(G)}
    if G.is_directed():
        s["reciprocity"] = nx.algorithms.reciprocity(G)
        # Average clustering on the undirected projection
        s["avg_clustering"] = nx.average_clustering(nx.Graph(G))
    else:
        s["avg_clustering"] = nx.average_clustering(G)
    return s
