#!/usr/bin/env python3
"""
Test script for generic ERD functions using mock type systems.
Demonstrates how the ERD functions now work with any type system that implements
the TypeSystem and TypeMetadata protocols.
"""

import os
import sys
from typing import Any, Dict, List, Set

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))

from mcli.lib.erd.erd import ERD, TypeMetadata, TypeSystem


class MockTypeMetadata:
    """Mock implementation of TypeMetadata for testing."""

    def __init__(
        self,
        name: str,
        fields: Dict[str, str],
        methods: List[str] = None,
        related_types: Set[str] = None,
    ):
        self.name = name
        self.fields = fields
        self.methods = methods or []
        self.related_types = related_types or set()

    def get_name(self) -> str:
        return self.name

    def get_fields(self) -> Dict[str, Any]:
        return self.fields

    def get_methods(self) -> List[str]:
        return self.methods

    def get_related_types(self) -> Set[str]:
        return self.related_types


class MockTypeSystem:
    """Mock implementation of TypeSystem for testing."""

    def __init__(self):
        # Define a sample type system with some interconnected types
        self.types = {
            "User": MockTypeMetadata(
                name="User",
                fields={
                    "id": "string",
                    "name": "string",
                    "email": "string",
                    "profile": "UserProfile",
                },
                methods=["login", "logout", "updateProfile"],
                related_types={"UserProfile"},
            ),
            "UserProfile": MockTypeMetadata(
                name="UserProfile",
                fields={
                    "user": "User",
                    "bio": "string",
                    "avatar": "string",
                    "preferences": "UserPreferences",
                },
                methods=["updateBio", "uploadAvatar"],
                related_types={"User", "UserPreferences"},
            ),
            "UserPreferences": MockTypeMetadata(
                name="UserPreferences",
                fields={"profile": "UserProfile", "theme": "string", "notifications": "boolean"},
                methods=["setTheme", "toggleNotifications"],
                related_types={"UserProfile"},
            ),
            "Article": MockTypeMetadata(
                name="Article",
                fields={
                    "id": "string",
                    "title": "string",
                    "content": "string",
                    "author": "User",
                    "tags": "Tag[]",
                },
                methods=["publish", "edit", "delete"],
                related_types={"User", "Tag"},
            ),
            "Tag": MockTypeMetadata(
                name="Tag",
                fields={"id": "string", "name": "string", "articles": "Article[]"},
                methods=["addArticle", "removeArticle"],
                related_types={"Article"},
            ),
            "Comment": MockTypeMetadata(
                name="Comment",
                fields={
                    "id": "string",
                    "content": "string",
                    "author": "User",
                    "article": "Article",
                },
                methods=["edit", "delete"],
                related_types={"User", "Article"},
            ),
        }

    def get_type(self, name: str) -> Any:
        if name not in self.types:
            raise ValueError(f"Type '{name}' not found")
        return self.types[name]

    def get_all_types(self) -> List[str]:
        return list(self.types.keys())

    def get_package_types(self, package_name: str) -> List[str]:
        # For this mock, we'll return types that start with the package name
        return [name for name in self.types.keys() if name.startswith(package_name)]

    def create_type_metadata(self, type_obj: Any) -> TypeMetadata:
        # In our mock, the type_obj is already the metadata
        return type_obj


def test_generic_erd_functions():
    """Test the generic ERD functions with our mock type system."""
    print("Testing Generic ERD Functions")
    print("=" * 50)

    # Create mock type system
    type_system = MockTypeSystem()

    # Test get_relevant_types
    print("\\n1. Testing get_relevant_types:")
    user_metadata = type_system.get_type("User")
    related_types = ERD.get_relevant_types(user_metadata)
    print(f"User related types: {related_types}")

    article_metadata = type_system.get_type("Article")
    related_types = ERD.get_relevant_types(article_metadata)
    print(f"Article related types: {related_types}")

    # Test get_pkg_types
    print("\\n2. Testing get_pkg_types:")
    all_types = ERD.get_pkg_types(type_system)
    print(f"All types: {all_types}")

    user_types = ERD.get_pkg_types(type_system, "User")
    print(f"User package types: {user_types}")

    # Test get_entity_methods
    print("\\n3. Testing get_entity_methods:")
    user_methods = ERD.get_entity_methods(user_metadata)
    print(f"User methods: {user_methods}")

    article_methods = ERD.get_entity_methods(article_metadata)
    print(f"Article methods: {article_methods}")

    # Test add_entity
    print("\\n4. Testing add_entity:")
    entities = {}
    ERD.add_entity(entities, "User", type_system)
    ERD.add_entity(entities, "Article", type_system)

    print("Generated entities:")
    for entity_name, entity_data in entities.items():
        print(f"  {entity_name}:")
        print(f"    Fields: {entity_data['fields']}")
        print(f"    Methods: {entity_data['methods']}")

    print("\\n" + "=" * 50)
    print("Generic ERD Functions Test Complete!")
    print("\\nThis demonstrates that the ERD functions now work with any")
    print("type system that implements the TypeSystem and TypeMetadata protocols.")
    print("The functions are no longer tied specifically to MCLI types.")


def demonstrate_extensibility():
    """Demonstrate how easy it is to extend the system with new type systems."""
    print("\\n\\nDemonstrating Extensibility")
    print("=" * 50)

    class PythonTypeSystem:
        """Example of extending the system to work with Python classes."""

        def __init__(self, classes: Dict[str, type]):
            self.classes = classes

        def get_type(self, name: str) -> Any:
            if name not in self.classes:
                raise ValueError(f"Class '{name}' not found")
            return self.classes[name]

        def get_all_types(self) -> List[str]:
            return list(self.classes.keys())

        def get_package_types(self, package_name: str) -> List[str]:
            return [name for name in self.classes.keys() if name.startswith(package_name)]

        def create_type_metadata(self, type_obj: Any) -> TypeMetadata:
            # Convert Python class to our metadata format
            class PythonTypeMetadata:
                def __init__(self, cls):
                    self.cls = cls

                def get_name(self) -> str:
                    return self.cls.__name__

                def get_fields(self) -> Dict[str, Any]:
                    # In a real implementation, you'd inspect the class annotations
                    return {"example_field": "string"}

                def get_methods(self) -> List[str]:
                    return [
                        name
                        for name in dir(self.cls)
                        if callable(getattr(self.cls, name)) and not name.startswith("_")
                    ]

                def get_related_types(self) -> Set[str]:
                    # In a real implementation, you'd analyze type annotations
                    return set()

            return PythonTypeMetadata(type_obj)

    # Example usage
    class ExampleClass:
        def method1(self):
            pass

        def method2(self):
            pass

    python_type_system = PythonTypeSystem({"ExampleClass": ExampleClass})

    print("\\nUsing PythonTypeSystem:")
    entities = {}
    ERD.add_entity(entities, "ExampleClass", python_type_system)

    for entity_name, entity_data in entities.items():
        print(f"  {entity_name}:")
        print(f"    Fields: {entity_data['fields']}")
        print(f"    Methods: {entity_data['methods']}")

    print("\\nThis shows how the generic interfaces allow the ERD")
    print("system to work with completely different type systems!")


if __name__ == "__main__":
    test_generic_erd_functions()
    demonstrate_extensibility()
