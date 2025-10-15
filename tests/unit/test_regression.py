import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch


class TestGenerateGraph(unittest.TestCase):
    def test_load_graph_data_with_valid_file(self):
        from mcli.lib.erd.generate_graph import load_graph_data

        # Create a temporary valid JSON file
        with tempfile.NamedTemporaryFile(mode="w", delete=False) as f:
            # Create a minimal valid graph structure
            data = {"graph": {"m_vertices": {"value": []}, "m_edges": {"value": []}}}
            json.dump(data, f)

        try:
            # Test loading the valid file
            result = load_graph_data(f.name)
            self.assertEqual(result, data)
        finally:
            # Clean up
            os.unlink(f.name)

    def test_load_graph_data_with_missing_file(self):
        from mcli.lib.erd.generate_graph import load_graph_data

        # Test with a non-existent file
        with self.assertRaises(FileNotFoundError):
            load_graph_data("nonexistent_file.json")

    def test_build_adjacency_list_with_valid_data(self):
        from mcli.lib.erd.generate_graph import build_adjacency_list

        # Create valid graph data
        graph_data = {
            "graph": {
                "m_vertices": {
                    "value": [
                        {"id": "node1", "data": {"name": "Node 1"}},
                        {"id": "node2", "data": {"name": "Node 2"}},
                    ]
                },
                "m_edges": {"value": [{"source": "node1", "target": "node2"}]},
            }
        }

        # Build adjacency list
        node_map, adj_list = build_adjacency_list(graph_data)

        # Verify results
        self.assertEqual(len(node_map), 2)
        self.assertIn("node1", node_map)
        self.assertIn("node2", node_map)
        self.assertEqual(adj_list["node1"], ["node2"])
        self.assertEqual(adj_list["node2"], [])

    def test_build_adjacency_list_with_invalid_data(self):
        from mcli.lib.erd.generate_graph import build_adjacency_list

        # Test with invalid data structure
        invalid_data = {"graph": {}}

        with self.assertRaises(ValueError):
            build_adjacency_list(invalid_data)


class TestFixedErdFunctions(unittest.TestCase):
    def test_find_top_nodes_in_graph_handles_non_integer_top_n(self):
        """Test that find_top_nodes_in_graph now properly handles non-integer top_n values."""
        try:
            from mcli.lib.erd import find_top_nodes_in_graph

            # Load test data - create a simple mock graph data structure
            graph_data = {
                "graph": {
                    "m_vertices": [
                        {"id": "node1", "data": {"name": "Node 1"}},
                        {"id": "node2", "data": {"name": "Node 2"}},
                        {"id": "node3", "data": {"name": "Node 3"}},
                        {"id": "node4", "data": {"name": "Node 4"}},
                        {"id": "node5", "data": {"name": "Node 5"}},
                    ],
                    "m_edges": [
                        {"from": {"id": "node1"}, "to": {"id": "node2"}},
                        {"from": {"id": "node1"}, "to": {"id": "node3"}},
                        {"from": {"id": "node2"}, "to": {"id": "node4"}},
                        {"from": {"id": "node3"}, "to": {"id": "node5"}},
                    ],
                }
            }

            # Test with various non-integer values for top_n
            non_integer_values = [
                "5",  # String containing a number
                "five",  # String containing text
                None,  # None value
                5.5,  # Float
                {},  # Empty dict
                [],  # Empty list
            ]

            for value in non_integer_values:
                try:
                    result = find_top_nodes_in_graph(graph_data, top_n=value)
                    # If we get here, no exception was thrown
                    self.assertIsInstance(
                        result,
                        list,
                        f"With top_n={value}, expected list result but got {type(result)}",
                    )
                    print(f"✓ top_n={value} passed")
                except Exception as e:
                    self.fail(f"find_top_nodes_in_graph failed with top_n={value}: {e}")

            # Also test with a valid integer to ensure normal operation still works
            result = find_top_nodes_in_graph(graph_data, top_n=3)
            self.assertIsInstance(
                result, list, f"Expected list result with top_n=3, but got {type(result)}"
            )
            print(f"✓ top_n=3 returned a valid result")

            return True
        except ImportError:
            self.skipTest("Could not import mcli.lib.erd.find_top_nodes_in_graph")


if __name__ == "__main__":
    unittest.main()
