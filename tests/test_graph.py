"""Tests for src/graph modules — synthetic fixtures only."""

import networkx as nx
import numpy as np
import pytest

from src.graph import builders, stats, patterns


# ---------------------------------------------------------------------------
# Fixtures — tiny synthetic graphs
# ---------------------------------------------------------------------------

def make_peel_graph():
    """A graph with a clear 6-node peel chain: A -> B -> C -> D -> E -> F
    plus a fan-out node G -> H, I, J.
    """
    G = nx.DiGraph()
    # Peel chain (each node in-degree=1, out-degree=1 except ends)
    chain = ["A", "B", "C", "D", "E", "F"]
    for i in range(len(chain) - 1):
        G.add_edge(chain[i], chain[i + 1])
    # Fan-out node
    G.add_edge("G", "H")
    G.add_edge("G", "I")
    G.add_edge("G", "J")
    # Fan-in node
    G.add_edge("K", "L")
    G.add_edge("M", "L")
    G.add_edge("N", "L")

    # Attach class labels
    for n in G.nodes:
        G.nodes[n]["class"] = 1 if n in ("A", "G", "K") else 2
    return G


@pytest.fixture
def peel_graph():
    return make_peel_graph()


# ---------------------------------------------------------------------------
# Stats tests
# ---------------------------------------------------------------------------

class TestStats:
    def test_compute_stats_keys(self, peel_graph):
        s = stats.compute_stats(peel_graph)
        expected_keys = [
            "num_nodes", "num_edges", "density",
            "num_connected_components", "largest_cc_size",
            "avg_degree", "max_degree", "max_in_degree", "max_out_degree",
        ]
        for k in expected_keys:
            assert k in s, f"Missing key: {k}"

    def test_compute_stats_values(self, peel_graph):
        s = stats.compute_stats(peel_graph)
        # A-F (6) + G,H,I,J (4) + K,L,M,N (4) = 14 nodes
        assert s["num_nodes"] == 14
        # 5 chain + 3 fan-out + 3 fan-in = 11 edges
        assert s["num_edges"] == 11

    def test_degree_distribution(self, peel_graph):
        degs, counts = stats.degree_distribution(peel_graph)
        assert len(degs) > 0
        assert len(counts) > 0
        assert all(isinstance(d, (int, np.integer)) for d in degs)

    def test_connected_components_summary(self, peel_graph):
        s = stats.connected_components_summary(peel_graph)
        assert "total" in s
        assert "sizes" in s
        assert "top_10" in s
        assert "giant_fraction" in s
        assert s["total"] >= 1

    def test_density_summary(self, peel_graph):
        s = stats.density_summary(peel_graph)
        assert "density" in s
        assert "avg_clustering" in s
        assert "reciprocity" in s


# ---------------------------------------------------------------------------
# Pattern detection tests
# ---------------------------------------------------------------------------

class TestPatterns:
    def test_detect_peel_chains(self, peel_graph):
        chains = patterns.detect_peel_chains(peel_graph, min_length=3)
        assert len(chains) > 0, "Should find at least one peel chain"
        # The chain A->B->C->D->E->F has 6 nodes
        chain_lengths = [len(c) for c in chains]
        assert max(chain_lengths) >= 5, "Longest peel chain should be at least 5 nodes"

    def test_detect_fan_out(self, peel_graph):
        fans = patterns.detect_fan_out(peel_graph, min_degree=3)
        fan_nodes = [n for n, *_ in fans]
        assert "G" in fan_nodes, "G should be detected as fan-out node"

    def test_detect_fan_in(self, peel_graph):
        fans = patterns.detect_fan_in(peel_graph, min_degree=3)
        fan_nodes = [n for n, *_ in fans]
        assert "L" in fan_nodes, "L should be detected as fan-in node"

    def test_fan_illicit_counts(self, peel_graph):
        s = patterns.get_fan_illicit_counts(peel_graph, min_degree=3)
        assert "fan_out_total" in s
        assert "fan_out_illicit" in s
        assert "illicit_ratio_out" in s
        assert "fan_in_total" in s
        assert "fan_in_illicit" in s
        assert "illicit_ratio_in" in s
        # G is class=1 (illicit)
        assert s["fan_out_illicit"] >= 1

    def test_path_length_distribution(self, peel_graph):
        s = patterns.path_length_distribution(peel_graph)
        assert "path_lengths" in s
        assert "hist_counts" in s
        assert "hist_edges" in s
        assert len(s["path_lengths"]) > 0

    def test_summarize_layering_patterns(self, peel_graph):
        s = patterns.summarize_layering_patterns(peel_graph)
        expected = [
            "peel_chains", "longest_peel_chain",
            "fan_out_nodes", "fan_in_nodes",
            "fan_illicit", "avg_path_length", "max_path_length",
        ]
        for k in expected:
            assert k in s, f"Missing key: {k}"
        assert s["longest_peel_chain"] >= 5
        assert s["fan_out_nodes"] >= 1
        assert s["fan_in_nodes"] >= 1
