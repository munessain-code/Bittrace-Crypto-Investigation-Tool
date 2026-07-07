"""Random Forest baseline matching Elliptic++ paper methodology.

Reproduces the exact RF pipeline from the KDD '23 paper notebooks:
- Transactions: timestep split (train < 35, test >= 35), binary classification
- Actors: 70/30 split (shuffle=False, random_state=15), binary classification
- MinMaxScaler on feature columns
- RandomForest(n_estimators=50)
- Drop unknown class (3) before training
- Binary labels: licit=0, illicit=1
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    classification_report,
    f1_score,
    precision_recall_fscore_support,
)
from sklearn.preprocessing import MinMaxScaler

logger = logging.getLogger(__name__)

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"


@dataclass(frozen=True)
class ModelResults:
    """Container for RF baseline evaluation results."""

    precision: float
    recall: float
    f1: float
    micro_f1: float
    report: str
    model: RandomForestClassifier = field(repr=False)
    y_test: np.ndarray = field(repr=False)
    y_pred: np.ndarray = field(repr=False)
    feature_names: list[str] = field(default_factory=list)


def load_transaction_features() -> pd.DataFrame:
    """Load and merge transaction features with classes."""
    features = pd.read_csv(DATA_DIR / "txs_features.csv")
    classes = pd.read_csv(DATA_DIR / "txs_classes.csv")
    return features.merge(classes, on="txId", how="left")


def load_actor_features() -> pd.DataFrame:
    """Load actor (wallet) features with classes (combined CSV)."""
    return pd.read_csv(DATA_DIR / "wallets_features_classes_combined.csv")


# ── Transactions pipeline ───────────────────────────────────────────────


def preprocess_transactions(df: pd.DataFrame) -> pd.DataFrame:
    """Apply paper preprocessing to transaction data.

    Steps:
    1. Drop NaN rows
    2. MinMaxScaler on feature columns (exclude txId, Time step, class)
    3. Remove unknown class (3)
    4. Binary encode: licit(2)=0, illicit(1)=1
    """
    df = df.dropna().copy()

    # MinMaxScaler on all feature columns (exclude non-numeric)
    exclude_cols = {"txId", "Time step", "class"}
    feature_cols = [c for c in df.columns if c not in exclude_cols]
    for col in feature_cols:
        scaler = MinMaxScaler()
        df[col] = scaler.fit_transform(df[[col]]).ravel()

    # Remove unknown class
    df = df[df["class"] != 3].copy()

    # Binary: licit=0, illicit=1
    df["class"] = df["class"].apply(lambda c: 0 if c == 2 else 1)

    return df


def split_transactions(
    df: pd.DataFrame, train_cutoff: int = 35
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Split by timestep: train < 35, test >= 35 (as in paper)."""
    train_ids = df.loc[df["Time step"] < train_cutoff, "txId"]
    test_ids = df.loc[df["Time step"] >= train_cutoff, "txId"]

    train = df[df["txId"].isin(train_ids)].copy()
    test = df[df["txId"].isin(test_ids)].copy()

    feature_cols = [c for c in df.columns if c not in ("txId", "class", "Time step")]
    X_train = train[feature_cols]
    X_test = test[feature_cols]
    y_train = train["class"]
    y_test = test["class"]

    return X_train, X_test, y_train, y_test


def train_rf_transactions(
    train_cutoff: int = 35,
    n_estimators: int = 50,
    random_state: int = 42,
) -> ModelResults:
    """Train RF on transactions following exact paper methodology.

    Returns ModelResults with precision/recall on the illicit class (class 1).
    """
    logger.info("Loading transaction data...")
    df = load_transaction_features()
    df = preprocess_transactions(df)

    logger.info("Splitting by timestep (train < %d, test >= %d)...", train_cutoff, train_cutoff)
    X_train, X_test, y_train, y_test = split_transactions(df, train_cutoff)

    logger.info(
        "Training RF: %d samples, %d features | Test: %d samples",
        len(X_train),
        X_train.shape[1],
        len(X_test),
    )

    model = RandomForestClassifier(
        n_estimators=n_estimators,
        random_state=random_state,
        n_jobs=-1,
    )
    model.fit(X_train.values, y_train.values)
    y_pred = model.predict(X_test.values)

    prec, rec, f1, _ = precision_recall_fscore_support(y_test.values, y_pred, zero_division=0)
    micro_f1 = f1_score(y_test.values, y_pred, average="micro")
    report = classification_report(
        y_test.values,
        y_pred,
        target_names=["licit (0)", "illicit (1)"],
        zero_division=0,
    )

    logger.info(
        "RF Transactions — Precision: %.3f, Recall: %.3f, F1: %.3f, Micro-F1: %.3f",
        prec[1],
        rec[1],
        f1[1],
        micro_f1,
    )

    return ModelResults(
        precision=prec[1],
        recall=rec[1],
        f1=f1[1],
        micro_f1=micro_f1,
        report=report,
        model=model,
        y_test=y_test.values,
        y_pred=y_pred,
        feature_names=list(X_train.columns),
    )


# ── Actors pipeline ──────────────────────────────────────────────────────


def preprocess_actors(df: pd.DataFrame) -> pd.DataFrame:
    """Apply paper preprocessing to actor data.

    Steps:
    1. Drop 'Time step' column and duplicates
    2. MinMaxScaler on feature columns (from index 2 onward, after address+class)
    3. Remove unknown class (3)
    4. Binary encode: licit(2)=0, illicit(1)=1
    """
    df = df.drop(columns=["Time step"]).drop_duplicates().copy()

    # MinMaxScaler on feature columns (index 2+)
    for col in df.columns[2:]:
        scaler = MinMaxScaler()
        df[col] = scaler.fit_transform(df[[col]]).ravel()

    # Remove unknown class
    df = df[df["class"] != 3].copy()

    # Binary: licit=0, illicit=1
    df["class"] = df["class"].apply(lambda c: 0 if c == 2 else 1)

    return df


def split_actors(
    df: pd.DataFrame,
    test_size: float = 0.30,
    random_state: int = 15,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """70/30 split with shuffle=False and random_state=15 (as in paper)."""
    from sklearn.model_selection import train_test_split

    feature_cols = [c for c in df.columns if c not in ("address", "class")]
    X = df[feature_cols]
    y = df["class"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, shuffle=False
    )

    return X_train, X_test, y_train, y_test


def train_rf_actors(
    n_estimators: int = 50,
    random_state: int = 42,
    model_random_state: int = 42,
) -> ModelResults:
    """Train RF on actors following exact paper methodology.

    Returns ModelResults with precision/recall on the illicit class (class 1).
    """
    logger.info("Loading actor data...")
    df = load_actor_features()
    df = preprocess_actors(df)

    logger.info("Splitting actors: 70/30 (shuffle=False, rs=%d)...", random_state)
    X_train, X_test, y_train, y_test = split_actors(df, random_state=random_state)

    logger.info(
        "Training RF: %d samples, %d features | Test: %d samples",
        len(X_train),
        X_train.shape[1],
        len(X_test),
    )

    model = RandomForestClassifier(
        n_estimators=n_estimators,
        random_state=model_random_state,
        n_jobs=-1,
    )
    model.fit(X_train.values, y_train.values)
    y_pred = model.predict(X_test.values)

    prec, rec, f1, _ = precision_recall_fscore_support(y_test.values, y_pred, zero_division=0)
    micro_f1 = f1_score(y_test.values, y_pred, average="micro")
    report = classification_report(
        y_test.values,
        y_pred,
        target_names=["licit (0)", "illicit (1)"],
        zero_division=0,
    )

    logger.info(
        "RF Actors — Precision: %.3f, Recall: %.3f, F1: %.3f, Micro-F1: %.3f",
        prec[1],
        rec[1],
        f1[1],
        micro_f1,
    )

    return ModelResults(
        precision=prec[1],
        recall=rec[1],
        f1=f1[1],
        micro_f1=micro_f1,
        report=report,
        model=model,
        y_test=y_test.values,
        y_pred=y_pred,
        feature_names=list(X_train.columns),
    )


# ── CLI entry point ─────────────────────────────────────────────────────


def main():
    """Run both RF baselines from command line."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    print("=" * 60)
    print("BitTrace — Random Forest Baseline")
    print("Matching Elliptic++ paper methodology (KDD '23)")
    print("=" * 60)

    print("\n--- Transactions ---")
    tx_results = train_rf_transactions()
    print(tx_results.report)

    print("\n--- Actors ---")
    actor_results = train_rf_actors()
    print(actor_results.report)

    print("\n--- Paper Benchmarks for comparison ---")
    print("Transactions (paper): Precision=0.986, Recall=0.727")
    print("Actors (paper):       Precision=0.921, Recall=0.802")


if __name__ == "__main__":
    main()
