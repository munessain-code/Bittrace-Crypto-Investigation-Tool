# BitTrace — Methodology

## Overview

BitTrace applies a multi-layer forensic pipeline to the [Elliptic++ dataset](https://github.com/git-disl/EllipticPlusPlus) for Bitcoin fraud detection and explainability. The pipeline progresses from classical ML baselines to graph neural networks, then layers post-hoc interpretability on top.

## Data Pipeline (Phase 1)

### Dataset

Elliptic++ provides four graph views derived from ~200K Bitcoin transactions across 49 timesteps:

| Graph | Nodes | Edges | Use Case |
|-------|-------|-------|----------|
| Tx→Tx (money flow) | 203K | 234K | Temporal GNN, fraud classification |
| Addr→Addr (actor) | 822K | 2.9M | Community detection, illicit actor profiling |
| Addr↔Tx (bipartite) | 1.3M | — | Heterogeneous GNN |

### Class Distribution

The dataset has severe class imbalance:
- **Illicit (1):** 4,545 transactions (2.2%)
- **Licit (2):** 42,019 transactions (20.6%)
- **Unknown (3):** 157,205 transactions (77.2%)

For binary classification, unknown (3) is dropped and labels are remapped: licit→0, illicit→1.

### Storage

Raw CSVs are loaded via **DuckDB** for fast SQL queries without full in-memory pandas DataFrames. Schema defined in `src/data/schema.sql`.

## RF Baseline (Phase 2)

Reproduces the KDD '23 paper methodology:

### Transactions
- **Preprocessing:** MinMaxScaler per feature, drop unknown class, drop NaN
- **Split:** Temporal — train on timesteps < 35, test on ≥ 35
- **Model:** RandomForestClassifier(n_estimators=50, random_state=42, n_jobs=-1)
- **Paper benchmark:** Precision=0.986, Recall=0.727

### Actors
- **Preprocessing:** MinMaxScaler per feature, drop unknown class, drop duplicates
- **Split:** 70/30 with shuffle=False, random_state=15
- **Model:** RandomForestClassifier(n_estimators=50, random_state=42, n_jobs=-1)
- **Paper benchmark:** Precision=0.921, Recall=0.802

### Evaluation Metric Priority

For AML/financial forensics: **recall > precision**. Missing fraud is costlier than false alarms.

## Graph Analytics (Phase 3)

NetworkX-based graph construction and pattern detection:

- **Graph builders:** `src/graph/builders.py` — tx→tx, addr→addr, bipartite graphs
- **Layering patterns:** `src/graph/patterns.py` — peel chains, fan-in, fan-out detection
- **Graph statistics:** degree distributions, connected components, community detection

## Graph Explorer Backend (Phase 4)

API-ready graph operations for the frontend:

- **Tracing:** `src/graph/trace.py` — upstream/downstream BFS with class filters
- **Expansion:** `src/graph/expand.py` — lazy 1-hop neighbor expansion
- **Export:** `src/graph/export.py` — Cytoscape.js-compatible JSON serialization
- **Cases:** `src/graph/cases.py` — precurated EASY/HARD/AVERAGE subgraph extracts

## Graph ML (Phase 5)

### GCN/GAT on Transaction Graph

- **Architecture:** 2-layer GCN and GAT with ReLU activation, binary cross-entropy loss
- **Features:** 183 transaction features normalized via MinMaxScaler
- **Training:** PyTorch Geometric, CPU-only, 50 epochs with early stopping
- **Split:** Same temporal split as RF baseline (timestep < 35 / ≥ 35)
- **Evaluation:** Precision, Recall, F1, Micro-F1

### Results (10% sample)

| Model | Precision | Recall | F1 |
|-------|-----------|--------|----|
| RF (full) | 0.986 | 0.727 | 0.826 |
| GCN (10%) | ~0.33 | ~0.33 | ~0.33 |
| GAT (10%) | ~0.33 | ~0.33 | ~0.33 |

GNN performance on small samples is limited by lack of feature normalization and class weighting. Full-dataset training with focal loss and class-weighted sampling is the planned improvement.

## Explainability (Phase 6)

### SHAP Feature Attribution

Uses **TreeSHAP** (exact SHAP for tree ensembles) to explain individual RF predictions:

- **Method:** `shap.TreeExplainer` on the trained RandomForestClassifier
- **Sampling:** 500 test rows for speed (preserves distribution via stratified sampling)
- **Output:** Per-feature contribution to the illicit class prediction
- **Visualizations:** SHAP summary beeswarm plots showing feature importance × impact direction

#### Why SHAP?

- **Local explanations:** Each transaction gets its own feature attribution
- **Model-agnostic for trees:** TreeSHAP is exact (not approximate) for tree ensembles
- **Actionable:** Investigators can see *why* a specific tx was flagged

### k-hop Subgraph Extraction

For any flagged transaction, extracts the surrounding k-hop neighborhood:

- **Bidirectional BFS:** Collects both upstream (funding sources) and downstream (money flow) neighbors
- **Depth limit:** Default k=2, max_nodes=500 cap prevents runaway expansion
- **Output:** Cytoscape.js-compatible JSON with class coloring, hop distances, and seed highlighting

### Unified Node Inspector

`get_node_explanation(G, model, node_id)` returns a single dict combining:

1. **Identity:** txId, class, timestep
2. **Risk score:** P(illicit) from RF model
3. **SHAP top-5:** Features driving this specific prediction
4. **Subgraph context:** k-hop neighborhood stats
5. **Subgraph JSON:** Ready for frontend visualization

This powers the "Explain this wallet" interaction in the Graph Explorer.

## Technical Stack

| Layer | Technology |
|-------|-----------|
| Data storage | DuckDB (in-memory) + CSV |
| Graph analysis | NetworkX |
| Classical ML | scikit-learn (Random Forest) |
| Graph ML | PyTorch + PyTorch Geometric |
| Explainability | SHAP (TreeSHAP) |
| Visualization | matplotlib, plotly |
| Frontend (Phase 8) | Next.js + Cytoscape.js |

## Citation

```bibtex
@article{elmougy2023demystifying,
  title={Demystifying Fraudulent Transactions and Illicit Nodes in the Bitcoin Network for Financial Forensics},
  author={Elmougy, Youssef and Liu, Ling},
  journal={arXiv preprint arXiv:2306.06108},
  year={2023}
}
```
