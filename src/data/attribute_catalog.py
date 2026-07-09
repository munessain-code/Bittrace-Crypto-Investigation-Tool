"""Canonical display names and field mappings for BitTrace node attributes.

Mirrors the spec in bittrace-project-plan.md — "Node Hover / Attribute Panel".
Used by both the API (attribute labeling) and the frontend (hover/inspector panels).
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
    "1": "#ef4444",   # illicit — red
    "2": "#22c55e",   # licit — green
    "3": "#6b7280",   # unknown — gray
}


# ---------------------------------------------------------------------------
# Hover attributes (compact tooltip — Tier 1)
# ---------------------------------------------------------------------------

HOVER_ATTRIBUTES: list[dict] = [
    {"field": "txId", "display": "Transaction ID", "type": "int"},
    {"field": "class_label", "display": "Class", "type": "str"},
    {"field": "timestep", "display": "Timestep", "type": "int"},
    {"field": "total_BTC", "display": "Total BTC", "type": "float", "precision": 4},
    {"field": "fees", "display": "Fees", "type": "float", "precision": 6},
    {"field": "in_degree", "display": "In-Degree", "type": "int", "source": "graph"},
    {"field": "out_degree", "display": "Out-Degree", "type": "int", "source": "graph"},
    {"field": "num_input_addresses", "display": "Inputs", "type": "int"},
    {"field": "num_output_addresses", "display": "Outputs", "type": "int"},
]


# ---------------------------------------------------------------------------
# Click attributes (Node Inspector — Tier 2, full detail)
# ---------------------------------------------------------------------------

CLICK_ATTRIBUTES: list[dict] = [
    # All hover attributes first
    *HOVER_ATTRIBUTES,
    # Extended fields
    {"field": "size", "display": "TX Size", "type": "float"},
    {"field": "in_BTC_total", "display": "Input BTC (total)", "type": "float", "precision": 4},
    {"field": "out_BTC_total", "display": "Output BTC (total)", "type": "float", "precision": 4},
    {"field": "in_txs_degree", "display": "Input TXs (graph)", "type": "int"},
    {"field": "out_txs_degree", "display": "Output TXs (graph)", "type": "int"},
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def resolve_class_label(class_val) -> str:
    """Map numeric class to human-readable label."""
    if class_val is None:
        return "unknown"
    return CLASS_LABELS.get(int(class_val), "unknown")


def resolve_class_color(class_val) -> str:
    """Map numeric class to hex color."""
    if class_val is None:
        return CLASS_COLORS.get("3", "#6b7280")
    return CLASS_COLORS.get(str(int(class_val)), "#6b7280")


def get_display_name(field: str) -> str:
    """Get human-readable display name for a field."""
    for attr in CLICK_ATTRIBUTES:
        if attr["field"] == field:
            return attr["display"]
    return field


# Build a quick lookup
DISPLAY_NAMES: dict[str, str] = {attr["field"]: attr["display"] for attr in CLICK_ATTRIBUTES}
