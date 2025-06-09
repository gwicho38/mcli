#!/usr/bin/env python3
"""
Test script for generate_graph.py - Creates a comprehensive sample dataset
that mimics the structure of the original realGraph.json file.
"""
import json
import os
import pydot
import time
import sys

# Add the src directory to the path so we can import generate_graph
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from mcli.app.readiness.generate_graph import (
    build_adjacency_list, count_descendants, find_top_level_nodes,
    build_hierarchical_graph, create_dot_graph, extract_fields_from_node
)

def create_comprehensive_sample_data():
    """
    Create a comprehensive sample dataset that mimics the structure of realGraph.json
    but with more detailed entity and field definitions.
    """
    # Define entity types with detailed field definitions
    entity_types = [
        {
            "type": "GlobalCanvasGraphEntityNode",
            "id": "ReliabilityAssetCase",
            "category": "Entity",
            "data": {
                "name": "ReliabilityAssetCase",
                "categoryMetadataIdentifier": "ReliabilityAssetCase",
                "package": "reliabilityAssetCase",
                "fields": [
                    {"name": "vehicleAssetClass", "type": "AssetClass"},
                    {"name": "currentState", "type": "CaseState"},
                    {"name": "createdTimestamp", "type": "DateTimeType"},
                    {"name": "lastUpdatedTimestamp", "type": "DateTimeType"},
                    {"name": "caseId", "type": "StringType"},
                    {"name": "priority", "type": "IntegerType"},
                    {"name": "reliabilityAssetAlert", "type": "ReliabilityAssetAlert"},
                    {"name": "asset", "type": "Asset"},
                    {"name": "assetSerial", "type": "StringType"}
                ]
            }
        },
        {
            "type": "GlobalCanvasGraphEntityNode",
            "id": "ReliabilityAssetAlert",
            "category": "Entity",
            "data": {
                "name": "ReliabilityAssetAlert",
                "categoryMetadataIdentifier": "ReliabilityAssetAlert",
                "package": "reliabilityAssetAlert",
                "fields": [
                    {"name": "alertId", "type": "StringType"},
                    {"name": "createdTimestamp", "type": "DateTimeType"},
                    {"name": "priority", "type": "IntegerType"},
                    {"name": "state", "type": "AlertState"},
                    {"name": "asset", "type": "Asset"},
                    {"name": "failureMode", "type": "FailureMode"},
                    {"name": "adjudicatedMaintenanceAction", "type": "AdjudicatedMaintenanceAction"}
                ]
            }
        },
        {
            "type": "GlobalCanvasGraphEntityNode",
            "id": "Asset",
            "category": "Entity",
            "data": {
                "name": "Asset",
                "categoryMetadataIdentifier": "Asset",
                "package": "asset",
                "fields": [
                    {"name": "assetId", "type": "StringType"},
                    {"name": "serialNumber", "type": "StringType"},
                    {"name": "assetClass", "type": "AssetClass"},
                    {"name": "location", "type": "Location"},
                    {"name": "status", "type": "AssetStatus"},
                    {"name": "operationalState", "type": "OperationalState"},
                    {"name": "lastUpdatedTimestamp", "type": "DateTimeType"}
                ]
            }
        },
        {
            "type": "GlobalCanvasGraphEntityNode",
            "id": "AssetClass",
            "category": "Entity",
            "data": {
                "name": "AssetClass",
                "categoryMetadataIdentifier": "AssetClass",
                "package": "asset",
                "fields": [
                    {"name": "classId", "type": "StringType"},
                    {"name": "name", "type": "StringType"},
                    {"name": "description", "type": "StringType"},
                    {"name": "category", "type": "StringType"}
                ]
            }
        },
        {
            "type": "GlobalCanvasGraphEntityNode",
            "id": "Location",
            "category": "Entity",
            "data": {
                "name": "Location",
                "categoryMetadataIdentifier": "Location",
                "package": "common",
                "fields": [
                    {"name": "locationId", "type": "StringType"},
                    {"name": "name", "type": "StringType"},
                    {"name": "type", "type": "LocationType"},
                    {"name": "geoCoordinates", "type": "GeoCoordinates"}
                ]
            }
        },
        {
            "type": "GlobalCanvasGraphEntityNode",
            "id": "GeoCoordinates",
            "category": "Entity",
            "data": {
                "name": "GeoCoordinates",
                "categoryMetadataIdentifier": "GeoCoordinates",
                "package": "common",
                "fields": [
                    {"name": "latitude", "type": "DoubleType"},
                    {"name": "longitude", "type": "DoubleType"},
                    {"name": "altitude", "type": "DoubleType"}
                ]
            }
        },
        {
            "type": "GlobalCanvasGraphEntityNode",
            "id": "AdjudicatedMaintenanceAction",
            "category": "Entity",
            "data": {
                "name": "AdjudicatedMaintenanceAction",
                "categoryMetadataIdentifier": "AdjudicatedMaintenanceAction",
                "package": "maintenance",
                "fields": [
                    {"name": "actionId", "type": "StringType"},
                    {"name": "description", "type": "StringType"},
                    {"name": "type", "type": "MaintenanceActionType"},
                    {"name": "status", "type": "MaintenanceActionStatus"},
                    {"name": "estimatedCompletionTime", "type": "DateTimeType"},
                    {"name": "assignedTechnician", "type": "Technician"},
                    {"name": "asset", "type": "Asset"}
                ]
            }
        },
        {
            "type": "GlobalCanvasGraphEntityNode",
            "id": "Technician",
            "category": "Entity",
            "data": {
                "name": "Technician",
                "categoryMetadataIdentifier": "Technician", 
                "package": "personnel",
                "fields": [
                    {"name": "technicianId", "type": "StringType"},
                    {"name": "name", "type": "StringType"},
                    {"name": "specialization", "type": "StringType"},
                    {"name": "certification", "type": "Certification"}
                ]
            }
        },
        {
            "type": "GlobalCanvasGraphEntityNode",
            "id": "FailureMode",
            "category": "Entity",
            "data": {
                "name": "FailureMode",
                "categoryMetadataIdentifier": "FailureMode",
                "package": "reliability",
                "fields": [
                    {"name": "failureModeId", "type": "StringType"},
                    {"name": "description", "type": "StringType"},
                    {"name": "severity", "type": "IntegerType"},
                    {"name": "assetClass", "type": "AssetClass"},
                    {"name": "recommendedAction", "type": "MaintenanceAction"}
                ]
            }
        },
        {
            "type": "GlobalCanvasGraphEntityNode",
            "id": "AirBase",
            "category": "Entity",
            "data": {
                "name": "AirBase", 
                "categoryMetadataIdentifier": "AirBase",
                "package": "facility",
                "fields": [
                    {"name": "baseId", "type": "StringType"},
                    {"name": "name", "type": "StringType"},
                    {"name": "location", "type": "Location"},
                    {"name": "commandingOfficer", "type": "Personnel"},
                    {"name": "status", "type": "BaseStatus"}
                ]
            }
        },
        {
            "type": "GlobalCanvasGraphEntityNode",
            "id": "MaintenanceAction",
            "category": "Entity",
            "data": {
                "name": "MaintenanceAction",
                "categoryMetadataIdentifier": "MaintenanceAction",
                "package": "maintenance",
                "fields": [
                    {"name": "actionId", "type": "StringType"},
                    {"name": "description", "type": "StringType"},
                    {"name": "type", "type": "MaintenanceActionType"},
                    {"name": "estimatedDuration", "type": "DoubleType"},
                    {"name": "requiredParts", "type": "Part[]"},
                    {"name": "instructions", "type": "StringType"}
                ]
            }
        },
        {
            "type": "GlobalCanvasGraphEntityNode",
            "id": "Part",
            "category": "Entity",
            "data": {
                "name": "Part",
                "categoryMetadataIdentifier": "Part",
                "package": "inventory",
                "fields": [
                    {"name": "partId", "type": "StringType"},
                    {"name": "name", "type": "StringType"},
                    {"name": "nsn", "type": "StringType"},
                    {"name": "stockLevel", "type": "IntegerType"},
                    {"name": "supplierInfo", "type": "Supplier"}
                ]
            }
        },
        {
            "type": "GlobalCanvasGraphEntityNode",
            "id": "Supplier",
            "category": "Entity",
            "data": {
                "name": "Supplier",
                "categoryMetadataIdentifier": "Supplier",
                "package": "inventory",
                "fields": [
                    {"name": "supplierId", "type": "StringType"},
                    {"name": "name", "type": "StringType"},
                    {"name": "contactInfo", "type": "ContactInfo"},
                    {"name": "leadTime", "type": "DoubleType"}
                ]
            }
        },
        {
            "type": "GlobalCanvasGraphEntityNode",
            "id": "ReadinessOperation",
            "category": "Entity",
            "data": {
                "name": "ReadinessOperation",
                "categoryMetadataIdentifier": "ReadinessOperation",
                "package": "readiness",
                "fields": [
                    {"name": "operationId", "type": "StringType"},
                    {"name": "name", "type": "StringType"},
                    {"name": "startDate", "type": "DateTimeType"},
                    {"name": "endDate", "type": "DateTimeType"},
                    {"name": "status", "type": "OperationStatus"},
                    {"name": "location", "type": "Location"},
                    {"name": "commandingOfficer", "type": "Personnel"}
                ]
            }
        },
        {
            "type": "GlobalCanvasGraphEntityNode",
            "id": "ReliabilityAssetToReadinessOperationRelation",
            "category": "Entity",
            "data": {
                "name": "ReliabilityAssetToReadinessOperationRelation",
                "categoryMetadataIdentifier": "ReliabilityAssetToReadinessOperationRelation",
                "package": "relations",
                "fields": [
                    {"name": "id", "type": "StringType"},
                    {"name": "asset", "type": "Asset"},
                    {"name": "operation", "type": "ReadinessOperation"},
                    {"name": "startDate", "type": "DateTimeType"},
                    {"name": "endDate", "type": "DateTimeType"},
                    {"name": "status", "type": "RelationStatus"}
                ]
            }
        },
        {
            "type": "GlobalCanvasGraphEntityNode",
            "id": "Personnel",
            "category": "Entity",
            "data": {
                "name": "Personnel",
                "categoryMetadataIdentifier": "Personnel",
                "package": "personnel",
                "fields": [
                    {"name": "personnelId", "type": "StringType"},
                    {"name": "name", "type": "StringType"},
                    {"name": "rank", "type": "Rank"},
                    {"name": "position", "type": "StringType"},
                    {"name": "contactInfo", "type": "ContactInfo"}
                ]
            }
        },
        {
            "type": "GlobalCanvasGraphEntityNode",
            "id": "ContactInfo",
            "category": "Entity",
            "data": {
                "name": "ContactInfo",
                "categoryMetadataIdentifier": "ContactInfo",
                "package": "common",
                "fields": [
                    {"name": "email", "type": "StringType"},
                    {"name": "phone", "type": "StringType"},
                    {"name": "address", "type": "Address"}
                ]
            }
        },
        {
            "type": "GlobalCanvasGraphEntityNode",
            "id": "Address",
            "category": "Entity",
            "data": {
                "name": "Address",
                "categoryMetadataIdentifier": "Address",
                "package": "common",
                "fields": [
                    {"name": "street", "type": "StringType"},
                    {"name": "city", "type": "StringType"},
                    {"name": "state", "type": "StringType"},
                    {"name": "zipCode", "type": "StringType"},
                    {"name": "country", "type": "StringType"}
                ]
            }
        },
        {
            "type": "GlobalCanvasGraphEntityNode",
            "id": "MissionType", 
            "category": "Entity",
            "data": {
                "name": "MissionType",
                "categoryMetadataIdentifier": "MissionType",
                "package": "mission",
                "fields": [
                    {"name": "missionTypeId", "type": "StringType"},
                    {"name": "name", "type": "StringType"},
                    {"name": "description", "type": "StringType"},
                    {"name": "requiredAssetClasses", "type": "AssetClass[]"}
                ]
            }
        }
    ]

    # Define edges (relationships between entities)
    edges = [
        # ReliabilityAssetCase relationships
        {"source": "ReliabilityAssetCase", "target": "ReliabilityAssetAlert"},
        {"source": "ReliabilityAssetCase", "target": "Asset"},
        {"source": "ReliabilityAssetCase", "target": "AssetClass"},
        
        # ReliabilityAssetAlert relationships
        {"source": "ReliabilityAssetAlert", "target": "Asset"},
        {"source": "ReliabilityAssetAlert", "target": "FailureMode"},
        {"source": "ReliabilityAssetAlert", "target": "AdjudicatedMaintenanceAction"},
        
        # Asset relationships
        {"source": "Asset", "target": "AssetClass"},
        {"source": "Asset", "target": "Location"},
        
        # Location relationships
        {"source": "Location", "target": "GeoCoordinates"},
        
        # AdjudicatedMaintenanceAction relationships
        {"source": "AdjudicatedMaintenanceAction", "target": "Asset"},
        {"source": "AdjudicatedMaintenanceAction", "target": "Technician"},
        {"source": "AdjudicatedMaintenanceAction", "target": "MaintenanceAction"},
        
        # FailureMode relationships
        {"source": "FailureMode", "target": "AssetClass"},
        {"source": "FailureMode", "target": "MaintenanceAction"},
        
        # MaintenanceAction relationships
        {"source": "MaintenanceAction", "target": "Part"},
        
        # Part relationships
        {"source": "Part", "target": "Supplier"},
        
        # AirBase relationships
        {"source": "AirBase", "target": "Location"},
        {"source": "AirBase", "target": "Personnel"},
        
        # ReadinessOperation relationships
        {"source": "ReadinessOperation", "target": "Location"},
        {"source": "ReadinessOperation", "target": "Personnel"},
        
        # ReliabilityAssetToReadinessOperationRelation relationships
        {"source": "ReliabilityAssetToReadinessOperationRelation", "target": "Asset"},
        {"source": "ReliabilityAssetToReadinessOperationRelation", "target": "ReadinessOperation"},
        
        # Additional relations to create a more complex graph
        {"source": "Asset", "target": "MaintenanceAction"},
        {"source": "Asset", "target": "ReadinessOperation"},
        {"source": "Personnel", "target": "ContactInfo"},
        {"source": "Supplier", "target": "ContactInfo"},
        {"source": "ContactInfo", "target": "Address"},
        {"source": "ReadinessOperation", "target": "MissionType"},
        {"source": "MissionType", "target": "AssetClass"},
        
        # Bidirectional relationships
        {"source": "ReliabilityAssetAlert", "target": "ReliabilityAssetCase"},
        {"source": "AdjudicatedMaintenanceAction", "target": "ReliabilityAssetAlert"},
        {"source": "Location", "target": "AirBase"}
    ]

    # Combine all entities and edges into a format similar to realGraph.json
    graph_data = {
        "graph": {
            "m_vertices": {
                "value": entity_types
            },
            "m_edges": {
                "value": edges
            }
        }
    }
    
    return graph_data

def fix_json_file(input_path, output_path):
    """
    Attempt to fix common JSON errors in a file.
    """
    with open(input_path, 'r') as f:
        content = f.read()
    
    # Try to fix the JSON by looking for common errors
    # 1. Missing quotes around property names
    import re
    
    # This regex finds patterns like {key: where 'key' doesn't have quotes
    # and adds quotes around the key
    corrected = re.sub(r'{\s*([a-zA-Z0-9_]+)\s*:', r'{"\1":', content)
    
    # 2. Missing quotes around property values (if they're not numbers or booleans)
    corrected = re.sub(r':\s*([a-zA-Z0-9_]+)\s*[,}]', r':"\1",', corrected)
    
    # Fix trailing commas in arrays and objects
    corrected = re.sub(r',\s*}', r'}', corrected)
    corrected = re.sub(r',\s*]', r']', corrected)
    
    with open(output_path, 'w') as f:
        f.write(corrected)
    
    print(f"Attempted to fix JSON file and saved to {output_path}")
    return output_path

def test_hierarchical_transformation(max_depth=2, top_n=5):
    """
    Test the hierarchical transformation with the actual realGraph.json data if possible,
    otherwise fall back to the comprehensive sample dataset.
    """
    real_graph_path = '/Users/lefv/repos/mcli/realGraph.json'
    
    try:
        # Try a different approach - import from mcli.lib.erd
        print(f"Using mcli.lib.erd functions...")
        from mcli.lib.erd import find_top_nodes_in_graph, generate_erd_for_top_nodes
        
        # Test find_top_nodes_in_graph
        with open(real_graph_path, 'r') as f:
            graph_data = json.load(f)
        
        # Find top nodes
        top_graph_nodes = find_top_nodes_in_graph(graph_data, top_n=top_n)
        print(f"Found {len(top_graph_nodes)} top nodes:")
        for node_id, count in top_graph_nodes:
            print(f"- {node_id}: {count} descendants")
        
        # Test generate_erd_for_top_nodes
        print(f"\nGenerating ERDs for top nodes with depth {max_depth}...")
        files = generate_erd_for_top_nodes(real_graph_path, max_depth=max_depth, top_n=top_n)
        
        if files:
            print("\nGenerated ERD files:")
            for dot_file, png_file, count in files:
                print(f"- {png_file} with {count} descendants")
            return True
    except Exception as e:
        print(f"Error using mcli.lib.erd approach: {e}")
        import traceback
        print(traceback.format_exc())
    
    print("Falling back to comprehensive sample dataset")
    
    # Create sample data
    graph_data = create_comprehensive_sample_data()
    
    # Build adjacency list
    node_map, adj_list = build_adjacency_list(graph_data)
    
    # Find top-level nodes
    top_nodes = find_top_level_nodes(node_map, adj_list, top_n)
    print(f"Top {top_n} nodes with the most descendants:")
    for node in top_nodes:
        desc_count = count_descendants(node, adj_list)
        print(f"- {node}: {desc_count} descendants")
    
    # Build hierarchical graph
    hierarchy = build_hierarchical_graph(top_nodes, node_map, adj_list, max_depth)
    
    # Generate DOT graphs for visualization
    timestamp = str(int(time.time() * 1000000))
    
    # For each top-level node, create a separate visualization
    for root_node_id in top_nodes:
        # Count descendants for this node
        descendant_count = count_descendants(root_node_id, adj_list)
        
        # Create the DOT graph
        dot_graph = create_dot_graph(hierarchy, root_node_id, max_depth)
        
        # Define file paths
        depth_info = f"_depth{max_depth}"
        dot_file = f"{root_node_id}{depth_info}__{timestamp}.dot"
        png_file = f"{root_node_id}{depth_info}__{timestamp}.png"
        
        # Save the files
        dot_graph.write_raw(dot_file)
        dot_graph.write_png(png_file)
        
        print(f"Generated graph for {root_node_id} with {descendant_count} descendants:")
        print(f"- DOT file: {dot_file}")
        print(f"- PNG file: {png_file}")

if __name__ == "__main__":
    import sys
    
    # Default parameters
    max_depth = 2
    top_n = 5
    
    # Check command line arguments
    if len(sys.argv) > 1:
        max_depth = int(sys.argv[1])
    if len(sys.argv) > 2:
        top_n = int(sys.argv[2])
    
    print(f"Running test with max_depth={max_depth}, top_n={top_n}")
    test_hierarchical_transformation(max_depth, top_n)