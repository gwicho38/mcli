"""
Generic Entity Relationship Diagram (ERD) generation utilities.
This module provides functions and classes for generating Entity Relationship Diagrams (ERDs)
from generic type metadata or from graph data files. It supports both MCLI-specific type
systems and generic type system interfaces.
"""

import json
import os
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List, Optional, Protocol, Set, Tuple, Union
from urllib.request import urlopen

import click
import pydot

from mcli.lib.auth.mcli_manager import MCLIManager
from mcli.lib.logger.logger import get_logger


class TypeSystem(Protocol):
    """Protocol for generic type system interface."""

    def get_type(self, name: str) -> Any:
        """Get a type by name."""
        ...

    def get_all_types(self) -> List[str]:
        """Get all available type names."""
        ...

    def get_package_types(self, package_name: str) -> List[str]:
        """Get all types in a specific package."""
        ...

    def create_type_metadata(self, type_obj: Any) -> "TypeMetadata":
        """Create type metadata from a type object."""
        ...


class TypeMetadata(Protocol):
    """Protocol for type metadata interface."""

    def get_name(self) -> str:
        """Get the type name."""
        ...

    def get_fields(self) -> Dict[str, Any]:
        """Get field definitions."""
        ...

    def get_methods(self) -> List[str]:
        """Get method names."""
        ...

    def get_related_types(self) -> Set[str]:
        """Get names of related types."""
        ...


class MCLITypeSystem:
    """MCLI-specific implementation of TypeSystem."""

    def __init__(self, mcli_obj):
        self.mcli_obj = mcli_obj

    def get_type(self, name: str) -> Any:
        """Get a type by name from MCLI namespace."""
        if "." in name:
            parts = name.split(".")
            current_obj = self.mcli_obj
            for part in parts:
                current_obj = getattr(current_obj, part)
            return current_obj
        else:
            return getattr(self.mcli_obj, name)

    def get_all_types(self) -> List[str]:
        """Get all available type names from MCLI namespace."""
        type_names = []
        for attr_name in dir(self.mcli_obj):
            if not attr_name.startswith("_") and attr_name not in ERD.system_types:
                try:
                    attr = getattr(self.mcli_obj, attr_name)
                    if hasattr(attr, "meta") and callable(attr.meta):
                        type_names.append(attr_name)
                except:
                    pass
        return type_names

    def get_package_types(self, package_name: str) -> List[str]:
        """Get all types in a specific package from MCLI namespace."""
        type_names = []
        try:
            pkg = getattr(self.mcli_obj, package_name)
            for attr_name in dir(pkg):
                if attr_name.startswith("_"):
                    continue
                try:
                    attr = getattr(pkg, attr_name)
                    if hasattr(attr, "meta") and callable(attr.meta):
                        type_names.append(f"{package_name}.{attr_name}")
                except:
                    pass
        except Exception:
            pass
        return type_names

    def create_type_metadata(self, type_obj: Any) -> TypeMetadata:
        """Create MCLI type metadata from a type object."""
        return MCLITypeMetadata(type_obj)


class MCLITypeMetadata:
    """MCLI-specific implementation of TypeMetadata."""

    def __init__(self, mcli_type):
        self.mcli_type = mcli_type
        self._meta = mcli_type.meta()

    def get_name(self) -> str:
        """Get the type name."""
        return getattr(self.mcli_type, "name", lambda: str(self.mcli_type))()

    def get_fields(self) -> Dict[str, Any]:
        """Get field definitions from MCLI type metadata."""
        fields = {}
        fts = self._meta.fieldTypesByName()
        for name, ft in fts.items():
            if name not in ERD.black_list:
                fields[name] = ft
        return fields

    def get_methods(self) -> List[str]:
        """Get method names from MCLI type."""
        methods = []
        for name in dir(self.mcli_type):
            if name.startswith("_") or name in ERD.black_list:
                continue
            attr = getattr(self.mcli_type, name)
            if callable(attr):
                methods.append(name)
        return sorted(methods)

    def get_related_types(self) -> Set[str]:
        """Get names of related types from MCLI type metadata."""
        related_types = set()
        fts = self._meta.fieldTypesByName()

        for name, ft in fts.items():
            if name in ERD.black_list:
                continue
            try:
                vt = ft.valueType()
                if hasattr(vt, "elementType"):
                    if vt.elementType.isReference():
                        related_types.add(vt.elementType.name)
                else:
                    if vt.isReference():
                        related_types.add(vt.name)
            except Exception:
                pass

        return related_types


logger = get_logger(__name__)


class ERD:
    """
    ERD generation utility class.
    """

    black_list = [
        "meta",
        "typeWithBindings",
        "subject",
        "model",
        "parent",
        "itemFacility",
        "recommendation",
        "id",
        "versionEdits",
        "name",
        "unit",
        "typeIdent",
        "version",
        "unit",
        "value",
        "currency",
        "updatedBy",
        "status",
    ]

    system_types = [
        "Object",
        "Type",
        "ArrayType",
        "BooleanType",
        "DateTimeType",
        "DoubleType",
        "IntegerType",
        "StringType",
    ]

    include_list = [
        "id",
        "name",
    ]

    @staticmethod
    def get_relevant_types(type_metadata: TypeMetadata) -> Set[str]:
        """Get relevant reference types from type metadata."""
        return type_metadata.get_related_types()

    @staticmethod
    def get_pkg_types(type_system: TypeSystem, pkg_name: Optional[str] = None) -> Set[str]:
        """Get all types from a package or root namespace."""
        if pkg_name:
            return set(type_system.get_package_types(pkg_name))
        else:
            return set(type_system.get_all_types())

    @staticmethod
    def get_entity_methods(type_metadata: TypeMetadata) -> List[str]:
        """Get methods of a type."""
        return type_metadata.get_methods()

    @staticmethod
    def add_entity(entities: Dict[str, Dict], type_name: str, type_system: TypeSystem):
        """Add entity to the ERD using generic type system."""
        try:
            type_obj = type_system.get_type(type_name)
            type_metadata = type_system.create_type_metadata(type_obj)
        except Exception as e:
            logger.warning(f"Could not load type {type_name}: {e}")
            return

        fields = type_metadata.get_fields()
        entries = []

        # Convert field metadata to display format
        for name, field_metadata in fields.items():
            try:
                # Try to extract type information for display
                if hasattr(field_metadata, "valueType"):
                    vt = field_metadata.valueType()
                    if hasattr(vt, "elementType"):
                        field_type = vt.elementType.name
                        label_ = f"[{field_type}]"
                    else:
                        label_ = getattr(vt, "name", str(vt))
                else:
                    label_ = str(field_metadata)
            except:
                label_ = str(field_metadata)

            entries.append((name, label_))

        entries = sorted(entries, key=lambda x: x[1])
        entities[type_name] = {"fields": entries, "methods": {}}


def do_erd(max_depth=1, type_system: Optional[TypeSystem] = None):
    """Generate an ERD (Entity Relationship Diagram) for a MCLI type.

    This function now has two modes:
    1. Traditional mode: Connects to a MCLI cluster and generates ERD based on type metadata
    2. Offline mode: Uses realGraph.json to create a hierarchical model based on reachable subgraphs

    Args:
        max_depth: Maximum depth of relationships to include in the diagram
    """
    # Ask the user which mode they prefer
    import click
    import pydot

    logger.info("do_erd")

    max_depth = int(max_depth)

    mode = click.prompt(
        "Do you want to generate an ERD using a MCLI cluster or using the realGraph.json file?",
        type=click.Choice(["mcli", "realGraph"]),
        default="realGraph",
    )

    if mode == "realGraph":
        # Use the new hierarchical model approach
        try:
            # Import the modified_do_erd function from generate_graph
            from mcli.app.main.generate_graph import modified_do_erd

            logger.info("Generating ERD using realGraph.json...")
            result = modified_do_erd(max_depth=max_depth)
            if result:
                logger.info(f"Successfully generated ERD with realGraph.json approach: {result}")
                return result
            else:
                logger.warning(
                    "Failed to generate ERD with realGraph.json approach, falling back to MCLI connection method."
                )
                mode = "mcli"
        except Exception as e:
            logger.error(f"Error generating ERD from realGraph.json: {e}")
            logger.info("Falling back to traditional MCLI connection method...")
            # Fall back to traditional method
            mode = "mcli"

    if mode == "mcli":
        # Original ERD generation logic
        env_url = click.prompt("Please provide your environment url - no trailing slash")

        mcli_mngr = MCLIManager(env_url=env_url)
        mcli = mcli_mngr.mcli_as_basic_user()

        # Create generic type system adapter
        if type_system is None:
            type_system = MCLITypeSystem(mcli)

        # Ask if the user wants to generate an ERD for a specific type or a package
        mode = click.prompt(
            "Do you want to generate an ERD for a specific type or a package?",
            type=click.Choice(["type", "package", "all"]),
            default="type",
        )

        root_type = None
        pkg_types = set()

        if mode == "type":
            # Get the mcli type from user input
            type_name = click.prompt("Please enter the MCLI type name (e.g., ReliabilityAssetCase)")

            # Dynamically access the mcli namespace using getattr
            try:
                root_type = getattr(mcli, type_name)
                click.echo(f"Successfully retrieved type: {type_name}")
                click.echo(f"Type info: {type(root_type)}")
            except AttributeError:
                available_types = []
                for attr_name in dir(mcli):
                    if (
                        not attr_name.startswith("_") and attr_name not in ERD.system_types
                    ):  # Skip private attributes and system types
                        try:
                            attr = getattr(mcli, attr_name)
                            # Check if it's a type by looking for meta method
                            if hasattr(attr, "meta") and callable(attr.meta):
                                available_types.append(attr_name)
                        except Exception:
                            pass

                click.echo(f"Error: Type '{type_name}' not found in mcli namespace.")
                if available_types:
                    click.echo("\nAvailable types you can try:")
                    for t in sorted(available_types[:20]):  # Show first 20 to keep it manageable
                        click.echo(f"  - {t}")
                    if len(available_types) > 20:
                        click.echo(f"  ... and {len(available_types) - 20} more")
                return

        elif mode == "package":
            # Get package name
            pkg_name = click.prompt("Please enter the package name (e.g., Pkg)")
            try:
                pkg = getattr(mcli, pkg_name)
                click.echo(f"Successfully retrieved package: {pkg_name}")

                # Get all types in the package
                pkg_types = ERD.get_pkg_types(type_system, pkg_name)
                if not pkg_types:
                    click.echo(f"No types found in package {pkg_name}")
                    return

                click.echo(f"Found {len(pkg_types)} types in package {pkg_name}")

                # If there are many types, ask the user if they want to include all or select
                if len(pkg_types) > 10:
                    include_all = click.confirm(
                        f"Package contains {len(pkg_types)} types. Include all in ERD?",
                        default=False,
                    )
                    if not include_all:
                        # Let user select a specific type as the root
                        for t in sorted(list(pkg_types)[:20]):
                            click.echo(f"  - {t}")
                        if len(pkg_types) > 20:
                            click.echo(f"  ... and {len(pkg_types) - 20} more")

                        type_name = click.prompt("Please select a type to use as the root node")
                        try:
                            type_parts = type_name.split(".")
                            if len(type_parts) > 1:
                                current_obj = mcli
                                for part in type_parts:
                                    current_obj = getattr(current_obj, part)
                                root_type = current_obj
                            else:
                                root_type = getattr(getattr(mcli, pkg_name), type_name)
                            click.echo(f"Using {type_name} as root node")
                            pkg_types = {type_name}  # Only include the selected type
                        except AttributeError:
                            click.echo(f"Error: Type '{type_name}' not found")
                            return

                # If no root type is selected, use the first type in the package
                if root_type is None and pkg_types:
                    first_type = sorted(list(pkg_types))[0]
                    type_parts = first_type.split(".")
                    if len(type_parts) > 1:
                        current_obj = mcli
                        for part in type_parts:
                            current_obj = getattr(current_obj, part)
                        root_type = current_obj
                    else:
                        root_type = getattr(getattr(mcli, pkg_name), first_type)
                    click.echo(f"Using {first_type} as root node")
            except AttributeError:
                click.echo(f"Error: Package '{pkg_name}' not found")
                # List available packages
                packages = []
                for attr_name in dir(mcli):
                    if not attr_name.startswith("_") and attr_name not in ERD.system_types:
                        try:
                            attr = getattr(mcli, attr_name)
                            # Check if it might be a package by checking if it has types with meta method
                            for sub_attr_name in dir(attr):
                                if not sub_attr_name.startswith("_"):
                                    try:
                                        sub_attr = getattr(attr, sub_attr_name)
                                        if hasattr(sub_attr, "meta") and callable(sub_attr.meta):
                                            packages.append(attr_name)
                                            break
                                    except:
                                        pass
                        except:
                            pass

                if packages:
                    click.echo("\nAvailable packages you can try:")
                    for p in sorted(packages):
                        click.echo(f"  - {p}")
                return

        elif mode == "all":
            # Get all types from the root namespace
            pkg_types = ERD.get_pkg_types(type_system)
            if not pkg_types:
                click.echo("No types found in root namespace")
                return

            click.echo(f"Found {len(pkg_types)} types in root namespace")

            # Let user select a specific type as the root
            for t in sorted(list(pkg_types)[:20]):
                click.echo(f"  - {t}")
            if len(pkg_types) > 20:
                click.echo(f"  ... and {len(pkg_types) - 20} more")

            type_name = click.prompt("Please select a type to use as the root node")
            try:
                root_type = getattr(mcli, type_name)
                click.echo(f"Using {type_name} as root node")

                # Ask if user wants to include Pkg types too
                include_pkg_types = click.confirm(
                    "Would you like to include types from packages as well?", default=True
                )
                if include_pkg_types:
                    # Get list of available packages
                    packages = []
                    for attr_name in dir(mcli):
                        if not attr_name.startswith("_") and attr_name not in ERD.system_types:
                            try:
                                attr = getattr(mcli, attr_name)
                                # Check if it might be a package by checking if it has types with meta method
                                for sub_attr_name in dir(attr):
                                    if not sub_attr_name.startswith("_"):
                                        try:
                                            sub_attr = getattr(attr, sub_attr_name)
                                            if hasattr(sub_attr, "meta") and callable(
                                                sub_attr.meta
                                            ):
                                                packages.append(attr_name)
                                                break
                                        except:
                                            pass
                            except:
                                pass

                    if packages:
                        click.echo("\nAvailable packages:")
                        for p in sorted(packages):
                            click.echo(f"  - {p}")

                        # Let user select packages to include
                        selected_pkg = click.prompt(
                            "Enter package name to include (or 'all' for all packages)",
                            default="all",
                        )

                        if selected_pkg.lower() == "all":
                            # Add types from all packages
                            for pkg_name in packages:
                                pkg_type_set = ERD.get_pkg_types(type_system, pkg_name)
                                click.echo(
                                    f"Adding {len(pkg_type_set)} types from package {pkg_name}"
                                )
                                pkg_types.update(pkg_type_set)
                        else:
                            # Add types from selected package
                            if selected_pkg in packages:
                                pkg_type_set = ERD.get_pkg_types(type_system, selected_pkg)
                                click.echo(
                                    f"Adding {len(pkg_type_set)} types from package {selected_pkg}"
                                )
                                pkg_types.update(pkg_type_set)
                            else:
                                click.echo(
                                    f"Package '{selected_pkg}' not found, using only root namespace types"
                                )
            except AttributeError:
                click.echo(f"Error: Type '{type_name}' not found")
                return

        if root_type is None:
            click.echo("Error: No root type selected for ERD generation")
            return

        # Initialize a dictionary to track processed types
        processed_types = set()
        # Initialize a dictionary to map types to their depth
        type_depth = {root_type.name(): 0}

        # Add the root type to processed types
        processed_types.add(root_type.name())

        # If we're including types from a package, add them to the initial list
        if pkg_types and mode != "type":
            click.echo(
                f"Including {len(pkg_types)} types from {'package' if mode == 'package' else 'root namespace'}"
            )
            # We'll process these up to max_depth from the root type

            # Prepare to process all selected types
            # We'll need to include them all in the graph
            additional_types_to_process = []

            for type_name in pkg_types:
                # Skip the root type
                if type_name == root_type.name():
                    continue

                try:
                    # Handle both package.Type and Type formats
                    if "." in type_name:
                        parts = type_name.split(".")
                        current_obj = mcli
                        for part in parts:
                            current_obj = getattr(current_obj, part)
                        pkg_type = current_obj
                    else:
                        pkg_type = getattr(mcli, type_name)

                    if hasattr(pkg_type, "meta") and callable(pkg_type.meta):
                        additional_types_to_process.append((type_name, 0))  # Start at depth 0
                except Exception as e:
                    # Skip any type that can't be loaded
                    logger.info(f"Error loading type {type_name}: {e}")

            click.echo(f"Will process {len(additional_types_to_process)} additional types")

        entities = {}

        ERD.add_entity(entities, root_type.name(), type_system)
        processed_types.add(root_type.name())

        # Get all related types up to max_depth
        to_process = [(root_type.name(), 0)]  # (type_name, current_depth)

        # Add additional types from packages if applicable
        if pkg_types and mode != "type" and "additional_types_to_process" in locals():
            to_process.extend(additional_types_to_process)

        while to_process:
            current_type, current_depth = to_process.pop(0)

            if current_depth >= max_depth:
                continue

            # Get relevant types for the current type
            try:
                current_type_obj = type_system.get_type(current_type)
                current_type_metadata = type_system.create_type_metadata(current_type_obj)

                # Add entity for this type if not already added
                if current_type not in entities:
                    ERD.add_entity(entities, current_type, type_system)
                    processed_types.add(current_type)
                    type_depth[current_type] = current_depth

                relevant_types = ERD.get_relevant_types(current_type_metadata)

                for related_type in relevant_types:
                    if related_type not in processed_types:
                        ERD.add_entity(entities, related_type, type_system)
                        processed_types.add(related_type)
                        type_depth[related_type] = current_depth + 1
                        to_process.append((related_type, current_depth + 1))
            except Exception as e:
                logger.info(f"Error processing {current_type}: {e}")

        # Create a new graph
        graph = pydot.Dot(graph_type="digraph", rankdir="TB", splines="ortho", bgcolor="white")

        # Function to create table-based node labels
        def create_table_html(entity, entity_data, font_size=10):
            fields = entity_data["fields"]
            methods = entity_data["methods"]

            entity = entity.replace(".", "_")
            entity = entity.replace("<", "[")
            entity = entity.replace(">", "]")

            html = f'<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="2">'
            html += f'<TR><TD PORT="header" COLSPAN="2" BGCOLOR="lightgrey"><B><FONT POINT-SIZE="{font_size}">{entity}</FONT></B></TD></TR>'

            # Fields/Members section
            if fields:
                html += f'<TR><TD COLSPAN="2" BGCOLOR="#E0E0E0"><B><FONT POINT-SIZE="{font_size}">Fields</FONT></B></TD></TR>'
                for field, type_ in fields:
                    type_ = type_.replace("<", "[")
                    type_ = type_.replace(">", "]")
                    if not type_:
                        continue
                    html += f'<TR><TD><FONT POINT-SIZE="{font_size}">{field}</FONT></TD><TD><FONT POINT-SIZE="{font_size}">{type_}</FONT></TD></TR>'

            # Methods section
            if methods:
                html += f'<TR><TD COLSPAN="2" BGCOLOR="#E0E0E0"><B><FONT POINT-SIZE="{font_size}">Methods</FONT></B></TD></TR>'
                for method in methods:
                    html += f'<TR><TD COLSPAN="2"><FONT POINT-SIZE="{font_size}">{method}()</FONT></TD></TR>'

            html += "</TABLE>>"
            return html

        # Create nodes for all entities
        for entity, entity_data in entities.items():
            entity_normalized = entity.replace(".", "_")

            # Create a node with table-style label showing fields and methods
            node_label = create_table_html(entity, entity_data, font_size=10)

            # Determine node color based on depth
            node_depth = type_depth.get(entity, 0)
            bg_color = "white"  # default
            if entity == root_type.name():
                bg_color = "lightblue"  # root node
            elif node_depth == 1:
                bg_color = "#E6F5FF"  # light blue for first level
            elif node_depth == 2:
                bg_color = "#F0F8FF"  # even lighter blue for second level

            # Create the node
            node = pydot.Node(
                entity_normalized,
                shape="none",  # Using 'none' to allow custom HTML table
                label=node_label,
                style="filled",
                fillcolor=bg_color,
                margin="0",
            )
            graph.add_node(node)

        # Track child-parent relationships dynamically
        parent_map = {}  # Maps entity -> parent

        # Get all relationships and track which type belongs under which parent
        for entity_type in processed_types:
            if entity_type == root_type.name():
                continue

            current_mcli_type = getattr(mcli, entity_type, None)
            if not current_mcli_type:
                continue

            try:
                relevant_types = ERD.get_relevant_types(current_mcli_type)
                for related_type in relevant_types:
                    if related_type not in processed_types:
                        continue
                    # Store the parent-child mapping
                    parent_map[related_type] = entity_type
            except Exception as e:
                logger.info(f"Error processing {entity_type}: {e}")

        # Add edges based on parent-child relationships
        for child, parent in parent_map.items():
            child_normalized = child.replace(".", "_")
            parent_normalized = parent.replace(".", "_")

            edge = pydot.Edge(
                parent_normalized,
                child_normalized,
                dir="both",
                arrowtail="none",
                arrowhead="normal",
                constraint=True,
                color="black",
                penwidth=1.5,
            )
            graph.add_edge(edge)

        # Set root node
        root_type_name = root_type.name().replace(".", "_")

        # Use a subgraph to force the root node to be at the center/top
        root_subgraph = pydot.Subgraph(rank="min")
        # We don't need to recreate the root node here as we've already created it in the loop above
        # Just add it to the subgraph
        root_subgraph.add_node(pydot.Node(root_type_name))
        graph.add_subgraph(root_subgraph)

        # Save the graph to a file
        depth_info = f"_depth{max_depth}"
        time_info = str(time.time_ns())
        sep = "__"
        dot_file = root_type.name() + depth_info + sep + time_info + ".dot"
        png_file = root_type.name() + depth_info + sep + time_info + ".png"
        graph.write_png(png_file)
        graph.write_raw(dot_file)

        logger.info(
            f"ERD generated successfully with fields and methods. Output files: {png_file} and {dot_file}"
        )

        return dot_file, png_file


def create_merged_erd(
    types: List[str],
    type_system: Optional[TypeSystem] = None,
    mcli=None,
    env_url: str = None,
    max_depth: int = 2,
    output_prefix: str = "MergedERD",
    include_methods: bool = False,
) -> Tuple[str, str]:
    """
    Create a merged ERD from multiple root types.

    Args:
        types: List of MCLI type names to include as root nodes
        mcli: Optional MCLI connection object. If not provided, env_url must be provided.
        env_url: Optional environment URL to connect to MCLI. Only needed if mcli is not provided.
        max_depth: Maximum depth of relationships to include in the diagram
        output_prefix: Prefix for output files
        include_methods: Whether to include method information in the diagram

    Returns:
        Tuple of (dot_file_path, png_file_path)
    """
    logger.info("create_merged_erd")
    # Establish MCLI connection if needed
    if type_system is None:
        if mcli is None:
            if env_url is None:
                raise ValueError("Either type_system, mcli, or env_url must be provided")
            mcli_mngr = MCLIManager(env_url=env_url)
            mcli = mcli_mngr.mcli_as_basic_user()
        type_system = MCLITypeSystem(mcli)

    # Validate all types exist
    root_types = []
    for type_name in types:
        try:
            root_type = type_system.get_type(type_name)
            root_types.append((type_name, root_type))
            logger.info(f"Successfully loaded type: {type_name}")
        except Exception as e:
            logger.warning(f"Type '{type_name}' not found in type system. Skipping. Error: {e}")

    if not root_types:
        raise ValueError("None of the provided types could be found in the MCLI namespace")

    # Process all types and their relationships
    processed_types = set()
    type_depth = {}  # Maps type name to depth from any root
    entities = {}

    # Initialize processing queue with all root types at depth 0
    to_process = [
        (name, obj, 0) for name, obj in root_types
    ]  # (type_name, type_obj, current_depth)

    # Add all root types to the processed set
    for name, _ in root_types:
        processed_types.add(name)
        type_depth[name] = 0  # Root types are at depth 0
        ERD.add_entity(entities, name, type_system)

    # Process all types up to max_depth
    process_types_to_depth(
        to_process, processed_types, type_depth, entities, type_system, max_depth
    )

    # Create a merged graph visualization
    graph = create_merged_graph(entities, type_depth, root_types, include_methods)

    # Save the graph to files
    depth_info = f"_depth{max_depth}"
    time_info = str(int(time.time() * 1000000))
    dot_file = f"{output_prefix}{depth_info}_{time_info}.dot"
    png_file = f"{output_prefix}{depth_info}_{time_info}.png"

    graph.write_png(png_file)
    graph.write_raw(dot_file)

    logger.info(f"Merged ERD generated successfully. Output files: {png_file} and {dot_file}")

    return dot_file, png_file


def process_types_to_depth(
    to_process: List[Tuple[str, object, int]],
    processed_types: Set[str],
    type_depth: Dict[str, int],
    entities: Dict[str, Dict],
    type_system: TypeSystem,
    max_depth: int,
) -> None:
    """
    Process types recursively up to max_depth, building entity information.

    Args:
        to_process: Queue of types to process (type_name, type_obj, current_depth)
        processed_types: Set of already processed type names
        type_depth: Dictionary mapping type names to their depth
        entities: Dictionary to store entity information
        mcli: MCLI connection object
        max_depth: Maximum depth to process
    """
    while to_process:
        current_type_name, current_type_obj, current_depth = to_process.pop(0)

        if current_depth >= max_depth:
            continue

        # Get relevant types for the current type
        try:
            current_type_metadata = type_system.create_type_metadata(current_type_obj)
            relevant_types = ERD.get_relevant_types(current_type_metadata)

            for related_type_name in relevant_types:
                # Check if we've already processed this type
                if related_type_name in processed_types:
                    # Update depth if we found a shorter path
                    if current_depth + 1 < type_depth.get(related_type_name, float("inf")):
                        type_depth[related_type_name] = current_depth + 1
                    continue

                try:
                    related_type_obj = type_system.get_type(related_type_name)

                    # Add entity information
                    ERD.add_entity(entities, related_type_name, type_system)
                    processed_types.add(related_type_name)
                    type_depth[related_type_name] = current_depth + 1

                    # Add to processing queue
                    to_process.append((related_type_name, related_type_obj, current_depth + 1))
                except Exception as e:
                    logger.warning(f"Error loading related type {related_type_name}: {e}")
        except Exception as e:
            logger.warning(f"Error processing type {current_type_name}: {e}")


def create_merged_graph(
    entities: Dict[str, Dict],
    type_depth: Dict[str, int],
    root_types: List[Tuple[str, object]],
    include_methods: bool = False,
) -> pydot.Dot:
    """
    Create a merged graph visualization from the processed entities.

    Args:
        entities: Dictionary of entity information
        type_depth: Dictionary mapping type names to their depth
        root_types: List of (type_name, type_obj) tuples representing root types
        include_methods: Whether to include method information

    Returns:
        pydot.Dot graph object
    """
    # Create a new graph
    graph = pydot.Dot(
        graph_type="digraph",
        rankdir="TB",
        splines="ortho",
        bgcolor="white",
        label="Merged Entity Relationship Diagram",
        fontsize=16,
        labelloc="t",
    )

    # Function to create table-based node labels
    def create_table_html(entity, entity_data, font_size=10):
        fields = entity_data["fields"]
        methods = entity_data["methods"] if include_methods else {}

        entity = entity.replace(".", "_")
        entity = entity.replace("<", "[")
        entity = entity.replace(">", "]")

        html = f'<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="2">'
        html += f'<TR><TD PORT="header" COLSPAN="2" BGCOLOR="lightgrey"><B><FONT POINT-SIZE="{font_size+2}">{entity}</FONT></B></TD></TR>'

        # Fields/Members section
        if fields:
            html += f'<TR><TD COLSPAN="2" BGCOLOR="#E0E0E0"><B><FONT POINT-SIZE="{font_size}">Fields</FONT></B></TD></TR>'
            for field, type_ in fields:
                type_ = type_.replace("<", "[")
                type_ = type_.replace(">", "]")
                if not type_:
                    continue
                html += f'<TR><TD><FONT POINT-SIZE="{font_size}">{field}</FONT></TD><TD><FONT POINT-SIZE="{font_size}">{type_}</FONT></TD></TR>'

        # Methods section
        if methods:
            html += f'<TR><TD COLSPAN="2" BGCOLOR="#E0E0E0"><B><FONT POINT-SIZE="{font_size}">Methods</FONT></B></TD></TR>'
            for method in methods:
                html += f'<TR><TD COLSPAN="2"><FONT POINT-SIZE="{font_size}">{method}()</FONT></TD></TR>'

        html += "</TABLE>>"
        return html

    # Create nodes for all entities
    added_nodes = set()  # Track added nodes to avoid duplicates

    for entity, entity_data in entities.items():
        entity_normalized = entity.replace(".", "_")

        if entity_normalized in added_nodes:
            continue

        # Create a node with table-style label showing fields and methods
        node_label = create_table_html(entity, entity_data, font_size=10)

        # Determine node color based on depth
        node_depth = type_depth.get(entity, 0)
        is_root = any(entity == name for name, _ in root_types)

        if is_root:
            bg_color = "lightblue"  # Root node
        elif node_depth == 1:
            bg_color = "#E6F5FF"  # Light blue for first level
        elif node_depth == 2:
            bg_color = "#F0F8FF"  # Even lighter blue for second level
        else:
            bg_color = "white"  # Default for deeper levels

        # Create the node
        node = pydot.Node(
            entity_normalized,
            shape="none",  # Using 'none' to allow custom HTML table
            label=node_label,
            style="filled",
            fillcolor=bg_color,
            margin="0",
        )
        graph.add_node(node)
        added_nodes.add(entity_normalized)

    # Build relationship map
    relationship_map = build_relationship_map(entities)

    # Add edges based on relationships
    for source, targets in relationship_map.items():
        source_normalized = source.replace(".", "_")
        for target in targets:
            target_normalized = target.replace(".", "_")

            # Skip if either node wasn't added
            if source_normalized not in added_nodes or target_normalized not in added_nodes:
                continue

            edge = pydot.Edge(
                source_normalized,
                target_normalized,
                dir="both",
                arrowtail="none",
                arrowhead="normal",
                constraint=True,
                color="black",
                penwidth=1.5,
            )
            graph.add_edge(edge)

    # Create a subgraph to force root nodes to be at the top
    root_subgraph = pydot.Subgraph(rank="min")
    for name, _ in root_types:
        normalized_name = name.replace(".", "_")
        if normalized_name in added_nodes:
            root_subgraph.add_node(pydot.Node(normalized_name))
    graph.add_subgraph(root_subgraph)

    return graph


def build_relationship_map(entities: Dict[str, Dict]) -> Dict[str, Set[str]]:
    """
    Build a map of relationships between entities based on field types.

    Args:
        entities: Dictionary of entity information

    Returns:
        Dictionary mapping source entity names to sets of target entity names
    """
    relationship_map = {}

    for entity_name, entity_data in entities.items():
        fields = entity_data["fields"]

        for field_name, field_type in fields:
            # Skip empty field types
            if not field_type:
                continue

            # Handle array types like [Type]
            is_array = field_type.startswith("[") and field_type.endswith("]")
            if is_array:
                target_type = field_type[1:-1]  # Remove brackets
            else:
                target_type = field_type

            # Skip primitive types
            if target_type in [
                "StringType",
                "IntegerType",
                "DoubleType",
                "DateTimeType",
                "BooleanType",
            ]:
                continue

            # Add relationship
            if entity_name not in relationship_map:
                relationship_map[entity_name] = set()
            relationship_map[entity_name].add(target_type)

    return relationship_map


def generate_merged_erd_for_types(
    type_names: List[str],
    env_url: str = None,
    type_system: Optional[TypeSystem] = None,
    max_depth: int = 2,
    output_prefix: str = "MergedERD",
) -> Tuple[str, str]:
    """
    Generate a merged ERD for multiple MCLI types.

    Args:
        type_names: List of MCLI type names to include as root nodes
        env_url: Environment URL to connect to MCLI
        max_depth: Maximum depth of relationships to include in the diagram
        output_prefix: Prefix for output files

    Returns:
        Tuple of (dot_file_path, png_file_path)
    """
    return create_merged_erd(
        types=type_names,
        type_system=type_system,
        env_url=env_url,
        max_depth=max_depth,
        output_prefix=output_prefix,
    )


def find_top_nodes_in_graph(graph_data: Dict, top_n: int = 5) -> List[Tuple[str, int]]:
    """
    Find the top N nodes in a graph that would serve as good roots for a hierarchical export.
    Nodes are ranked by the number of descendants they have (size of reachable subgraph).

    Args:
        graph_data: Dictionary containing graph data with vertices and edges
        top_n: Number of top-level nodes to return

    Returns:
        List of tuples containing (node_id, descendant_count) sorted by descendant count
    """
    logger.info("START | find_top_nodes_in_graph")
    try:
        # Ensure top_n is an integer
        try:
            top_n = int(top_n)
        except (ValueError, TypeError):
            logger.warning(f"Invalid top_n value: {top_n}, using default of 5")
            top_n = 5

        # Build adjacency list from the graph data
        from mcli.app.main.generate_graph import build_adjacency_list, count_descendants

        logger.info("START INVOKE | build_adjacency_list")
        node_map, adj_list = build_adjacency_list(graph_data)
        logger.info("END INVOKE | build_adjacency_list")

        # Count descendants for each node
        descendant_counts = {}
        logger.info("START INVOKE | count_descendants")
        for node_id in node_map:
            descendant_counts[node_id] = count_descendants(node_id, adj_list)
        logger.info("END INVOKE | count_descendants")

        # Sort nodes by descendant count
        logger.info("START INVOKE | descendant_counts.items()")
        sorted_nodes = sorted(descendant_counts.items(), key=lambda x: x[1], reverse=True)
        logger.info("END INVOKE | descendant_counts.items()")

        # Return top N nodes
        logger.info(f"START INVOKE [(node_id, count) for node_id, count in sorted_nodes[:{top_n}]]")
        top_nodes = [(node_id, count) for node_id, count in sorted_nodes[:top_n]]
        logger.info(f"END INVOKE [(node_id, count) for node_id, count in sorted_nodes[:{top_n}]]")
        logger.info("END | find_top_nodes_in_graph")
        return top_nodes
    except Exception as e:
        logger.error(f"Error finding top nodes in graph: {e}")
        return []


def generate_erd_for_top_nodes(
    graph_file_path: str, max_depth: int = 2, top_n: int = 50
) -> List[Tuple[str, str, int]]:
    """
    Generate ERDs for the top N nodes in a graph.

    Args:
        graph_file_path: Path to the JSON file containing the graph data
        max_depth: Maximum depth for building the hierarchical model
        top_n: Number of top-level nodes to include

    Returns:
        List of tuples containing (dot_file_path, png_file_path, descendant_count) for each top node
    """
    logger.info("START | generate_erd_for_top_nodes")
    try:
        # Check if the file exists
        if not os.path.exists(graph_file_path):
            logger.error(f"Graph file not found: {graph_file_path}")
            raise FileNotFoundError(f"Graph file not found: {graph_file_path}")

        # Load the graph data
        try:
            with open(graph_file_path, "r") as f:
                graph_data = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in graph file: {e}")
            raise ValueError(f"Invalid JSON in graph file: {e}")

        # Find top nodes
        top_nodes = find_top_nodes_in_graph(graph_data, top_n)
        if not top_nodes:
            logger.warning("No top nodes found in the graph.")
            return []

        logger.info(
            f"Found {len(top_nodes)} top nodes in the graph: {', '.join([node_id for node_id, _ in top_nodes])}"
        )

        # Generate ERDs for each top node
        from mcli.app.main.generate_graph import (
            build_adjacency_list,
            build_hierarchical_graph,
            create_dot_graph,
        )

        # Build adjacency list from the graph data
        logger.info("START | build_adjacency_list")
        node_map, adj_list = build_adjacency_list(graph_data)
        logger.info("END | build_adjacency_list")

        # Build hierarchical graph with top nodes as roots
        top_node_ids = [node_id for node_id, _ in top_nodes]
        logger.info(
            f"Building hierarchical graph with {len(top_node_ids)} root nodes and max depth {max_depth}"
        )
        logger.info("START | build_hierarchical_graph")
        hierarchy = build_hierarchical_graph(top_node_ids, node_map, adj_list, max_depth)
        logger.info("END | build_hierarchical_graph")

        # Create output directory if it doesn't exist
        output_dir = os.path.join(os.path.dirname(os.path.abspath(graph_file_path)), "output")
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logger.info(f"Created output directory: {output_dir}")

        # Generate file paths
        timestamp = str(int(time.time() * 1000000))
        generated_files = []

        # For each top-level node, generate DOT and PNG files
        for root_node_id, descendant_count in top_nodes:
            try:
                # Create the DOT graph
                logger.info(f"Creating DOT graph for {root_node_id}")
                dot_graph = create_dot_graph(hierarchy, root_node_id, max_depth)

                # Define file paths
                depth_info = f"_depth{max_depth}"
                dot_file = os.path.join(output_dir, f"{root_node_id}{depth_info}_{timestamp}.dot")
                png_file = os.path.join(output_dir, f"{root_node_id}{depth_info}_{timestamp}.png")

                # Save the files
                logger.info(f"Saving DOT file to {dot_file}")
                dot_graph.write_raw(dot_file)

                logger.info(f"Generating PNG file to {png_file}")
                dot_graph.write_png(png_file)

                # Return just the filenames (not full paths) for consistency
                dot_filename = os.path.basename(dot_file)
                png_filename = os.path.basename(png_file)

                generated_files.append((dot_filename, png_filename, descendant_count))
                logger.info(
                    f"Generated graph for {root_node_id} with {descendant_count} descendants: {png_filename}"
                )
            except Exception as e:
                logger.error(f"Error generating graph for node {root_node_id}: {e}")

        if not generated_files:
            logger.warning("No files were generated successfully")

        return generated_files
    except Exception as e:
        logger.error(f"Error generating ERDs for top nodes: {e}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        raise


def analyze_graph_for_hierarchical_exports(graph_file_path: str, top_n: int = 5) -> List[Dict]:
    """
    Analyze a graph to identify the top N nodes that would serve as good roots for
    hierarchical exports, based on the number of descendants each node has.

    Args:
        graph_file_path: Path to the JSON file containing the graph data
        top_n: Number of top-level nodes to identify

    Returns:
        List of dictionaries containing information about each top node
    """
    logger.info("analyze_graph_for_hierarchical_exports")
    try:
        logger.info(f"Analyzing graph file: {graph_file_path}")

        # Check if the file exists
        if not os.path.exists(graph_file_path):
            logger.error(f"Graph file not found: {graph_file_path}")
            raise FileNotFoundError(f"Graph file not found: {graph_file_path}")

        # Load the graph data
        try:
            with open(graph_file_path, "r") as f:
                graph_data = json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in graph file: {e}")
            raise ValueError(f"Invalid JSON in graph file: {e}")

        # Validate the structure of the graph data
        if "graph" not in graph_data:
            logger.error("Invalid graph data: missing 'graph' key")
            raise ValueError("Invalid graph data: missing 'graph' key")

        # Find top nodes
        logger.info(f"Finding top {top_n} nodes in graph by descendant count")
        top_nodes = find_top_nodes_in_graph(graph_data, top_n)
        if not top_nodes:
            logger.warning("No top nodes found in the graph.")
            return []

        logger.info(f"Found {len(top_nodes)} top nodes")

        # Build adjacency list from the graph data
        from mcli.app.main.generate_graph import build_adjacency_list

        logger.info("Building adjacency list from graph data")
        node_map, adj_list = build_adjacency_list(graph_data)

        # Get node information
        results = []
        for node_id, descendant_count in top_nodes:
            try:
                node_info = node_map.get(node_id, {})

                # Extract node metadata
                node_type = node_info.get("type", "Unknown")
                node_category = node_info.get("category", "Unknown")

                # Extract additional data if available
                data = node_info.get("data", {})
                name = data.get("name", node_id)
                package = data.get("package", "Unknown")

                # Get direct children
                direct_children = adj_list.get(node_id, [])

                results.append(
                    {
                        "id": node_id,
                        "name": name,
                        "type": node_type,
                        "category": node_category,
                        "package": package,
                        "descendant_count": descendant_count,
                        "direct_children_count": len(direct_children),
                        "direct_children": direct_children[
                            :10
                        ],  # Limit to first 10 children for brevity
                    }
                )

                logger.info(
                    f"Top node: {node_id} - {name} - {descendant_count} descendants, {len(direct_children)} direct children"
                )
            except Exception as e:
                logger.error(f"Error processing node {node_id}: {e}")

        return results
    except Exception as e:
        logger.error(f"Error analyzing graph for hierarchical exports: {e}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        raise
