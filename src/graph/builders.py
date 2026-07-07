"""Build NetworkX graphs from Elliptic++ data via DuckDB."""

from typing import Optional

import duckdb
import networkx as nx
import pandas as pd

from src.data.loaders import get_duckdb_connection


def build_tx_graph(db: Optional[duckdb.DuckDBPyConnection] = None) -> nx.DiGraph:
    """Build a directed tx-to-tx graph from tx_edges with node attributes.

    Node attributes attached:
      - class: 1=illicit, 2=licit, 3=unknown
      - timestep: from transactions."Time step"
    """
    if db is None:
        db = get_duckdb_connection()

    edges_df = db.execute("SELECT txId1, txId2 FROM tx_edges").fetchdf()
    G = nx.DiGraph()
    G.add_edges_from(zip(edges_df["txId1"], edges_df["txId2"]))

    attrs = db.execute(
        'SELECT t.txId, t.class, tr."Time step" AS timestep '
        "FROM tx_classes t "
        "LEFT JOIN transactions tr ON t.txId = tr.txId"
    ).fetchdf()

    for _, row in attrs.iterrows():
        nid = int(row["txId"])
        attr = {}
        if pd.notna(row.get("class")):
            attr["class"] = int(row["class"])
        if pd.notna(row.get("timestep")):
            attr["timestep"] = int(row["timestep"])
        G.nodes[nid].update(attr)

    if db is None:
        db.close()
    return G


def build_tx_graph_sample(
    db: Optional[duckdb.DuckDBPyConnection] = None,
    fraction: float = 0.01,
) -> nx.DiGraph:
    """Same as build_tx_graph but samples *fraction* of edges via DuckDB TABLESAMPLE."""
    if db is None:
        db = get_duckdb_connection()

    pct = fraction * 100
    # Use reservoir sampling with explicit percentage literal
    edges_df = db.execute(
        f"SELECT * FROM tx_edges USING SAMPLE reservoir({pct}%)"
    ).fetchdf()
    G = nx.DiGraph()
    G.add_edges_from(zip(edges_df["txId1"], edges_df["txId2"]))

    # Collect unique txIds from sampled edges
    txids = set(edges_df["txId1"]).union(set(edges_df["txId2"]))
    placeholder = ",".join("?" for _ in txids)
    attrs = db.execute(
        f'SELECT t.txId, t.class, tr."Time step" AS timestep '
        f"FROM tx_classes t LEFT JOIN transactions tr ON t.txId = tr.txId "
        f"WHERE t.txId IN ({placeholder})",
        list(txids),
    ).fetchdf()

    for _, row in attrs.iterrows():
        nid = int(row["txId"])
        attr = {}
        if pd.notna(row.get("class")):
            attr["class"] = int(row["class"])
        if pd.notna(row.get("timestep")):
            attr["timestep"] = int(row["timestep"])
        G.nodes[nid].update(attr)

    if db is None:
        db.close()
    return G


def build_addr_graph(
    db: Optional[duckdb.DuckDBPyConnection] = None,
) -> nx.Graph:
    """Build an undirected address-to-address graph with class labels."""
    if db is None:
        db = get_duckdb_connection()

    edges_df = db.execute("SELECT input_address, output_address FROM addr_addr_edges").fetchdf()
    G = nx.Graph()
    G.add_edges_from(zip(edges_df["input_address"], edges_df["output_address"]))

    classes_df = db.execute("SELECT address, class FROM wallet_classes").fetchdf()
    for _, row in classes_df.iterrows():
        addr = row["address"]
        if addr in G and pd.notna(row.get("class")):
            G.nodes[addr]["class"] = int(row["class"])

    if db is None:
        db.close()
    return G


def build_bipartite(
    db: Optional[duckdb.DuckDBPyConnection] = None,
) -> nx.Graph:
    """Build addr-tx-addr bipartite graph.

    Nodes have a `node_type` attribute: 'address' or 'transaction'.
    """
    if db is None:
        db = get_duckdb_connection()

    G = nx.Graph()

    addr_tx = db.execute("SELECT input_address, txId FROM addr_tx_edges").fetchdf()
    for _, r in addr_tx.iterrows():
        a, t = r["input_address"], int(r["txId"])
        if not G.has_node(a):
            G.add_node(a, node_type="address")
        if not G.has_node(t):
            G.add_node(t, node_type="transaction")
        G.add_edge(a, t)

    tx_addr = db.execute("SELECT txId, output_address FROM tx_addr_edges").fetchdf()
    for _, r in tx_addr.iterrows():
        t, a = int(r["txId"]), r["output_address"]
        if not G.has_node(a):
            G.add_node(a, node_type="address")
        if not G.has_node(t):
            G.add_node(t, node_type="transaction")
        G.add_edge(t, a)

    if db is None:
        db.close()
    return G
