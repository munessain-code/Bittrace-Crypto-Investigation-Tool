"""Graph analysis utilities for the BitTrace project."""

from src.graph.builders import (
    build_tx_graph,
    build_tx_graph_sample,
    build_addr_graph,
    build_bipartite,
)
from src.graph.stats import (
    compute_stats,
    degree_distribution,
    get_degree_histogram_data,
    connected_components_summary,
    density_summary,
)
from src.graph.patterns import (
    detect_peel_chains,
    detect_fan_out,
    detect_fan_in,
    get_fan_illicit_counts,
    path_length_distribution,
    summarize_layering_patterns,
)

from src.graph.trace import (
    trace_downstream,
    trace_upstream,
    trace_bipartite,
)
from src.graph.expand import (
    expand_node,
    expand_bipartite,
)
from src.graph.export import (
    subgraph_to_cytoscape,
    subgraph_to_json_file,
    trace_to_cytoscape,
    CLASS_COLORS,
    CLASS_LABELS,
)
from src.graph.cases import (
    find_seed_node,
    extract_case_subgraph,
    save_case_subgraph,
    generate_all_cases,
)

__all__ = [
    # builders
    "build_tx_graph",
    "build_tx_graph_sample",
    "build_addr_graph",
    "build_bipartite",
    # stats
    "compute_stats",
    "degree_distribution",
    "get_degree_histogram_data",
    "connected_components_summary",
    "density_summary",
    # patterns
    "detect_peel_chains",
    "detect_fan_out",
    "detect_fan_in",
    "get_fan_illicit_counts",
    "path_length_distribution",
    "summarize_layering_patterns",
    # trace
    "trace_downstream",
    "trace_upstream",
    "trace_bipartite",
    # expand
    "expand_node",
    "expand_bipartite",
    # export
    "subgraph_to_cytoscape",
    "subgraph_to_json_file",
    "trace_to_cytoscape",
    "CLASS_COLORS",
    "CLASS_LABELS",
    # cases
    "find_seed_node",
    "extract_case_subgraph",
    "save_case_subgraph",
    "generate_all_cases",
]
