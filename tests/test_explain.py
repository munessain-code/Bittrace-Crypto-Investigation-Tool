#!/usr/bin/env python3
"""Tests for Phase 6 explainability modules.

Covers:
  - SHAP computation on small RF model (transactions)
  - k-hop subgraph extraction on fixture graph
  - node_inspector returns expected dict keys on real data
"""

from __future__ import annotations

import pytest
import networkx as nx
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier

from src.explain.shap_explainer import ShapResult
from src.explain.subgraph_explainer import extract_k_hop_subgraph, get_subgraph_path
from src.explain.node_inspector import NodeExplanation


# ── Fixtures ──────────────────────────────────────────────────────────────

@pytest.fixture
def tiny_graph():
    """Small directed graph for subgraph testing."""
    G = nx.DiGraph()
    edges = [
        (1, 2), (2, 3), (3, 4), (1, 5), (5, 6),
        (7, 1), (8, 2), (4, 9), (6, 10),
    ]
    G.add_edges_from(edges)
    for nid in G.nodes:
        G.nodes[nid]["class"] = 1 if nid in (1, 3, 7) else 2
        G.nodes[nid]["timestep"] = (nid % 49) + 1
    return G


@pytest.fixture
def tiny_rf_model():
    """Tiny RF model trained on synthetic data for SHAP testing."""
    X = np.random.rand(200, 5)
    y = (X[:, 0] + X[:, 1] > 1.0).astype(int)
    model = RandomForestClassifier(n_estimators=5, random_state=42)
    model.fit(X, y)
    return model, list("ABCDE"), X[:20]


@pytest.fixture
def mock_model_results():
    """Mock ModelResults dataclass for node_inspector testing."""
    from dataclasses import dataclass, field

    @dataclass
    class FakeResults:
        model: RandomForestClassifier
        feature_names: list[str] = field(default_factory=list)

    X = np.random.rand(50, 3)
    y = (X[:, 0] > 0.5).astype(int)
    model = RandomForestClassifier(n_estimators=3, random_state=42)
    model.fit(X, y)
    return FakeResults(model=model, feature_names=["f0", "f1", "f2"])


# ── Subgraph tests ───────────────────────────────────────────────────────

class TestSubgraphExplainer:
    """k-hop subgraph extraction tests."""

    def test_extract_1_hop(self, tiny_graph):
        """1-hop from node 1 should get immediate neighbors."""
        result = extract_k_hop_subgraph(tiny_graph, node_id=1, k=1)
        assert result["seed"] == 1
        assert 2 in result["nodes"]
        assert 5 in result["nodes"]
        assert 7 in result["nodes"]
        assert result["stats"]["node_count"] >= 4
        assert "cytoscape" in result

    def test_extract_2_hop(self, tiny_graph):
        """2-hop from node 1 should get deeper neighbors."""
        result = extract_k_hop_subgraph(tiny_graph, node_id=1, k=2)
        assert result["stats"]["max_hop"] >= 2
        assert result["stats"]["node_count"] > len(
            extract_k_hop_subgraph(tiny_graph, node_id=1, k=1)["nodes"]
        )

    def test_max_nodes_cap(self, tiny_graph):
        """max_nodes cap should limit subgraph size."""
        result = extract_k_hop_subgraph(tiny_graph, node_id=1, k=5, max_nodes=5)
        assert result["stats"]["node_count"] <= 5

    def test_seed_class(self, tiny_graph):
        """Seed node class should be reported."""
        result = extract_k_hop_subgraph(tiny_graph, node_id=1, k=1)
        assert result["seed_class"] == "illicit"

    def test_nonexistent_node(self, tiny_graph):
        """Should raise ValueError for node not in graph."""
        with pytest.raises(ValueError, match="not in graph"):
            extract_k_hop_subgraph(tiny_graph, node_id=999, k=1)

    def test_cytoscape_output(self, tiny_graph):
        """Cytoscape output should have nodes and edges lists."""
        result = extract_k_hop_subgraph(tiny_graph, node_id=1, k=1)
        cy = result["cytoscape"]
        assert "nodes" in cy
        assert "edges" in cy
        assert len(cy["nodes"]) > 0
        assert len(cy["edges"]) > 0
        seed_nodes = [n for n in cy["nodes"] if n["data"].get("is_seed")]
        assert len(seed_nodes) == 1

    def test_subgraph_path(self, tiny_graph):
        """get_subgraph_path finds shortest path or returns None."""
        path = get_subgraph_path(tiny_graph, 1, 4)
        assert path is not None
        assert path[0] == 1
        assert path[-1] == 4
        assert len(path) <= 4

    def test_subgraph_path_none(self, tiny_graph):
        """No path between disconnected components returns None."""
        path = get_subgraph_path(tiny_graph, 1, 99)
        assert path is None


# ── SHAP tests ────────────────────────────────────────────────────────────

class TestShapExplainer:
    """SHAP value computation tests."""

    def test_shap_values_shape(self, tiny_rf_model):
        """SHAP values should match input shape."""
        model, feature_names, X_test = tiny_rf_model
        import shap
        explainer = shap.TreeExplainer(model)
        shap_vals = explainer.shap_values(X_test)
        # Binary classification: list of 2 arrays, or 3D array, or 2D array
        if isinstance(shap_vals, list):
            assert len(shap_vals) == 2
            assert shap_vals[1].shape == X_test.shape
        elif hasattr(shap_vals, 'ndim') and shap_vals.ndim == 3:
            assert shap_vals.shape[0] == X_test.shape[0]
            assert shap_vals.shape[1] == X_test.shape[1]

    def test_shap_importance_sign(self, tiny_rf_model):
        """SHAP values should have both positive and negative contributions."""
        model, feature_names, X_test = tiny_rf_model
        import shap
        explainer = shap.TreeExplainer(model)
        shap_vals = explainer.shap_values(X_test)
        if isinstance(shap_vals, list):
            shap_vals = shap_vals[1]
        elif hasattr(shap_vals, 'ndim') and shap_vals.ndim == 3:
            shap_vals = shap_vals[:, :, 1]
        assert shap_vals.min() < 0
        assert shap_vals.max() > 0

    def test_top_features_ranking(self, tiny_rf_model):
        """Top features should be sorted by mean absolute SHAP."""
        model, feature_names, X_test = tiny_rf_model
        import shap
        explainer = shap.TreeExplainer(model)
        shap_vals = explainer.shap_values(X_test)
        if isinstance(shap_vals, list):
            shap_vals = shap_vals[1]
        elif hasattr(shap_vals, 'ndim') and shap_vals.ndim == 3:
            shap_vals = shap_vals[:, :, 1]
        mean_abs = np.abs(shap_vals).mean(axis=0).flatten()
        top_idx = np.argsort(mean_abs)[::-1][:3].tolist()
        top_features = [
            (feature_names[i], float(mean_abs[i]))
            for i in top_idx
        ]
        assert len(top_features) == 3
        for i in range(len(top_features) - 1):
            assert top_features[i][1] >= top_features[i + 1][1]


# ── Node Inspector tests ─────────────────────────────────────────────────

class TestNodeInspector:
    """Node explanation dict tests."""

    def test_node_explanation_dataclass(self):
        """NodeExplanation has all required fields."""
        exp = NodeExplanation(
            node_id=123,
            node_type="transaction",
            class_label="illicit",
            class_value=1,
            timestep=12,
            risk_score=0.85,
            predicted_class="illicit",
        )
        assert exp.node_id == 123
        assert exp.class_label == "illicit"
        assert exp.risk_score == 0.85

    def test_to_dict(self):
        """to_dict serializes all fields."""
        exp = NodeExplanation(
            node_id=456,
            node_type="transaction",
            class_label="licit",
            class_value=2,
            timestep=5,
            risk_score=0.12,
            predicted_class="licit",
            shap_top5=[{"feature": "f0", "shap": 0.3, "value": 0.7}],
            features={"f0": 0.7},
            subgraph_node_count=15,
            subgraph_edge_count=12,
        )
        d = exp.to_dict()
        required_keys = {
            "node_id", "node_type", "class_label", "class_value",
            "timestep", "risk_score", "predicted_class", "shap_top5",
            "features", "subgraph_node_count", "subgraph_edge_count",
            "subgraph_path",
        }
        assert set(d.keys()) == required_keys
        assert d["node_id"] == 456
        assert len(d["shap_top5"]) == 1

    def test_shap_top_features_computation(self, tiny_rf_model):
        """_get_shap_top_features returns list of dicts sorted by |shap|."""
        from src.explain.node_inspector import _get_shap_top_features

        model, feature_names, X_test = tiny_rf_model
        sample = X_test[0]

        top = _get_shap_top_features(model, sample, feature_names, top_n=3)
        assert len(top) == 3
        assert all("feature" in t for t in top)
        assert all("shap" in t for t in top)
        assert all("value" in t for t in top)
        for i in range(len(top) - 1):
            assert abs(top[i]["shap"]) >= abs(top[i + 1]["shap"])

    def test_node_inspector_on_fixture_graph(self, tiny_graph, mock_model_results):
        """get_node_explanation handles missing data gracefully."""
        from src.explain.node_inspector import get_node_explanation

        exp = get_node_explanation(
            tiny_graph, mock_model_results, node_id=1, k=1,
        )
        assert exp.node_id == 1
        assert exp.class_label in ("illicit", "licit", "unknown")
        assert exp.node_type == "transaction"
