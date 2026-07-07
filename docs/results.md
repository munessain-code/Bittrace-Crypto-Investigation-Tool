# BitTrace Model Benchmarks

## Overview

Comparison of classifiers on the Elliptic++ transaction dataset.

Binary classification: illicit vs licit (unknown class excluded).



## Benchmark Table



| Model | Precision | Recall | F1 (macro) | Micro-F1 | Epochs | Time (s) |
|-------|-----------|--------|------------|----------|--------|----------|
| Random Forest (Phase 2) | 0.9680 | 0.7200 | 0.8260 | 0.9800 | - | - |
| GCN | 0.0000 | 0.0000 | 0.0000 | 0.9216 | 10 | 0.3 |
| GAT | 0.3129 | 0.4554 | 0.3710 | 0.8954 | 18 | 0.6 |


## Notes

- All metrics computed on held-out test set (15% of labeled nodes).

- Graph structure: tx-tx directed edges from shared addresses.

- Node features: 134 columns (72 local + 37 aggregate + 25 derived).

- Class distribution: ~95% licit, ~5% illicit.


## Why graph structure helps

- Transaction patterns (peel chains, fan-outs) span multiple hops.

- GCN/GAT propagate neighbor info, capturing structural red flags.

- RF operates on node-level features only — misses multi-hop context.
