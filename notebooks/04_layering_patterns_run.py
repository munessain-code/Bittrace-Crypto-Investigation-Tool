#!/usr/bin/env python3
"""Layering pattern detection — runs top-to-bottom, saves charts to docs/."""
import sys
sys.path.insert(0, '..')

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import networkx as nx

from src.graph.builders import build_tx_graph_sample
from src.graph.patterns import (
    detect_peel_chains, detect_fan_out, detect_fan_in,
    get_fan_illicit_counts, path_length_distribution,
    summarize_layering_patterns,
)

plt.rcParams.update({'figure.dpi': 150, 'savefig.dpi': 150})

# --- Build sampled graph ---
G = build_tx_graph_sample(fraction=0.01)
print(f"Sampled tx graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges")

# --- Peel chains ---
peel = detect_peel_chains(G, min_length=3)
print(f"\n--- Peel Chains (length >= 3) ---")
print(f"  Found: {len(peel)} peel chains")
if peel:
    lengths = [len(p) for p in peel]
    print(f"  Longest: {max(lengths)} hops")
    print(f"  Average length: {np.mean(lengths):.1f}")
    print(f"  Top 5 longest: {sorted(lengths, reverse=True)[:5]}")
else:
    print("  (none found in this sample)")

# --- Fan-out nodes ---
fan_out = detect_fan_out(G, min_degree=3)
print(f"\n--- Fan-Out (out-degree >= 3) ---")
print(f"  Found: {len(fan_out)} fan-out nodes")
if fan_out:
    fan_out_degrees = [f[1] for f in fan_out]
    print(f"  Max fan-out: {max(fan_out_degrees)}")
    print(f"  Average fan-out: {np.mean(fan_out_degrees):.1f}")

# --- Fan-in nodes ---
fan_in = detect_fan_in(G, min_degree=3)
print(f"\n--- Fan-In (in-degree >= 3) ---")
print(f"  Found: {len(fan_in)} fan-in nodes")
if fan_in:
    fan_in_degrees = [f[1] for f in fan_in]
    print(f"  Max fan-in: {max(fan_in_degrees)}")
    print(f"  Average fan-in: {np.mean(fan_in_degrees):.1f}")

# --- Illicit involvement ---
illicit = get_fan_illicit_counts(G, min_degree=3)
print(f"\n--- Illicit Involvement in Fan Patterns ---")
print(f"  Fan-out: {illicit['fan_out_illicit']}/{illicit['fan_out_total']} ({illicit['illicit_ratio_out']:.1%}) are illicit")
print(f"  Fan-in:  {illicit['fan_in_illicit']}/{illicit['fan_in_total']} ({illicit['illicit_ratio_in']:.1%}) are illicit")

# --- Path length distribution ---
path_dist = path_length_distribution(G, max_samples=500)
paths = path_dist['path_lengths']
print(f"\n--- Path Length Distribution ---")
if paths:
    print(f"  Samples: {len(paths)} shortest paths computed")
    print(f"  Mean path length: {np.mean(paths):.2f}")
    print(f"  Median path length: {np.median(paths):.1f}")
    print(f"  Max path length: {max(paths)}")
    print(f"  Paths <= 3 hops: {sum(1 for p in paths if p <= 3)} ({sum(1 for p in paths if p <= 3)/len(paths):.1%})")
    print(f"  Paths > 3 hops: {sum(1 for p in paths if p > 3)} ({sum(1 for p in paths if p > 3)/len(paths):.1%})")

# --- Summary ---
summary = summarize_layering_patterns(G)
print("\n=== LAYERING PATTERN SUMMARY ===")
for k, v in summary.items():
    print(f"  {k}: {v}")

# --- Peel chain length histogram ---
if peel:
    lengths = np.array([len(p) for p in peel])
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(lengths, range(1, len(lengths)+1), color='steelblue', edgecolor='none')
    ax.set_xlabel('Peel Chain Length', fontsize=12)
    ax.set_ylabel('Number of Chains', fontsize=12)
    ax.set_title(f'Peel Chain Length Distribution ({len(peel)} chains found)', fontsize=14)
    ax.grid(axis='y', alpha=0.3)
    fig.tight_layout()
    fig.savefig('../docs/peel_chain_lengths.png', bbox_inches='tight')
    plt.close(fig)
    print("\nPeel chain chart saved")

# --- Fan degree distribution ---
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
if fan_out:
    fan_out_degrees = np.array([f[1] for f in fan_out])
    ax1.hist(fan_out_degrees, bins=range(2, max(fan_out_degrees)+3), color='coral', edgecolor='none')
    ax1.set_xlabel('Out-Degree', fontsize=12)
    ax1.set_ylabel('Count', fontsize=12)
    ax1.set_title(f'Fan-Out Degree Distribution ({len(fan_out)} nodes)', fontsize=12)
if fan_in:
    fan_in_degrees = np.array([f[1] for f in fan_in])
    ax2.hist(fan_in_degrees, bins=range(2, max(fan_in_degrees)+3), color='teal', edgecolor='none')
    ax2.set_xlabel('In-Degree', fontsize=12)
    ax2.set_ylabel('Count', fontsize=12)
    ax2.set_title(f'Fan-In Degree Distribution ({len(fan_in)} nodes)', fontsize=12)
fig.tight_layout()
fig.savefig('../docs/fan_degree_distribution.png', bbox_inches='tight')
plt.close(fig)
print("Fan degree charts saved")

# --- Path length histogram ---
if paths:
    fig, ax = plt.subplots(figsize=(8, 5))
    # Compute histogram manually for clean bins
    unique_lengths = sorted(set(paths))
    counts = [paths.count(l) for l in unique_lengths]
    ax.bar([str(l) for l in unique_lengths], counts, color='purple', edgecolor='none', alpha=0.8)
    ax.set_xlabel('Shortest Path Length (hops)', fontsize=12)
    ax.set_ylabel('Count', fontsize=12)
    ax.set_title(f'Path Length Distribution ({len(paths)} samples)', fontsize=14)
    ax.grid(axis='y', alpha=0.3)
    fig.tight_layout()
    fig.savefig('../docs/path_length_distribution.png', bbox_inches='tight')
    plt.close(fig)
    print("Path length chart saved")

# --- Fan network visualization ---
if fan_out:
    # Pick the top fan-out node and its neighbors for a small viz
    top_fan = max(fan_out, key=lambda x: x[1])
    fan_id, fan_deg, neighbors = top_fan
    fan_sub = G.subgraph([fan_id] + neighbors[:10])

    class_colors = {1: 'red', 2: 'green', 3: 'gray'}
    node_colors = []
    for n in fan_sub.nodes():
        cls = G.nodes[n].get('class', 3)
        if n == fan_id:
            node_colors.append('orange')
        else:
            node_colors.append(class_colors.get(cls, 'gray'))

    fig, ax = plt.subplots(figsize=(10, 6))
    pos = nx.spring_layout(fan_sub, seed=42, k=0.5, iterations=50)
    node_sizes = [80 if n == fan_id else 20 for n in fan_sub.nodes()]
    nx.draw_networkx_nodes(fan_sub, pos, node_color=node_colors, node_size=node_sizes, ax=ax)
    nx.draw_networkx_edges(fan_sub, pos, alpha=0.4, edge_color='gray', ax=ax)
    ax.set_title(f'Fan-Out Node (out-degree={fan_deg}, class={class_colors.get(G.nodes[fan_id].get("class", 3), "?")})', fontsize=13)
    ax.axis('off')
    fig.tight_layout()
    fig.savefig('../docs/fan_network_visualization.png', bbox_inches='tight')
    plt.close(fig)
    print("Fan network visualization saved")

print("\nCharts saved to docs/:")
print("  - peel_chain_lengths.png")
print("  - fan_degree_distribution.png")
print("  - path_length_distribution.png")
print("  - fan_network_visualization.png")
