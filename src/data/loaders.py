"""Data loaders for Elliptic++ dataset via DuckDB and pandas."""

import os
from pathlib import Path
from typing import Optional

import duckdb
import pandas as pd

# Project root is two levels up from this file
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SCHEMA_PATH = PROJECT_ROOT / "src" / "data" / "schema.sql"


def _check_data_files() -> list[str]:
    """Return list of expected CSV files that exist in data/."""
    expected = [
        "txs_features.csv",
        "txs_classes.csv",
        "txs_edgelist.csv",
        "wallets_features.csv",
        "wallets_classes.csv",
        "AddrAddr_edgelist.csv",
        "AddrTx_edgelist.csv",
        "TxAddr_edgelist.csv",
    ]
    return [f for f in expected if (DATA_DIR / f).exists()]


def get_duckdb_connection(db_path: Optional[str] = None) -> duckdb.DuckDBPyConnection:
    """Create a DuckDB connection and load schema from CSVs.

    Args:
        db_path: Optional path to persist the database. If None, uses in-memory.

    Returns:
        DuckDB connection with tables loaded.
    """
    if db_path:
        con = duckdb.connect(db_path)
    else:
        con = duckdb.connect()

    present = _check_data_files()
    if not present:
        raise FileNotFoundError(
            "No Elliptic++ CSVs found in data/. Run `python data/download.py --download` first."
        )

    # Load schema if available — use absolute paths so read_csv_auto resolves correctly
    if SCHEMA_PATH.exists():
        schema_sql = SCHEMA_PATH.read_text().replace(
            "'data/", f"'{DATA_DIR}/"
        )
        try:
            con.execute(schema_sql)
        except Exception:
            # Some tables may fail if their CSVs aren't present
            pass

    return con


def load_transactions(features: bool = True, classes: bool = True, edges: bool = False) -> pd.DataFrame:
    """Load transaction dataset.

    Args:
        features: Include txs_features.csv (183 features per transaction).
        classes: Include txs_classes.csv (labels: 1=illicit, 2=licit, 3=unknown).
        edges: Include txs_edgelist.csv (tx-to-tx money flow edges).

    Returns:
        DataFrame with transactions (features + classes) or edges DataFrame.
    """
    con = get_duckdb_connection()

    if edges:
        return con.execute("SELECT * FROM tx_edges").fetchdf()

    df = pd.DataFrame()
    if features:
        df = con.execute("SELECT * FROM transactions").fetchdf()
    if classes:
        classes_df = con.execute("SELECT * FROM tx_classes").fetchdf()
        if df.empty:
            df = classes_df
        else:
            # Merge on transaction ID (first column)
            df = df.merge(classes_df, left_on=df.columns[0], right_on=classes_df.columns[0], how="left", suffixes=("", "_y"))

    return df


def load_actors(features: bool = True, classes: bool = True) -> pd.DataFrame:
    """Load wallet/actor dataset.

    Args:
        features: Include wallets_features.csv (56 features per wallet).
        classes: Include wallets_classes.csv (labels).

    Returns:
        DataFrame with wallet data.
    """
    con = get_duckdb_connection()

    df = pd.DataFrame()
    if features:
        df = con.execute("SELECT * FROM wallets").fetchdf()
    if classes:
        classes_df = con.execute("SELECT * FROM wallet_classes").fetchdf()
        if df.empty:
            df = classes_df
        else:
            df = df.merge(classes_df, left_on=df.columns[0], right_on=classes_df.columns[0], how="left", suffixes=("", "_y"))

    return df


def load_edges(edge_type: str = "tx_tx") -> pd.DataFrame:
    """Load edge list.

    Args:
        edge_type: One of 'tx_tx', 'addr_addr', 'addr_tx', 'tx_addr'.

    Returns:
        DataFrame with edge data.
    """
    con = get_duckdb_connection()

    table_map = {
        "tx_tx": "tx_edges",
        "addr_addr": "addr_addr_edges",
        "addr_tx": "addr_tx_edges",
        "tx_addr": "tx_addr_edges",
    }

    table = table_map.get(edge_type)
    if not table:
        raise ValueError(f"Unknown edge_type: {edge_type}. Choose from {list(table_map.keys())}")

    return con.execute(f"SELECT * FROM {table}").fetchdf()


def get_dataset_summary() -> dict:
    """Return a summary of available data files and row counts."""
    summary = {}
    con = get_duckdb_connection()

    table_names = [
        "transactions",
        "tx_classes",
        "tx_edges",
        "wallets",
        "wallet_classes",
        "addr_addr_edges",
        "addr_tx_edges",
        "tx_addr_edges",
    ]

    for tbl in table_names:
        try:
            count = con.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
            summary[tbl] = {"rows": count, "status": "ok"}
        except Exception as e:
            summary[tbl] = {"rows": 0, "status": str(e)}

    return summary
