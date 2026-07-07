#!/usr/bin/env python3
"""Unit tests for src/graph/trace.py.

Tests on synthetic chain/graph fixtures — no DuckDB required.
"""

import networkx as nx
import pytest

from src.graph.trace import trace_downstream, trace_upstream


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def chain_graph() -> nx.DiGraph:
    """A→B→C→D→E linear chain with class labels."""
    G = nx.DiGraph()
    G.add_edges_from([(1, 2), (2, 3), (3, 4), (4, 5)])
    nx.set_node_attributes(G, {1: 1, 2: 3, 3: 3, 4: 3, 5: 3}, "class")
    return G


@pytest.fixture
def fan_graph() -> nx.DiGraph:
    """A node fans out to 5 nodes, each fanning out further."""
    G = nx.DiGraph()
    G.add_edge(0, 1)
    G.add_edge(0, 2)
    G.add_edge(0, 3)
    G.add_edge(1, 4)
    G.add_edge(2, 5)
    G.add_edge(3, 6)
    nx.set_node_attributes(G, {n: 3 for n in G.nodes()}, "class")
    G.nodes[0]["class"] = 1  # illicit
    return G


# ---------------------------------------------------------------------------
# Downstream trace tests
# ---------------------------------------------------------------------------
class TestTraceDownstream:
    def test_linear_chain_full(self, chain_graph):
        result = trace_downstream(chain_graph, 1, max_hops=10)
        assert result["max_reached"] == 4
        assert result["node_count"] == 5
        assert result["edge_count"] == 4
        assert result["direction"] == "downstream"

    def test_linear_chain_hops(self, chain_graph):
        result = trace_downstream(chain_graph, 1, max_hops=2)
        assert result["max_reached"] == 2
        assert result["node_count"] == 3  # 1, 2, 3
        assert 1 in result["nodes"]
        assert 2 in result["nodes"]
        assert 3 in result["nodes"]
        assert 4 not in result["nodes"]

    def test_hop_distances(self, chain_graph):
        result = trace_downstream(chain_graph, 1, max_hops=10)
        assert result["hops"][1] == 0
        assert result["hops"][2] == 1
        assert result["hops"][3] == 2
        assert result["hops"][4] == 3
        assert result["hops"][5] == 4

    def test_invalid_node(self, chain_graph):
        with pytest.raises(ValueError, match="not in graph"):
            trace_downstream(chain_graph, 999, max_hops=10)

    def test_class_filter(self, chain_graph):
        # Only follow illicit nodes (class 1)
        chain_graph.nodes[2]["class"] = 1
        chain_graph.nodes[3]["class"] = 1
        result = trace_downstream(chain_graph, 1, max_hops=10, class_filter=[1])
        # Should only reach nodes with class 1
        for node in result["nodes"]:
            if node != 1:  # seed is always included
                assert chain_graph.nodes[node]["class"] == 1

    def test_fan_outdownstream(self, fan_graph):
        result = trace_downstream(fan_graph, 0, max_hops=10)
        assert result["node_count"] == 7
        assert result["edge_count"] == 6
        assert result["max_reached"] == 2


# ---------------------------------------------------------------------------
# Upstream trace tests
# ---------------------------------------------------------------------------
class TestTraceUpstream:
    def test_linear_chain_upstream(self, chain_graph):
        result = trace_upstream(chain_graph, 5, max_hops=10)
        assert result["max_reached"] == 4
        assert result["node_count"] == 5
        assert result["direction"] == "upstream"

    def test_linear_chain_upstream_hops(self, chain_graph):
        result = trace_upstream(chain_graph, 5, max_hops=2)
        assert result["max_reached"] == 2
        assert result["node_count"] == 3  # 5, 4, 3

    def test_hop_distances_upstream(self, chain_graph):
        result = trace_upstream(chain_graph, 5, max_hops=10)
        assert result["hops"][5] == 0
        assert result["hops"][4] == 1
        assert result["hops"][3] == 2
        assert result["hops"][2] == 3
        assert result["hops"][1] == 4

    def test_invalid_node_upstream(self, chain_graph):
        with pytest.raises(ValueError, match="not in graph"):
            trace_upstream(chain_graph, 999, max_hops=10)

    def test_fan_in_upstream(self, fan_graph):
        # From node 4 back to 0
        result = trace_upstream(fan_graph, 4, max_hops=10)
        assert 0 in result["nodes"]
        assert 1 in result["nodes"]
        assert result["max_reached"] == 2
