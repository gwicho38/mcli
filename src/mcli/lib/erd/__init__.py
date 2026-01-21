"""
Entity Relationship Diagram (ERD) package.

This package provides utilities for generating Entity Relationship Diagrams from MCLI type metadata.
"""

# Import and export all public functions from erd.py
from .erd import (
    analyze_graph_for_hierarchical_exports,
    create_merged_erd,
    do_erd,
    find_top_nodes_in_graph,
    generate_erd_for_top_nodes,
    generate_merged_erd_for_types,
)

# Define __all__ to control exports
__all__ = [
    "do_erd",
    "create_merged_erd",
    "generate_merged_erd_for_types",
    "find_top_nodes_in_graph",
    "generate_erd_for_top_nodes",
    "analyze_graph_for_hierarchical_exports",
]
