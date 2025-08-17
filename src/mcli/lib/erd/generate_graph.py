import json
import os
import time
from collections import Counter, defaultdict
from pathlib import Path

import pydot


def load_graph_data(json_file_path):
    """Load the graph data from a JSON file."""
    try:
        with open(json_file_path, "r") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        raise ValueError(f"Error parsing JSON file {json_file_path}: {e}")
    except FileNotFoundError:
        raise FileNotFoundError(f"Graph data file not found: {json_file_path}")


def build_adjacency_list(graph_data):
    """Build an adjacency list from the graph data."""
    try:
        # Extract vertices and edges
        vertices = graph_data["graph"]["m_vertices"]["value"]
        edges = graph_data["graph"]["m_edges"]["value"]

        # Create mapping of IDs to node info
        node_map = {node["id"]: node for node in vertices}

        # Build adjacency list (directed graph)
        adj_list = defaultdict(list)
        for edge in edges:
            source = edge["source"]
            target = edge["target"]
            adj_list[source].append(target)

        return node_map, adj_list
    except KeyError as e:
        raise ValueError(
            f"Invalid graph data structure: missing key {e}. Check the format of your graph data file."
        )
    except TypeError as e:
        raise ValueError(
            f"Invalid graph data structure: {e}. Check the format of your graph data file."
        )


def count_descendants(node_id, adj_list, visited=None):
    """Count the number of descendants for a node (reachable subgraph size)."""
    if visited is None:
        visited = set()

    if node_id in visited:
        return 0

    visited.add(node_id)
    count = 1  # Count the node itself

    for neighbor in adj_list.get(node_id, []):
        if neighbor not in visited:
            count += count_descendants(neighbor, adj_list, visited)

    return count


def find_top_level_nodes(node_map, adj_list, top_n=10):
    """Find the top N nodes with the most descendants."""
    # Count descendants for each node
    descendant_counts = {}
    for node_id in node_map:
        descendant_counts[node_id] = count_descendants(node_id, adj_list)

    # Sort nodes by descendant count
    sorted_nodes = sorted(descendant_counts.items(), key=lambda x: x[1], reverse=True)

    # Return top N nodes
    return [node_id for node_id, count in sorted_nodes[:top_n]]


def build_hierarchical_graph(top_level_nodes, node_map, adj_list, max_depth=2):
    """Build a hierarchical graph with top-level nodes as roots."""
    hierarchy = {}

    # For each top-level node, build its subgraph
    for node_id in top_level_nodes:
        subgraph = {}
        visited = set()
        build_subgraph(node_id, node_map, adj_list, subgraph, visited, 0, max_depth)
        hierarchy[node_id] = subgraph

    return hierarchy


def build_subgraph(node_id, node_map, adj_list, subgraph, visited, current_depth, max_depth):
    """Recursively build a subgraph for a node up to max_depth."""
    if node_id in visited or current_depth > max_depth:
        return

    visited.add(node_id)
    subgraph[node_id] = {"node_info": node_map[node_id], "children": {}}

    if current_depth < max_depth:
        for child_id in adj_list.get(node_id, []):
            build_subgraph(
                child_id,
                node_map,
                adj_list,
                subgraph[node_id]["children"],
                visited,
                current_depth + 1,
                max_depth,
            )


def extract_fields_from_node(node_data):
    """Extract fields from node data for display in the table."""
    fields = []

    # If this is an entity node, extract fields from the data
    if node_data.get("category") == "Entity":
        # Get fields from node data
        if "data" in node_data:
            # Add package as a field
            if "package" in node_data["data"]:
                fields.append(("package", node_data["data"]["package"]))

            # Add name if available
            if "name" in node_data["data"]:
                fields.append(("name", node_data["data"]["name"]))

            # Add categoryMetadataIdentifier if available
            if "categoryMetadataIdentifier" in node_data["data"]:
                fields.append(("type", node_data["data"]["categoryMetadataIdentifier"]))

    # Add id field
    if "id" in node_data:
        fields.append(("id", node_data["id"]))

    # Add category field
    if "category" in node_data:
        fields.append(("category", node_data["category"]))

    return fields


def create_table_html(entity, node_data, font_size=10):
    """Create HTML table-style label for a node."""
    fields = extract_fields_from_node(node_data)

    # Sanitize entity name
    entity = entity.replace(".", "_")
    entity = entity.replace("<", "[")
    entity = entity.replace(">", "]")

    # Start the HTML table
    html = f'<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="2">'

    # Header row
    html += f'<TR><TD PORT="header" COLSPAN="2" BGCOLOR="lightgrey"><B><FONT POINT-SIZE="{font_size+2}">{entity}</FONT></B></TD></TR>'

    # Add "Data" section if there are fields
    if fields:
        html += f'<TR><TD COLSPAN="2" BGCOLOR="#E0E0E0"><B><FONT POINT-SIZE="{font_size}">Fields</FONT></B></TD></TR>'

        # Add each field
        for field_name, field_value in fields:
            # Convert < and > to [ and ] for HTML compatibility
            if field_value:
                field_value = str(field_value).replace("<", "[").replace(">", "]")
            html += f'<TR><TD><FONT POINT-SIZE="{font_size}">{field_name}</FONT></TD><TD><FONT POINT-SIZE="{font_size}">{field_value}</FONT></TD></TR>'

    # Close the table
    html += "</TABLE>>"
    return html


def create_dot_graph(hierarchy, root_node_id, max_depth=2):
    """Create a DOT graph visualization from the hierarchical model."""
    graph = pydot.Dot(
        graph_type="digraph",
        rankdir="TB",
        splines="ortho",
        bgcolor="white",
        label=f"Hierarchical Model for {root_node_id}",
        fontsize=14,
        labelloc="t",
    )

    # Track nodes that have been added to avoid duplicates
    added_nodes = set()
    # Track node depths for coloring
    node_depths = {root_node_id: 0}

    # Add nodes and edges recursively
    add_nodes_and_edges(graph, hierarchy, root_node_id, added_nodes, node_depths, max_depth)

    # Create a subgraph to force the root node to be at the top
    root_subgraph = pydot.Subgraph(rank="min")
    root_subgraph.add_node(pydot.Node(root_node_id))
    graph.add_subgraph(root_subgraph)

    return graph


def add_nodes_and_edges(
    graph, hierarchy, node_id, added_nodes, node_depths, max_depth, current_depth=0
):
    """Recursively add nodes and edges to the graph."""
    if current_depth > max_depth or node_id in added_nodes:
        return

    # Find the node data
    # For root nodes, it's in hierarchy[node_id][node_id]
    # For other nodes, we need to look through the hierarchy to find them
    if node_id in hierarchy:
        node_data = hierarchy[node_id][node_id]["node_info"]
    else:
        # Look for this node in other nodes' children
        for root in hierarchy:
            found = find_node_in_hierarchy(hierarchy[root], node_id)
            if found:
                node_data = found
                break
        else:
            # Node not found in hierarchy
            print(f"Warning: Node {node_id} not found in hierarchy")
            return

    # Record node depth
    node_depths[node_id] = current_depth

    # Create HTML table label for this node
    node_label = create_table_html(node_id, node_data)

    # Determine node color based on depth
    if current_depth == 0:
        bg_color = "lightblue"  # Root node
    elif current_depth == 1:
        bg_color = "#E6F5FF"  # First level
    else:
        bg_color = "#F0F8FF"  # Deeper levels

    # Create the node with HTML table label
    dot_node = pydot.Node(
        node_id,
        shape="none",  # Using 'none' to allow custom HTML table
        label=node_label,
        style="filled",
        fillcolor=bg_color,
        margin="0",
    )

    graph.add_node(dot_node)
    added_nodes.add(node_id)

    # Add edges to children if not at max depth
    if current_depth < max_depth:
        # Get children - different path depending on whether this is a root node
        if node_id in hierarchy:
            children = hierarchy[node_id][node_id]["children"]
        else:
            # Look up this node's children
            children_container = find_children_container(hierarchy, node_id)
            if not children_container:
                return
            children = children_container

        for child_id in children:
            # Add an edge from this node to the child
            edge = pydot.Edge(
                node_id,
                child_id,
                dir="both",
                arrowtail="none",
                arrowhead="normal",
                constraint=True,
                color="black",
                penwidth=1.5,
            )
            graph.add_edge(edge)

            # Recursively add the child node and its children
            if child_id not in added_nodes:
                add_nodes_and_edges(
                    graph,
                    hierarchy,
                    child_id,
                    added_nodes,
                    node_depths,
                    max_depth,
                    current_depth + 1,
                )


def find_node_in_hierarchy(subgraph, target_node):
    """Find a node's data in the hierarchy."""
    # Check each node in the subgraph
    for node_id, node_data in subgraph.items():
        if node_id == target_node:
            return node_data["node_info"]

        # Recursively check children
        if "children" in node_data:
            result = find_node_in_hierarchy(node_data["children"], target_node)
            if result:
                return result

    return None


def find_children_container(hierarchy, parent_node):
    """Find a node's children container in the hierarchy."""
    # Check each root node
    for root_id, root_data in hierarchy.items():
        # Check if the target is a direct child of this root
        if parent_node in root_data[root_id]["children"]:
            return root_data[root_id]["children"][parent_node]["children"]

        # Look in the children of this root's children
        for child_id, child_data in root_data[root_id]["children"].items():
            if parent_node == child_id:
                return child_data["children"]

            # Could add deeper searching if needed

    return {}


def transform_graph(graph_data, max_depth=3, top_n=5):
    """
    Transform a graph into a hierarchical model based on descendant counts.

    Args:
        graph_data: Dictionary containing graph data with vertices and edges
        max_depth: Maximum depth for building the hierarchical model
        top_n: Number of top-level nodes to include

    Returns:
        tuple: (hierarchy, top_nodes) - Hierarchical model and list of top nodes
    """
    # Build adjacency list from the graph data
    node_map, adj_list = build_adjacency_list(graph_data)

    # Find the top N nodes based on descendant count
    top_nodes = find_top_level_nodes(node_map, adj_list, top_n)

    # Build hierarchical graph with these as roots
    hierarchy = build_hierarchical_graph(top_nodes, node_map, adj_list, max_depth)

    # Count descendants for the top nodes
    top_nodes_with_counts = [(node, count_descendants(node, adj_list)) for node in top_nodes]

    return hierarchy, top_nodes_with_counts


def modified_do_erd(max_depth=3, top_n=5):
    """
    Generate ERD diagrams based on hierarchical model where top-level nodes
    are those with the largest reachable subgraphs.

    Args:
        max_depth: Maximum depth for the hierarchical model (default: 3)
        top_n: Number of top-level nodes to include (default: 5)

    Returns:
        tuple: (dot_file, png_file) - Paths to the generated files for the first top node
    """
    from mcli.lib.logger.logger import get_logger

    logger = get_logger(__name__)

    try:
        # Define the path to the JSON file
        json_file_path = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            ),
            "realGraph.json",
        )

        logger.info(f"Using graph data from: {json_file_path}")

        # Validate the file exists before attempting to load it
        if not os.path.exists(json_file_path):
            logger.error(f"Graph data file not found: {json_file_path}")
            raise FileNotFoundError(f"Graph data file not found: {json_file_path}")

        # Load the graph data
        graph_data = load_graph_data(json_file_path)

        # Create output directory if it doesn't exist
        base_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
        )
        output_dir = os.path.join(base_dir, "output")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logger.info(f"Created output directory: {output_dir}")

        # Transform the graph into a hierarchical model
        logger.info(f"Transforming graph with max_depth={max_depth}, top_n={top_n}")
        hierarchy, top_nodes = transform_graph(graph_data, max_depth, top_n)

        if not top_nodes:
            logger.warning("No top-level nodes found in the graph.")
            return None

        # Generate file paths
        timestamp = str(int(time.time() * 1000000))
        generated_files = []

        # For each top-level node, generate DOT and PNG files
        for root_node_id, descendant_count in top_nodes:
            try:
                # Create the DOT graph
                logger.info(f"Creating DOT graph for {root_node_id}")
                dot_graph = create_dot_graph(hierarchy, root_node_id, max_depth)

                # Define file paths - save to output directory
                depth_info = f"_depth{max_depth}"
                dot_file = os.path.join(output_dir, f"{root_node_id}{depth_info}_{timestamp}.dot")
                png_file = os.path.join(output_dir, f"{root_node_id}{depth_info}_{timestamp}.png")

                # Save the files
                logger.info(f"Saving DOT file to {dot_file}")
                dot_graph.write_raw(dot_file)

                logger.info(f"Generating PNG file to {png_file}")
                dot_graph.write_png(png_file)

                # For return values, use just the filenames without full paths
                dot_filename = os.path.basename(dot_file)
                png_filename = os.path.basename(png_file)

                generated_files.append((dot_filename, png_filename, root_node_id, descendant_count))
                logger.info(
                    f"Generated graph for {root_node_id} with {descendant_count} descendants: {png_filename}"
                )
            except Exception as e:
                logger.error(f"Error generating graph for node {root_node_id}: {e}")

        # Return the first top-level node's file names for compatibility
        if generated_files:
            return generated_files[0][0], generated_files[0][1]
        return None
    except Exception as e:
        logger.error(f"Error in modified_do_erd: {e}")
        raise


if __name__ == "__main__":
    modified_do_erd(max_depth=3)
