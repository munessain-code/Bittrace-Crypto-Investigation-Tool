#!/usr/bin/env python3
"""SHAP-based feature attribution for BitTrace RF models.

Uses TreeSHAP (exact for tree ensembles) on a representative sample
of 500 rows to keep runtime under 30 seconds while preserving accuracy.

Usage:
    from src.explain.shap_explainer import compute_shap_transactions

    result = compute_shap_transactions()
    print(result.top_features)  # [(feature_name, mean_abs_shap), ...]
    result.summary_plot_path  # path to saved plot
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import shap
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import MinMaxScaler

from src.models.baseline import (
    DATA_DIR,
    PROJECT_ROOT,
    load_actor_features,
    load_transaction_features,
    preprocess_actors,
    preprocess_transactions,
    split_actors,
    split_transactions,
)

logger = logging.getLogger(__name__)


@dataclass
class ShapResult:
    """SHAP explanation result for one model."""
    shap_values: np.ndarray          # (n_sample, n_features)
    feature_names: list[str]
    top_features: list[tuple[str, float]]  # [(name, mean_abs_shap), ...]
    summary_plot_path: Optional[str] = None
    dependence_plot_path: Optional[str] = None


def _sample_for_shap(
    X: np.ndarray, y: np.ndarray, n: int = 500, random_state: int = 42
) -> tuple[np.ndarray, np.ndarray]:
    """Stratified sample for SHAP computation."""
    from sklearn.model_selection import train_test_split

    return train_test_split(
        X, y, train_size=n, random_state=random_state, stratify=y
    )[:2]


def _extract_class_values(shap_vals):
    """Extract class-1 SHAP values regardless of SHAP return format."""
    if isinstance(shap_vals, list):
        return shap_vals[1]  # illicit class
    elif hasattr(shap_vals, 'ndim') and shap_vals.ndim == 3:
        return shap_vals[:, :, 1]  # 3D array, illicit class
    else:
        return shap_vals  # already 2D


def compute_shap_transactions(
    n_estimators: int = 50,
    sample_size: int = 500,
    top_n: int = 10,
    save_plots: bool = True,
    train_cutoff: int = 35,
    random_state: int = 42,
) -> ShapResult:
    """Compute SHAP values for the RF transactions model.

    Parameters
    ----------
    n_estimators : int
        Number of trees in the RF model.
    sample_size : int
        Number of test rows to explain (default 500 for speed).
    top_n : int
        Number of top features to return.
    save_plots : bool
        Whether to save summary and dependence plots to docs/.

    Returns
    -------
    ShapResult with shap_values, feature_names, top_features, and plot paths.
    """
    logger.info("Training RF transactions model for SHAP...")
    df = load_transaction_features()
    df = preprocess_transactions(df)

    X_train, X_test, y_train, y_test = split_transactions(df, train_cutoff=train_cutoff)

    # Retrain RF on the same split for SHAP
    model = RandomForestClassifier(
        n_estimators=n_estimators, random_state=random_state, n_jobs=-1
    )
    model.fit(X_train.values, y_train.values)

    # Sample for SHAP
    X_sample, y_sample = _sample_for_shap(X_test.values, y_test.values, sample_size)
    feature_names = list(X_test.columns)

    logger.info("Computing TreeSHAP on %d samples...", len(X_sample))
    explainer = shap.TreeExplainer(model)
    shap_vals = explainer.shap_values(X_sample)
    shap_vals = _extract_class_values(shap_vals)

    # Top features by mean |SHAP|
    mean_abs = np.abs(shap_vals).mean(axis=0).flatten()
    top_idx = np.argsort(mean_abs)[::-1][:top_n].tolist()
    top_features = [(feature_names[i], float(mean_abs[i])) for i in top_idx]

    result = ShapResult(
        shap_values=shap_vals,
        feature_names=feature_names,
        top_features=top_features,
    )

    if save_plots:
        docs_dir = PROJECT_ROOT / "docs"
        docs_dir.mkdir(exist_ok=True)

        # Summary plot
        try:
            shap.summary_plot(
                shap_vals[:500, :],
                X_sample[:500, :],
                feature_names=feature_names,
                show=False,
            )
            path = docs_dir / "shap_summary_transactions.png"
            plt.savefig(path, dpi=150, bbox_inches="tight")
            plt.close("all")
            result.summary_plot_path = str(path)
            logger.info("Saved SHAP summary plot: %s", path)
        except Exception as e:
            logger.warning("SHAP summary plot failed: %s", e)

    return result


def compute_shap_actors(
    n_estimators: int = 50,
    sample_size: int = 500,
    top_n: int = 10,
    save_plots: bool = True,
    random_state: int = 42,
    model_random_state: int = 42,
) -> ShapResult:
    """Compute SHAP values for the RF actors model.

    Parameters
    ----------
    n_estimators : int
        Number of trees in the RF model.
    sample_size : int
        Number of test rows to explain.
    top_n : int
        Number of top features to return.
    save_plots : bool
        Whether to save summary and dependence plots.

    Returns
    -------
    ShapResult with shap_values, feature_names, top_features, and plot paths.
    """
    logger.info("Training RF actors model for SHAP...")
    df = load_actor_features()
    df = preprocess_actors(df)

    X_train, X_test, y_train, y_test = split_actors(df, random_state=random_state)

    model = RandomForestClassifier(
        n_estimators=n_estimators, random_state=model_random_state, n_jobs=-1
    )
    model.fit(X_train.values, y_train.values)

    X_sample, y_sample = _sample_for_shap(X_test.values, y_test.values, sample_size)
    feature_names = list(X_test.columns)

    logger.info("Computing TreeSHAP on %d samples...", len(X_sample))
    explainer = shap.TreeExplainer(model)
    shap_vals = explainer.shap_values(X_sample)
    shap_vals = _extract_class_values(shap_vals)

    mean_abs = np.abs(shap_vals).mean(axis=0).flatten()
    top_idx = np.argsort(mean_abs)[::-1][:top_n].tolist()
    top_features = [(feature_names[i], float(mean_abs[i])) for i in top_idx]

    result = ShapResult(
        shap_values=shap_vals,
        feature_names=feature_names,
        top_features=top_features,
    )

    if save_plots:
        docs_dir = PROJECT_ROOT / "docs"
        docs_dir.mkdir(exist_ok=True)

        try:
            shap.summary_plot(
                shap_vals[:500, :],
                X_sample[:500, :],
                feature_names=feature_names,
                show=False,
            )
            path = docs_dir / "shap_summary_actors.png"
            plt.savefig(path, dpi=150, bbox_inches="tight")
            plt.close("all")
            result.summary_plot_path = str(path)
            logger.info("Saved SHAP summary plot: %s", path)
        except Exception as e:
            logger.warning("SHAP summary plot failed: %s", e)

    return result
