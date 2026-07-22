# BitTrace: Crypto Investigation Tool

**Bitcoin fraud forensics demo** on the [Elliptic++](https://github.com/git-disl/EllipticPlusPlus) dataset — interactive money-flow tracing, graph storytelling, classical ML, graph neural networks, and a full-stack investigation UI.

> *Zoom from a 203K-transaction network into individual money trails. Click any node to inspect transaction and wallet attributes. Trace illicit flows hop by hop — in 2D or 3D (timestep as the Z-axis).*

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Dataset: Elliptic++](https://img.shields.io/badge/dataset-Elliptic%2B%2B-lightgrey.svg)](https://github.com/git-disl/EllipticPlusPlus)
[![Built 100% with AI agents](https://img.shields.io/badge/built%20with-AI%20agents%20(Grok%20Build%20%2B%20Hermes)-orange.svg)](https://x.ai/)
[![Profile: munessain-code](https://img.shields.io/badge/GitHub-munessain--code-blue.svg)](https://github.com/munessain-code)

---

## This entire project was built with AI

> **Important:** BitTrace is an **AI-native portfolio project**. Nearly **all of the application code, scaffolding, ML pipelines, API, and dashboard** were produced by AI coding agents under human direction — not written line-by-line by hand.  
>  
> The goal of this repo is to demonstrate **professional skill at directing, specifying, auditing, and shipping software with AI** (product judgment + verification), which is how modern engineering work increasingly gets done.

| What the human did | What AI agents did |
|--------------------|--------------------|
| Product vision and constraints | Scaffolded the full monorepo |
| Dataset and hardware choices | Built data loaders, graphs, ML training |
| Phase priorities and attribute decisions | Implemented FastAPI + Next.js Explorer |
| Review, acceptance, Telegram steering | Stories, tests, docs figures, GNN/RF runs |
| **Grok Build:** plan, audits, hard bugfixes | **Hermes:** majority of feature delivery (local Qwen) |

**Hermes setup:** the coding agent is wired to a **locally hosted Qwen model** (served by **`llama-server`** with quantized GGUF weights on a local GPU). Agent work does not depend on a cloud chat API for that loop.

If you are evaluating this as a hiring sample, please treat it as evidence of **AI-augmented development ability**: writing specs, decomposing work into phases, running agents on **self-hosted models**, validating results, and remediating gaps — not as a claim of sole manual authorship of every file.

---

## Table of contents

1. [This entire project was built with AI](#this-entire-project-was-built-with-ai)
2. [Screenshots](#screenshots)
3. [Project overview](#project-overview)
4. [Built with Grok Build + Hermes agents](#built-with-grok-build--hermes-agents)
5. [What you can do in the demo](#what-you-can-do-in-the-demo)
6. [Problem & dataset](#problem--dataset)
7. [System architecture](#system-architecture)
8. [Repository map (every folder)](#repository-map-every-folder)
9. [Local machine & Hermes hosting](#local-machine--hermes-hosting)
10. [Quick start](#quick-start)
11. [API reference](#api-reference)
12. [ML results snapshot](#ml-results-snapshot)
13. [Implementation phases](#implementation-phases)
14. [Agent workflow](#agent-workflow)
15. [Citation & author](#citation--author)

---

## Screenshots

Captured from a live local run of the API + Next.js dashboard (Explorer, Macro, Story Mode).

### Graph Explorer (2D) — node inspector

Transaction subgraph with **Transaction details** (BTC, fees, size) and **Account details** (sender/receiver wallets, illicit labels, non-BTC activity stats). Expand depth/budget/accumulate controls along the bottom.

![Graph Explorer 2D with node inspector](docs/screenshots/01-explorer-2d.png)

### Trace Down + fan-out

Illicit seed with **out-degree 3** (fan-out badge). **Trace Down** highlights the full multi-branch BFS tree (all edges), not a single peel-chain path.

![Trace Down multi-branch fan-out](docs/screenshots/03-explorer-trace-down.png)

### Macro overview

Full-graph stats (~204K nodes / ~234K edges), class distribution (illicit / licit / unknown), class-to-class edge flows, and illicit activity by timestep.

![Macro overview dashboard](docs/screenshots/05-macro-overview.png)

### Story Mode

Guided investigation narratives (peel chain, fan-out, consolidation) with step-through text and synchronized graph highlights.

![Story Mode peel-chain investigation](docs/screenshots/06-story-mode.png)

### 3D Explorer (timestep on Z)

Same investigation controls as 2D; view toggle to **3D View**. Inspector still shows illicit TX + wallet accounts while the force layout uses timestep for depth.

![3D Graph Explorer](docs/screenshots/04-explorer-3d.png)

---

## Project overview

### Why this project exists

Financial crime investigations on blockchains are **graph problems**: funds hop through chains of transactions and wallets (layering, peel chains, fan-out/fan-in) so that origin and destination are hard to see in a spreadsheet. Academic datasets such as **Elliptic++** already label illicit vs licit activity and ship rich features — but most tutorials stop at a classifier notebook.

**BitTrace** is a portfolio-scale demo that goes further:

| Layer | Goal |
|-------|------|
| **Data** | Load Elliptic++ into DuckDB, expose clean Python loaders |
| **Analytics** | Build TX→TX (and related) graphs; measure topology and layering patterns |
| **ML** | Random Forest baseline + GCN/GAT graph models with forensic metrics (precision/recall) |
| **Explainability** | SHAP / subgraph helpers so a flag is not a black box |
| **Product UI** | Interactive **Graph Explorer** (2D/3D), macro stats, guided **story** investigations |
| **Process** | Built primarily by **Hermes coding agents**, planned and audited by **Grok Build** |

The result is something you can **run locally**, click through, and discuss in an interview: not only “we trained a model,” but “we can *trace* money, *expand* neighborhoods, *inspect* wallets, and *narrate* a case.”

### What “done so far” means

| Area | Status |
|------|--------|
| Data loaders + DuckDB schema | Done |
| Graph builders, trace, expand, export | Done |
| RF baseline + docs/results | Done |
| GCN/GAT training pipeline | Done (see notes on GCN imbalance in `docs/results.md`) |
| SHAP / explain library code | Done (UI wiring progressive) |
| Investigation stories (YAML) | Done (peel-chain, fan-out, consolidation) |
| FastAPI + Next.js Explorer (2D/3D) | Done |
| Account details (wallets, no BTC on accounts) + TX value details | Done |
| Expand depth/budget/accumulate + fan-out badges | Done |
| Hybrid TX↔wallet **tab** | Spec/prompt ready (Phase 8d) — not required for core demo |
| Local LLM “AI investigator” chat | Planned / partial (Phase 9) — `llama-server` hosted locally for this path |

### Core ideas the product encodes

1. **Multi-scale investigation** — macro overview (counts, timesteps) → micro subgraph (expand/trace) → story walkthrough.
2. **TX graph first** — canvas nodes are **transactions**; money flows on directed TX→TX edges. Wallets appear in the **inspector** (and later hybrid tab).
3. **Clear class language** — UI always says **illicit / licit / unknown**, never raw `1` / `2` / `3`.
4. **Attribute split** — **Transaction details** hold value fields (BTC, fees, size); **Account details** hold wallet IDs and non-BTC activity only.
5. **Branch-aware tracing** — Trace Down/Up follows **all** BFS branches within hop limits, not only a single peel-chain line.

---

## Built with Grok Build + Hermes agents

This project was **designed and mostly implemented through an agentic workflow**, not as a pure solo hand-coded greenfield.

| Role | Tool | What it did |
|------|------|-------------|
| **Architecture & orchestration** | **[Grok Build](https://x.ai/)** (IDE agent) | Project plan, phase prompts, architecture (API vs UI, CORS, GPU strategy), **audits**, focused remediations, and this README |
| **Primary builder** | **Hermes agent** (Oz orchestrator + subagents) | Repo scaffold, data pipeline, graph analytics, RF/GNN, SHAP, FastAPI, Next.js Graph Explorer (2D/3D), stories, bulk of Phases 1–8 |
| **Human** | **Munessain** | Product goals, attribute choices, Telegram steering, acceptance of demos |

**Distribution of work (honest summary):**

1. **Grok Build** turned the idea into a durable **project plan** and copy-paste **Hermes phase prompts** (Telegram progress after each subtask).
2. **Hermes** executed those phases and **built the majority of the application**.
3. **Grok Build** re-entered as **auditor and remediator**: full-stack audits, silent failures, dashboard TypeScript/build fixes, LAN CORS, account API polish, expand accumulate, multi-branch trace highlight, fan-out UX.
4. **Hermes coding agents are powered by a local Qwen model** served with **`llama-server`** (GGUF on GPU). The same local-LLM stack can support optional investigation chat (Phase 9).

---

## What you can do in the demo

| Capability | Details |
|------------|---------|
| **Graph Explorer (2D / 3D)** | Force-directed TX→TX graph; in 3D, **Z ≈ timestep** so temporal layering is visible |
| **Trace Down / Trace Up** | BFS along money-flow edges; **all branches** highlighted |
| **Expand** | k-hop neighborhood; controls for **depth**, **max nodes**, **accumulate** (union into current view) |
| **Node inspector** | TX values + linked **sender/receiver wallets** (class labels + non-BTC profile fields) |
| **Fan-out / fan-in badges** | When graph degree > 1, UI flags branching explicitly |
| **Macro view** | Class mix, illicit-per-timestep heatmap, class-to-class edge flow |
| **Story mode** | Guided peel-chain / fan-out / consolidation narratives |
| **ML & explain** | RF baseline, GNN training scripts, SHAP tooling under `src/` |

---

## Problem & dataset

### Domain problem

Bad actors **layer** illicit funds: peel chains (linear hops), fan-outs (split), fan-ins (consolidate), and temporal delays across blocks/timesteps. Analysts need both **classifiers** and **navigable graphs**.

### Elliptic++ at a glance

| Graph / table | Scale (approx.) | Role in BitTrace |
|---------------|-----------------|------------------|
| **Tx→Tx** (`txs_edgelist`) | ~203K nodes, ~234K edges | Primary Explorer canvas |
| **Tx features / classes** | 183-ish features + labels | RF/GNN, inspector values |
| **Wallets** | ~822K addresses, 56 features | Account details, future hybrid tab |
| **Addr↔Tx** | Bipartite edgelists | Link TX to senders/receivers |
| **Time** | 49 timesteps | Macro heatmaps; 3D Z-axis |

Labels: **1 = illicit**, **2 = licit**, **3 = unknown** (always mapped to words in the UI).

**Paper baselines (KDD-oriented Elliptic++ work):** RF on transactions historically ~98.6% precision / ~72.7% recall in the paper; this repo’s Phase 2 RF lands near **~97% P / ~72% R** (see `docs/results.md`).

---

## System architecture

```
┌────────────────────────────────────────────────────────────┐
│  Next.js Graph Explorer  (localhost:3001)                  │
│  Macro · Explorer 2D/3D · Story Mode                       │
└────────────────────────────┬───────────────────────────────┘
                             │ HTTP + CORS
┌────────────────────────────▼───────────────────────────────┐
│  FastAPI  (localhost:8000)                                 │
│  /graph/*  /stories/*                                      │
└────────────────────────────┬───────────────────────────────┘
                             │
┌────────────────────────────▼───────────────────────────────┐
│  src/  DuckDB · NetworkX · RF/GNN · SHAP · stories YAML    │
└────────────────────────────┬───────────────────────────────┘
                             │
┌────────────────────────────▼───────────────────────────────┐
│  Elliptic++ CSVs  (gitignored — download separately)       │
└────────────────────────────────────────────────────────────┘
```

**AI agents + local Qwen model (how Hermes runs on this project):**

```
Telegram / chat UI
        │
        ▼
Hermes agent gateway  (local process on the workstation)
        │
        ├─► Coding agents (scaffold, implement features, tests)
        │
        └─► OpenAI-compatible API  →  llama-server (local)
                    ▲
                    │  loads quantized Qwen GGUF weights
                    │  inference on local GPU (not cloud-hosted chat)
                    ▼
              Local Qwen model
```

Hermes is **configured to use that local Qwen endpoint** as its LLM backend — agent planning, tool use, and code work run against a model you host yourself, not a third-party cloud API for the agent loop.

---

## Repository map (every folder)

Top-level layout:

```
bittrace/
├── api/                 # HTTP API (FastAPI)
├── dashboard/           # Web UI (Next.js)
├── src/                 # Python domain library (importable package)
├── data/                # Dataset + download helper (CSVs gitignored)
├── notebooks/           # Experiment / EDA / training notebooks & runners
├── docs/                # Written methodology, metrics, figures
├── tests/               # Automated pytest suite
├── scripts/             # CLI utilities (e.g. graph tooling)
├── pyproject.toml       # Package metadata & Python dependencies
├── README.md            # This file
└── .gitignore           # Excludes venv, node_modules, CSVs, secrets
```

### `api/`

**Purpose:** Serve the Graph Explorer and stories over HTTP so the dashboard never loads 200K+ nodes into the browser at once.

| Item | Role |
|------|------|
| `main.py` | FastAPI app: CORS, lazy graph load, endpoints for overview, expand, trace, node (+ accounts), stories |
| `__init__.py` | Package marker |

Typical run: `uvicorn api.main:app --port 8000 --host 0.0.0.0 --reload`.

### `dashboard/`

**Purpose:** Browser UI for investigation workflows.

| Item | Role |
|------|------|
| `src/app/` | Next.js App Router pages, layout, global CSS (full-viewport shell) |
| `src/components/GraphExplorer/` | 2D force graph, expand/trace controls, accumulate mode |
| `src/components/GraphExplorer3D/` | 3D force graph; timestep on Z |
| `src/components/MacroOverview/` | Aggregate stats and illicit-per-timestep exploration |
| `src/components/StoryPanel/` | Step-through investigation narratives |
| `src/components/NodeInspector/` | Side panel: TX details + account (wallet) details |
| `src/lib/graph-api.ts` | Typed client for the FastAPI backend |
| `package.json` | Scripts: `npm run dev` on **port 3001** |
| `.env.local` | Optional `NEXT_PUBLIC_API_URL` (gitignored) |

### `src/` (Python package `bittrace`)

**Purpose:** All reusable domain logic. The API and notebooks import from here.

| Subfolder | Role |
|-----------|------|
| **`src/data/`** | DuckDB connection helpers, SQL schema, CSV loaders, **`attribute_catalog.py`** (hover/inspector field lists, class labels) |
| **`src/graph/`** | NetworkX builders (TX graph, etc.), **trace** (up/downstream BFS), **expand** (k-hop budgeted BFS), export to Cytoscape JSON, layering **patterns**, case extraction |
| **`src/models/`** | Random Forest baseline, GCN/GAT, graph dataset construction, evaluation → `docs/results.md` |
| **`src/explain/`** | SHAP explainer, node inspector helpers, subgraph explanation utilities |
| **`src/stories/`** | YAML investigation cases + loader/schema for Story Mode |
| **`src/features/`** | Feature-engineering hooks (as filled by Hermes phases) |
| **`src/viz/`** | Precompute helpers for subgraphs / static viz used in docs |
| **`src/ai/`** | Place for LLM investigation client/prompts (Phase 9) |

### `data/`

**Purpose:** Hold Elliptic++ files and small precomputed artifacts. **Large CSVs are gitignored.**

| Item | Role |
|------|------|
| `download.py` | Helper to fetch/check dataset placement |
| `*.csv` | Raw Elliptic++ tables (local only; multi-GB) |
| `subgraphs/` | Optional precomputed case JSON for demos |

### `notebooks/`

**Purpose:** Exploratory and reproducible experiment entry points (often paired with `*_run.py` scripts for headless execution).

Examples: graph topology, layering patterns, RF baseline, GNN training, explainability, case studies.

### `docs/`

**Purpose:** Human-readable methodology, benchmark tables, and figures (loss curves, confusion matrices, story previews, illicit timelines).

Start with `docs/methodology.md` and `docs/results.md`.

### `tests/`

**Purpose:** Regression safety for graph logic, stories, accounts payload, models on tiny fixtures, etc. Run with `pytest tests/`.

### `scripts/`

**Purpose:** Command-line tools (e.g. graph CLI) that wrap `src/` without starting the full web stack.

### Root config

| File | Role |
|------|------|
| `pyproject.toml` | Package name, dependencies, pytest config |
| `.gitignore` | Keeps `venv/`, `node_modules/`, CSVs, `.env*`, caches out of git |
| `venv/` | Local virtualenv (**not** committed) |

---

## Local machine & Hermes hosting

Built and demoed on a **local workstation** (self-hosted AI stack — not a cloud-only demo).

### Hermes agent + local Qwen (important)

| Piece | Role |
|-------|------|
| **Hermes agent** | Multi-agent coding orchestrator (e.g. “Oz”) used to implement most of BitTrace |
| **Where it runs** | On the same local machine as the project (gateway process; often Telegram-connected for progress) |
| **LLM backend** | **Local Qwen** — not a remote SaaS chat API for the agent loop |
| **How the model is served** | **`llama-server`** (OpenAI-compatible HTTP API) loads a **quantized Qwen GGUF** and serves completions/tools |
| **Hardware for inference** | Local **NVIDIA GPU** for model inference (and optional GNN training) |

In short: **Hermes is set up and driven by a Qwen model that you host yourself via `llama-server`.** That is the intentional architecture for this portfolio — privacy, cost control, and demonstrating full local agent ops.

Grok Build (IDE agent) also works on this machine for planning and audits; it is separate from Hermes but part of the same AI-native workflow.

### Generic environment (no machine-specific identifiers)

| Component | Setup |
|-----------|--------|
| **OS** | Linux workstation with enough RAM for DuckDB + graph loads |
| **GPU** | Local CUDA GPU for Qwen inference / training |
| **Python** | `venv/` via **[uv](https://github.com/astral-sh/uv)** |
| **Hermes** | Local agent gateway → **local Qwen** through `llama-server` |
| **BitTrace API** | uvicorn on port **8000** (prefer `127.0.0.1` unless you intentionally demo on a trusted LAN) |
| **BitTrace UI** | Next.js on port **3001** |

**Security note:** Binding with `--host 0.0.0.0` exposes the API on all interfaces **with no authentication**. Use `127.0.0.1` for solo local work; only bind to the LAN on a trusted network.

---

## Quick start

### 1. Environment

```bash
cd bittrace
uv venv venv
source venv/bin/activate
uv pip install -e ".[dev]"
```

You may also need: `torch`, `torch_geometric`, `fastapi`, `uvicorn`, `pyyaml` depending on install completeness.

### 2. Dataset

Download Elliptic++ CSVs into `data/` from the [official Drive folder](https://drive.google.com/drive/folders/1MRPXz79Lu_JGLlJ21MDfML44dKN9R08l) ([Elliptic++ repo](https://github.com/git-disl/EllipticPlusPlus)).

```bash
python data/download.py --check
```

### 3. Run API + dashboard

```bash
# Terminal 1 — prefer loopback unless you need LAN access
source venv/bin/activate
uvicorn api.main:app --port 8000 --host 127.0.0.1 --reload

# Terminal 2
cd dashboard && npm install && npm run dev
```

Open **http://localhost:3001**.  
Optional `dashboard/.env.local` (gitignored): `NEXT_PUBLIC_API_URL=http://127.0.0.1:8000`

If you must demo from another device on a **trusted** LAN only:

```bash
uvicorn api.main:app --port 8000 --host 0.0.0.0 --reload   # no auth — do not expose publicly
```

### 4. Tests

```bash
source venv/bin/activate
pytest tests/ -q
```

---

## API reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/graph/overview` | Macro stats: counts, timesteps, class flow |
| GET | `/graph/node/{id}` | TX attributes + **accounts** (senders/receivers, counts, profiles) |
| GET | `/graph/expand?node_id=&depth=&max_nodes=` | k-hop neighborhood (Cytoscape JSON) |
| GET | `/graph/trace?node_id=&direction=&max_hops=` | Downstream/upstream money-flow BFS |
| GET | `/graph/subgraph/{case_id}` | Story/case subgraph (`peel-chain`, `easy`, …) |
| GET | `/stories` | List investigation stories |
| GET | `/stories/{id}` | Full story steps + highlights |

---

## ML results snapshot

| Model | Precision | Recall | Notes |
|-------|-----------|--------|--------|
| Random Forest (transactions) | ~0.97 | ~0.72 | Strong baseline; AML-style recall framing |
| GCN / GAT | See `docs/results.md` | | Graph training pipeline present; watch class imbalance |

---

## Implementation phases

| Phase | Focus | Primary builder |
|-------|--------|-----------------|
| 1 | Foundation, loaders | Hermes |
| 2 | RF baselines | Hermes |
| 3 | Graph analytics | Hermes |
| 4 | Trace / expand backend | Hermes |
| 5 | GNN (GCN/GAT) | Hermes (+ audit on metrics) |
| 6 | Explainability libraries | Hermes |
| 7 | Investigation stories | Hermes |
| 8 / 8b / 8c | Dashboard, 3D, accounts, expand UX | Hermes + **Grok Build audit/fix** |
| 8d | Hybrid TX↔wallet tab | Prompt ready |
| 9 | Local LLM investigator | Planned / partial |
| 10 | Polish & publish | Grok Build + human |

---

## Agent workflow

1. Maintain an authoritative plan (e.g. Documents: `bittrace-project-plan.md`).
2. Send **one phase prompt** at a time to Hermes (Telegram).
3. Hermes reports subtasks as it builds.
4. Grok Build **audits** (pytest, live API, `npm run build`, silent failures) and applies targeted fixes.
5. Human locks product choices (attributes, UX) before large UI phases.

---

## Citation & author

```bibtex
@article{elmougy2023demystifying,
  title={Demystifying Fraudulent Transactions and Illicit Nodes in the Bitcoin Network for Financial Forensics},
  author={Elmougy, Youssef and Liu, Ling},
  journal={arXiv preprint arXiv:2306.06108},
  year={2023}
}
```

**Author:** [Munessain](https://github.com/munessain-code) (`munessain-code`)  

**Built entirely with AI tooling under human direction:**

- [Grok Build](https://x.ai/) — plan, audit, remediation, documentation  
- **Hermes** multi-agent coding — majority of application code, **running against a local Qwen model**  
- Local **`llama-server` + Qwen GGUF** — Hermes LLM backend (self-hosted inference)

This repository is a **portfolio demonstration of AI-assisted software development**, including operating a **local agent + local foundation model** stack.

### License / data notice

- **Code:** portfolio use unless a `LICENSE` file states otherwise.
- **Data:** Elliptic++ is third-party — follow the dataset authors’ terms. **Do not commit raw CSVs.**
