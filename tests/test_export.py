#!/usr/bin/env python3
"""Unit tests for src/graph/export.py.

Tests Cytoscape JSON schema, file I/O, and trace conversion — no DuckDB.
"""

import json
import networkx as nx
import pytest
from pathlib import Path

from src.graph.export import (
    subgraph_to_cytoscape,
    subgraph_to_json_file,
    trace_to_cytoscape,
    CLASS_COLORS,
    CLASS_LABELS,
)
from src.graph.trace import trace_downstream


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture
def small_graph() -> nx.DiGraph:
    G = nx.DiGraph()
    G.add_node(1)
    G.add_node(2)
    G.add_node(3)
    nx.set_node_attributes(G, {1: 1, 2: 2, 3: 3}, "class")
    nx.set_node_attributes(G, {1: 1, 2: 1, 3: 2}, "timestep")
    G.add_edge(1, 2)
    G.add_edge(2, 3)
    return G


@pytest.fixture
def tmp_dir(tmp_path) -> Path:
    return tmp_path


# ---------------------------------------------------------------------------
# subgraph_to_cytoscape tests
# ---------------------------------------------------------------------------
class TestSubgraphToCytoscape:
    def test_basic_structure(self, small_graph):
        result = subgraph_to_cytoscape(small_graph)
        assert "nodes" in result
        assert "edges" in result
        assert len(result["nodes"]) == 3
        assert len(result["edges"]) == 2

    def test_node_schema(self, small_graph):
        result = subgraph_to_cytoscape(small_graph)
        # Find the illicit node by ID (don't assume order)
        illicit = [n for n in result["nodes"] if n["data"]["id"] == "1"][0]
        assert illicit["data"]["class"] == 1
        assert illicit["data"]["class_label"] == "illicit"
        assert illicit["data"]["color"] == "#ef4444"
        assert illicit["data"]["timestep"] == 1

        # Also verify licit and unknown nodes exist
        classes = {n["data"]["id"]: n["data"]["class"] for n in result["nodes"]}
        assert classes["2"] == 2
        assert classes["3"] == 3

    def test_edge_schema(self, small_graph):
        result = subgraph_to_cytoscape(small_graph)
        edge0 = result["edges"][0]
        assert "data" in edge0
        assert "source" in edge0["data"]
        assert "target" in edge0["data"]
        assert "id" in edge0["data"]

    def test_subset_nodes(self, small_graph):
        result = subgraph_to_cytoscape(
            small_graph, subgraph_nodes=[1, 2], subgraph_edges=[(1, 2)]
        )
        assert len(result["nodes"]) == 2
        assert len(result["edges"]) == 1

    def test_empty_subgraph(self, small_graph):
        result = subgraph_to_cytoscape(small_graph, subgraph_nodes=[], subgraph_edges=[])
        assert result["nodes"] == []
        assert result["edges"] == []

    def test_class_colors(self):
        assert CLASS_COLORS[1] == "#ef4444"  # illicit
        assert CLASS_COLORS[2] == "#22c55e"  # licit
        assert CLASS_COLORS[3] == "#6b7280"  # unknown

    def test_class_labels(self):
        assert CLASS_LABELS[1] == "illicit"
        assert CLASS_LABELS[2] == "licit"
        assert CLASS_LABELS[3] == "unknown"


# ---------------------------------------------------------------------------
# subgraph_to_json_file tests
# ---------------------------------------------------------------------------
class TestSubgraphToJsonFile:
    def test_write_and_read(self, small_graph, tmp_dir):
        cyto = subgraph_to_cytoscape(small_graph)
        out_path = str(tmp_dir / "test_export.json")
        result_path = subgraph_to_json_file(cyto, out_path)

        assert Path(result_path).exists()
        with open(result_path) as f:
            data = json.load(f)
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) == 3

    def test_creates_parent_dirs(self, small_graph, tmp_dir):
        cyto = subgraph_to_cytoscape(small_graph)
        out_path = str(tmp_dir / "sub" / "nested" / "export.json")
        result_path = subgraph_to_json_file(cyto, out_path)

        assert Path(result_path).exists()
        assert "nested" in result_path

    def test_pretty_json(self, small_graph, tmp_dir):
        cyto = subgraph_to_cytoscape(small_graph)
        out_path = str(tmp_dir / "pretty.json")
        subgraph_to_json_file(cyto, out_path, pretty=True)
        content = Path(out_path).read_text()
        assert "\n" in content  # pretty-printed has newlines

    def test_compact_json(self, small_graph, tmp_dir):
        cyto = subgraph_to_cytoscape(small_graph)
        out_path = str(tmp_dir / "compact.json")
        subgraph_to_json_file(cyto, out_path, pretty=False)
        content = Path(out_path).read_text()
        # Compact JSON should be one line
        assert content.count("\n") <= 1


# ---------------------------------------------------------------------------
# trace_to_cytoscape tests
# ---------------------------------------------------------------------------
class TestTraceToCytoscape:
    def test_trace_conversion(self, small_graph):
        trace = trace_downstream(small_graph, 1, max_hops=10)
        result = trace_to_cytoscape(small_graph, trace)

        assert "nodes" in result
        assert "edges" in result
        assert len(result["nodes"]) == 3

        # Check hop annotations
        hops = {n["data"]["id"]: n["data"]["hop"] for n in result["nodes"]}
        assert hops["1"] == 0
        assert hops["2"] == 1
        assert hops["3"] == 2

    def test_valid_cytoscape_schema(self, small_graph):
        """Verify output matches Cytoscape.js expected schema."""
        trace = trace_downstream(small_graph, 1, max_hops=2)
        result = trace_to_cytoscape(small_graph, trace)

        # Cytoscape requires "data" key with "id" on every node
        for node in result["nodes"]:
            assert "data" in node
            assert "id" in node["data"]

        # Cytoscape requires "data" key with "source" and "target" on every edge
        for edge in result["edges"]:
            assert "data" in edge
            assert "source" in edge["data"]
            assert "target" in edge["data"]

    def test_json_serializable(self, small_graph):
        """Ensure output can be serialized to JSON without errors."""
        trace = trace_downstream(small_graph, 1, max_hops=10)
        result = trace_to_cytoscape(small_graph, trace)
        # Should not raise
        json_str = json.dumps(result, default=str)
        assert len(json_str) > 0
