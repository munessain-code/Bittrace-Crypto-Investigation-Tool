"""Tests for Phase 8c/8c+ account payload on /graph/node and helpers."""

from __future__ import annotations

import pytest

from src.data.attribute_catalog import (
    ACCOUNT_PROFILE_FIELDS,
    is_account_value_field,
    resolve_class_label,
)
from src.data.loaders import get_duckdb_connection


def test_class_labels_never_numeric_strings():
    assert resolve_class_label(1) == "illicit"
    assert resolve_class_label(2) == "licit"
    assert resolve_class_label(3) == "unknown"
    assert resolve_class_label(None) == "unknown"


def test_account_value_fields_excluded():
    assert is_account_value_field("btc_sent_total")
    assert is_account_value_field("fees_total")
    assert not is_account_value_field("num_txs_as_sender")
    assert not is_account_value_field("lifetime_in_blocks")


def test_profile_fields_have_no_btc():
    for f in ACCOUNT_PROFILE_FIELDS:
        name = f["field"]
        assert not name.startswith("btc_"), name
        assert not name.startswith("fees"), name


@pytest.fixture(scope="module")
def db():
    return get_duckdb_connection()


def test_get_accounts_structure_and_no_btc(db):
    from api.main import _get_accounts

    # Peel-chain seed — known to have 1 sender and 2 receivers
    acc = _get_accounts(10000476, db, timestep=29)
    assert "senders" in acc and "receivers" in acc
    assert acc["sender_count"] >= 1
    assert acc["receiver_count"] >= 1
    assert len(acc["senders"]) >= 1
    assert len(acc["receivers"]) >= 1

    for party in acc["senders"] + acc["receivers"]:
        assert "address" in party
        assert party["class_label"] in ("illicit", "licit", "unknown")
        for k in party:
            assert not str(k).startswith("btc_"), k
            assert not str(k).startswith("fees"), k

    # Profiles keyed by address
    by_addr = acc.get("profiles", {}).get("by_address", {})
    assert isinstance(by_addr, dict)
    if by_addr:
        sample = next(iter(by_addr.values()))
        assert "address" in sample or any(
            f["field"] in sample for f in ACCOUNT_PROFILE_FIELDS
        )


def test_get_accounts_counts_can_exceed_list(db):
    """When a TX has many parties, count >= len(list)."""
    from api.main import _get_accounts

    acc = _get_accounts(10000476, db, timestep=29)
    assert acc["sender_count"] >= len(acc["senders"])
    assert acc["receiver_count"] >= len(acc["receivers"])
