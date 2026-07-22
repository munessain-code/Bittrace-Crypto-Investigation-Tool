"""Canonical display names and field mappings for BitTrace node attributes.

Authoritative UI split (confirmed 2026-07-21):
  - Transaction details → all monetary / size / fee / count-of-addresses fields
  - Account details → wallet IDs + non-BTC activity only (no btc_*, no wallet fees)

See bittrace-project-plan.md — "Node Inspector Attribute Spec — CONFIRMED".
"""

# ---------------------------------------------------------------------------
# Class label mapping (mandatory — never show raw 1/2/3 in UI)
# ---------------------------------------------------------------------------

CLASS_LABELS: dict[int, str] = {
    1: "illicit",
    2: "licit",
    3: "unknown",
}

CLASS_COLORS: dict[str, str] = {
    "1": "#ef4444",  # illicit — red
    "2": "#22c55e",  # licit — green
    "3": "#6b7280",  # unknown — gray
}


# ---------------------------------------------------------------------------
# Hover attributes (compact tooltip)
# ---------------------------------------------------------------------------

HOVER_ATTRIBUTES: list[dict] = [
    {"field": "txId", "display": "Transaction ID", "type": "int", "section": "hover"},
    {"field": "class_label", "display": "Class", "type": "str", "section": "hover"},
    {"field": "timestep", "display": "Timestep", "type": "int", "section": "hover"},
    {"field": "in_degree", "display": "In-Degree", "type": "int", "source": "graph", "section": "hover"},
    {"field": "out_degree", "display": "Out-Degree", "type": "int", "source": "graph", "section": "hover"},
    {"field": "primary_sender", "display": "Primary sender", "type": "str", "source": "accounts", "section": "hover"},
    {"field": "sender_count", "display": "Senders", "type": "int", "source": "accounts", "section": "hover"},
    {"field": "receiver_count", "display": "Receivers", "type": "int", "source": "accounts", "section": "hover"},
]


# ---------------------------------------------------------------------------
# Transaction details (Node Inspector) — values live here only
# ---------------------------------------------------------------------------

TRANSACTION_DETAILS: list[dict] = [
    {"field": "total_BTC", "display": "Total BTC", "type": "float", "precision": 6, "section": "transaction"},
    {"field": "fees", "display": "Fees", "type": "float", "precision": 8, "section": "transaction"},
    {"field": "size", "display": "TX Size (bytes)", "type": "float", "section": "transaction"},
    {"field": "in_BTC_total", "display": "Input BTC (total)", "type": "float", "precision": 6, "section": "transaction"},
    {"field": "out_BTC_total", "display": "Output BTC (total)", "type": "float", "precision": 6, "section": "transaction"},
    {"field": "num_input_addresses", "display": "Input addresses", "type": "int", "section": "transaction"},
    {"field": "num_output_addresses", "display": "Output addresses", "type": "int", "section": "transaction"},
    {"field": "in_txs_degree", "display": "Input TXs (feature)", "type": "int", "section": "transaction"},
    {"field": "out_txs_degree", "display": "Output TXs (feature)", "type": "int", "section": "transaction"},
]


# ---------------------------------------------------------------------------
# Account details (Node Inspector) — wallets only, NO BTC / NO fees
# ---------------------------------------------------------------------------

# List caps for AddrTx / TxAddr parties
ACCOUNT_LIST_LIMIT = 5

ACCOUNT_PARTY_FIELDS: list[dict] = [
    {"field": "address", "display": "Wallet ID", "type": "str", "section": "account"},
    {"field": "class_label", "display": "Account class", "type": "str", "section": "account"},
]

# Profile stats joined from wallets_features (exclude all btc_* and fees_*)
ACCOUNT_PROFILE_FIELDS: list[dict] = [
    {"field": "num_txs_as_sender", "display": "Txs as sender", "type": "float", "section": "account"},
    # Column name in CSV has a space: "num_txs_as receiver"
    {"field": "num_txs_as receiver", "display": "Txs as receiver", "type": "float", "section": "account"},
    {"field": "total_txs", "display": "Total txs", "type": "float", "section": "account"},
    {"field": "lifetime_in_blocks", "display": "Lifetime (blocks)", "type": "float", "section": "account"},
    {"field": "first_block_appeared_in", "display": "First block", "type": "float", "section": "account"},
    {"field": "last_block_appeared_in", "display": "Last block", "type": "float", "section": "account"},
    {"field": "num_timesteps_appeared_in", "display": "Timesteps appeared", "type": "float", "section": "account"},
    {"field": "transacted_w_address_total", "display": "Distinct counterparties", "type": "float", "section": "account"},
]

# Wallet feature columns that must NEVER appear in Account details
ACCOUNT_EXCLUDED_PREFIXES: tuple[str, ...] = (
    "btc_",
    "fees",
    "fees_as_share",
)


# ---------------------------------------------------------------------------
# Back-compat: full click inspector = identity + transaction values
# (account parties come from the separate `accounts` payload)
# ---------------------------------------------------------------------------

CLICK_ATTRIBUTES: list[dict] = [
    {"field": "txId", "display": "Transaction ID", "type": "int", "section": "header"},
    {"field": "class_label", "display": "Class", "type": "str", "section": "header"},
    {"field": "timestep", "display": "Timestep", "type": "int", "section": "header"},
    {"field": "in_degree", "display": "In-Degree", "type": "int", "source": "graph", "section": "header"},
    {"field": "out_degree", "display": "Out-Degree", "type": "int", "source": "graph", "section": "header"},
    {"field": "degree", "display": "Degree", "type": "int", "source": "graph", "section": "header"},
    *TRANSACTION_DETAILS,
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def resolve_class_label(class_val) -> str:
    """Map numeric class to human-readable label."""
    if class_val is None:
        return "unknown"
    try:
        return CLASS_LABELS.get(int(class_val), "unknown")
    except (TypeError, ValueError):
        return "unknown"


def resolve_class_color(class_val) -> str:
    """Map numeric class to hex color."""
    if class_val is None:
        return CLASS_COLORS.get("3", "#6b7280")
    try:
        return CLASS_COLORS.get(str(int(class_val)), "#6b7280")
    except (TypeError, ValueError):
        return CLASS_COLORS.get("3", "#6b7280")


def get_display_name(field: str) -> str:
    """Get human-readable display name for a field."""
    for attr in (
        HOVER_ATTRIBUTES
        + CLICK_ATTRIBUTES
        + ACCOUNT_PARTY_FIELDS
        + ACCOUNT_PROFILE_FIELDS
    ):
        if attr["field"] == field:
            return attr["display"]
    return field


def is_account_value_field(field: str) -> bool:
    """True if a wallets_features column is monetary and must stay out of Account details."""
    f = field.lower()
    return f.startswith("btc_") or f.startswith("fees")


DISPLAY_NAMES: dict[str, str] = {
    attr["field"]: attr["display"]
    for attr in (
        HOVER_ATTRIBUTES
        + CLICK_ATTRIBUTES
        + ACCOUNT_PARTY_FIELDS
        + ACCOUNT_PROFILE_FIELDS
    )
}
