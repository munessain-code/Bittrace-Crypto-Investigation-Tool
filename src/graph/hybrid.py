"""Build hybrid TX↔Wallet bipartite subgraphs.

Mental model:
  [prev TXs] ← wallets ← seed TX → wallets → [next TXs]

Node IDs are prefixed to avoid collisions:
  - Transactions: "tx:<txId>"
  - Wallets:      "w:<address>"

Edges encode direction:
  - wallet → tx  (AddrTx: input_address → txId, role="input")
  - tx → wallet  (TxAddr: txId → output_address, role="output")
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Set, Tuple

import duckdb
import networkx as nx
import pandas as pd

from src.data.attribute_catalog import resolve_class_label, resolve_class_color
from src.data.loaders import get_duckdb_connection

logger = logging.getLogger(__name__)

# Wallet ID prefix for graph nodes
WALLET_PREFIX = "w:"
TX_PREFIX = "tx:"


def _tx_id(txid: Any) -> str:
    """Return prefixed transaction node ID."""
    return f"{TX_PREFIX}{int(txid)}"


def _w_id(address: str) -> str:
    """Return prefixed wallet node ID."""
    return f"{WALLET_PREFIX}{address}"


def build_hybrid_subgraph(
    db: Optional[duckdb.DuckDBPyConnection] = None,
    tx_graph: Optional[nx.DiGraph] = None,
    seed_tx: int = 10000476,
    wallet_depth: int = 0,
    max_wallets: int = 50,
    max_txs: int = 100,
) -> Dict:
    """Build a hybrid TX↔wallet bipartite subgraph around a seed transaction.

    Args:
        db: DuckDB connection. Auto-opened if None.
        tx_graph: Existing tx-tx DiGraph for neighbor resolution (optional).
        seed_tx: Seed transaction ID.
        wallet_depth: 0 = only direct parties of seed TX;
                      1 = include neighbor TXs those wallets participate in.
        max_wallets: Max wallets per side (sender/receiver).
        max_txs: Max additional TX nodes beyond the seed.

    Returns:
        Dict with nodes, edges, seed_tx, and meta keys.
    """
    if db is None:
        db = get_duckdb_connection()
        close_db = True
    else:
        close_db = False

    nodes: Dict[str, Dict] = {}
    edges: List[Dict] = []

    # --- Seed TX node ---
    tx_attrs = _fetch_tx_attrs(db, seed_tx)
    tx_attrs["kind"] = "transaction"
    seed_key = _tx_id(seed_tx)
    nodes[seed_key] = {"id": seed_key, **tx_attrs}

    # --- Fetch sender wallets (AddrTx: input_address → txId) ---
    senders = _fetch_wallets_for_tx(db, "addr_tx_edges", "input_address", seed_tx, max_wallets)
    # --- Fetch receiver wallets (TxAddr: txId → output_address) ---
    receivers = _fetch_wallets_for_tx(db, "tx_addr_edges", "output_address", seed_tx, max_wallets)

    total_senders = _count_wallets_for_tx(db, "addr_tx_edges", seed_tx)
    total_receivers = _count_wallets_for_tx(db, "tx_addr_edges", seed_tx)

    # Add sender wallet nodes and edges
    for addr, cls in senders:
        w_key = _w_id(addr)
        if w_key not in nodes:
            nodes[w_key] = {
                "id": w_key,
                "kind": "wallet",
                "address": addr,
                "class_label": resolve_class_label(cls),
                "class_color": resolve_class_color(cls),
            }
        edges.append({
            "source": w_key,
            "target": seed_key,
            "role": "input",
        })

    # Add receiver wallet nodes and edges
    for addr, cls in receivers:
        w_key = _w_id(addr)
        if w_key not in nodes:
            nodes[w_key] = {
                "id": w_key,
                "kind": "wallet",
                "address": addr,
                "class_label": resolve_class_label(cls),
                "class_color": resolve_class_color(cls),
            }
        edges.append({
            "source": seed_key,
            "target": w_key,
            "role": "output",
        })

    # --- wallet_depth=1: expand to neighbor TXs ---
    if wallet_depth >= 1:
        all_wallets: Set[str] = {addr for addr, _ in senders} | {addr for addr, _ in receivers}
        neighbor_txs = _fetch_neighbor_txs(db, all_wallets, seed_tx, max_txs)
        for txid, addr, direction in neighbor_txs:
            tx_key = _tx_id(txid)
            if tx_key not in nodes:
                n_attrs = _fetch_tx_attrs(db, txid)
                n_attrs["kind"] = "transaction"
                nodes[tx_key] = {"id": tx_key, **n_attrs}
            w_key = _w_id(addr)
            if w_key not in nodes:
                cls = _fetch_wallet_class(db, addr)
                nodes[w_key] = {
                    "id": w_key,
                    "kind": "wallet",
                    "address": addr,
                    "class_label": resolve_class_label(cls),
                    "class_color": resolve_class_color(cls),
                }
            if direction == "input":
                edges.append({
                    "source": w_key,
                    "target": tx_key,
                    "role": "input",
                })
            else:
                edges.append({
                    "source": tx_key,
                    "target": w_key,
                    "role": "output",
                })

    truncated = (len(senders) >= max_wallets or len(receivers) >= max_wallets)

    if close_db:
        db.close()

    return {
        "seed_tx": seed_tx,
        "nodes": [{"data": n} for n in nodes.values()],
        "edges": [{"data": {"id": f"e_{e['source']}_{e['target']}", **e}} for e in edges],
        "meta": {
            "sender_count": total_senders,
            "receiver_count": total_receivers,
            "wallet_count": len([n for n in nodes.values() if n["kind"] == "wallet"]),
            "tx_count": len([n for n in nodes.values() if n["kind"] == "transaction"]),
            "truncated": truncated,
        },
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fetch_tx_attrs(db: duckdb.DuckDBPyConnection, txid: int) -> Dict:
    """Fetch transaction attributes from DuckDB."""
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
                t.num_output_addresses
            FROM transactions t
            JOIN tx_classes c ON t."txId" = c."txId"
            WHERE t."txId" = ?
        """, [txid]).fetchone()

        if row:
            cls = int(row[1]) if row[1] is not None else 3
            return {
                "txId": int(row[0]),
                "class": cls,
                "class_label": resolve_class_label(cls),
                "class_color": resolve_class_color(cls),
                "timestep": int(row[2]) if row[2] is not None else None,
                "total_BTC": float(row[3]) if row[3] is not None else None,
                "fees": float(row[4]) if row[4] is not None else None,
                "size": float(row[5]) if row[5] is not None else None,
                "num_input_addresses": int(row[6]) if row[6] is not None else None,
                "num_output_addresses": int(row[7]) if row[7] is not None else None,
            }
    except Exception as e:
        logger.warning("Failed to fetch tx attrs for %s: %s", txid, e)

    return {
        "txId": txid,
        "class": 3,
        "class_label": "unknown",
        "class_color": "#6b7280",
        "timestep": None,
        "total_BTC": None,
        "fees": None,
        "size": None,
        "num_input_addresses": None,
        "num_output_addresses": None,
    }


def _fetch_wallets_for_tx(
    db: duckdb.DuckDBPyConnection,
    table: str,
    addr_col: str,
    txid: int,
    limit: int,
) -> List[Tuple[str, int]]:
    """Fetch wallets for a TX, prioritizing illicit."""
    try:
        rows = db.execute(
            f"""
            SELECT a."{addr_col}", COALESCE(c.class, 3) AS class
            FROM {table} a
            LEFT JOIN wallet_classes c ON a."{addr_col}" = c.address
            WHERE a."txId" = ?
            ORDER BY c.class, a."{addr_col}"
            LIMIT ?
            """,
            [txid, limit],
        ).fetchall()
        return [(addr, int(cls) if cls is not None else 3) for addr, cls in rows]
    except Exception as e:
        logger.warning("fetch_wallets failed table=%s tx=%s: %s", table, txid, e)
        return []


def _count_wallets_for_tx(
    db: duckdb.DuckDBPyConnection,
    table: str,
    txid: int,
) -> int:
    """Count total wallets for a TX."""
    try:
        row = db.execute(
            f'SELECT COUNT(*) FROM {table} WHERE "txId" = ?',
            [txid],
        ).fetchone()
        return int(row[0]) if row else 0
    except Exception:
        return 0


def _fetch_wallet_class(db: duckdb.DuckDBPyConnection, address: str) -> int:
    """Fetch wallet class."""
    try:
        row = db.execute(
            "SELECT COALESCE(class, 3) FROM wallet_classes WHERE address = ?",
            [address],
        ).fetchone()
        return int(row[0]) if row else 3
    except Exception:
        return 3


def _fetch_neighbor_txs(
    db: duckdb.DuckDBPyConnection,
    wallet_addresses: Set[str],
    exclude_tx: int,
    max_txs: int,
) -> List[Tuple[int, str, str]]:
    """Fetch neighboring TXs for a set of wallets, excluding the seed.

    Returns list of (txid, wallet_address, direction) where direction is
    'input' (wallet→tx) or 'output' (tx→wallet).
    """
    if not wallet_addresses:
        return []

    placeholders = ",".join(["?"] * len(wallet_addresses))
    try:
        # Input side: wallet → tx (AddrTx)
        input_rows = db.execute(
            f"""
            SELECT DISTINCT "txId", "input_address"
            FROM addr_tx_edges
            WHERE "input_address" IN ({placeholders})
              AND "txId" != ?
            ORDER BY "txId"
            LIMIT ?
            """,
            list(wallet_addresses) + [exclude_tx, max_txs // 2],
        ).fetchall()

        # Output side: tx → wallet (TxAddr)
        output_rows = db.execute(
            f"""
            SELECT DISTINCT "txId", "output_address"
            FROM tx_addr_edges
            WHERE "output_address" IN ({placeholders})
              AND "txId" != ?
            ORDER BY "txId"
            LIMIT ?
            """,
            list(wallet_addresses) + [exclude_tx, max_txs // 2],
        ).fetchall()

        result = []
        seen_txs: Set[int] = set()
        for txid, addr in input_rows:
            txid_int = int(txid)
            if txid_int not in seen_txs and len(seen_txs) < max_txs:
                result.append((txid_int, addr, "input"))
                seen_txs.add(txid_int)
        for txid, addr in output_rows:
            txid_int = int(txid)
            if txid_int not in seen_txs and len(seen_txs) < max_txs:
                result.append((txid_int, addr, "output"))
                seen_txs.add(txid_int)

        return result
    except Exception as e:
        logger.warning("fetch_neighbor_txs failed: %s", e)
        return []
