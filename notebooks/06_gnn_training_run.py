#!/usr/bin/env python3
"""GNN training notebook — GCN/GAT on transaction graph.

Loads labeled nodes from DuckDB, builds PyG dataset, trains GCN
and GAT models, compares against RF baseline.

Outputs:
  - docs/gcn_loss_curve.png, docs/gat_loss_curve.png
  - docs/results.md (benchmark table)
  - Console metrics summary

Usage:
  python notebooks/06_gnn_training_run.py [--sample 0.1]
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import argparse
import time

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import torch

from src.models.graph_dataset import build_labeled_dataset
from src.models.gcn import GCNClassifier, GCNConfig, train as train_gcn
from src.models.gat import GATClassifier, GATConfig, train as train_gat
from src.models.evaluation import (
    ModelResult, write_results_md, get_rf_baseline_metrics,
)


def plot_loss_curve(history: dict, title: str, output_path: str) -> None:
    """Plot training and validation loss curves."""
    plt.figure(figsize=(10, 5))

    plt.subplot(1, 2, 1)
    plt.plot(history["loss"], label="Training Loss", color="steelblue")
    plt.xlabel("Epoch")
    plt.ylabel("Loss")
    plt.title(f"{title} — Loss Curve")
    plt.legend()
    plt.grid(alpha=0.3)

    plt.subplot(1, 2, 2)
    plt.plot(history["val_f1"], label="Val F1", color="darkorange")
    plt.plot(history["val_recall"], label="Val Recall", color="seagreen")
    plt.xlabel("Epoch")
    plt.ylabel("Score")
    plt.title(f"{title} — Validation Metrics")
    plt.legend()
    plt.grid(alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {output_path}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sample", type=float, default=None,
                        help="Graph sample percentage (e.g. 0.1 for 10%%)")
    parser.add_argument("--epochs", type=int, default=50,
                        help="Max training epochs")
    parser.add_argument("--no-gat", action="store_true",
                        help="Skip GAT training")
    args = parser.parse_args()

    os.makedirs("docs", exist_ok=True)

    # ---- Load dataset ----
    print("=== Building graph dataset ===")
    sample_info = f" ({args.sample:.0f}%% sample)" if args.sample else ""
    print(f"  Mode: labeled nodes only{sample_info}")

    data = build_labeled_dataset(sample_pct=args.sample / 100 if args.sample else None)
    print(f"  Nodes: {data.num_nodes}, Edges: {data.num_edges}")
    print(f"  Features: {data.x.shape[1]}")
    print(f"  Class distribution: licit={(data.y==0).sum().item()}, "
          f"illicit={(data.y==1).sum().item()}")

    # ---- Train GCN ----
    print("\n=== Training GCN ===")
    gcn_model = GCNClassifier(num_features=data.x.shape[1], num_classes=2)
    gcn_config = GCNConfig(epochs=args.epochs, verbose=True)

    gcn_results = train_gcn(gcn_model, data, gcn_config)

    print(f"\n  GCN Results:")
    print(f"    Test  — P: {gcn_results.test_metrics['precision']:.4f}, "
          f"R: {gcn_results.test_metrics['recall']:.4f}, "
          f"F1: {gcn_results.test_metrics['f1']:.4f}, "
          f"Micro: {gcn_results.test_metrics['micro_f1']:.4f}")
    print(f"    Epochs: {gcn_results.epochs_run}, Time: {gcn_results.training_time:.1f}s")

    plot_loss_curve(gcn_results.history, "GCN", "docs/gcn_loss_curve.png")

    # ---- Train GAT ----
    gat_results = None
    if not args.no_gat:
        print("\n=== Training GAT ===")
        gat_model = GATClassifier(
            num_features=data.x.shape[1], num_classes=2,
            hidden1=16, heads1=2, hidden2=8, heads2=2,
        )
        gat_config = GATConfig(epochs=args.epochs, verbose=True)

        gat_results = train_gat(gat_model, data, gat_config)

        print(f"\n  GAT Results:")
        print(f"    Test  — P: {gat_results.test_metrics['precision']:.4f}, "
              f"R: {gat_results.test_metrics['recall']:.4f}, "
              f"F1: {gat_results.test_metrics['f1']:.4f}, "
              f"Micro: {gat_results.test_metrics['micro_f1']:.4f}")
        print(f"    Epochs: {gat_results.epochs_run}, Time: {gat_results.training_time:.1f}s")

        plot_loss_curve(gat_results.history, "GAT", "docs/gat_loss_curve.png")

    # ---- Compare with RF baseline ----
    print("\n=== Benchmark Comparison ===")
    rf_metrics = get_rf_baseline_metrics()

    results = [
        ModelResult(
            name="GCN",
            precision=gcn_results.test_metrics["precision"],
            recall=gcn_results.test_metrics["recall"],
            f1=gcn_results.test_metrics["f1"],
            micro_f1=gcn_results.test_metrics["micro_f1"],
            epochs_run=gcn_results.epochs_run,
            training_time=gcn_results.training_time,
        )
    ]

    if gat_results:
        results.append(ModelResult(
            name="GAT",
            precision=gat_results.test_metrics["precision"],
            recall=gat_results.test_metrics["recall"],
            f1=gat_results.test_metrics["f1"],
            micro_f1=gat_results.test_metrics["micro_f1"],
            epochs_run=gat_results.epochs_run,
            training_time=gat_results.training_time,
        ))

    # Write results
    write_results_md(results, rf_metrics=rf_metrics)

    print("\n=== Phase 5 GNN Training Complete ===")
    print(f"  GCN Test F1:    {gcn_results.test_metrics['f1']:.4f}")
    if gat_results:
        print(f"  GAT Test F1:    {gat_results.test_metrics['f1']:.4f}")
    if rf_metrics:
        print(f"  RF  Test F1:    {rf_metrics['f1']:.4f} (Phase 2 baseline)")
    print(f"  Loss curves: docs/gcn_loss_curve.png" +
          (", docs/gat_loss_curve.png" if gat_results else ""))
    print(f"  Benchmark:   docs/results.md")


if __name__ == "__main__":
    main()
