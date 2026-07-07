#!/usr/bin/env python3
"""Generate notebooks/03_graph_topology.ipynb"""
import json

NB = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "cells": [],
    "metadata": {
        "kernelspec": {
            "display_name": "Python 3",
            "language": "python",
            "name": "python3",
        },
        "language_info": {"name": "python", "version": "3.11.0"},
    },
}

md = NB["cells"].append

def code(src):
    NB["cells"].append({
        "cell_type": "code",
        "execution_count": None,
        "id": f"code-{len(NB['cells'])}",
        "metadata": {},
        "outputs": [],
        "source": src.rstrip("\n"),  # store as single string with real newlines
    })

# --- Title (markdown cell) ---
NB["cells"].append({
    "cell_type": "markdown",
    "id": "md-0",
    "metadata": {},
    "source": [
        "## Graph Topology Analysis",
        "",
        "Exploratory analysis of the Elliptic++ transaction graph using NetworkX.",
        "Builds a sampled tx-to-tx graph and reports basic structural statistics.",
        "",
        "```python",
        "# Verify commands",
        "python -c \"from src.graph.builders import build_tx_graph_sample; G = build_tx_graph_sample(fraction=0.01); print(f'{G.number_of_nodes()} nodes, {G.number_of_edges()} edges')\"",
        "```",
    ],
})

# --- Imports ---
code("""import sys
sys.path.insert(0, '..')

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import networkx as nx

from src.graph.builders import build_tx_graph_sample
from src.graph.stats import (
    compute_stats, degree_distribution,
    connected_components_summary, density_summary,
)

plt.rcParams.update({'figure.dpi': 150, 'savefig.dpi': 150})
print("Imports OK")""")

# --- Build sampled graph ---
code("""# Build a 1% sample of the tx graph (full graph has 234K edges)
# Using sample to keep RAM manageable during exploration
G = build_tx_graph_sample(fraction=0.01)
print(f"Sampled tx graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")""")

# --- Basic stats ---
code("""stats = compute_stats(G)
print("\\n--- Basic Graph Statistics ---")
for k, v in stats.items():
    print(f"  {k}: {v}")""")

# --- Component summary ---
code("""cc = connected_components_summary(G)
print(f"\\n--- Connected Components ---")
print(f"  Total components: {cc['total']}")
print(f"  Largest component: {cc['top_10'][0]} nodes ({cc['giant_fraction']:.1%} of graph)")
print(f"  Top 5 component sizes: {cc['top_10'][:5]}")""")

# --- Density / clustering ---
code("""dens = density_summary(G)
print(f"\\n--- Density & Clustering ---")
for k, v in dens.items():
    print(f"  {k}: {v:.6f}")""")

# --- Degree distribution plot ---
code("""# In-degree distribution
fig, ax = plt.subplots(figsize=(8, 5))
deg_counts, deg_vals = degree_distribution(G, mode='in')
ax.bar(deg_vals, deg_counts, color='steelblue', edgecolor='none', width=0.8)
ax.set_xlabel('In-Degree', fontsize=12)
ax.set_ylabel('Number of Transactions', fontsize=12)
ax.set_title('In-Degree Distribution (Tx Graph Sample)', fontsize=14)
ax.set_yscale('log')
ax.grid(axis='y', alpha=0.3)
fig.tight_layout()
fig.savefig('../docs/degree_distribution_in.png', bbox_inches='tight')
plt.close(fig)

# Out-degree distribution
fig, ax = plt.subplots(figsize=(8, 5))
deg_counts2, deg_vals2 = degree_distribution(G, mode='out')
ax.bar(deg_vals2, deg_counts2, color='coral', edgecolor='none', width=0.8)
ax.set_xlabel('Out-Degree', fontsize=12)
ax.set_ylabel('Number of Transactions', fontsize=12)
ax.set_title('Out-Degree Distribution (Tx Graph Sample)', fontsize=14)
ax.set_yscale('log')
ax.grid(axis='y', alpha=0.3)
fig.tight_layout()
fig.savefig('../docs/degree_distribution_out.png', bbox_inches='tight')
plt.close(fig)

print("Degree distribution plots saved")""")

# --- Component size distribution ---
code("""fig, ax = plt.subplots(figsize=(8, 5))
sizes = cc['sizes'][:100]  # Top 100 components
ax.bar(range(1, len(sizes)+1), sorted(sizes, reverse=True), color='teal', edgecolor='none')
ax.set_xlabel('Component Rank', fontsize=12)
ax.set_ylabel('Component Size (nodes)', fontsize=12)
ax.set_title('Top 100 Connected Components by Size', fontsize=14)
ax.grid(axis='y', alpha=0.3)
fig.tight_layout()
fig.savefig('../docs/component_sizes.png', bbox_inches='tight')
plt.close(fig)
print("Component size chart saved")""")

# --- Sample subgraph visualization ---
code("""# Visualize a subgraph of the largest connected component
largest_cc = max(nx.weakly_connected_components(G), key=len)
sub_nodes = list(largest_cc)[:100]
sub_G = G.subgraph(sub_nodes).copy()

print(f"Largest CC has {len(largest_cc)} nodes, visualizing first {len(sub_nodes)}")

# Color by class
class_colors = {1: 'red', 2: 'green', 3: 'gray'}
node_colors = []
for n in sub_G.nodes():
    cls = G.nodes[n].get('class', 3)
    node_colors.append(class_colors.get(cls, 'gray'))

fig, ax = plt.subplots(figsize=(12, 12))
pos = nx.spring_layout(sub_G, k=0.3, seed=42, iterations=50)
nx.draw_networkx_nodes(sub_G, pos, node_color=node_colors, node_size=20, ax=ax, alpha=0.8)
nx.draw_networkx_edges(sub_G, pos, alpha=0.15, edge_color='gray', ax=ax)
ax.set_title(f'Tx Graph Subgraph ({len(sub_nodes)} nodes from largest CC)', fontsize=14)
ax.axis('off')
fig.tight_layout()
fig.savefig('../docs/subgraph_visualization.png', bbox_inches='tight')
plt.close(fig)
print("Subgraph visualization saved")""")

# --- Summary table ---
code("""from IPython.display import display, Markdown, HTML
import pandas as pd

summary = {
    'Metric': ['Nodes', 'Edges', 'Density', 'Avg In-Degree', 'Avg Out-Degree',
               'Max In-Degree', 'Max Out-Degree',
               'Components', 'Largest CC', 'Giant CC Fraction'],
    'Value': [
        stats['num_nodes'],
        stats['num_edges'],
        f"{stats['density']:.6f}",
        f"{stats['avg_degree']:.2f}",
        f"{stats['avg_degree']:.2f}",
        stats['max_in_degree'],
        stats['max_out_degree'],
        cc['total'],
        cc['top_10'][0],
        f"{cc['giant_fraction']:.2%}",
    ],
}
df = pd.DataFrame(summary)
print("\\n=== GRAPH TOPOLOGY SUMMARY ===")
print(df.to_string(index=False))
print("\\nCharts saved to docs/:")
print("  - degree_distribution_in.png")
print("  - degree_distribution_out.png")
print("  - component_sizes.png")
print("  - subgraph_visualization.png")""")

with open("03_graph_topology.ipynb", "w") as f:
    json.dump(NB, f, indent=2)
print(f"Generated 03_graph_topology.ipynb with {len(NB['cells'])} cells")
