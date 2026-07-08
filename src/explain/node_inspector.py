#!/usr/bin/env python3
"""Unified node inspection for BitTrace explainability.

Combines SHAP values, RF risk scores, and k-hop subgraph extraction
into a single dict suitable for API/frontend consumption.

Usage:
    from src.explain.node_inspector import get_node_explanation

    # Build graph and train model first
    from src.graph.builders import build_tx_graph
    from src.models.baseline import train_rf_transactions

    G = build_tx_graph()
    rf = train_rf_transactions()

    # Get explanation for a specific transaction
    explanation = get_node_explanation(
        G=G,
        model_results=rf,
        node_id=272145560,
        k=2,
    )
    # explanation is a dict ready for JSON serialization
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd

import networkx as nx

from src.data.loaders import DATA_DIR
from src.graph.export import CLASS_COLORS, CLASS_LABELS
from src.explain.subgraph_explainer import extract_k_hop_subgraph

logger = logging.getLogger(__name__)


@dataclass
class NodeExplanation:
    """Complete explanation for a single transaction or wallet node."""

    # Identity
    node_id: int
    node_type: str  # "transaction" or "address"

    # Classification
    class_label: str
    class_value: int
    timestep: Optional[int]

    # Risk
    risk_score: Optional[float]
    predicted_class: Optional[str]

    # Feature importance (SHAP-based)
    shap_top5: List[Dict[str, Any]] = field(default_factory=list)

    # Node features
    features: Dict[str, float] = field(default_factory=dict)

    # Subgraph context
    subgraph_node_count: int = 0
    subgraph_edge_count: int = 0
    subgraph_path: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a JSON-friendly dict."""
        return asdict(self)


def _get_tx_row(tx_id: int, df: pd.DataFrame) -> Optional[pd.Series]:
    """Look up a transaction row by txId."""
    mask = df["txId"] == tx_id
    if mask.sum() == 0:
        return None
    return df[mask].iloc[0]


def _predict_single(
    model,
    feature_values: np.ndarray,
    feature_names: List[str],
) -> tuple[Optional[float], Optional[str]]:
    """Get risk score and predicted class for a single sample."""
    try:
        proba = model.predict_proba(feature_values.reshape(1, -1))[0]
        risk_score = float(proba[1])  # P(illicit)
        pred = int(model.predict(feature_values.reshape(1, -1))[0])
        pred_label = "illicit" if pred == 1 else "licit"
        return risk_score, pred_label
    except Exception as e:
        logger.warning("Prediction failed for node: %s", e)
        return None, None


def _get_shap_top_features(
    model,
    feature_values: np.ndarray,
    feature_names: List[str],
    top_n: int = 5,
) -> List[Dict[str, Any]]:
    """Compute per-node SHAP values and return top-N features."""
    try:
        import shap
    except ImportError:
        logger.warning("shap not installed — returning empty feature attribution")
        return []

    try:
        explainer = shap.TreeExplainer(model)
        sample_2d = np.atleast_2d(feature_values)
        shap_vals = explainer.shap_values(sample_2d)

        # For binary: shap_vals is [class_0_vals, class_1_vals] or 3D
        if isinstance(shap_vals, list):
            shap_vals = shap_vals[1]  # illicit class
        elif shap_vals.ndim == 3:
            shap_vals = shap_vals[:, :, 1]  # illicit class

        # Ensure 1D
        shap_arr = np.asarray(shap_vals).flatten()
        vals_arr = np.asarray(feature_values).flatten()

        paired = []
        for i, fname in enumerate(feature_names):
            paired.append(
                {
                    "feature": fname,
                    "shap": float(shap_arr[i]),
                    "value": float(vals_arr[i]),
                }
            )

        # Sort by absolute SHAP contribution
        paired.sort(key=lambda x: abs(x["shap"]), reverse=True)
        return paired[:top_n]

    except Exception as e:
        logger.warning("SHAP computation failed: %s", e)
        return []


def get_node_explanation(
    G: nx.DiGraph,
    model_results: Any,
    node_id: int,
    k: int = 2,
    node_type: str = "transaction",
    top_n: int = 5,
) -> NodeExplanation:
    """Build a complete explanation dict for a single node.

    This is the main entry point used by the API / frontend. It combines:
    1. Node attributes from the graph (class, timestep)
    2. RF risk score and prediction
    3. SHAP top-N feature attribution
    4. k-hop subgraph extraction

    Parameters
    ----------
    G : nx.DiGraph
        The tx→tx (or addr→addr) graph with node attributes.
    model_results : ModelResults
        Output from train_rf_transactions() or train_rf_actors().
    node_id : int
        The transaction (or wallet) ID to explain.
    k : int
        Hop depth for subgraph extraction.
    node_type : str
        Either "transaction" or "address".
    top_n : int
        Number of top SHAP features to include.

    Returns
    -------
    NodeExplanation — dataclass with all explanation fields.
    """
    # 1. Node attributes from graph
    if node_id not in G:
        raise ValueError(f"Node {node_id} not in graph")

    attrs = G.nodes[node_id]
    cls = attrs.get("class", 3)
    timestep = attrs.get("timestep", None)
    class_label = CLASS_LABELS.get(cls, "unknown")

    # 2. Load feature data and predict
    model = model_results.model
    feature_names = model_results.feature_names

    if node_type == "transaction":
        df = pd.read_csv(DATA_DIR / "txs_features.csv")
        classes_df = pd.read_csv(DATA_DIR / "txs_classes.csv")
        df = df.merge(classes_df, on="txId", how="left")
        row = _get_tx_row(node_id, df)
        if row is None:
            logger.warning("Transaction %d not in feature CSV — skipping prediction", node_id)
            return NodeExplanation(
                node_id=node_id,
                node_type=node_type,
                class_label=class_label,
                class_value=cls,
                timestep=timestep,
                risk_score=None,
                predicted_class=None,
            )

        # Preprocess single row (same pipeline as baseline)
        from src.models.baseline import preprocess_transactions

        row_df = pd.DataFrame([row])
        processed = preprocess_transactions(row_df)
        if processed.empty:
            logger.warning("Row dropped during preprocessing (NaN or unknown class)")
            return NodeExplanation(
                node_id=node_id,
                node_type=node_type,
                class_label=class_label,
                class_value=cls,
                timestep=timestep,
                risk_score=None,
                predicted_class=None,
            )

        feat_cols = [c for c in processed.columns if c not in ("txId", "class", "Time step")]
        feature_values = processed[feat_cols].values

        # Reorder to match model's training columns
        # The model was trained with feature_names ordering; find matching columns
        common_cols = [c for c in feature_names if c in feat_cols]
        if set(common_cols) != set(feature_names):
            logger.warning(
                "Feature mismatch: model has %d, row has %d common out of %d",
                len(feature_names), len(common_cols), len(feat_cols),
            )
        ordered_cols = [c for c in feature_names if c in feat_cols]
        # Fill missing features with 0
        feat_dict = dict(zip(feat_cols, feature_values[0]))
        feature_vector = np.array([feat_dict.get(c, 0.0) for c in feature_names])
    else:
        # Address node — simpler lookup
        wallets_df = pd.read_csv(DATA_DIR / "wallets_features_classes_combined.csv")
        row = wallets_df[wallets_df.iloc[:, 0] == node_id]
        if row.empty:
            return NodeExplanation(
                node_id=node_id,
                node_type=node_type,
                class_label=class_label,
                class_value=cls,
                timestep=None,
                risk_score=None,
                predicted_class=None,
            )
        from src.models.baseline import preprocess_actors

        row_df = pd.DataFrame([row.iloc[0]])
        processed = preprocess_actors(row_df)
        if processed.empty:
            return NodeExplanation(
                node_id=node_id,
                node_type=node_type,
                class_label=class_label,
                class_value=cls,
                timestep=None,
                risk_score=None,
                predicted_class=None,
            )
        feat_cols = [c for c in processed.columns if c not in ("address", "class")]
        feature_values = processed[feat_cols].values[0]
        feat_dict = dict(zip(feat_cols, feature_values))
        feature_vector = np.array([feat_dict.get(c, 0.0) for c in feature_names])

    # 3. Predict
    risk_score, predicted_class = _predict_single(model, feature_vector, feature_names)

    # 4. SHAP attribution
    shap_top5 = _get_shap_top_features(model, feature_vector, feature_names, top_n=top_n)

    # 5. Node feature values (top by SHAP)
    feature_values_dict = {}
    if node_type == "transaction":
        for item in shap_top5:
            feature_values_dict[item["feature"]] = round(item["value"], 6)

    # 6. Subgraph extraction
    try:
        subgraph = extract_k_hop_subgraph(G, node_id, k=k, max_nodes=200)
        subgraph_path_json = str(subgraph.get("cytoscape", {}))
        sg_node_count = subgraph["stats"]["node_count"]
        sg_edge_count = subgraph["stats"]["edge_count"]
    except Exception as e:
        logger.warning("Subgraph extraction failed for %d: %s", node_id, e)
        sg_node_count = 0
        sg_edge_count = 0
        subgraph_path_json = ""

    return NodeExplanation(
        node_id=node_id,
        node_type=node_type,
        class_label=class_label,
        class_value=cls,
        timestep=timestep,
        risk_score=round(risk_score, 4) if risk_score is not None else None,
        predicted_class=predicted_class,
        shap_top5=shap_top5,
        features=feature_values_dict,
        subgraph_node_count=sg_node_count,
        subgraph_edge_count=sg_edge_count,
        subgraph_path=subgraph_path_json,
    )
