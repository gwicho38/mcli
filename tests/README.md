# Testing the MCLI Generate Graph Functionality

This directory contains tests and demo scripts for the `generate_graph.py` module which transforms the realGraph.json data into a hierarchical model for visualization.

## Test Files

- `test_generate_graph.py` - Unit tests for the generate_graph module
- `test_harness.py` - Test harness with sample data and utility functions
- `run_tests.py` - Script to run all tests or specific test files
- `demo_generate_graph.py` - Demo script showing how to use the modified_do_erd function

## Running Tests

To run all tests:

```bash
cd /path/to/mcli
python tests/run_tests.py
```

To run a specific test file:

```bash
python tests/run_tests.py generate_graph  # Runs test_generate_graph.py
```

## Demo Script

The demo script demonstrates how to use the modified_do_erd function with mocked data:

```bash
cd /path/to/mcli
python tests/demo_generate_graph.py
```

It will:
1. Create a mock realGraph.json file with sample data
2. Patch the file path to use this mock file
3. Run modified_do_erd with a max_depth of 2
4. Display information about the generated files
5. Clean up the mock file

## Running Unit Tests from the Demo Script

You can also run the unit tests directly from the demo script:

```bash
python tests/demo_generate_graph.py --test
```

## Test Structure

The tests are structured to test each part of the graph processing pipeline:

1. Loading graph data from a JSON file
2. Building an adjacency list from the graph data
3. Counting descendants for nodes
4. Finding top-level nodes based on descendant count
5. Building a hierarchical graph from top-level nodes
6. Creating a DOT graph from the hierarchical model
7. Generating DOT and PNG files

## Sample Data

The `test_harness.py` file contains a simplified version of the realGraph.json data structure with nodes and edges representing entities in the reliability asset case domain.