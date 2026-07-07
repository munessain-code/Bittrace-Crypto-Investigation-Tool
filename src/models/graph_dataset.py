"""PyG dataset construction from BitTrace DuckDB data.

Converts the tx-tx NetworkX graph (or DuckDB tables) into
a PyTorch Geometric Data object with node features, edge
indices, and binary labels (licit=0, illicit=1).

Unknown-class nodes are handled via two modes:
  - 'exclude': drop unknown nodes entirely (transductive)
  - 'mask': keep unknown nodes in the graph but mask them from loss

Usage:
    from src.models.graph_dataset import build_graph_dataset

    # Transductive: only labeled nodes in feature matrix
    data = build_graph_dataset(mode='exclude')
    # -> data.x shape: (N_labeled, 134), data.y shape: (N_labeled,)

    # Full graph with masked unknowns
    data = build_graph_dataset(mode='mask')
    # -> data.x includes unknown nodes, data.mask marks labeled ones
"""

from __future__ import annotations

import numpy as np
import torch
from torch_geometric.data import Data

from src.data.loaders import get_duckdb_connection
from src.graph.builders import build_tx_graph, build_tx_graph_sample


def _reindex_nodes(nodes: list[int]) -> dict[int, int]:
    """Map arbitrary node IDs to contiguous indices 0..N-1."""
    return {old: new for new, old in enumerate(nodes)}


def _extract_features(
    conn, node_ids: list[int]
) -> np.ndarray:
    """Pull the 134 feature columns + edges from DuckDB for the given nodes.

    Returns a (len(node_ids), 134) numpy array in the same order as node_ids.
    """
    import duckdb

    # Build a set lookup query
    placeholders = ", ".join(f"'{nid}'" for nid in node_ids)
    query = f"""
        SELECT txId,
            {", ".join([
                f'Local_feature_{i}' for i in range(1, 73)
            ] + [
                f'Aggregate_feature_{i}' for i in range(1, 38)
            ])}
        FROM transactions
        WHERE txId IN ({placeholders})
    """
    df = conn.execute(query).fetchdf()
    feature_cols = [c for c in df.columns if c != "txId"]

    # Preserve input order
    idx_map = {tid: i for i, tid in enumerate(node_ids)}
    df = df.set_index("txId").loc[node_ids].fillna(0)

    return df[feature_cols].values.astype(np.float32)


def _extract_labels(
    conn, node_ids: list[int]
) -> np.ndarray:
    """Return binary labels: 0=licit, 1=illicit.

    Unknown nodes are assigned -1.
    """
    placeholders = ", ".join(f"'{nid}'" for nid in node_ids)
    query = f"""
        SELECT txId, class FROM tx_classes
        WHERE txId IN ({placeholders})
    """
    df = conn.execute(query).fetchdf()

    labels = np.full(len(node_ids), -1, dtype=np.int64)
    for tid, cls in zip(df["txId"], df["class"]):
        idx = node_ids.index(tid)
        labels[idx] = int(cls)  # 1=illicit, 2=licit, 3=unknown

    # Remap: 1 -> 1 (illicit), 2 -> 0 (licit), 3 -> -1 (unknown)
    labels[labels == 2] = 0
    labels[labels == 3] = -1
    return labels


def build_graph_dataset(
    mode: str = "exclude",
    sample_pct: float | None = None,
) -> Data:
    """Build a PyG Data object from the tx-tx graph.

    Parameters
    ----------
    mode : str
        - 'exclude': drop unknown-class nodes; binary labels only.
        - 'mask': keep unknown nodes in adjacency but mask from training loss.
    sample_pct : float, optional
        If set, use a reservoir sample of the graph (e.g. 0.1 for 10%).

    Returns
    -------
    Data
        PyTorch Geometric Data object with:
        - x : (N, 134) node features
        - edge_index : (2, E) edge indices
        - y : (N,) labels (-1 for unknown)
        - mask : (N,) boolean True for labeled nodes (only when mode='mask')
    """
    # Build the graph
    if sample_pct:
        G = build_tx_graph_sample(fraction=sample_pct)
    else:
        G = build_tx_graph()

    nodes = list(G.nodes())
    edge_list = list(G.edges())

    # Get DuckDB connection for features & labels
    conn = get_duckdb_connection()
    try:
        features = _extract_features(conn, nodes)
        labels = _extract_labels(conn, nodes)
    finally:
        conn.close()

    # Build label mask
    labeled_mask = labels != -1  # True for licit/illicit

    if mode == "exclude":
        # Keep only labeled nodes
        keep = labeled_mask
        keep_nodes = [nodes[i] for i in range(len(nodes)) if keep[i]]
        reindex = _reindex_nodes(keep_nodes)

        x = features[keep]
        y = labels[keep]
        mask = None

        # Remap edges to new indices
        new_edges = [
            (reindex[src], reindex[dst])
            for src, dst in edge_list
            if src in reindex and dst in reindex
        ]
    else:
        # mode == 'mask' — keep all nodes
        reindex = _reindex_nodes(nodes)
        x = features
        y = labels
        mask = labeled_mask

        new_edges = [(reindex[src], reindex[dst]) for src, dst in edge_list]

    # Build edge_index tensor
    edge_index = torch.tensor(new_edges, dtype=torch.long).t().contiguous()

    # Remove self-loops
    mask_tensor = edge_index[0] != edge_index[1]
    edge_index = edge_index[:, mask_tensor]

    data = Data(
        x=torch.tensor(x, dtype=torch.float),
        edge_index=edge_index,
        y=torch.tensor(y, dtype=torch.long),
    )

    if mask is not None:
        data.mask = torch.tensor(mask, dtype=torch.bool)

    return data


def build_labeled_dataset(sample_pct: float | None = None) -> Data:
    """Convenience: build dataset excluding unknown nodes (binary classification)."""
    return build_graph_dataset(mode="exclude", sample_pct=sample_pct)
