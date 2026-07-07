"""Feature importance extraction — permutation importance + SHAP.

Provides:
- get_feature_importance: RF built-in feature importances
- get_permutation_importance: sklearn permutation importance
- get_shap_values: SHAP TreeExplainer on RF
- plot_top_features: horizontal bar chart of top-N features
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.inspection import permutation_importance

logger = logging.getLogger(__name__)

RESULTS_DIR = Path(__file__).resolve().parent.parent.parent / "docs"


def get_feature_importance(
    model: RandomForestClassifier,
    feature_names: list[str],
) -> pd.DataFrame:
    """Return RF built-in feature importances as a sorted DataFrame."""
    importances = model.feature_importances_
    idx = np.argsort(importances)[::-1]

    df = pd.DataFrame(
        {
            "feature": [feature_names[i] for i in idx],
            "importance": importances[idx],
        }
    )
    return df


def get_permutation_importance(
    model: RandomForestClassifier,
    X_test: np.ndarray,
    y_test: np.ndarray,
    feature_names: list[str],
    n_repeats: int = 10,
    random_state: int = 42,
) -> pd.DataFrame:
    """Return permutation importance (sklearn) as a sorted DataFrame."""
    logger.info("Computing permutation importance (n_repeats=%d)...", n_repeats)
    perm_imp = permutation_importance(
        model,
        X_test,
        y_test,
        n_repeats=n_repeats,
        random_state=random_state,
        n_jobs=-1,
    )

    importances_mean = perm_imp.importances_mean
    importances_std = perm_imp.importances_std
    idx = np.argsort(importances_mean)[::-1]

    df = pd.DataFrame(
        {
            "feature": [feature_names[i] for i in idx],
            "importance_mean": importances_mean[idx],
            "importance_std": importances_std[idx],
        }
    )
    return df


def get_shap_values(
    model: RandomForestClassifier,
    X_test: np.ndarray,
    feature_names: list[str],
    max_samples: int = 2000,
    random_state: int = 42,
) -> tuple[object, np.ndarray, np.ndarray]:
    """Compute SHAP values using TreeExplainer.

    Returns:
        shap_explainer: shap.Explainer object
        shap_values: SHAP value array
        X_sample: the subset of X_test used for SHAP
    """
    try:
        import shap
    except ImportError:
        logger.warning("shap not installed — skipping SHAP values")
        return None, None, None

    logger.info("Computing SHAP values (max_samples=%d)...", max_samples)
    rng = np.random.RandomState(random_state)
    indices = rng.choice(X_test.shape[0], size=min(max_samples, X_test.shape[0]), replace=False)
    X_sample = X_test[indices]

    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(X_sample)

    return explainer, shap_values, X_sample


def plot_top_features(
    importance_df: pd.DataFrame,
    top_n: int = 20,
    title: str = "Top Feature Importances",
    output_path: Optional[str] = None,
    value_col: str = "importance",
) -> str:
    """Plot top-N features as a horizontal bar chart.

    Returns:
        Path to the saved figure.
    """
    df = importance_df.head(top_n).iloc[::-1]  # reverse for matplotlib (top at top)

    fig, ax = plt.subplots(figsize=(10, max(5, top_n * 0.35)))
    colors = ["#e74c3c" if v < 0 else "#3498db" for v in df[value_col]]
    ax.barh(
        df["feature"],
        df[value_col],
        color=colors,
        edgecolor="white",
        linewidth=0.5,
    )
    ax.set_title(title, fontsize=14, fontweight="bold", pad=12)
    ax.set_xlabel("Importance", fontsize=12)
    ax.set_ylabel("")
    ax.yaxis.label.set_visible(False)
    ax.tick_params(axis="y", labelsize=9)
    fig.tight_layout()

    if output_path is None:
        output_path = RESULTS_DIR / f"{title.replace(' ', '_').lower()}.png"

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)

    logger.info("Saved feature importance plot → %s", output_path)
    return output_path


def plot_shap_summary(
    shap_values: np.ndarray,
    X_sample: np.ndarray,
    feature_names: list[str],
    output_path: Optional[str] = None,
    max_display: int = 20,
) -> str:
    """Plot SHAP summary beeswarm plot.

    Returns:
        Path to the saved figure.
    """
    try:
        import shap
    except ImportError:
        logger.warning("shap not installed — skipping SHAP summary plot")
        return ""

    if output_path is None:
        output_path = RESULTS_DIR / "shap_summary.png"

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    plt.figure(figsize=(10, max(6, max_display * 0.3)))
    shap.summary_plot(
        shap_values,
        X_sample,
        feature_names=feature_names,
        max_display=max_display,
        show=False,
    )
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close()

    logger.info("Saved SHAP summary plot → %s", output_path)
    return output_path
