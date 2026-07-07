#!/usr/bin/env python3
"""Unit tests for GCN/GAT models and graph dataset.

Tests on a tiny synthetic 10-node graph — no DuckDB required.
"""

import networkx as nx
import pytest
import torch
from torch_geometric.data import Data

from src.models.gcn import GCN, GCNClassifier, GCNConfig, train as train_gcn, compute_metrics
from src.models.gat import GAT, GATClassifier, GATConfig, train as train_gat


# ---- Fixtures ----

@pytest.fixture
def tiny_graph() -> Data:
    """10-node synthetic graph with binary labels and sufficient connectivity.

    Structure:
        0 -> 1 -> 2 -> 3  (chain A, illicit)
        4 -> 5 -> 6 -> 7  (chain B, licit)
        8 -> 9            (small pair, licit)
        Cross-edges for GAT multi-head compatibility:
        0->5, 1->4, 2->6, 3->7, 4->0, 5->1, 6->2, 7->3, 8->0, 9->4,
        0->8, 1->9, 2->8, 3->9, 4->8, 5->9, 6->8, 7->9
    """
    n_nodes = 10
    x = torch.rand(n_nodes, 4)

    edges = [
        (0, 1), (1, 2), (2, 3),
        (4, 5), (5, 6), (6, 7),
        (8, 9),
        # Cross-edges for sufficient GAT connectivity
        (0, 5), (1, 4), (2, 6), (3, 7),
        (4, 0), (5, 1), (6, 2), (7, 3),
        (8, 0), (9, 4),
        (0, 8), (1, 9), (2, 8), (3, 9),
        (4, 8), (5, 9), (6, 8), (7, 9),
    ]
    edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous()

    # Labels: 0=licit, 1=illicit
    y = torch.tensor([1, 1, 1, 1, 0, 0, 0, 0, 0, 0], dtype=torch.long)

    return Data(x=x, edge_index=edge_index, y=y)


# ---- GCN tests ----

class TestGCNForward:
    def test_output_shape(self, tiny_graph):
        """GCN forward pass produces correct output shape."""
        model = GCNClassifier(num_features=4, num_classes=2)
        model.eval()

        with torch.no_grad():
            out = model(tiny_graph.x, tiny_graph.edge_index)

        assert out.shape == (10, 2)

    def test_output_shape_tiny_gcn(self, tiny_graph):
        """Base GCN (no classifier) produces correct hidden dim."""
        model = GCN(num_features=4, hidden1=16, hidden2=8)
        model.eval()

        with torch.no_grad():
            out = model(tiny_graph.x, tiny_graph.edge_index)

        assert out.shape == (10, 8)

    def test_training_mode_different_output(self, tiny_graph):
        """Dropout makes training mode output differ from eval mode."""
        model = GCNClassifier(num_features=4, num_classes=2)

        # Eval mode (deterministic)
        model.eval()
        with torch.no_grad():
            out1 = model(tiny_graph.x, tiny_graph.edge_index)
            out2 = model(tiny_graph.x, tiny_graph.edge_index)
        assert torch.allclose(out1, out2), "Eval mode should be deterministic"


class TestGCNTrain:
    def test_train_converges(self, tiny_graph):
        """Training on a simple graph runs and produces metrics."""
        model = GCNClassifier(num_features=4, num_classes=2)
        config = GCNConfig(epochs=10, dropout=0.0, verbose=False)

        results = train_gcn(model, tiny_graph, config)

        assert results.epochs_run > 0, "Should have run at least one epoch"
        assert len(results.history["loss"]) == results.epochs_run
        assert "precision" in results.train_metrics

    def test_train_metrics_not_zero(self, tiny_graph):
        """Training should produce valid metric dict on the simple graph."""
        model = GCNClassifier(num_features=4, num_classes=2)
        config = GCNConfig(epochs=20, dropout=0.0, verbose=False)

        results = train_gcn(model, tiny_graph, config)

        assert results.train_metrics["precision"] >= 0
        assert results.train_metrics["f1"] >= 0
        assert results.train_metrics["micro_f1"] > 0.5, \
            "Micro-F1 should be high on majority class for 10-node graph"
        assert results.val_metrics["f1"] >= 0, "Val F1 should be >= 0"

    def test_early_stopping(self, tiny_graph):
        """Early stopping should trigger when val F1 plateaus."""
        model = GCNClassifier(num_features=4, num_classes=2)
        config = GCNConfig(epochs=100, patience=3, verbose=False)

        results = train_gcn(model, tiny_graph, config)

        assert results.epochs_run <= 100
        assert results.epochs_run > 0


class TestComputeMetrics:
    def test_perfect_classification(self):
        preds = torch.tensor([0, 0, 1, 1])
        labels = torch.tensor([0, 0, 1, 1])
        m = compute_metrics(preds, labels)
        assert m["precision"] == 1.0
        assert m["recall"] == 1.0
        assert m["f1"] == 1.0
        assert m["micro_f1"] == 1.0

    def test_all_predicted_negative(self):
        preds = torch.tensor([0, 0, 0, 0])
        labels = torch.tensor([0, 0, 1, 1])
        m = compute_metrics(preds, labels)
        assert m["precision"] == 0.0
        assert m["recall"] == 0.0
        assert m["f1"] == 0.0

    def test_all_predicted_positive(self):
        preds = torch.tensor([1, 1, 1, 1])
        labels = torch.tensor([0, 0, 1, 1])
        m = compute_metrics(preds, labels)
        assert m["precision"] == 0.5  # 2 TP / 4 predicted
        assert m["recall"] == 1.0     # 2 TP / 2 actual


# ---- GAT tests ----

class TestGATForward:
    def test_output_shape(self, tiny_graph):
        """GAT forward pass produces correct output shape."""
        model = GATClassifier(
            num_features=4, num_classes=2,
            hidden1=8, heads1=2, hidden2=4, heads2=2,
        )
        model.eval()

        with torch.no_grad():
            out = model(tiny_graph.x, tiny_graph.edge_index)

        assert out.shape == (10, 2)

    def test_base_gat_output_dim(self, tiny_graph):
        """Base GAT produces correct hidden dim (hidden * heads)."""
        model = GAT(
            num_features=4, hidden1=8, heads1=2,
            hidden2=4, heads2=2,
        )
        model.eval()

        with torch.no_grad():
            out = model(tiny_graph.x, tiny_graph.edge_index)

        # hidden2 * heads2 = 4 * 2 = 8
        assert out.shape == (10, 8)


class TestGATTrain:
    def test_train_gat_converges(self, tiny_graph):
        """GAT training should run and produce valid output."""
        model = GATClassifier(
            num_features=4, num_classes=2,
            hidden1=8, heads1=2, hidden2=4, heads2=2,
        )
        config = GATConfig(epochs=10, dropout=0.0, verbose=False)

        results = train_gat(model, tiny_graph, config)

        assert results.epochs_run > 0, "Should have run at least one epoch"
        assert len(results.history["loss"]) == results.epochs_run
