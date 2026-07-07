"""Export NetworkX subgraphs to Cytoscape.js-compatible JSON.

Provides subgraph serialization for the frontend explorer.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import networkx as nx

# Class-to-color mapping for visualization
CLASS_COLORS = {
    1: "#ef4444",  # illicit — red
    2: "#22c55e",  # licit — green
    3: "#6b7280",  # unknown — gray
}

CLASS_LABELS = {
    1: "illicit",
    2: "licit",
    3: "unknown",
}


def _node_attrs(node_id: Any, G: nx.Graph, attrs: Dict) -> Dict:
    """Extract node attributes for Cytoscape output."""
    cls = attrs.get("class", 3)
    timestep = attrs.get("timestep", None)

    return {
        "data": {
            "id": str(node_id),
            "label": str(node_id),
            "class": cls,
            "class_label": CLASS_LABELS.get(cls, "unknown"),
            "color": CLASS_COLORS.get(cls, CLASS_COLORS[3]),
            "timestep": timestep,
        }
    }


def subgraph_to_cytoscape(
    G: nx.Graph,
    subgraph_nodes: Optional[List] = None,
    subgraph_edges: Optional[List] = None,
) -> Dict:
    """Convert a NetworkX subgraph to Cytoscape.js-compatible JSON.

    If *subgraph_nodes* / *subgraph_edges* are provided, only those
    are included. Otherwise the entire graph *G* is exported.

    Returns:
        {"nodes": [...], "edges": [...]}
    """
    if subgraph_nodes is not None:
        nodes_to_export = subgraph_nodes
        edges_to_export = subgraph_edges or []
    else:
        nodes_to_export = list(G.nodes())
        edges_to_export = list(G.edges())

    cy_nodes = []
    for nid in nodes_to_export:
        attrs = G.nodes.get(nid, {})
        cy_nodes.append(_node_attrs(nid, G, attrs))

    cy_edges = []
    for edge in edges_to_export:
        src, dst = edge[0], edge[1]
        edge_attrs = G.get_edge_data(src, dst, {}) if isinstance(G, nx.DiGraph) or G.has_edge(src, dst) else {}
        cy_edges.append({
            "data": {
                "id": f"e_{src}_{dst}",
                "source": str(src),
                "target": str(dst),
                **(edge_attrs or {}),
            }
        })

    return {
        "nodes": cy_nodes,
        "edges": cy_edges,
    }


def subgraph_to_json_file(
    subgraph: Dict,
    path: str,
    pretty: bool = True,
) -> str:
    """Write a Cytoscape subgraph dict to a JSON file.

    Args:
        subgraph: Output from ``subgraph_to_cytoscape()`` or similar.
        path: File path (created if missing).
        pretty: If True, use indented JSON.

    Returns:
        Absolute path to the written file.
    """
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)

    indent = 2 if pretty else None
    out.write_text(json.dumps(subgraph, indent=indent, default=str))

    return str(out.resolve())


def trace_to_cytoscape(
    G: nx.Graph,
    trace_result: Dict,
) -> Dict:
    """Convert a ``trace_downstream`` / ``trace_upstream`` result to Cytoscape JSON.

    Args:
        G: The full graph (for node attributes).
        trace_result: Output from ``trace_downstream()`` or ``trace_upstream()``.

    Returns:
        Cytoscape-compatible dict with hop annotations.
    """
    nodes = trace_result.get("nodes", [])
    edges = trace_result.get("edges", [])
    hops = trace_result.get("hops", {})

    cy_nodes = []
    for nid in nodes:
        attrs = G.nodes.get(nid, {})
        cls = attrs.get("class", 3)
        node_data = {
            "id": str(nid),
            "label": str(nid),
            "class": cls,
            "class_label": CLASS_LABELS.get(cls, "unknown"),
            "color": CLASS_COLORS.get(cls, CLASS_COLORS[3]),
            "hop": hops.get(nid, 0),
        }
        ts = attrs.get("timestep")
        if ts is not None:
            node_data["timestep"] = ts
        cy_nodes.append({"data": node_data})

    cy_edges = []
    for src, dst in edges:
        cy_edges.append({
            "data": {
                "id": f"e_{src}_{dst}",
                "source": str(src),
                "target": str(dst),
            }
        })

    return {"nodes": cy_nodes, "edges": cy_edges}
