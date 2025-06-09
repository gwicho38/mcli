"""
Test harness for mcli tests.
This module provides sample data and utility functions for testing.
"""

import os
import json
import tempfile
from pathlib import Path

# Sample graph data that represents a subset of realGraph.json
SAMPLE_GRAPH_DATA = {
    "type": "GlobalCanvasMergeGraphResult",
    "graph": {
        "m_vertices": {
            "type": "Array<GlobalCanvasGraphNode<GlobalCanvasGraphNodeData>>",
            "value": [
                {
                    "type": "GlobalCanvasGraphEntityNode",
                    "id": "ReliabilityAssetCase",
                    "category": "Entity",
                    "data": {
                        "name": "ReliabilityAssetCase",
                        "categoryMetadataIdentifier": "ReliabilityAssetCase",
                        "package": "reliabilityAssetCase"
                    }
                },
                {
                    "type": "GlobalCanvasGraphEntityNode",
                    "id": "MaintenanceAssetAlert",
                    "category": "Entity",
                    "data": {
                        "name": "MaintenanceAssetAlert",
                        "categoryMetadataIdentifier": "MaintenanceAssetAlert",
                        "package": "reliabilityAssetCase"
                    }
                },
                {
                    "type": "GlobalCanvasGraphEntityNode",
                    "id": "Asset",
                    "category": "Entity",
                    "data": {
                        "name": "Asset",
                        "categoryMetadataIdentifier": "Asset",
                        "package": "reliabilityAssetCase"
                    }
                },
                {
                    "type": "GlobalCanvasGraphEntityNode",
                    "id": "AssetType",
                    "category": "Entity",
                    "data": {
                        "name": "AssetType",
                        "categoryMetadataIdentifier": "AssetType",
                        "package": "reliabilityAssetCase"
                    }
                },
                {
                    "type": "GlobalCanvasGraphEntityNode",
                    "id": "MaintenanceAction",
                    "category": "Entity",
                    "data": {
                        "name": "MaintenanceAction",
                        "categoryMetadataIdentifier": "MaintenanceAction",
                        "package": "reliabilityAssetCase"
                    }
                },
                {
                    "type": "GlobalCanvasGraphEntityNode",
                    "id": "ReadinessAssetAlert",
                    "category": "Entity",
                    "data": {
                        "name": "ReadinessAssetAlert",
                        "categoryMetadataIdentifier": "ReadinessAssetAlert",
                        "package": "reliabilityAssetCase"
                    }
                },
                {
                    "type": "GlobalCanvasGraphEntityNode",
                    "id": "ReadinessOperation",
                    "category": "Entity",
                    "data": {
                        "name": "ReadinessOperation",
                        "categoryMetadataIdentifier": "ReadinessOperation",
                        "package": "reliabilityAssetCase"
                    }
                }
            ]
        },
        "m_edges": {
            "type": "Array<GlobalCanvasGraphEdge<GlobalCanvasGraphEdgeData>>",
            "value": [
                {
                    "type": "GlobalCanvasGraphEdge",
                    "source": "ReliabilityAssetCase",
                    "target": "Asset",
                    "data": {
                        "type": "relation"
                    }
                },
                {
                    "type": "GlobalCanvasGraphEdge",
                    "source": "Asset",
                    "target": "AssetType",
                    "data": {
                        "type": "relation"
                    }
                },
                {
                    "type": "GlobalCanvasGraphEdge",
                    "source": "ReliabilityAssetCase",
                    "target": "MaintenanceAction",
                    "data": {
                        "type": "relation"
                    }
                },
                {
                    "type": "GlobalCanvasGraphEdge",
                    "source": "ReliabilityAssetCase",
                    "target": "MaintenanceAssetAlert",
                    "data": {
                        "type": "relation"
                    }
                },
                {
                    "type": "GlobalCanvasGraphEdge",
                    "source": "ReadinessOperation",
                    "target": "Asset",
                    "data": {
                        "type": "relation"
                    }
                },
                {
                    "type": "GlobalCanvasGraphEdge",
                    "source": "ReadinessAssetAlert",
                    "target": "Asset",
                    "data": {
                        "type": "relation"
                    }
                },
                {
                    "type": "GlobalCanvasGraphEdge",
                    "source": "ReadinessAssetAlert",
                    "target": "ReadinessOperation",
                    "data": {
                        "type": "relation"
                    }
                }
            ]
        }
    }
}

class TestData:
    """Class to manage test data for tests"""
    
    @staticmethod
    def create_temp_json_file():
        """Create a temporary JSON file with sample data
        
        Returns:
            tuple: (file_path, temp_dir) where file_path is the path to the JSON file
                  and temp_dir is the temporary directory object (keep this to cleanup later)
        """
        temp_dir = tempfile.TemporaryDirectory()
        json_file_path = os.path.join(temp_dir.name, 'test_graph.json')
        
        with open(json_file_path, 'w') as f:
            json.dump(SAMPLE_GRAPH_DATA, f)
        
        return json_file_path, temp_dir
    
    @staticmethod
    def cleanup_temp_dir(temp_dir):
        """Clean up the temporary directory
        
        Args:
            temp_dir: The temporary directory object to clean up
        """
        temp_dir.cleanup()


# Function to create a mock realGraph.json file for testing
def create_mock_graph_json(file_path=None):
    """Create a mock realGraph.json file for testing
    
    Args:
        file_path: Optional path to write the file. If None, uses the tests directory.
    
    Returns:
        str: Path to the created mock file
    """
    if file_path is None:
        # Use a file in the tests directory
        file_path = os.path.join(os.path.dirname(__file__), 'mock_real_graph.json')
    
    with open(file_path, 'w') as f:
        json.dump(SAMPLE_GRAPH_DATA, f, indent=2)
    
    return file_path