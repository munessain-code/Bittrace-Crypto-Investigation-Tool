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
import logging
import sys
from pathlib import Path
from typing import Literal, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger(__name__)

# Project root so we can import src/
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.loaders import get_duckdb_connection
from src.data.attribute_catalog import (
    CLASS_LABELS as CATALOG_CLASS_LABELS,
    CLASS_COLORS as CATALOG_CLASS_COLORS,
    resolve_class_label,
    resolve_class_color,
    HOVER_ATTRIBUTES,
    CLICK_ATTRIBUTES,
    ACCOUNT_LIST_LIMIT,
    ACCOUNT_PROFILE_FIELDS,
    ACCOUNT_EXCLUDED_PREFIXES,
    DISPLAY_NAMES,
)
from src.graph.builders import build_tx_graph
from src.graph.export import trace_to_cytoscape
from src.graph.trace import trace_downstream, trace_upstream
from src.graph.hybrid import build_hybrid_subgraph
from src.stories import load_all_stories, get_story_by_id

# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------
app = FastAPI(
    title="BitTrace Graph Explorer",
    description="API for interactive money-flow tracing on Elliptic++",
    version="1.0.0",
)

# Local-dev CORS defaults. Private LAN ranges via regex for optional
# same-network demos (no hard-coded hostnames or machine-specific IPs).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
    ],
    allow_origin_regex=r"https?://("
    r"localhost|127\.0\.0\.1|"
    r"192\.168\.\d{1,3}\.\d{1,3}|"
    r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
    r"172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}"
    r")(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Legacy difficulty aliases → story IDs (Phase 4 precomputed cases)
DIFFICULTY_ALIASES = {
    "easy": "peel-chain",
    "average": "fan-out-split",
    "hard": "consolidation",
}

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


def _get_accounts(node_id: int, db, timestep: Optional[int] = None):
    """Fetch sender/receiver wallets for a transaction node.

    Returns parties with profile fields merged onto each object (keyed by
    address — never by parallel list index). Includes total counts when the
    list is capped. No BTC / fee wallet fields.

    Account details = wallets only, NO BTC balances, NO fees.
    """
    limit = ACCOUNT_LIST_LIMIT
    profile_cols = ", ".join(f'w."{f["field"]}"' for f in ACCOUNT_PROFILE_FIELDS)
    warnings: list[str] = []

    def count_parties(table: str, addr_col: str) -> int:
        try:
            row = db.execute(
                f'SELECT COUNT(*) FROM {table} WHERE "txId" = ?',
                [node_id],
            ).fetchone()
            return int(row[0]) if row else 0
        except Exception as e:
            logger.warning("count_parties failed for %s tx=%s: %s", table, node_id, e)
            warnings.append(f"count_{table}_failed")
            return 0

    def fetch_parties(table: str, addr_col: str) -> list[dict]:
        try:
            rows = db.execute(
                f"""
                SELECT
                    a."{addr_col}",
                    COALESCE(c.class, 3) AS class
                FROM {table} a
                LEFT JOIN wallet_classes c ON a."{addr_col}" = c.address
                WHERE a."txId" = ?
                ORDER BY c.class, a."{addr_col}"
                LIMIT ?
                """,
                [node_id, limit],
            ).fetchall()
            return [
                {
                    "address": addr,
                    "class_label": resolve_class_label(int(cls) if cls is not None else 3),
                }
                for addr, cls in rows
            ]
        except Exception as e:
            logger.warning(
                "fetch_parties failed table=%s tx=%s: %s", table, node_id, e
            )
            warnings.append(f"parties_{table}_failed")
            return []

    def fetch_profiles_by_address(addresses: list[str]) -> dict[str, dict]:
        """Return {address: {profile fields...}} preferring TX timestep when set."""
        if not addresses:
            return {}
        placeholders = ", ".join(["?"] * len(addresses))
        # Prefer feature row at the transaction's timestep, else nearest then any
        ts_order = (
            f'ABS(COALESCE(w."Time step", 0) - {int(timestep)})'
            if timestep is not None
            else '0'
        )
        try:
            rows = db.execute(
                f"""
                SELECT
                    w.address,
                    {profile_cols},
                    w."Time step" AS _ts
                FROM wallets w
                WHERE w.address IN ({placeholders})
                QUALIFY ROW_NUMBER() OVER (
                    PARTITION BY w.address
                    ORDER BY {ts_order} ASC, w."Time step" ASC
                ) = 1
                """,
                addresses,
            ).fetchall()
        except Exception as e:
            # Fallback without QUALIFY (older DuckDB) — first row per address
            logger.warning("profile QUALIFY query failed, using simple fetch: %s", e)
            try:
                rows = db.execute(
                    f"""
                    SELECT w.address, {profile_cols}, w."Time step" AS _ts
                    FROM wallets w
                    WHERE w.address IN ({placeholders})
                    """,
                    addresses,
                ).fetchall()
            except Exception as e2:
                logger.warning("fetch_profiles failed: %s", e2)
                warnings.append("profiles_failed")
                return {}

        by_addr: dict[str, dict] = {}
        for row in rows:
            addr = row[0]
            if addr in by_addr:
                continue  # keep first (best-ranked) row
            profile: dict = {"address": addr}
            for i, field_def in enumerate(ACCOUNT_PROFILE_FIELDS):
                raw = row[i + 1]
                if raw is not None and not str(field_def["field"]).lower().startswith(
                    ACCOUNT_EXCLUDED_PREFIXES
                ):
                    # Skip any accidental BTC/fee fields
                    fname = field_def["field"]
                    if fname.startswith("btc_") or fname.startswith("fees"):
                        continue
                    try:
                        profile[fname] = float(raw)
                    except (TypeError, ValueError):
                        profile[fname] = raw
            by_addr[addr] = profile
        return by_addr

    senders = fetch_parties("addr_tx_edges", "input_address")
    receivers = fetch_parties("tx_addr_edges", "output_address")
    sender_count = count_parties("addr_tx_edges", "input_address")
    receiver_count = count_parties("tx_addr_edges", "output_address")

    all_addrs = [p["address"] for p in senders] + [p["address"] for p in receivers]
    profiles_by_addr = fetch_profiles_by_address(all_addrs)

    def merge_parties(parties: list[dict]) -> list[dict]:
        merged = []
        for p in parties:
            prof = profiles_by_addr.get(p["address"], {})
            entry = {**prof, **p}  # party class_label wins over profile
            # Drop any monetary keys that snuck in
            for k in list(entry.keys()):
                if k.startswith("btc_") or k.startswith("fees"):
                    del entry[k]
            merged.append(entry)
        return merged

    senders_m = merge_parties(senders)
    receivers_m = merge_parties(receivers)

    return {
        "senders": senders_m,
        "receivers": receivers_m,
        "sender_count": sender_count,
        "receiver_count": receiver_count,
        # Back-compat: dict keyed by address (not parallel lists)
        "profiles": {
            "by_address": profiles_by_addr,
            "senders": [profiles_by_addr.get(p["address"], {}) for p in senders_m],
            "receivers": [profiles_by_addr.get(p["address"], {}) for p in receivers_m],
        },
        "warnings": warnings,
    }


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


def _load_subgraph_json(path: Path) -> Optional[dict]:
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def _resolve_story(case_id: str):
    """Resolve a case/story ID, including legacy difficulty aliases."""
    try:
        return get_story_by_id(case_id)
    except KeyError:
        pass

    alias = DIFFICULTY_ALIASES.get(case_id.lower())
    if alias:
        try:
            return get_story_by_id(alias)
        except KeyError:
            pass
    return None


@app.get("/graph/subgraph/{case_id}")
def graph_subgraph(case_id: str):
    """Return a precomputed case-study subgraph as Cytoscape JSON.

    Uses the story YAML cases (peel-chain, fan-out-split, consolidation)
    and traces the appropriate direction for each.
    """
    story = _resolve_story(case_id)
    if story is None:
        # Try loading from docs/story_*_subgraph.json as fallback
        payload = _load_subgraph_json(PROJECT_ROOT / "docs" / f"story_{case_id}_subgraph.json")
        if payload is None:
            payload = _load_subgraph_json(
                PROJECT_ROOT / "data" / "subgraphs" / f"{case_id}_case.json"
            )
        if payload is not None:
            return payload
        available = [s.id for s in load_all_stories()]
        aliases = list(DIFFICULTY_ALIASES.keys())
        raise HTTPException(
            404,
            f"Case '{case_id}' not found. Available stories: {available}; "
            f"legacy aliases: {aliases}",
        )

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
    """Return attributes for a single node.

    Joins DuckDB transactions + tx_classes for full attribute data.
    Returns HOVER_ATTRIBUTES and CLICK_ATTRIBUTES fields.
    """
    G = get_graph()
    if node_id not in G:
        raise HTTPException(404, f"Node {node_id} not found")

    graph_attrs = _node_attr(G, node_id)

    # DuckDB JOIN for interpretable attributes
    db = get_db()
    try:
        row = db.execute("""
            SELECT
                t."txId",
                c.class,
                t."Time step",
                t.total_BTC,
                t.fees,
                t.size,
                t.num_input_addresses,
                t.num_output_addresses,
                t.in_txs_degree,
                t.out_txs_degree,
                t.in_BTC_total,
                t.out_BTC_total
            FROM transactions t
            JOIN tx_classes c ON t."txId" = c."txId"
            WHERE t."txId" = ?
        """, [node_id]).fetchone()
    except Exception:
        row = None

    # Build attributes dict
    if row:
        cls_val = int(row[1]) if row[1] is not None else 3
        attrs = {
            "txId": int(row[0]),
            "class": cls_val,
            "class_label": resolve_class_label(cls_val),
            "class_color": resolve_class_color(cls_val),
            "timestep": int(row[2]) if row[2] is not None else None,
            "total_BTC": float(row[3]) if row[3] is not None else None,
            "fees": float(row[4]) if row[4] is not None else None,
            "size": float(row[5]) if row[5] is not None else None,
            "num_input_addresses": int(row[6]) if row[6] is not None else None,
            "num_output_addresses": int(row[7]) if row[7] is not None else None,
            "in_txs_degree": int(row[8]) if row[8] is not None else None,
            "out_txs_degree": int(row[9]) if row[9] is not None else None,
            "in_BTC_total": float(row[10]) if row[10] is not None else None,
            "out_BTC_total": float(row[11]) if row[11] is not None else None,
        }
    else:
        attrs = graph_attrs or {}
        if attrs and "class" in attrs and "class_label" not in attrs:
            attrs["class_label"] = resolve_class_label(attrs.get("class"))
            attrs["class_color"] = resolve_class_color(attrs.get("class"))

    ts = attrs.get("timestep")
    try:
        ts_int = int(ts) if ts is not None else None
    except (TypeError, ValueError):
        ts_int = None

    out_deg = int(G.out_degree(node_id))
    in_deg = int(G.in_degree(node_id))

    return {
        "node_id": node_id,
        "attributes": attrs,
        "in_degree": in_deg,
        "out_degree": out_deg,
        "degree": int(G.degree(node_id)),
        "is_fan_out": out_deg > 1,
        "is_fan_in": in_deg > 1,
        "accounts": _get_accounts(node_id, db, timestep=ts_int),
    }


@app.get("/graph/node/{node_id}/attributes")
def graph_node_attributes_schema(node_id: int):
    """Return the schema of available hover/click attributes.

    Useful for frontend to know which fields to display.
    """
    G = get_graph()
    if node_id not in G:
        raise HTTPException(404, f"Node {node_id} not found")

    return {
        "node_id": node_id,
        "hover_attributes": HOVER_ATTRIBUTES,
        "click_attributes": CLICK_ATTRIBUTES,
        "display_names": DISPLAY_NAMES,
    }


@app.get("/graph/hybrid")
def graph_hybrid(
    node_id: int = Query(..., description="Seed transaction ID"),
    wallet_depth: int = Query(0, ge=0, le=2, description="0=parties only, 1=include neighbor TXs"),
    max_wallets: int = Query(50, ge=5, le=200, description="Max wallets per side"),
    max_txs: int = Query(100, ge=10, le=500, description="Max additional TX nodes"),
):
    """Hybrid TX↔wallet bipartite subgraph.

    Returns a graph where:
      - Nodes are prefixed: "tx:<id>" for transactions, "w:<addr>" for wallets
      - Edges have role="input" (wallet→tx) or role="output" (tx→wallet)
      - Wallet nodes: class_label only (NO btc_*, NO fees)
      - Transaction nodes: include total_BTC/fees for hover
    """
    G = get_graph()
    if node_id not in G:
        raise HTTPException(404, f"Transaction {node_id} not found in graph")

    db = get_db()
    return build_hybrid_subgraph(
        db=db,
        tx_graph=G,
        seed_tx=node_id,
        wallet_depth=wallet_depth,
        max_wallets=max_wallets,
        max_txs=max_txs,
    )


@app.get("/graph/wallet/{wallet_address}")
def graph_wallet(wallet_address: str):
    """Return wallet profile (non-BTC fields only).

    Returns account profile fields from wallets_features.
    No btc_* or fees_* columns.
    """
    db = get_db()
    try:
        row = db.execute(
            "SELECT class FROM wallet_classes WHERE address = ?",
            [wallet_address],
        ).fetchone()
        cls = int(row[0]) if row and row[0] is not None else 3
        class_label = resolve_class_label(cls)
        class_color = resolve_class_color(cls)
    except Exception:
        cls = 3
        class_label = "unknown"
        class_color = "#6b7280"

    profile_cols = ", ".join(f'w."{f["field"]}"' for f in ACCOUNT_PROFILE_FIELDS)
    try:
        row = db.execute(
            f"SELECT w.address, {profile_cols} "
            f"FROM wallets w WHERE w.address = ?",
            [wallet_address],
        ).fetchone()
    except Exception:
        row = None

    profile: dict = {
        "address": wallet_address,
        "class": cls,
        "class_label": class_label,
        "class_color": class_color,
    }

    if row:
        for i, field_def in enumerate(ACCOUNT_PROFILE_FIELDS):
            raw = row[i + 1]
            fname = field_def["field"]
            if fname.startswith("btc_") or fname.startswith("fees"):
                continue
            if raw is not None:
                try:
                    profile[fname] = float(raw)
                except (TypeError, ValueError):
                    profile[fname] = raw

    return profile


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
    story = _resolve_story(story_id)
    if story is None:
        available = [s.id for s in load_all_stories()]
        raise HTTPException(404, f"Story '{story_id}' not found. Available: {available}")
    return story.to_dict()
