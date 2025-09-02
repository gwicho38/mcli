"""
RAG-based Command Search and Self-Referential System for MCLI Chatbot
"""

import asyncio
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import click

from mcli.lib.discovery.command_discovery import ClickCommandDiscovery, DiscoveredCommand
from mcli.lib.logger.logger import get_logger
from mcli.lib.search.cached_vectorizer import SmartVectorizerManager

logger = get_logger(__name__)


@dataclass
class CommandContext:
    """Rich context information about a command"""

    command: DiscoveredCommand
    help_text: str
    parameters: List[Dict[str, Any]]
    examples: List[str]
    related_commands: List[str]
    usage_patterns: List[str]
    category: str
    tags: List[str]


class CommandRAGSystem:
    """
    RAG (Retrieval Augmented Generation) system for MCLI commands
    Provides semantic search and contextual command suggestions
    """

    def __init__(self, cache_dir: Optional[Path] = None):
        self.cache_dir = cache_dir or Path.home() / ".mcli" / "command_cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.discovery = ClickCommandDiscovery()
        self.vectorizer_manager = None
        self.command_contexts: Dict[str, CommandContext] = {}
        self.command_embeddings = None
        self._initialized = False

    async def initialize(self):
        """Initialize the RAG system"""
        if self._initialized:
            return

        logger.info("Initializing Command RAG system...")

        # Initialize vectorizer manager
        self.vectorizer_manager = SmartVectorizerManager()

        # Discover and analyze all commands
        await self._discover_commands()
        await self._build_command_index()

        self._initialized = True
        logger.info(f"RAG system initialized with {len(self.command_contexts)} commands")

    async def _discover_commands(self):
        """Discover all available commands and build rich contexts"""
        logger.info("Discovering available commands...")

        # Get all commands from the discovery system
        commands = self.discovery.discover_all_commands()

        for cmd in commands:
            try:
                context = await self._build_command_context(cmd)
                self.command_contexts[cmd.full_name] = context
            except Exception as e:
                logger.debug(f"Failed to build context for {cmd.full_name}: {e}")

    async def _build_command_context(self, cmd: DiscoveredCommand) -> CommandContext:
        """Build rich context for a command"""

        # Get help text by invoking the command with --help
        help_text = await self._get_command_help(cmd)

        # Extract parameters from the Click command
        parameters = self._extract_parameters(cmd)

        # Generate examples based on the command structure
        examples = self._generate_examples(cmd, parameters)

        # Find related commands
        related_commands = self._find_related_commands(cmd)

        # Extract usage patterns
        usage_patterns = self._extract_usage_patterns(help_text, cmd)

        # Categorize the command
        category = self._categorize_command(cmd)

        # Generate tags
        tags = self._generate_tags(cmd, help_text, category)

        return CommandContext(
            command=cmd,
            help_text=help_text,
            parameters=parameters,
            examples=examples,
            related_commands=related_commands,
            usage_patterns=usage_patterns,
            category=category,
            tags=tags,
        )

    async def _get_command_help(self, cmd: DiscoveredCommand) -> str:
        """Get help text for a command by invoking it"""
        try:
            # Build the command to get help
            cmd_parts = ["python", "-m", "mcli"] + cmd.full_name.split(".") + ["--help"]

            result = subprocess.run(cmd_parts, capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                return result.stdout
            else:
                return cmd.description or f"No help available for {cmd.full_name}"

        except (subprocess.TimeoutExpired, FileNotFoundError, Exception) as e:
            logger.debug(f"Failed to get help for {cmd.full_name}: {e}")
            return cmd.description or f"Command: {cmd.full_name}"

    def _extract_parameters(self, cmd: DiscoveredCommand) -> List[Dict[str, Any]]:
        """Extract parameter information from a Click command"""
        parameters = []

        if not cmd.callback:
            return parameters

        try:
            # Get the Click command object
            if hasattr(cmd.callback, "__click_params__"):
                for param in cmd.callback.__click_params__:
                    param_info = {
                        "name": param.name,
                        "type": str(param.type),
                        "required": param.required,
                        "help": getattr(param, "help", ""),
                        "default": getattr(param, "default", None),
                        "is_flag": isinstance(param, click.Option) and param.is_flag,
                        "opts": getattr(param, "opts", []),
                    }
                    parameters.append(param_info)
        except Exception as e:
            logger.debug(f"Failed to extract parameters for {cmd.full_name}: {e}")

        return parameters

    def _generate_examples(
        self, cmd: DiscoveredCommand, parameters: List[Dict[str, Any]]
    ) -> List[str]:
        """Generate usage examples for a command"""
        examples = []
        base_cmd = f"mcli {cmd.full_name.replace('.', ' ')}"

        # Basic example
        examples.append(base_cmd)

        # Examples with common parameters
        for param in parameters[:3]:  # Limit to first 3 params
            if param.get("is_flag"):
                examples.append(
                    f"{base_cmd} {param['opts'][0] if param['opts'] else '--' + param['name']}"
                )
            elif not param.get("required"):
                opt_name = param["opts"][0] if param["opts"] else f"--{param['name']}"
                if param["type"] == "TEXT":
                    examples.append(f"{base_cmd} {opt_name} 'value'")
                elif param["type"] == "INT":
                    examples.append(f"{base_cmd} {opt_name} 42")
                else:
                    examples.append(f"{base_cmd} {opt_name} <value>")

        return examples

    def _find_related_commands(self, cmd: DiscoveredCommand) -> List[str]:
        """Find commands related to the given command"""
        related = []

        # Commands in the same group/module
        for other_cmd in self.discovery.discovered_commands.values():
            if other_cmd.full_name != cmd.full_name and other_cmd.module_name == cmd.module_name:
                related.append(other_cmd.full_name)

        # Commands with similar names
        cmd_words = set(cmd.name.lower().split("_"))
        for other_cmd in self.discovery.discovered_commands.values():
            if other_cmd.full_name != cmd.full_name:
                other_words = set(other_cmd.name.lower().split("_"))
                if len(cmd_words.intersection(other_words)) > 0:
                    related.append(other_cmd.full_name)

        return related[:5]  # Limit to 5 related commands

    def _extract_usage_patterns(self, help_text: str, cmd: DiscoveredCommand) -> List[str]:
        """Extract common usage patterns from help text"""
        patterns = []

        # Extract usage lines from help text
        usage_section = re.search(
            r"Usage:(.*?)(?:\n\n|\n[A-Z]|\Z)", help_text, re.DOTALL | re.IGNORECASE
        )
        if usage_section:
            usage_lines = [
                line.strip() for line in usage_section.group(1).split("\n") if line.strip()
            ]
            patterns.extend(usage_lines)

        # Generate basic patterns
        base_pattern = f"mcli {cmd.full_name.replace('.', ' ')}"
        patterns.append(base_pattern)
        patterns.append(f"{base_pattern} [OPTIONS]")

        return list(set(patterns))  # Remove duplicates

    def _categorize_command(self, cmd: DiscoveredCommand) -> str:
        """Categorize the command based on its module and name"""
        module_parts = cmd.module_name.split(".")

        # Map modules to categories
        category_map = {
            "workflow": "Automation & Workflows",
            "app": "Application Management",
            "chat": "AI & Chat",
            "self": "System Management",
            "redis": "Cache & Performance",
            "visual": "UI & Visualization",
            "model": "AI Models",
            "daemon": "Background Services",
        }

        for module_part in module_parts:
            if module_part in category_map:
                return category_map[module_part]

        # Fallback categorization based on command name
        name_lower = cmd.name.lower()
        if any(word in name_lower for word in ["start", "stop", "restart", "status"]):
            return "Service Management"
        elif any(word in name_lower for word in ["list", "show", "info", "status"]):
            return "Information & Monitoring"
        elif any(word in name_lower for word in ["create", "add", "new"]):
            return "Creation & Setup"
        elif any(word in name_lower for word in ["delete", "remove", "clean"]):
            return "Cleanup & Removal"
        else:
            return "General Commands"

    def _generate_tags(self, cmd: DiscoveredCommand, help_text: str, category: str) -> List[str]:
        """Generate tags for better searchability"""
        tags = []

        # Add category as tag
        tags.append(category.lower().replace(" & ", "_").replace(" ", "_"))

        # Add module-based tags
        module_parts = cmd.module_name.split(".")
        tags.extend(module_parts)

        # Add name-based tags
        name_parts = cmd.name.split("_")
        tags.extend(name_parts)

        # Add tags based on help text content
        help_lower = help_text.lower()
        keyword_tags = {
            "file": ["file", "files", "filename"],
            "process": ["process", "processes", "pid"],
            "server": ["server", "service", "daemon"],
            "config": ["config", "configuration", "settings"],
            "performance": ["performance", "optimization", "speed"],
            "cache": ["cache", "caching", "redis"],
            "async": ["async", "asynchronous", "concurrent"],
            "monitor": ["monitor", "monitoring", "watch"],
            "automation": ["automation", "workflow", "schedule"],
        }

        for tag, keywords in keyword_tags.items():
            if any(keyword in help_lower for keyword in keywords):
                tags.append(tag)

        # Remove duplicates and return
        return list(set(tags))

    async def _build_command_index(self):
        """Build searchable index of all commands"""
        logger.info("Building command search index...")

        # Prepare documents for vectorization
        documents = []
        command_names = []

        for cmd_name, context in self.command_contexts.items():
            # Create a rich text representation of the command
            doc_text = self._create_command_document(context)
            documents.append(doc_text)
            command_names.append(cmd_name)

        if documents:
            # Get vectorizer for command search
            self.vectorizer = await self.vectorizer_manager.get_vectorizer(
                domain="commands", max_features=2000, ngram_range=(1, 3)
            )

            # Build the search index
            await self.vectorizer.fit_transform(documents)
            logger.info(f"Command index built with {len(documents)} commands")

    def _create_command_document(self, context: CommandContext) -> str:
        """Create a searchable document from command context"""
        parts = [
            f"Command: {context.command.full_name}",
            f"Description: {context.command.description}",
            f"Category: {context.category}",
            f"Help: {context.help_text}",
            f"Tags: {' '.join(context.tags)}",
        ]

        # Add parameter information
        for param in context.parameters:
            parts.append(f"Parameter: {param['name']} ({param['type']}) - {param.get('help', '')}")

        # Add examples
        parts.extend([f"Example: {ex}" for ex in context.examples])

        # Add usage patterns
        parts.extend([f"Usage: {pattern}" for pattern in context.usage_patterns])

        return " | ".join(parts)

    async def search_commands(
        self, query: str, limit: int = 10, category_filter: Optional[str] = None
    ) -> List[Tuple[CommandContext, float]]:
        """Search for commands using semantic similarity"""
        if not self._initialized:
            await self.initialize()

        if not self.command_contexts:
            return []

        try:
            # Get command names for search
            command_names = list(self.command_contexts.keys())
            documents = [
                self._create_command_document(ctx) for ctx in self.command_contexts.values()
            ]

            # Perform similarity search
            results = await self.vectorizer.similarity_search(query, documents, limit * 2)

            # Convert results to CommandContext objects with scores
            command_results = []
            for doc_idx, score in results:
                if 0 <= doc_idx < len(command_names):
                    cmd_name = command_names[doc_idx]
                    context = self.command_contexts[cmd_name]

                    # Apply category filter if specified
                    if category_filter and category_filter.lower() not in context.category.lower():
                        continue

                    command_results.append((context, score))

            return command_results[:limit]

        except Exception as e:
            logger.error(f"Command search failed: {e}")
            return []

    async def get_command_suggestions(
        self, user_input: str, context_history: List[str] = None
    ) -> List[Dict[str, Any]]:
        """Get intelligent command suggestions based on user input and context"""

        # Search for relevant commands
        search_results = await self.search_commands(user_input, limit=5)

        suggestions = []
        for context, score in search_results:
            suggestion = {
                "command": context.command.full_name,
                "name": context.command.name,
                "description": context.command.description,
                "category": context.category,
                "confidence": score,
                "examples": context.examples[:2],  # Top 2 examples
                "usage": context.usage_patterns[0] if context.usage_patterns else None,
                "parameters": [
                    p for p in context.parameters if p.get("required")
                ],  # Required params only
                "tags": context.tags,
            }
            suggestions.append(suggestion)

        return suggestions

    async def get_command_details(self, command_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific command"""
        context = self.command_contexts.get(command_name)
        if not context:
            return None

        return {
            "command": asdict(context.command),
            "help_text": context.help_text,
            "parameters": context.parameters,
            "examples": context.examples,
            "related_commands": context.related_commands,
            "usage_patterns": context.usage_patterns,
            "category": context.category,
            "tags": context.tags,
        }

    async def analyze_user_intent(self, user_message: str) -> Dict[str, Any]:
        """Analyze user intent and suggest appropriate actions"""
        intent_analysis = {
            "intent_type": "unknown",
            "confidence": 0.0,
            "suggested_commands": [],
            "action_keywords": [],
            "entities": [],
        }

        message_lower = user_message.lower()

        # Define intent patterns
        intent_patterns = {
            "start_service": ["start", "run", "launch", "begin", "activate", "turn on"],
            "stop_service": ["stop", "halt", "terminate", "kill", "shutdown", "turn off"],
            "status_check": ["status", "info", "show", "list", "check", "what is", "tell me about"],
            "help_request": ["help", "how to", "how do i", "explain", "tutorial", "guide"],
            "performance": ["performance", "optimize", "speed up", "faster", "slow", "cache"],
            "automation": ["automate", "schedule", "workflow", "cron", "recurring"],
        }

        # Find matching intent
        max_confidence = 0.0
        detected_intent = "unknown"

        for intent, keywords in intent_patterns.items():
            keyword_matches = sum(1 for keyword in keywords if keyword in message_lower)
            confidence = keyword_matches / len(keywords)

            if confidence > max_confidence:
                max_confidence = confidence
                detected_intent = intent
                intent_analysis["action_keywords"] = [kw for kw in keywords if kw in message_lower]

        intent_analysis["intent_type"] = detected_intent
        intent_analysis["confidence"] = max_confidence

        # Get relevant commands based on intent
        if max_confidence > 0:
            search_results = await self.search_commands(user_message, limit=3)
            intent_analysis["suggested_commands"] = [
                {
                    "command": ctx.command.full_name,
                    "description": ctx.command.description,
                    "confidence": score,
                }
                for ctx, score in search_results
            ]

        return intent_analysis

    def get_system_capabilities(self) -> Dict[str, Any]:
        """Get information about system capabilities for self-reference"""
        categories = {}
        for context in self.command_contexts.values():
            category = context.category
            if category not in categories:
                categories[category] = {"commands": [], "count": 0}

            categories[category]["commands"].append(
                {"name": context.command.full_name, "description": context.command.description}
            )
            categories[category]["count"] += 1

        return {
            "total_commands": len(self.command_contexts),
            "categories": categories,
            "available_services": [
                name
                for name, ctx in self.command_contexts.items()
                if any(tag in ctx.tags for tag in ["service", "daemon", "server"])
            ],
        }


# Global RAG system instance
_rag_system = None


async def get_command_rag_system() -> CommandRAGSystem:
    """Get or create the global RAG system instance"""
    global _rag_system
    if _rag_system is None:
        _rag_system = CommandRAGSystem()
        await _rag_system.initialize()
    return _rag_system
