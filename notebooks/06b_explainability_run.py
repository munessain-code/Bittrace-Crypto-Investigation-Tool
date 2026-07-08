#!/usr/bin/env python3
"""Phase 6 — Explainability notebook (executable Python script).

Covers:
  1. SHAP summary plot for top transaction features
  2. SHAP summary plot for top actor features
  3. Explain 3 illicit nodes with k-hop subgraph visualization
  4. Save all outputs to docs/
  5. Print summary table

Run:
    cd /home/eduardo/Documents/bittrace
    python notebooks/06b_explainability_run.py [--sample N]
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

# Ensure project root is on path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.loaders import DATA_DIR
from src.explain.shap_explainer import compute_shap_transactions, compute_shap_actors
from src.explain.subgraph_explainer import extract_k_hop_subgraph
from src.explain.node_inspector import get_node_explanation
from src.explain.importance import plot_top_features, get_feature_importance
from src.graph.builders import build_tx_graph
from src.graph.export import subgraph_to_json_file
from src.models.baseline import train_rf_transactions

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s: %(message)s")
logger = logging.getLogger(__name__)
DOCS = PROJECT_ROOT / "docs"
DOCS.mkdir(exist_ok=True)


def main():
    parser = argparse.ArgumentParser(description="Phase 6: Explainability")
    parser.add_argument("--sample", type=int, default=500, help="SHAP sample size")
    parser.add_argument("--top-n", type=int, default=10, help="Top features to show")
    args = parser.parse_args()

    print("=" * 60)
    print("Phase 6 — SHAP + k-hop Subgraph Explainability")
    print("=" * 60)

    # ── 1. Train RF model ──────────────────────────────────────────
    print("\n--- Step 1: Training RF Transactions model ---")
    rf = train_rf_transactions(n_estimators=50, random_state=42)
    print(f"  F1: {rf.f1:.3f}, Recall: {rf.recall:.3f}, Precision: {rf.precision:.3f}")

    # ── 2. SHAP for Transactions ───────────────────────────────────
    print("\n--- Step 2: SHAP — Transactions ---")
    tx_shap = compute_shap_transactions(
        n_estimators=50, sample_size=args.sample, top_n=args.top_n, save_plots=True,
    )
    print("  Top SHAP features (transactions):")
    for rank, (name, shap_val) in enumerate(tx_shap.top_features[:5], 1):
        print(f"    {rank}. {name}: {shap_val:.4f}")
    if tx_shap.summary_plot_path:
        print(f"  Summary plot: {tx_shap.summary_plot_path}")

    # ── 3. SHAP for Actors ─────────────────────────────────────────
    print("\n--- Step 3: SHAP — Actors ---")
    actor_shap = compute_shap_actors(
        n_estimators=50, sample_size=args.sample, top_n=args.top_n, save_plots=True,
    )
    print("  Top SHAP features (actors):")
    for rank, (name, shap_val) in enumerate(actor_shap.top_features[:5], 1):
        print(f"    {rank}. {name}: {shap_val:.4f}")
    if actor_shap.summary_plot_path:
        print(f"  Summary plot: {actor_shap.summary_plot_path}")

    # ── 4. Feature importance plot ─────────────────────────────────
    print("\n--- Step 4: RF Feature Importance ---")
    imp_df = get_feature_importance(rf.model, rf.feature_names)
    plot_path = plot_top_features(
        imp_df,
        top_n=20,
        title="RF Transactions — Top Feature Importance",
        output_path=str(DOCS / "feature_importance_shap.png"),
    )
    print(f"  Feature importance plot: {plot_path}")

    # ── 5. Build tx graph & explain 3 illicit nodes ───────────────
    print("\n--- Step 5: k-hop Subgraph — 3 illicit nodes ---")
    G = build_tx_graph()

    # Find illicit nodes
    illicit_nodes = [n for n, d in G.nodes(data=True) if d.get("class") == 1]
    sample_illicit = illicit_nodes[:3]
    print(f"  Total illicit nodes in graph: {len(illicit_nodes)}")
    print(f"  Explaining: {sample_illicit}")

    explanations = []
    for tx_id in sample_illicit:
        print(f"\n  >>> Explaining transaction {tx_id}...")
        exp = get_node_explanation(G, rf, node_id=tx_id, k=2, top_n=5)
        explanations.append(exp)

        print(f"    Class: {exp.class_label}")
        print(f"    Timestep: {exp.timestep}")
        print(f"    Risk score: {exp.risk_score}")
        print(f"    Predicted: {exp.predicted_class}")
        print(f"    Subgraph: {exp.subgraph_node_count} nodes, {exp.subgraph_edge_count} edges")

        if exp.shap_top5:
            print("    Top SHAP features:")
            for i, feat in enumerate(exp.shap_top5[:3], 1):
                direction = "↑" if feat["shap"] > 0 else "↓"
                print(f"      {i}. {feat['feature']}: SHAP={feat['shap']:.4f} {direction}")

        # Save subgraph JSON
        subgraph = extract_k_hop_subgraph(G, tx_id, k=2)
        sg_path = DOCS / f"subgraph_tx_{tx_id}_2hop.json"
        subgraph_to_json_file(subgraph["cytoscape"], str(sg_path))
        print(f"    Subgraph JSON: {sg_path}")

        # Save subgraph visualization
        _save_subgraph_viz(G, tx_id, k=2)

    # ── 6. Summary table ───────────────────────────────────────────
    print("\n" + "=" * 60)
    print("PHASE 6 SUMMARY")
    print("=" * 60)
    print(f"\nSHAP Plots saved:")
    print(f"  Transactions: {tx_shap.summary_plot_path or 'N/A'}")
    print(f"  Actors:       {actor_shap.summary_plot_path or 'N/A'}")
    print(f"\nExplained nodes:")
    for exp in explanations:
        top_feat = exp.shap_top5[0]["feature"] if exp.shap_top5 else "N/A"
        print(f"  Tx {exp.node_id}: class={exp.class_label}, "
              f"risk={exp.risk_score}, "
              f"top_feature={top_feat}, "
              f"subgraph={exp.subgraph_node_count}n/{exp.subgraph_edge_count}e")


def _save_subgraph_viz(G: nx.DiGraph, seed: int, k: int = 2):
    """Save a simple subgraph visualization as PNG."""
    try:
        subgraph = extract_k_hop_subgraph(G, seed, k=k)
        nodes = subgraph["nodes"]
        edges = subgraph["edges"]

        if not nodes:
            return

        H = G.subgraph(nodes)
        from src.graph.export import CLASS_COLORS

        node_colors = [
            CLASS_COLORS.get(G.nodes.get(n, {}).get("class", 3), "#6b7280")
            for n in nodes
        ]

        fig, ax = plt.subplots(figsize=(10, 8))
        pos = nx.spring_layout(H, k=0.5, iterations=50, seed=42)
        nx.draw_networkx(
            H, pos, ax=ax,
            node_color=node_colors,
            node_size=[20 if n == seed else 8 for n in nodes],
            edge_color="#999",
            width=0.5,
            arrows=True,
            arrowsize=8,
            with_labels=False,
        )

        # Highlight seed node
        if seed in pos:
            sx, sy = pos[seed]
            ax.plot(sx, sy, "y^", markersize=15, zorder=10)
            ax.text(sx, sy + 0.05, f"seed={seed}", fontsize=8,
                    ha="center", color="gold", fontweight="bold")

        ax.set_title(f"k={k} Subgraph — Tx {seed}", fontsize=12)
        ax.axis("off")
        fig.tight_layout()

        path = DOCS / f"subgraph_viz_tx_{seed}_{k}hop.png"
        fig.savefig(path, dpi=150, bbox_inches="tight")
        plt.close(fig)
        logger.info("Saved subgraph viz: %s", path)
    except Exception as e:
        logger.warning("Subgraph viz failed for tx %d: %s", seed, e)


if __name__ == "__main__":
    main()
