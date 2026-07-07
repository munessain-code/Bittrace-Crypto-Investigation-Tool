#!/usr/bin/env python3
"""GAT (Graph Attention Network) for transaction classification.

Binary classification: illicit (1) vs licit (0), unknown excluded.

Architecture:
    GATConv(in_feat, 32, heads=2) -> ELU -> Dropout
    GATConv(64, 16, heads=2) -> ELU -> Dropout
    Linear(32, 2)

Multi-head attention lets the model attend to different neighbor
subspaces simultaneously — useful for detecting diverse fraud patterns.

Usage:
    from src.models.gat import GATClassifier

    model = GATClassifier(num_features=134, num_classes=2)
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
from torch_geometric.nn import GATConv


@dataclass
class GATConfig:
    """Configuration for GAT training."""
    hidden1: int = 32
    heads1: int = 2
    hidden2: int = 16
    heads2: int = 2
    dropout: float = 0.6
    alpha: float = 0.2  # GAT negative slope
    lr: float = 0.005
    weight_decay: float = 4e-4
    epochs: int = 50
    patience: int = 10
    verbose: bool = True


class GAT(nn.Module):
    """2-layer GAT for binary transaction classification."""

    def __init__(
        self,
        num_features: int,
        hidden1: int = 32,
        heads1: int = 2,
        hidden2: int = 16,
        heads2: int = 2,
        dropout: float = 0.6,
        alpha: float = 0.2,
    ):
        super().__init__()
        self.conv1 = GATConv(
            num_features, hidden1,
            heads=heads1, dropout=dropout, negative_slope=alpha,
        )
        self.conv2 = GATConv(
            hidden1 * heads1, hidden2,
            heads=heads2, dropout=dropout, negative_slope=alpha,
        )
        self.dropout_val = dropout

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        x = self.conv1(x, edge_index)
        x = F.elu(x)
        x = F.dropout(x, p=self.dropout_val, training=self.training)

        x = self.conv2(x, edge_index)
        x = F.elu(x)
        x = F.dropout(x, p=self.dropout_val, training=self.training)

        return x

    @property
    def output_dim(self) -> int:
        return self.conv2.out_channels * self.conv2.heads


class GATClassifier(nn.Module):
    """GAT with final classification head."""

    def __init__(self, num_features: int, num_classes: int = 2, **kwargs):
        super().__init__()
        self.gat = GAT(num_features, **kwargs)
        self.classifier = nn.Linear(self.gat.output_dim, num_classes)

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> torch.Tensor:
        h = self.gat(x, edge_index)
        return self.classifier(h)


def train(
    model: GATClassifier,
    data: Data,
    config: GATConfig = GATConfig(),
    train_mask: Optional[torch.Tensor] = None,
    val_mask: Optional[torch.Tensor] = None,
    test_mask: Optional[torch.Tensor] = None,
) -> "GATResults":
    """Train the GAT with early stopping on validation F1."""
    from src.models.gcn import compute_metrics

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
            val_metrics = compute_metrics(val_preds, data.y[val_mask])

        history["loss"].append(loss.item())
        history["val_f1"].append(val_metrics["f1"])
        history["val_recall"].append(val_metrics["recall"])

        if config.verbose and (epoch % 10 == 0 or epoch == 1):
            elapsed = time.time() - start_time
            print(f"  Epoch {epoch:3d} | loss={loss.item():.4f} | "
                  f"val_f1={val_metrics['f1']:.4f} | val_recall={val_metrics['recall']:.4f} | "
                  f"time={elapsed:.1f}s")

        # Early stopping
        if val_metrics["f1"] > best_val_f1:
            best_val_f1 = val_metrics["f1"]
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

        test_preds = final_out[test_mask].argmax(dim=1)
        test_metrics = compute_metrics(test_preds, data.y[test_mask])

        train_preds = final_out[train_mask].argmax(dim=1)
        train_metrics = compute_metrics(train_preds, data.y[train_mask])

        val_preds = final_out[val_mask].argmax(dim=1)
        val_metrics = compute_metrics(val_preds, data.y[val_mask])

    elapsed = time.time() - start_time

    return GATResults(
        history=history,
        train_metrics=train_metrics,
        val_metrics=val_metrics,
        test_metrics=test_metrics,
        epochs_run=len(history["loss"]),
        training_time=elapsed,
    )


@dataclass
class GATResults:
    """Training results container."""
    history: dict
    train_metrics: dict
    val_metrics: dict
    test_metrics: dict
    epochs_run: int
    training_time: float
