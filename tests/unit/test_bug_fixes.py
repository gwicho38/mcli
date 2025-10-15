#!/usr/bin/env python3
"""
Test script to verify our fix to the find_top_nodes_in_graph function.
"""

import json
import os

from mcli.lib.erd import find_top_nodes_in_graph
from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)


def test_find_top_nodes():
    try:
        # Load the graph data
        with open("realGraph.json", "r") as f:
            graph_data = json.load(f)

        # Find top nodes
        top_nodes = find_top_nodes_in_graph(graph_data, top_n=5)

        print(f"Found {len(top_nodes)} top nodes:")
        for node_id, count in top_nodes:
            print(f"- {node_id}: {count} descendants")

        return top_nodes
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        print(traceback.format_exc())
        return []


if __name__ == "__main__":
    print("Testing fixed find_top_nodes_in_graph function...")
    test_find_top_nodes()
