#!/usr/bin/env python3
"""Visualization prototypes — static previews of exported subgraphs.

Loads precomputed subgraph JSONs, renders static previews with
matplotlib/networkx, computes macro stats (illicit count per timestep),
and documents the JSON schema for Phase 8 frontend.
"""

import sys
import json
import os
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import networkx as nx
import numpy as np
import pandas as pd

# ─── Paths ───
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

DATA_DIR = PROJECT_ROOT / "data"
SUBGRAPHS_DIR = DATA_DIR / "subgraphs"
DOCS_DIR = PROJECT_ROOT / "docs"
DOCS_DIR.mkdir(exist_ok=True)

CLASS_COLORS = {1: "#ef4444", 2: "#22c55e", 3: "#6b7280"}
CLASS_LABELS = {1: "illicit", 2: "licit", 3: "unknown"}


# ─── 1. Load exported JSON subgraphs ───
print("=== Loading subgraphs ===")
subgraphs = {}
for fp in sorted(SUBGRAPHS_DIR.glob("*_case.json")):
    with open(fp) as f:
        data = json.load(f)
    difficulty = fp.stem.replace("_case", "")
    subgraphs[difficulty] = data
    meta = data.get("metadata", {})
    print(f"  {difficulty}: {meta.get('node_count', '?')} nodes, "
          f"{meta.get('edge_count', '?')} edges "
          f"(seed={meta.get('seed_node', '?')})")

if not subgraphs:
    print("No precomputed subgraphs found in data/subgraphs/. "
          "Run: python -m src.viz.precompute")
    sys.exit(1)


# ─── 2. Render static previews with networkx ───
print("\n=== Rendering previews ===")

for difficulty, data in subgraphs.items():
    G_vis = nx.DiGraph()
    nodes = data.get("nodes", [])
    edges = data.get("edges", [])

    for n in nodes:
        d = n["data"]
        G_vis.add_node(d["id"], class_label=d.get("class_label", "unknown"),
                       color=d.get("color", "#6b7280"))

    for e in edges:
        d = e["data"]
        G_vis.add_edge(d["source"], d["target"])

    # Limit to first 100 nodes for readability
    if G_vis.number_of_nodes() > 100:
        top_nodes = list(G_vis.nodes())[:100]
        G_vis = G_vis.subgraph(top_nodes).copy()

    fig, ax = plt.subplots(figsize=(12, 10))
    pos = nx.spring_layout(G_vis, k=0.5, iterations=30, seed=42)
    node_colors = [G_vis.nodes[n]["color"] for n in G_vis.nodes()]

    nx.draw_networkx_nodes(G_vis, pos, node_color=node_colors, node_size=20, ax=ax)
    nx.draw_networkx_edges(G_vis, pos, alpha=0.3, width=0.5, ax=ax)

    meta = data.get("metadata", {})
    ax.set_title(
        f"BitTrace Subgraph: {difficulty.upper()} case\n"
        f"Seed: {meta.get('seed_node', '?')} | "
        f"{G_vis.number_of_nodes()} nodes, {G_vis.number_of_edges()} edges",
        fontsize=11
    )
    ax.axis("off")

    # Legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=CLASS_COLORS[1], label="Illicit"),
        Patch(facecolor=CLASS_COLORS[2], label="Licit"),
        Patch(facecolor=CLASS_COLORS[3], label="Unknown"),
    ]
    ax.legend(handles=legend_elements, loc="upper right", fontsize=9)

    fig.tight_layout()
    out_path = DOCS_DIR / f"subgraph_preview_{difficulty}.png"
    fig.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"  Saved: {out_path}")


# ─── 3. Macro stats: illicit count per timestep ───
print("\n=== Macro stats: illicit count per timestep ===")

from src.data.loaders import get_duckdb_connection

db = get_duckdb_connection()
timestep_df = db.execute("""
    SELECT t."Time step" as timestep, tc.class, COUNT(*) as cnt
    FROM tx_classes tc
    JOIN transactions t ON tc.txId = t.txId
    GROUP BY t."Time step", tc.class
    ORDER BY t."Time step", tc.class
""").fetchdf()

# Build heatmap data
heatmap_pivot = timestep_df.pivot(index="timestep", columns="class", values="cnt").fillna(0)
print(f"  Timesteps: {heatmap_pivot.shape[0]}, Classes: {heatmap_pivot.shape[1]}")
print(f"  Illicit per timestep (first 10):")
if 1 in heatmap_pivot.columns:
    print(heatmap_pivot[1].head(10).to_string())

# Plot heatmap
fig, axes = plt.subplots(1, 2, figsize=(16, 6))

# Heatmap
class_cols = [1, 2, 3]
available_cols = [c for c in class_cols if c in heatmap_pivot.columns]
if available_cols:
    im = axes[0].imshow(
        heatmap_pivot[available_cols].values.T,
        aspect="auto", cmap="YlOrRd"
    )
    axes[0].set_xticks(range(len(available_cols)))
    axes[0].set_xticklabels([CLASS_LABELS.get(c, str(c)) for c in available_cols])
    axes[0].set_yticks(range(heatmap_pivot.shape[0]))
    axes[0].set_yticklabels(heatmap_pivot.index.astype(str).tolist(), fontsize=7)
    axes[0].set_title("Illicit/Licit/Unknown count per timestep")
    axes[0].set_xlabel("Class")
    axes[0].set_ylabel("Timestep")
    plt.colorbar(im, ax=axes[0])

# Cumulative illicit vs licit over time
cumil = heatmap_pivot.get(1, pd.Series(0)).cumsum()
cumli = heatmap_pivot.get(2, pd.Series(0)).cumsum()
cumuk = heatmap_pivot.get(3, pd.Series(0)).cumsum()

axes[1].plot(cumil.index, cumil.values, label="Illicit", color=CLASS_COLORS[1])
axes[1].plot(cumli.index, cumli.values, label="Licit", color=CLASS_COLORS[2])
axes[1].plot(cumuk.index, cumuk.values, label="Unknown", color=CLASS_COLORS[3])
axes[1].set_title("Cumulative transactions per class over timesteps")
axes[1].set_xlabel("Timestep")
axes[1].set_ylabel("Cumulative count")
axes[1].legend()
axes[1].grid(alpha=0.3)

fig.tight_layout()
heatmap_path = DOCS_DIR / "illicit_timeline_heatmap.png"
fig.savefig(heatmap_path, dpi=150)
plt.close(fig)
print(f"  Saved: {heatmap_path}")

# Save heatmap data as CSV
heatmap_pivot.to_csv(DOCS_DIR / "illicit_per_timestep.csv")
print(f"  Saved CSV: {DOCS_DIR / 'illicit_per_timestep.csv'}")

db.close()


# ─── 4. JSON schema documentation ───
print("\n=== JSON schema for Phase 8 frontend ===")

schema_doc = """# BitTrace Graph Explorer — JSON Schema

## Subgraph file (e.g., `easy_case.json`)

```json
{
  "metadata": {
    "difficulty": "easy|average|hard",
    "seed_node": 272145560,
    "seed_class": 1,
    "seed_timestep": 1,
    "depth": 3,
    "budget": 500,
    "node_count": 234,
    "edge_count": 233,
    "description": "..."
  },
  "nodes": [
    {
      "data": {
        "id": "272145560",
        "label": "272145560",
        "class": 1,
        "class_label": "illicit",
        "color": "#ef4444",
        "hop": 0,
        "timestep": 1
      }
    }
  ],
  "edges": [
    {
      "data": {
        "id": "e_272145560_11747137",
        "source": "272145560",
        "target": "11747137"
      }
    }
  ]
}
```

## Cytoscape.js integration

The `nodes` and `edges` arrays are Cytoscape.js-compatible and can be
passed directly to `cy.add()`. The `data` keys map to Cytoscape element
properties:

| Key | Type | Description |
|---|---|---|
| `id` | string | Unique identifier |
| `class` | int | 1=illicit, 2=licit, 3=unknown |
| `class_label` | string | Human-readable label |
| `color` | string | Hex color for visualization |
| `hop` | int | BFS distance from seed (trace only) |
| `timestep` | int | Time bucket (1-20) |

## Phase 8 frontend requirements

1. Load JSON via `fetch()` or pre-bundle
2. Render with Cytoscape.js or D3 force layout
3. Color nodes by `data.color`
4. Filter by class, timestep, hop depth
5. Click node → show metadata panel with class, timestep, hop
6. Animated trace: reveal nodes hop-by-hop
"""

schema_path = SUBGRAPHS_DIR / "SCHEMA.md"
schema_path.write_text(schema_doc)
print(f"  Schema doc: {schema_path}")

print("\n=== Phase 4 visualization prototypes complete ===")
print(f"  Subgraphs: {len(subgraphs)}")
print(f"  Charts: {DOCS_DIR / 'subgraph_preview_easy.png'}, ...")
print(f"  Heatmap: {heatmap_path}")
print(f"  Schema: {schema_path}")
