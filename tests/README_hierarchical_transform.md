# Hierarchical Graph Transformation Tool

This tool transforms a graph (in JSON format with edges and vertices) into a hierarchical data model where the "top-level" nodes are selected based on having the most descendants (in other words, the largest reachable subgraphs beneath them).

## Features

- Identifies nodes with the largest reachable subgraphs by counting descendants
- Creates a hierarchical structure with these influential nodes as the top-level entries
- Visualizes the hierarchies with detailed node information in table format
- Colors nodes based on their depth in the hierarchy
- Generates both DOT and PNG output files

## How It Works

1. **Input**: A graph in JSON format with vertices and edges.
2. **Process**:
   - Build an adjacency list representation of the graph
   - Count descendants for each node using depth-first search
   - Identify top-level nodes as those with the most descendants
   - Build hierarchical models with these nodes as roots
   - Generate visual representations of each hierarchy
3. **Output**: DOT and PNG files for each top-level node's subgraph.

## Example Output

For a graph centered around ReliabilityAssetCase, the output shows the hierarchy with:
- The top node (ReliabilityAssetCase) in blue
- First-level descendants (Asset, MaintenanceAction, etc.) in light blue
- Second-level descendants (AssetType) in even lighter blue
- Detailed node information displayed in a table format
- Clear edges showing the relationships between nodes

## Integration with do_erd

This tool is designed to complement the existing `do_erd` function in `readiness.py`. While the traditional `do_erd` function requires a connection to a MCLI cluster to retrieve type information, this approach can work offline with a precomputed graph in JSON format.

The output format matches the detailed style of the ERD diagrams from `readiness.py`, but organizes the graph hierarchically based on descendant counts rather than explicit type relationships.

## Example Usage

```python
from demo_hierarchical_transform import transform_graph

# Load your graph data
with open('your_graph.json', 'r') as f:
    graph_data = json.load(f)

# Transform the graph into a hierarchical model
hierarchy, top_nodes = transform_graph(graph_data, max_depth=2, top_n=3)

# View the top-level nodes and their descendant counts
for node_id, count in top_nodes:
    print(f"{node_id}: {count} descendants")

# Examine the hierarchical structure
for root_node, subgraph in hierarchy.items():
    print(f"Root: {root_node}")
    print(f"  Children: {list(subgraph[root_node]['children'].keys())}")
```