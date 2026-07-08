#!/usr/bin/env python3
"""BitTrace Graph Explorer API — FastAPI.

Endpoints:
  GET /graph/overview
  GET /graph/subgraph/{case_id}
  GET /graph/expand?node_id=&depth=1
  GET /graph/trace?node_id=&direction=downstream|upstream&max_hops=10
  GET /graph/node/{id}
  GET /stories
  GET /stories/{id}

Run:
  uvicorn api.main:app --port 8000 --reload
"""

import json
import sys
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

# Project root so we can import src/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.loaders import get_duckdb_connection
from src.graph.builders import build_tx_graph
from src.graph.export import trace_to_cytoscape
from src.graph.trace import trace_downstream, trace_upstream
from src.stories import load_all_stories, get_story_by_id

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="BitTrace Graph Explorer",
    description="API for interactive money-flow tracing on Elliptic++",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Lazy graph & DB singletons
# ---------------------------------------------------------------------------
_graph = None
_db = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_tx_graph()
    return _graph


def get_db():
    global _db
    if _db is None:
        _db = get_duckdb_connection()
    return _db


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
CLASS_COLORS = {"1": "#ef4444", "2": "#22c55e", "3": "#6b7280"}
CLASS_LABELS = {"1": "illicit", "2": "licit", "3": "unknown"}


def _node_attr(G, node_id):
    """Return dict of attributes for a single node."""
    if node_id not in G:
        return None
    attrs = dict(G.nodes[node_id])
    c = attrs.get("class")
    attrs["class_label"] = CLASS_LABELS.get(str(c), "unknown") if c is not None else "unknown"
    attrs["class_color"] = CLASS_COLORS.get(str(c), "#6b7280") if c is not None else "#6b7280"
    return attrs


def _node_counts(G):
    counts = {1: 0, 2: 0, 3: 0}
    for _, a in G.nodes(data=True):
        c = a.get("class", 3)
        if c in counts:
            counts[c] += 1
    return {k: v for k, v in counts.items()}


def _timestep_counts(G):
    ts: dict = {}
    for _, a in G.nodes(data=True):
        t = a.get("timestep")
        if t is not None:
            ts[t] = ts.get(t, 0) + 1
    return {str(k): v for k, v in sorted(ts.items())}


def _illicit_per_timestep(G):
    ts: dict = {}
    for _, a in G.nodes(data=True):
        t = a.get("timestep")
        c = a.get("class")
        if t is not None and c == 1:
            ts[t] = ts.get(t, 0) + 1
    return {str(k): v for k, v in sorted(ts.items())}


def _class_flow(G):
    """Count edges grouped by (src_class, dst_class)."""
    flow: dict = {}
    for u, v in G.edges():
        sc = G.nodes[u].get("class", 3)
        dc = G.nodes[v].get("class", 3)
        key = f"{sc}->{dc}"
        flow[key] = flow.get(key, 0) + 1
    return flow


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.get("/graph/overview")
def graph_overview():
    """Macro stats: node counts, class breakdown, timestep distribution, class flow."""
    G = get_graph()
    return {
        "total_nodes": G.number_of_nodes(),
        "total_edges": G.number_of_edges(),
        "class_counts": _node_counts(G),
        "class_labels": {k: CLASS_LABELS[str(k)] for k in [1, 2, 3]},
        "timestep_counts": _timestep_counts(G),
        "illicit_per_timestep": _illicit_per_timestep(G),
        "class_flow": _class_flow(G),
        "density": G.number_of_edges() / max(G.number_of_nodes() * (G.number_of_nodes() - 1), 1),
    }


@app.get("/graph/subgraph/{case_id}")
def graph_subgraph(case_id: str):
    """Return a precomputed case-study subgraph as Cytoscape JSON.

    Uses the story YAML cases (peel-chain, fan-out-split, consolidation)
    and traces the appropriate direction for each.
    """
    story = get_story_by_id(case_id)
    if story is None:
        # Try loading from docs/story_*_subgraph.json as fallback
        json_path = PROJECT_ROOT / "docs" / f"story_{case_id}_subgraph.json"
        if json_path.exists():
            with open(json_path) as f:
                return json.load(f)
        # List available cases
        available = [s.id for s in load_all_stories()]
        raise HTTPException(404, f"Case '{case_id}' not found. Available: {available}")

    G = get_graph()
    direction = story.steps[0].trace_direction if story.steps else "downstream"
    if direction == "upstream":
        trace_result = trace_upstream(G, story.seed_node_id, max_hops=3)
    else:
        trace_result = trace_downstream(G, story.seed_node_id, max_hops=3)

    from src.graph.export import export_story_subgraph
    return export_story_subgraph(story, G, trace_result)


@app.get("/graph/expand")
def graph_expand(
    node_id: int = Query(..., description="Center node ID"),
    depth: int = Query(1, ge=1, le=5, description="BFS depth (1–5)"),
    max_nodes: int = Query(500, ge=10, le=5000, description="Max nodes to return"),
):
    """Lazy k-hop neighbor expansion around a node.

    Returns Cytoscape-compatible nodes and edges.
    """
    G = get_graph()
    if node_id not in G:
        raise HTTPException(404, f"Node {node_id} not found in graph")

    # BFS expansion
    visited = {node_id}
    frontier = [node_id]
    for _d in range(depth):
        next_frontier = []
        for n in frontier:
            for nb in G.successors(n):
                if nb not in visited and len(visited) < max_nodes:
                    visited.add(nb)
                    next_frontier.append(nb)
            for nb in G.predecessors(n):
                if nb not in visited and len(visited) < max_nodes:
                    visited.add(nb)
                    next_frontier.append(nb)
        if not next_frontier:
            break
        frontier = next_frontier

    sub_edges = [(u, v) for u, v in G.edges() if u in visited and v in visited]
    trace_result = {"nodes": list(visited), "edges": sub_edges, "hops": {}, "path": []}
    return trace_to_cytoscape(G, trace_result)


@app.get("/graph/trace")
def graph_trace(
    node_id: int = Query(..., description="Seed transaction ID"),
    direction: Literal["downstream", "upstream"] = Query(
        "downstream", description="Trace direction"
    ),
    max_hops: int = Query(10, ge=1, le=50, description="Max hop depth"),
):
    """Money-flow trace: follow directed edges from a seed node.

    Returns nodes, edges, hop distances, and the trace path.
    """
    G = get_graph()
    if node_id not in G:
        raise HTTPException(404, f"Node {node_id} not found in graph")

    if direction == "downstream":
        trace_result = trace_downstream(G, node_id, max_hops=max_hops)
    else:
        trace_result = trace_upstream(G, node_id, max_hops=max_hops)

    # Build a path from hops (ordered by increasing hop distance)
    sorted_hops = sorted(trace_result.get("hops", {}).items(), key=lambda x: x[1])
    path = [trace_result.get("seed", node_id)] + [int(nid) for nid, _ in sorted_hops]

    return {
        **trace_result,
        "path": path,
        "cytoscape": trace_to_cytoscape(G, trace_result),
    }


@app.get("/graph/node/{node_id}")
def graph_node(node_id: int):
    """Return attributes for a single node."""
    G = get_graph()
    if node_id not in G:
        raise HTTPException(404, f"Node {node_id} not found")

    attrs = _node_attr(G, node_id)
    return {
        "node_id": node_id,
        "attributes": attrs,
        "in_degree": G.in_degree(node_id),
        "out_degree": G.out_degree(node_id),
        "degree": G.degree(node_id),
    }


@app.get("/stories")
def list_stories():
    """List all available investigation stories."""
    stories = load_all_stories()
    return [
        {
            "id": s.id,
            "title": s.title,
            "difficulty": s.difficulty.value,
            "pattern": s.pattern,
            "seed_node_id": s.seed_node_id,
            "step_count": len(s.steps),
            "narrative_preview": s.narrative.strip()[:150] + "...",
        }
        for s in stories
    ]


@app.get("/stories/{story_id}")
def get_story(story_id: str):
    """Return a single story with its full step-by-step structure."""
    story = get_story_by_id(story_id)
    if story is None:
        available = [s.id for s in load_all_stories()]
        raise HTTPException(404, f"Story '{story_id}' not found. Available: {available}")
    return story.to_dict()
