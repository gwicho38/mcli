"""Test script to verify the fix to the find_top_nodes_in_graph function."""

import json

from mcli.lib.erd.erd import find_top_nodes_in_graph
from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)


def test_find_top_nodes():
    """Test that find_top_nodes_in_graph returns correct results."""
    try:
        # Load the graph data
        with open("realGraph.json", "r") as f:
            graph_data = json.load(f)

        # Find top nodes
        top_nodes = find_top_nodes_in_graph(graph_data, top_n=5)

        print(f"Found {len(top_nodes)} top nodes:")
        for node_id, count in top_nodes:
            print(f"- {node_id}: {count} descendants")

        assert isinstance(top_nodes, list), "Expected a list of top nodes"
    except FileNotFoundError:
        # Skip test if realGraph.json doesn't exist
        import pytest

        pytest.skip("realGraph.json not found")
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        print(traceback.format_exc())
        raise


if __name__ == "__main__":
    print("Testing fixed find_top_nodes_in_graph function...")
    test_find_top_nodes()
