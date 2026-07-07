#!/usr/bin/env python3
"""GCN (Graph Convolutional Network) for transaction classification.

Binary classification: illicit (1) vs licit (0), unknown excluded.

Architecture:
    GCNConv(in_feat, 64) -> ReLU -> Dropout -> BatchNorm
    GCNConv(64, 32) -> ReLU -> Dropout -> BatchNorm
    Linear(32, 2)

Trained with binary cross-entropy on labeled nodes.
Uses PyG's built-in train/val/test split utilities.

Usage:
    from src.models.gcn import GCNClassifier

    model = GCNClassifier(num_features=134, num_classes=2)
    output = model(data.x, data.edge_index)  # (N, 2)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

import torch
import torch.nn.functional as F
from torch import nn
from torch_geometric.data import Data
from torch_geometric.nn import GCNConv


@dataclass
class GCNConfig:
    """Configuration for GCN training."""
    hidden1: int = 64
    hidden2: int = 32
    dropout: float = 0.5
    lr: float = 0.01
    weight_decay: float = 5e-4
    epochs: int = 50
    patience: int = 10
    batch_norm: bool = True
    verbose: bool = True


class GCN(nn.Module):
    """2-layer GCN for binary transaction classification."""

    def __init__(self, num_features: int, hidden1: int = 64, hidden2: int = 32,
                 dropout: float = 0.5):
        super().__init__()
        self.conv1 = GCNConv(num_features, hidden1)
        self.conv2 = GCNConv(hidden1, hidden2)

        self.bn1 = nn.BatchNorm1d(hidden1)
        self.bn2 = nn.BatchNorm1d(hidden2)

        self.dropout_val = dropout

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        x = self.conv1(x, edge_index)
        x = self.bn1(x)
        x = F.relu(x)
        x = F.dropout(x, p=self.dropout_val, training=self.training)

        x = self.conv2(x, edge_index)
        x = self.bn2(x)
        x = F.relu(x)
        x = F.dropout(x, p=self.dropout_val, training=self.training)

        return x

    @property
    def output_dim(self) -> int:
        return self.conv2.out_channels


class GCNClassifier(nn.Module):
    """GCN with final classification head."""

    def __init__(self, num_features: int, num_classes: int = 2, **kwargs):
        super().__init__()
        self.gcn = GCN(num_features, **kwargs)
        self.classifier = nn.Linear(self.gcn.output_dim, num_classes)

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        h = self.gcn(x, edge_index)
        return self.classifier(h)


def train(
    model: GCNClassifier,
    data: Data,
    config: GCNConfig = GCNConfig(),
    train_mask: Optional[torch.Tensor] = None,
    val_mask: Optional[torch.Tensor] = None,
    test_mask: Optional[torch.Tensor] = None,
) -> "GCNResults":
    """Train the GCN with early stopping on validation F1.

    Returns training history and final metrics.
    """
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)
    data = data.to(device)

    optimizer = torch.optim.Adam(
        model.parameters(), lr=config.lr, weight_decay=config.weight_decay
    )

    # Manual train/val/test split if no masks provided
    if train_mask is None:
        n = len(data.y)
        indices = torch.randperm(n)
        train_size = int(0.7 * n)
        val_size = int(0.15 * n)
        train_mask = indices[:train_size]
        val_mask = indices[train_size: train_size + val_size]
        test_mask = indices[train_size + val_size:]

    history = {"loss": [], "val_f1": [], "val_recall": []}
    best_val_f1 = 0.0
    patience_counter = 0
    best_state = None

    start_time = time.time()

    for epoch in range(1, config.epochs + 1):
        model.train()
        optimizer.zero_grad()

        out = model(data.x, data.edge_index)
        loss = F.cross_entropy(out[train_mask], data.y[train_mask])
        loss.backward()
        optimizer.step()

        # Validation metrics
        model.eval()
        with torch.no_grad():
            val_out = model(data.x, data.edge_index)[val_mask]
            val_preds = val_out.argmax(dim=1)
            val_f1 = _f1_score(val_preds, data.y[val_mask])
            val_recall = _recall_score(val_preds, data.y[val_mask])

        history["loss"].append(loss.item())
        history["val_f1"].append(val_f1)
        history["val_recall"].append(val_recall)

        if config.verbose and (epoch % 10 == 0 or epoch == 1):
            elapsed = time.time() - start_time
            print(f"  Epoch {epoch:3d} | loss={loss.item():.4f} | "
                  f"val_f1={val_f1:.4f} | val_recall={val_recall:.4f} | "
                  f"time={elapsed:.1f}s")

        # Early stopping
        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            patience_counter = 0
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
        else:
            patience_counter += 1
            if patience_counter >= config.patience:
                if config.verbose:
                    print(f"  Early stopping at epoch {epoch}")
                break

    # Load best model
    if best_state:
        model.load_state_dict(best_state)

    # Final evaluation
    model.eval()
    with torch.no_grad():
        final_out = model(data.x, data.edge_index)

        # Test set metrics
        if test_mask is not None or (train_mask is None and len(data.y) > 0):
            if train_mask is None:
                test_mask = indices[train_size + val_size:]

            test_preds = final_out[test_mask].argmax(dim=1)
            test_y = data.y[test_mask]

            test_metrics = compute_metrics(test_preds, test_y)

            # Also compute train and val metrics
            train_preds = final_out[train_mask].argmax(dim=1)
            train_metrics = compute_metrics(train_preds, data.y[train_mask])

            val_preds = final_out[val_mask].argmax(dim=1)
            val_metrics = compute_metrics(val_preds, data.y[val_mask])
        else:
            test_metrics = {"precision": 0, "recall": 0, "f1": 0, "micro_f1": 0}
            train_metrics = {"precision": 0, "recall": 0, "f1": 0, "micro_f1": 0}
            val_metrics = {"precision": 0, "recall": 0, "f1": 0, "micro_f1": 0}

    elapsed = time.time() - start_time
    epochs_run = len(history["loss"])

    return GCNResults(
        history=history,
        train_metrics=train_metrics,
        val_metrics=val_metrics,
        test_metrics=test_metrics,
        epochs_run=epochs_run,
        training_time=elapsed,
    )


@dataclass
class GCNResults:
    """Training results container."""
    history: dict
    train_metrics: dict
    val_metrics: dict
    test_metrics: dict
    epochs_run: int
    training_time: float


# ---- Metric helpers ----

def _recall_score(preds: torch.Tensor, labels: torch.Tensor) -> float:
    """Recall for class 1 (illicit)."""
    tp = ((preds == 1) & (labels == 1)).sum().item()
    actual = (labels == 1).sum().item()
    return tp / actual if actual > 0 else 0.0


def _f1_score(preds: torch.Tensor, labels: torch.Tensor) -> float:
    """Macro F1 for binary classification."""
    prec = _precision_score(preds, labels)
    rec = _recall_score(preds, labels)
    return 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0


def _precision_score(preds: torch.Tensor, labels: torch.Tensor) -> float:
    """Precision for class 1 (illicit)."""
    tp = ((preds == 1) & (labels == 1)).sum().item()
    predicted = (preds == 1).sum().item()
    return tp / predicted if predicted > 0 else 0.0


def compute_metrics(preds: torch.Tensor, labels: torch.Tensor) -> dict:
    """Compute precision, recall, F1, micro-F1 for binary classification.

    Returns dict with keys: precision, recall, f1, micro_f1
    All metrics target class 1 (illicit).
    """
    tp = ((preds == 1) & (labels == 1)).sum().item()
    fp = ((preds == 1) & (labels == 0)).sum().item()
    fn = ((preds == 0) & (labels == 1)).sum().item()
    tn = ((preds == 0) & (labels == 0)).sum().item()

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0

    # Micro F1 (same as accuracy for binary)
    total = tp + fp + fn + tn
    micro_f1 = (tp + tn) / total if total > 0 else 0.0

    return {
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "micro_f1": round(micro_f1, 4),
        "tp": tp, "fp": fp, "fn": fn, "tn": tn,
    }
