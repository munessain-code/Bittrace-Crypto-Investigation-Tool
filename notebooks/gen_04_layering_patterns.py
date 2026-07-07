#!/usr/bin/env python3
"""Generate notebooks/04_layering_patterns.ipynb"""
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

code = lambda src: NB["cells"].append({
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
        "## Layering Pattern Detection",
        "",
        "Detects common money-layering patterns used by bad actors:",
        "- **Peel chains**: Linear sequences of transactions forwarding value",
        "- **Fan-in**: Multiple inputs consolidated into one output (mixing)",
        "- **Fan-out**: Single input split across many outputs (distribution)",
        "- **Path lengths**: How deep transactions propagate through the network",
        "",
        "```python",
        "# Verify commands",
        "python -c \"from src.graph.patterns import summarize_layering_patterns; from src.graph.builders import build_tx_graph_sample; G = build_tx_graph_sample(fraction=0.01); print(summarize_layering_patterns(G))\"",
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
import pandas as pd

from src.graph.builders import build_tx_graph_sample
from src.graph.patterns import (
    detect_peel_chains, get_longest_peel_chains,
    detect_fan_out, detect_fan_in,
    get_fan_illicit_counts, path_length_distribution,
    summarize_layering_patterns,
)

plt.rcParams.update({'figure.dpi': 150, 'savefig.dpi': 150})
print("Imports OK")""")

# --- Build graph ---
code("""# Use a larger sample for pattern detection (5% of 234K edges ~ 12K edges)
G = build_tx_graph_sample(fraction=0.05)
print(f"Sampled tx graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")""")

# --- Overall summary ---
code("""summary = summarize_layering_patterns(G, min_length=3, min_degree=3)
print("\\n=== LAYERING PATTERN SUMMARY ===")
print(f"  Peel chains found:       {summary['peel_chains']}")
print(f"  Longest peel chain:      {summary['longest_peel_chain']} nodes")
print(f"  Fan-out nodes (≥3):      {summary['fan_out_nodes']}")
print(f"  Fan-in nodes (≥3):       {summary['fan_in_nodes']}")
print(f"  Avg path length:         {summary['avg_path_length']:.2f}")
print(f"  Max path length:         {summary['max_path_length']:.1f}")

fi = summary['fan_illicit']
print(f"\\n--- Fan Illicit Ratios ---")
print(f"  Fan-out nodes:   {fi['fan_out_illicit']}/{fi['fan_out_total']} = {fi['illicit_ratio_out']:.1%}")
print(f"  Fan-in nodes:    {fi['fan_in_illicit']}/{fi['fan_in_total']} = {fi['illicit_ratio_in']:.1%}")""")

# --- Top peel chains ---
code("""top_chains = get_longest_peel_chains(G, top_k=10, min_length=3)
print(f"Found {len(top_chains)} top peel chains:")
for i, chain in enumerate(top_chains):
    classes = [G.nodes[n].get('class', '?') for n in chain[:5]]
    labels = {1: 'ILICIT', 2: 'licit', 3: 'unknown'}
    class_str = ', '.join(labels.get(c, '?') for c in classes)
    print(f"  Chain {i+1}: {len(chain)} nodes | first 5 classes: {class_str}")""")

# --- Peel chain length distribution ---
code("""# Histogram of all peel chain lengths
all_chains = detect_peel_chains(G, min_length=3)
chain_lengths = [len(c) for c in all_chains]

fig, axes = plt.subplots(1, 2, figsize=(12, 5))

# Distribution of chain lengths
axes[0].hist(chain_lengths, bins=min(50, max(10, max(chain_lengths))), color='crimson', edgecolor='white', alpha=0.8)
axes[0].set_xlabel('Chain Length (nodes)', fontsize=12)
axes[0].set_ylabel('Count', fontsize=12)
axes[0].set_title(f'Peel Chain Length Distribution (n={len(all_chains)})', fontsize=13)
axes[0].axvline(np.median(chain_lengths), color='white', linestyle='--', linewidth=2,
                label=f'Median: {np.median(chain_lengths):.0f}')
axes[0].legend()
axes[0].grid(axis='y', alpha=0.3)

# CDF of chain lengths
chain_lengths_sorted = sorted(chain_lengths)
axes[1].plot(chain_lengths_sorted, np.arange(1, len(chain_lengths_sorted)+1)/len(chain_lengths_sorted),
             color='darkred', linewidth=1.5)
axes[1].set_xlabel('Chain Length (nodes)', fontsize=12)
axes[1].set_ylabel('Cumulative Fraction', fontsize=12)
axes[1].set_title('Peel Chain Length CDF', fontsize=13)
axes[1].grid(alpha=0.3)

fig.tight_layout()
fig.savefig('../docs/peel_chain_distribution.png', bbox_inches='tight')
plt.close(fig)
print("Peel chain distribution saved")""")

# --- Fan-out / Fan-in counts ---
code("""# Count fan nodes by threshold
thresholds = [3, 5, 10, 20, 50]
fan_out_counts = []
fan_in_counts = []
fan_out_illicit = []
fan_in_illicit = []

for t in thresholds:
    fo = detect_fan_out(G, min_degree=t)
    fi = detect_fan_in(G, min_degree=t)
    fan_out_counts.append(len(fo))
    fan_in_counts.append(len(fi))
    fo_il = sum(1 for n, *_ in fo if G.nodes[n].get('class') == 1)
    fi_il = sum(1 for n, *_ in fi if G.nodes[n].get('class') == 1)
    fan_out_illicit.append(fo_il)
    fan_in_illicit.append(fi_il)

df = pd.DataFrame({
    'Threshold': thresholds,
    'Fan-out Total': fan_out_counts,
    'Fan-out Illicit': fan_out_illicit,
    'Fan-in Total': fan_in_counts,
    'Fan-in Illicit': fan_in_illicit,
})
df['Fan-out Illicit %'] = (df['Fan-out Illicit'] / df['Fan-out Total'] * 100).round(1)
df['Fan-in Illicit %'] = (df['Fan-in Illicit'] / df['Fan-in Total'] * 100).round(1)

print("\\n=== FAN-NODE ANALYSIS BY THRESHOLD ===")
print(df.to_string(index=False))""")

# --- Fan-node plot ---
code("""fig, ax = plt.subplots(figsize=(8, 5))
x = np.arange(len(thresholds))
w = 0.35

bars1 = ax.bar(x - w/2, fan_out_counts, w, label='Fan-out Total', color='steelblue')
bars2 = ax.bar(x + w/2, fan_in_counts, w, label='Fan-in Total', color='coral')

ax.set_xlabel('Minimum Degree Threshold', fontsize=12)
ax.set_ylabel('Number of Fan Nodes', fontsize=12)
ax.set_title('Fan-in / Fan-out Node Counts by Threshold', fontsize=13)
ax.set_xticks(x)
ax.set_xticklabels(thresholds)
ax.legend()
ax.grid(axis='y', alpha=0.3)
fig.tight_layout()
fig.savefig('../docs/fan_node_counts.png', bbox_inches='tight')
plt.close(fig)
print("Fan node counts chart saved")""")

# --- Path length distribution ---
code("""pl = path_length_distribution(G, max_samples=500, max_depth=50)
lengths = pl['path_lengths']
print(f"Computed {len(lengths)} shortest paths")
if lengths:
    print(f"  Min: {min(lengths)}, Max: {max(lengths)}, Mean: {np.mean(lengths):.2f}, Median: {np.median(lengths):.1f}")

fig, ax = plt.subplots(figsize=(8, 5))
if lengths:
    bins = np.logspace(0, np.ceil(np.log10(max(lengths))), 30).astype(int)
    ax.hist(lengths, bins=bins, color='teal', edgecolor='white', alpha=0.8)
    ax.set_xscale('log')
    ax.set_yscale('log')
ax.set_xlabel('Shortest Path Length', fontsize=12)
ax.set_ylabel('Count (log scale)', fontsize=12)
ax.set_title('Path Length Distribution (BFS from Source Nodes)', fontsize=13)
ax.grid(axis='both', alpha=0.3, which='both')
fig.tight_layout()
fig.savefig('../docs/path_length_distribution.png', bbox_inches='tight')
plt.close(fig)
print("Path length distribution saved")""")

# --- How bad actors layer ---
code("""md_text = \"\"\"## How Bad Actors Layer Transactions

The patterns detected above correspond to known money-layering techniques:

### Peel Chains
Criminal wallets send value to a new address, keeping change (the "peel"), then
forward the remaining value to yet another address. This creates a linear chain
of transactions that obscures the original source. **Longer peel chains = more
obfuscation effort.**

### Fan-In (Consolidation)
Multiple inputs consolidated into a single output is a hallmark of:
- **Mixers** — aggregating coins from many sources before redistributing
- **Darknet markets** — collecting payments from many buyers
- **Illicit service providers** — consolidating before cashing out

### Fan-Out (Distribution)
A single address distributing to many outputs suggests:
- **Payout distribution** — sending proceeds to multiple affiliated wallets
- **Mixer output** — redistributing mixed coins to recipients
- **Pyramid/Ponzi schemes** — paying out to many "investors"

### Temporal Spread
Layering also involves time delays between transactions to complicate analysis.
The timestep attribute tracks when transactions occurred within the dataset.

### Why These Patterns Matter
- Legitimate transactions tend to have short paths and simple fan structures
- Criminal activity shows **longer paths, deeper peel chains, and higher fan counts**
- These structural features become node/edge features for GNN models (Phase 4+)
\"\"\"

print(md_text)""")

# --- Summary ---
code("""print("\\n" + "="*50)
print("LAYERING PATTERN ANALYSIS COMPLETE")
print("="*50)
print(f"Graph sample: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")
print(f"Peel chains: {summary['peel_chains']} (longest: {summary['longest_peel_chain']} nodes)")
print(f"Fan-out nodes (≥3): {summary['fan_out_nodes']}")
print(f"Fan-in nodes (≥3): {summary['fan_in_nodes']}")
print(f"Avg path length: {summary['avg_path_length']:.2f}")
print()
print("Charts saved to docs/:")
print("  - peel_chain_distribution.png")
print("  - fan_node_counts.png")
print("  - path_length_distribution.png")""")

with open("04_layering_patterns.ipynb", "w") as f:
    json.dump(NB, f, indent=2)
print(f"Generated 04_layering_patterns.ipynb with {len(NB['cells'])} cells")
