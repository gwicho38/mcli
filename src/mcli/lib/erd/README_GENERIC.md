# Generic ERD System

The ERD (Entity Relationship Diagram) system has been refactored to support generic type systems, not just MCLI. This makes it extensible and reusable with any type system.

## Key Changes

### 1. Generic Interfaces

Two main protocols define the interface:

```python
class TypeSystem(Protocol):
    """Protocol for generic type system interface."""
    
    def get_type(self, name: str) -> Any:
        """Get a type by name."""
        
    def get_all_types(self) -> List[str]:
        """Get all available type names."""
        
    def get_package_types(self, package_name: str) -> List[str]:
        """Get all types in a specific package."""
        
    def create_type_metadata(self, type_obj: Any) -> "TypeMetadata":
        """Create type metadata from a type object."""

class TypeMetadata(Protocol):
    """Protocol for type metadata interface."""
    
    def get_name(self) -> str:
        """Get the type name."""
        
    def get_fields(self) -> Dict[str, Any]:
        """Get field definitions."""
        
    def get_methods(self) -> List[str]:
        """Get method names."""
        
    def get_related_types(self) -> Set[str]:
        """Get names of related types."""
```

### 2. MCLI Compatibility

The system maintains full backward compatibility with MCLI through concrete implementations:

- `MCLITypeSystem`: Adapts MCLI objects to the generic interface
- `MCLITypeMetadata`: Wraps MCLI type metadata

### 3. Generic ERD Functions

All core ERD functions now accept generic type systems:

```python
# Generic function signatures
ERD.get_relevant_types(type_metadata: TypeMetadata) -> Set[str]
ERD.get_pkg_types(type_system: TypeSystem, pkg_name: Optional[str] = None) -> Set[str]
ERD.get_entity_methods(type_metadata: TypeMetadata) -> List[str]
ERD.add_entity(entities: Dict[str, Dict], type_name: str, type_system: TypeSystem)

# Main ERD generation with optional type system
do_erd(max_depth=1, type_system: Optional[TypeSystem] = None)
create_merged_erd(types: List[str], type_system: Optional[TypeSystem] = None, ...)
```

## Usage Examples

### Using with MCLI (Backward Compatible)

```python
from mcli.lib.erd.erd import do_erd

# Works exactly as before
do_erd(max_depth=2)
```

### Using with Custom Type System

```python
from mcli.lib.erd.erd import ERD, TypeSystem, TypeMetadata

class MyTypeSystem:
    def get_type(self, name: str):
        # Your implementation
        pass
    
    def get_all_types(self) -> List[str]:
        # Your implementation
        pass
    
    def get_package_types(self, package_name: str) -> List[str]:
        # Your implementation
        pass
    
    def create_type_metadata(self, type_obj):
        # Your implementation
        pass

# Use with custom type system
my_type_system = MyTypeSystem()
entities = {}
ERD.add_entity(entities, "MyType", my_type_system)
```

### Creating ERDs for Any Type System

```python
from mcli.lib.erd.erd import create_merged_erd

# With custom type system
result = create_merged_erd(
    types=["Type1", "Type2"], 
    type_system=my_type_system,
    max_depth=2
)
```

## Benefits

1. **Extensibility**: Can work with any type system (Python classes, C# types, JSON schemas, etc.)
2. **Testability**: Easy to create mock type systems for testing
3. **Separation of Concerns**: ERD logic is separate from specific type system details
4. **Backward Compatibility**: Existing MCLI code continues to work unchanged
5. **Future-Proof**: Easy to add support for new type systems

## Implementation Notes

- All MCLI-specific logic is encapsulated in `MCLITypeSystem` and `MCLITypeMetadata`
- The core ERD algorithms work with the generic interfaces
- Type systems can implement the protocols as classes or use duck typing
- Error handling preserves specific type system error messages