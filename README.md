# BitTrace

> *Financial institutions lose billions to crypto fraud annually. BitTrace applies graph neural networks and local LLM investigation to the Elliptic++ dataset — 203K Bitcoin transactions and 822K wallet addresses — detecting illicit activity with explainable, AI-generated forensic reports.*

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Dataset: Elliptic++](https://img.shields.io/badge/dataset-Elliptic%2B%2B-lightgrey.svg)](https://github.com/git-disl/EllipticPlusPlus)

## Overview

BitTrace is a portfolio project demonstrating skills in **data analytics**, **graph networks**, **machine learning**, and **applied AI**. It builds on the [Elliptic++ dataset](https://github.com/git-disl/EllipticPlusPlus) to detect fraudulent Bitcoin transactions and illicit wallet addresses using:

- **Random Forest** baseline (matching KDD '23 paper metrics)
- **Graph Neural Networks** (GCN, GAT) on transaction and wallet graphs
- **AI Investigator** — local LLM generating natural-language forensic reports

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        PORTFOLIO APP                            │
│              FastAPI  +  Next.js Dashboard                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────────┐
│                     AI INVESTIGATOR                             │
│   Local Hermes LLM (llama-server, port 8080)                   │
│   Graph-context RAG  →  Investigation Reports                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────────┐
│                   ML / GRAPH ML                                 │
│   Random Forest Baseline  |  GCN / GAT / HGT                   │
│   SHAP + Graph Explainer                                      │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────┼────────────────────────────────────┐
│                   ANALYTICS LAYER                               │
│   EDA & Temporal Analysis  |  Feature Engineering               │
│   Interactive Graph Visualization                               │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────┴────────────────────────────────────┐
│                      DATA LAYER                                 │
│   Elliptic++ CSVs  →  DuckDB / Parquet                         │
└─────────────────────────────────────────────────────────────────┘
```

## Quick Start

### 1. Setup environment

```bash
cd /home/eduardo/Documents/bittrace

# Remove any old .venv and create venv/ with uv
rm -rf .venv
uv venv venv
source venv/bin/activate

# Install dependencies
uv pip install -e ".[dev]"
```

### 2. Download the dataset

```bash
python data/download.py --check
```

The Elliptic++ dataset needs to be downloaded from [Google Drive](https://drive.google.com/drive/folders/1MRPXz79Lu_JGLlJ21MDfML44dKN9R08l) and placed in the `data/` directory.

### 3. Run EDA notebooks

```bash
jupyter notebook notebooks/01_eda_transactions.ipynb
```

## Dataset

The [Elliptic++ dataset](https://github.com/git-disl/EllipticPlusPlus) provides four graph types from Bitcoin forensic data:

| Graph | Nodes | Edges | Use Case |
|-------|-------|-------|----------|
| **Tx→Tx** (money flow) | 203K transactions | 234K | Temporal GNN, fraud classification |
| **Addr→Addr** (actor interaction) | 822K wallets | 2.9M | Community detection, illicit actor profiling |
| **Addr↔Tx** (bipartite) | 1.3M edges | — | Heterogeneous GNN |
| **User entity** (clusters) | — | — | De-anonymization / risk clustering |

### Baseline Benchmarks (KDD '23 Paper)

| Task | Precision | Recall |
|------|-----------|--------|
| Transactions (RF) | 98.6% | 72.7% |
| Actors (RF) | 92.1% | 80.2% |

## Running the Explorer

```bash
# Terminal 1 — FastAPI backend (port 8000)
cd /home/eduardo/Documents/bittrace
source venv/bin/activate
uvicorn api.main:app --port 8000 --reload

# Terminal 2 — Next.js dashboard (port 3000)
cd dashboard
npm install  # first time only
npm run dev
```

Open **http://localhost:3000** in your browser.

### Dashboard tabs

| Tab | What it does |
|---|---|
| **Explorer** | Force-directed graph. Click nodes → inspect, trace upstream/downstream, expand neighbors. |
| **Macro** | Illicit heatmap by timestep (click to filter), class distribution, class-to-class edge flow. |
| **Story Mode** | Step-by-step investigation stories synced with graph highlights. |

### API endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/graph/overview` | Node/edge counts, class breakdown, timestep distribution |
| GET | `/graph/node/{id}` | Attributes, degrees, class for a single node |
| GET | `/graph/expand?node_id=&depth=` | k-hop BFS neighbor expansion (Cytoscape JSON) |
| GET | `/graph/trace?node_id=&direction=&max_hops=` | Directed money-flow trace |
| GET | `/graph/subgraph/{case_id}` | Precomputed story subgraph with step annotations |
| GET | `/stories` | List all investigation stories |
| GET | `/stories/{id}` | Full story with step-by-step structure |

## Project Structure

```
bittrace/
├── data/                     # Elliptic++ CSVs (gitignored)
│   └── download.py           # Dataset download script
├── notebooks/                # Python scripts for EDA & experiments
├── src/
│   ├── data/                 # DuckDB loaders, schema
│   ├── features/             # Graph feature engineering
│   ├── models/               # RF, GCN, GAT models
│   ├── explain/              # SHAP + subgraph explanations
│   ├── graph/                # Graph builders, tracing, export, patterns
│   ├── stories/              # YAML case studies, loader, schema
│   └── ai/                   # LLM investigation pipeline
├── api/                      # FastAPI endpoints (port 8000)
├── dashboard/                # Next.js dashboard (port 3000)
├── docs/                     # Methodology docs + story visualizations
├── tests/                    # pytest unit tests (77 passing)
└── pyproject.toml
```

## Implementation Phases

| Phase | Deliverable | Status |
|-------|-------------|--------|
| **1. Foundation** | Data pipeline, DuckDB loaders, EDA | ✅ Done |
| **2. Baselines** | RF classifier (F1 0.826) | ✅ Done |
| **3. Graph ML** | GCN/GAT on tx & addr graphs | ✅ Done |
| **4. Explainability** | SHAP + k-hop subgraph extraction | ✅ Done |
| **5. AI Investigator** | LLM reports with graph context | ✅ Done |
| **6. Dashboard + API** | FastAPI + Next.js UI | ✅ Done |
| **7. Investigation Stories** | YAML cases, step-through narratives | ✅ Done |
| **8. Graph Explorer** | Interactive dashboard, trace, story mode | ✅ Done |

## Citation

```bibtex
@article{elmougy2023demystifying,
  title={Demystifying Fraudulent Transactions and Illicit Nodes in the Bitcoin Network for Financial Forensics},
  author={Elmougy, Youssef and Liu, Ling},
  journal={arXiv preprint arXiv:2306.06108},
  year={2023}
}
```
