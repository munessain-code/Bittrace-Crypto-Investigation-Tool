"""BitTrace explainability — SHAP values, subgraph extraction, node inspection."""

from src.explain.node_inspector import get_node_explanation, NodeExplanation
from src.explain.shap_explainer import (
    ShapResult,
    compute_shap_transactions,
    compute_shap_actors,
    _extract_class_values,
)
from src.explain.subgraph_explainer import extract_k_hop_subgraph, get_subgraph_path
from src.explain.importance import (
    get_feature_importance,
    get_permutation_importance,
    get_shap_values,
    plot_top_features,
    plot_shap_summary,
)

__all__ = [
    "get_node_explanation",
    "NodeExplanation",
    "compute_shap_transactions",
    "compute_shap_actors",
    "ShapResult",
    "extract_k_hop_subgraph",
    "get_subgraph_path",
    "get_feature_importance",
    "get_permutation_importance",
    "get_shap_values",
    "plot_top_features",
    "plot_shap_summary",
]
