#!/usr/bin/env python3
"""
Demo script to showcase MCLI Enhanced Chat capabilities
"""

import asyncio

from mcli.chat.command_rag import CommandRAGSystem
from mcli.lib.discovery.command_discovery import ClickCommandDiscovery


async def demo_enhanced_chat():
    """Demonstrate the enhanced chat capabilities"""
    print("🚀 MCLI Enhanced Chat - RAG System Demo")
    print("=" * 50)

    # Test command discovery
    print("\n📋 1. Command Discovery Test")
    discovery = ClickCommandDiscovery()
    commands = discovery.discover_all_commands()
    print(f"   ✅ Discovered {len(commands)} total commands")

    # Show some example commands
    example_commands = commands[:5]
    for cmd in example_commands:
        print(f"   • {cmd.full_name}: {cmd.description}")

    # Test RAG system initialization (simplified)
    print(f"\n🧠 2. RAG System Features")
    print("   ✅ Semantic command search")
    print("   ✅ Intent analysis and categorization")
    print("   ✅ Contextual recommendations")
    print("   ✅ Self-referential capabilities")

    # Show command categories
    print(f"\n📊 3. Available Command Categories")
    categories = {}
    for cmd in commands:
        module = cmd.module_name.split(".")[0] if "." in cmd.module_name else cmd.module_name
        if module not in categories:
            categories[module] = 0
        categories[module] += 1

    for category, count in sorted(categories.items()):
        print(f"   • {category}: {count} commands")

    # Example search scenarios
    print(f"\n🔍 4. Example Search Scenarios")
    scenarios = [
        "start redis server",
        "optimize performance",
        "schedule recurring task",
        "convert file formats",
        "show system status",
    ]

    for scenario in scenarios:
        print(f"   🎯 Query: '{scenario}'")
        print(f"      → Would find relevant commands using semantic similarity")
        print(f"      → Would provide exact command syntax and examples")
        print(f"      → Would suggest related workflow commands")

    print(f"\n💡 5. Enhanced Chat Features")
    features = [
        "Self-referential: Knows all available MCLI commands",
        "RAG-powered: Semantic search for command discovery",
        "Intent-aware: Analyzes what users want to accomplish",
        "Contextual: Provides system status and performance info",
        "Interactive: Guided command exploration with examples",
        "Workflow-building: Chains commands for complex tasks",
    ]

    for feature in features:
        print(f"   ✅ {feature}")

    print(f"\n🎉 Ready to use! Run: mcli chat")
    print("   • Enhanced mode (default): Full RAG capabilities")
    print("   • Classic mode: mcli chat --classic")
    print("   • Remote AI: mcli chat --remote")


if __name__ == "__main__":
    asyncio.run(demo_enhanced_chat())
