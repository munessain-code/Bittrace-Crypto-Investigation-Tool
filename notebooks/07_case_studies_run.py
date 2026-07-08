#!/usr/bin/env python3
# %% [markdown]
# # Phase 7 — Case Studies & Investigation Stories
#
# Curated investigation stories that walk analysts through real money-layering
# patterns in the Elliptic++ transaction graph.
#
# Reference: KDD paper EASY / AVERAGE / HARD case study framework.

# %% [markdown]
# ## Setup

# %%
import json
import logging
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.data.loaders import get_duckdb_connection
from src.graph.builders import build_tx_graph
from src.graph.export import export_story_subgraph
from src.graph.trace import trace_downstream, trace_upstream
from src.stories import load_all_stories, get_story_by_id

logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")
logger = logging.getLogger(__name__)

# Output directory for artifacts
DOCS = Path(__file__).resolve().parent.parent / "docs"
DOCS.mkdir(exist_ok=True)

# %% [markdown]
# ## Load the full transaction graph
#
# Building the full graph takes ~30s. The graph contains ~200K transactions
# and ~400K edges.

# %%
logger.info("Building full tx graph (this may take a moment)...")
db = get_duckdb_connection()
G = build_tx_graph(db)
db.close()

logger.info(
    "Graph loaded: %d nodes, %d edges",
    G.number_of_nodes(),
    G.number_of_edges(),
)

# Class distribution
classes = {}
for n, attrs in G.nodes(data=True):
    c = attrs.get("class", 3)
    classes[c] = classes.get(c, 0) + 1
logger.info("Class distribution: %s", classes)

# %% [markdown]
# ## Load investigation stories

# %%
stories = load_all_stories()
logger.info("Loaded %d stories", len(stories))

for s in stories:
    logger.info(
        "  [%s] %s — seed %d, %d steps",
        s.difficulty.value,
        s.title,
        s.seed_node_id,
        len(s.steps),
    )

# %% [markdown]
# ## Run each story — trace, verify, visualize

# %%
CLASS_COLORS = {1: "#ef4444", 2: "#22c55e", 3: "#6b7280"}
CLASS_LABELS = {1: "illicit", 2: "licit", 3: "unknown"}

def trace_for_story(story, G):
    """Run the appropriate trace based on the story's first step direction."""
    direction = story.steps[0].trace_direction if story.steps else "downstream"
    seed = story.seed_node_id

    if direction == "upstream":
        return trace_upstream(G, seed, max_hops=3)
    else:
        return trace_downstream(G, seed, max_hops=3)


def plot_story_graph(story, trace_result, G, out_path):
    """Generate a visualization for a story's traced subgraph."""
    nodes = trace_result.get("nodes", [])
    edges = trace_result.get("edges", [])
    hops = trace_result.get("hops", {})

    # Build subgraph
    SG = nx.DiGraph()
    SG.add_nodes_from(nodes)
    SG.add_edges_from(edges)

    # Node colors
    colors = []
    for n in nodes:
        cls = G.nodes[n].get("class", 3)
        colors.append(CLASS_COLORS.get(cls, CLASS_COLORS[3]))

    # Highlight nodes from all steps
    highlight = set()
    for step in story.steps:
        highlight.update(step.highlight_nodes)
    highlight_sizes = [800 if n in highlight else 50 for n in nodes]

    # Layout
    pos = nx.spring_layout(SG, k=0.5, iterations=50, seed=42)

    fig, ax = plt.subplots(1, 1, figsize=(14, 10))

    nx.draw_networkx_nodes(
        SG, pos,
        nodelist=list(SG.nodes()),
        node_color=colors,
        node_size=highlight_sizes,
        alpha=0.85,
        ax=ax,
    )

    nx.draw_networkx_edges(
        SG, pos,
        edgelist=list(SG.edges()),
        alpha=0.3,
        arrowstyle="->",
        arrowsize=8,
        ax=ax,
    )

    # Labels for highlighted nodes
    labels = {}
    for n in highlight:
        if n in SG:
            cls = G.nodes[n].get("class", 3)
            labels[n] = f"{n}\n({CLASS_LABELS.get(cls, '?')})"
    nx.draw_networkx_labels(SG, pos, labels, font_size=6, ax=ax)

    # Legend
    from matplotlib.patches import Patch
    legend_elements = [
        Patch(facecolor=CLASS_COLORS[1], label="illicit"),
        Patch(facecolor=CLASS_COLORS[2], label="licit"),
        Patch(facecolor=CLASS_COLORS[3], label="unknown"),
    ]
    ax.legend(handles=legend_elements, loc="upper left", fontsize=9)

    ax.set_title(
        f"{story.title}\n"
        f"Difficulty: {story.difficulty.value} | "
        f"Pattern: {story.pattern} | "
        f"Nodes: {len(nodes)} | Edges: {len(edges)}",
        fontsize=12,
    )
    ax.axis("off")
    plt.tight_layout()
    plt.savefig(str(out_path), dpi=150, bbox_inches="tight")
    plt.close(fig)
    return str(out_path)


# %% [markdown]
# ### Story 1: The Peel Chain (EASY)

# %%
story_peel = get_story_by_id("peel-chain")
logger.info("=== %s ===", story_peel.title)
logger.info("Narrative: %s", story_peel.narrative[:120] + "...")

# Trace
trace_peel = trace_for_story(story_peel, G)
trace_nodes = trace_peel.get("nodes", [])
trace_edges = trace_peel.get("edges", [])
logger.info("Traced: %d nodes, %d edges", len(trace_nodes), len(trace_edges))

# Verify highlight nodes exist in trace
highlight = story_peel.all_highlight_nodes()
found = [n for n in highlight if n in trace_nodes]
logger.info(
    "Highlight verification: %d/%d nodes found in trace",
    len(found), len(highlight),
)

# Also verify the seed is illicit
seed_class = G.nodes[story_peel.seed_node_id].get("class", 3)
logger.info("Seed node %d class: %s", story_peel.seed_node_id, CLASS_LABELS.get(seed_class, "?"))

# Export subgraph JSON
story_json_peel = export_story_subgraph(story_peel, G, trace_peel)
json_path_peel = DOCS / f"story_{story_peel.id}_subgraph.json"
with open(json_path_peel, "w") as f:
    json.dump(story_json_peel, f, default=str)
logger.info("Exported subgraph JSON: %s", json_path_peel)

# Plot
img_path_peel = DOCS / f"story_{story_peel.id}_graph.png"
plot_story_graph(story_peel, trace_peel, G, img_path_peel)
logger.info("Saved graph visualization: %s", img_path_peel)

# %% [markdown]
# ### Story 2: Fan-Out Split (AVERAGE)

# %%
story_fanout = get_story_by_id("fan-out-split")
logger.info("=== %s ===", story_fanout.title)
logger.info("Narrative: %s", story_fanout.narrative[:120] + "...")

trace_fanout = trace_for_story(story_fanout, G)
trace_nodes = trace_fanout.get("nodes", [])
trace_edges = trace_fanout.get("edges", [])
logger.info("Traced: %d nodes, %d edges", len(trace_nodes), len(trace_edges))

highlight = story_fanout.all_highlight_nodes()
found = [n for n in highlight if n in trace_nodes]
logger.info(
    "Highlight verification: %d/%d nodes found in trace",
    len(found), len(highlight),
)

seed_class = G.nodes[story_fanout.seed_node_id].get("class", 3)
logger.info("Seed node %d class: %s", story_fanout.seed_node_id, CLASS_LABELS.get(seed_class, "?"))

# Export
story_json_fanout = export_story_subgraph(story_fanout, G, trace_fanout)
json_path_fanout = DOCS / f"story_{story_fanout.id}_subgraph.json"
with open(json_path_fanout, "w") as f:
    json.dump(story_json_fanout, f, default=str)
logger.info("Exported subgraph JSON: %s", json_path_fanout)

# Plot
img_path_fanout = DOCS / f"story_{story_fanout.id}_graph.png"
plot_story_graph(story_fanout, trace_fanout, G, img_path_fanout)
logger.info("Saved graph visualization: %s", img_path_fanout)

# %% [markdown]
# ### Story 3: The Consolidation (HARD)

# %%
story_consolidation = get_story_by_id("consolidation")
logger.info("=== %s ===", story_consolidation.title)
logger.info("Narrative: %s", story_consolidation.narrative[:120] + "...")

trace_consolidation = trace_for_story(story_consolidation, G)
trace_nodes = trace_consolidation.get("nodes", [])
trace_edges = trace_consolidation.get("edges", [])
logger.info("Traced: %d nodes, %d edges", len(trace_nodes), len(trace_edges))

highlight = story_consolidation.all_highlight_nodes()
found = [n for n in highlight if n in trace_nodes]
logger.info(
    "Highlight verification: %d/%d nodes found in trace",
    len(found), len(highlight),
)

seed_class = G.nodes[story_consolidation.seed_node_id].get("class", 3)
logger.info("Seed node %d class: %s", story_consolidation.seed_node_id, CLASS_LABELS.get(seed_class, "?"))

# Export
story_json_consolidation = export_story_subgraph(story_consolidation, G, trace_consolidation)
json_path_consolidation = DOCS / f"story_{story_consolidation.id}_subgraph.json"
with open(json_path_consolidation, "w") as f:
    json.dump(story_json_consolidation, f, default=str)
logger.info("Exported subgraph JSON: %s", json_path_consolidation)

# Plot
img_path_consolidation = DOCS / f"story_{story_consolidation.id}_graph.png"
plot_story_graph(story_consolidation, trace_consolidation, G, img_path_consolidation)
logger.info("Saved graph visualization: %s", img_path_consolidation)

# %% [markdown]
# ## Summary

# %%
print("=" * 70)
print("PHASE 7 — CASE STUDIES SUMMARY")
print("=" * 70)

for story in [story_peel, story_fanout, story_consolidation]:
    trace = trace_for_story(story, G)
    t_nodes = len(trace.get("nodes", []))
    t_edges = len(trace.get("edges", []))
    hl = story.all_highlight_nodes()
    hl_found = sum(1 for n in hl if n in trace.get("nodes", []))

    print(f"\n  [{story.difficulty.value}] {story.title}")
    print(f"    Seed node:     {story.seed_node_id}")
    print(f"    Pattern:       {story.pattern}")
    print(f"    Traced:        {t_nodes} nodes, {t_edges} edges")
    print(f"    Highlights:    {hl_found}/{len(hl)} found in trace")
    print(f"    JSON export:   docs/story_{story.id}_subgraph.json")
    print(f"    Visualization: docs/story_{story.id}_graph.png")

print("\n" + "=" * 70)
print("All stories completed successfully.")
print("=" * 70)
