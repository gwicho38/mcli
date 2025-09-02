"""
Enhanced MCLI Chat Assistant with Self-Referential Capabilities and RAG-based Command Search
"""

import asyncio
import json
import os
import re
import readline
from datetime import datetime
from typing import Any, Dict, List, Optional

import requests
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from mcli.chat.command_rag import get_command_rag_system
from mcli.chat.system_integration import handle_system_request
from mcli.lib.api.daemon_client import get_daemon_client
from mcli.lib.logger.logger import get_logger
from mcli.lib.toml.toml import read_from_toml
from mcli.lib.ui.styling import console

logger = get_logger(__name__)

# Load config
CONFIG_PATH = "config.toml"
config = {}
try:
    config = read_from_toml(CONFIG_PATH, "llm") or {}
except Exception:
    config = {}

# Enhanced system prompt for self-referential capabilities
ENHANCED_SYSTEM_PROMPT = """You are the MCLI Personal Assistant, an intelligent self-aware agent that helps manage your computer and tasks.

## Core Capabilities
I am a true personal assistant with deep knowledge of the MCLI system and these capabilities:
- **System Management**: Memory, disk, applications, cleanup, performance optimization
- **Job Scheduling**: Cron jobs, reminders, recurring tasks, automation workflows  
- **Process Management**: Background services, daemon control, Redis cache management
- **File Operations**: Organization, search, batch processing, format conversion
- **AI Integration**: Local and remote models, chat assistance, command reasoning
- **Performance**: Rust extensions, Redis caching, async operations, monitoring

## Self-Awareness & Command Knowledge
I have complete knowledge of all available MCLI commands and can:
- **Search Commands**: Find relevant commands using semantic similarity
- **Suggest Actions**: Recommend specific commands with proper options and parameters
- **Provide Examples**: Show exact command syntax and usage patterns
- **Explain Capabilities**: Detail what each command does and when to use it
- **Guide Workflows**: Chain commands together for complex automation tasks

## Current System Status
I maintain awareness of:
- All available MCLI commands and their parameters
- Currently scheduled jobs and their status
- System health and resource usage (CPU, memory, disk)
- Background services (Redis, daemon processes)
- Recent activities and completed tasks
- Performance optimization status (Rust extensions, caching)

## Communication Style
- **Actionable**: Always suggest specific MCLI commands when relevant
- **Precise**: Use exact command syntax with proper options
- **Contextual**: Consider user's current task and system state
- **Proactive**: Suggest optimizations and automations
- **Self-Referential**: Leverage my knowledge of MCLI capabilities

When users ask about tasks, I should:
1. Analyze their intent using command knowledge
2. Suggest specific MCLI commands with exact syntax
3. Provide working examples they can run immediately
4. Explain the reasoning behind my suggestions
5. Offer related commands for extended workflows

I can execute system commands and searches to provide real-time information and suggestions.
"""


class EnhancedChatClient:
    """Enhanced chat client with RAG-based command search and self-referential capabilities"""

    def __init__(self, use_remote: bool = False, model_override: str = None):
        self.daemon = get_daemon_client()
        self.history = []
        self.session_active = True
        self.use_remote = use_remote
        self.model_override = model_override
        self.console = Console()

        # RAG system for command search
        self.rag_system = None

        # Enhanced context tracking
        self.conversation_context = []
        self.system_context = {}
        self.user_preferences = {}
        self.simple_command_lookup = {}

        self._configure_model_settings()
        self._ensure_daemon_running()

        # Initialize basic command discovery synchronously
        try:
            from mcli.lib.discovery.command_discovery import ClickCommandDiscovery

            discovery = ClickCommandDiscovery()
            commands = discovery.discover_all_commands()

            self.simple_command_lookup = {}
            self.commands_list = commands  # Keep full list for better searching

            # Index by name and full_name
            for cmd in commands:
                self.simple_command_lookup[cmd.name] = cmd
                self.simple_command_lookup[cmd.full_name] = cmd

            logger.info(f"Initialized with {len(commands)} commands")
        except Exception as e:
            logger.debug(f"Command discovery failed: {e}")
            self.simple_command_lookup = {}
            self.commands_list = []

    async def _initialize_rag_system(self):
        """Initialize the RAG system for command search"""
        try:
            # Use a simplified command discovery for now to avoid hanging
            from mcli.lib.discovery.command_discovery import ClickCommandDiscovery

            discovery = ClickCommandDiscovery()
            commands = discovery.discover_all_commands()

            # Create a comprehensive command lookup for basic functionality
            self.simple_command_lookup = {}
            self.commands_list = commands  # Keep full list for better searching

            # Index by name, full_name, and description keywords
            for cmd in commands:
                self.simple_command_lookup[cmd.name] = cmd
                self.simple_command_lookup[cmd.full_name] = cmd
            logger.info(f"Simple command discovery initialized with {len(commands)} commands")

            # Skip the full RAG system for now to avoid hanging
            self.rag_system = None

        except Exception as e:
            logger.error(f"Failed to initialize command discovery: {e}")
            self.rag_system = None
            self.simple_command_lookup = {}

    def _configure_model_settings(self):
        """Configure model settings with enhanced system prompt"""
        global config

        if not self.use_remote:
            config.update(
                {
                    "provider": "local",
                    "model": self.model_override or "prajjwal1/bert-tiny",
                    "ollama_base_url": "http://localhost:8080",
                    "system_prompt": ENHANCED_SYSTEM_PROMPT,
                }
            )
        else:
            if config.get("openai_api_key") or config.get("anthropic_api_key"):
                config["system_prompt"] = ENHANCED_SYSTEM_PROMPT
            else:
                self.console.print(
                    "⚠️ No API keys found. Switching to local models.", style="yellow"
                )
                self.use_remote = False
                self._configure_model_settings()

    def _ensure_daemon_running(self):
        """Ensure the daemon is running for system integration"""
        try:
            if not self.daemon.health_check():
                self.daemon.start_daemon()
        except Exception as e:
            logger.debug(f"Daemon check failed: {e}")

    async def _enrich_message_with_context(self, user_message: str) -> str:
        """Enrich user message with relevant command context and system information"""
        enriched_parts = [user_message]

        # Initialize RAG system if not already done
        if self.rag_system is None:
            await self._initialize_rag_system()

        # Skip command enrichment in the context - let the AI response handle it
        try:
            # Add system status only
            system_status = await self._get_system_status()
            if system_status:
                enriched_parts.append(f"\n--- SYSTEM STATUS ---")
                enriched_parts.append(system_status)

        except Exception as e:
            logger.debug(f"System status failed: {e}")

        return "\n".join(enriched_parts)

    async def _get_system_status(self) -> str:
        """Get current system status for context"""
        status_parts = []

        try:
            # Redis status
            import subprocess

            result = subprocess.run(
                ["python", "-m", "mcli", "redis", "status"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if "RUNNING" in result.stdout:
                status_parts.append("Redis cache: Active")
            else:
                status_parts.append("Redis cache: Inactive")
        except:
            pass

        try:
            # Performance status
            from mcli.lib.performance.rust_bridge import check_rust_extensions

            rust_status = check_rust_extensions()
            if rust_status["available"]:
                status_parts.append(
                    f"Rust extensions: Active ({sum(rust_status.values()) - 1}/4 components)"
                )
            else:
                status_parts.append("Rust extensions: Inactive")
        except:
            pass

        return " | ".join(status_parts) if status_parts else "System status unavailable"

    def start_interactive_session(self):
        """Start enhanced interactive chat session"""
        self.console.print("\n🤖 MCLI Enhanced Chat Assistant", style="bold cyan")
        self.console.print(
            "I can help you discover and use MCLI commands through intelligent search!",
            style="cyan",
        )
        self.console.print(
            "Type 'help' for assistance, 'commands' to search commands, or 'quit' to exit.\n"
        )

        while self.session_active:
            try:
                user_input = input("💬 You: ").strip()

                if not user_input:
                    continue

                # Handle special commands
                if user_input.lower() in ["quit", "exit", "bye"]:
                    self._handle_quit()
                    break
                elif user_input.lower() == "help":
                    self._show_help()
                    continue
                elif user_input.lower().startswith("commands"):
                    asyncio.run(self._handle_command_search(user_input))
                    continue
                elif user_input.lower() == "status":
                    asyncio.run(self._show_system_status())
                    continue
                elif user_input.lower() == "clear":
                    os.system("clear" if os.name == "posix" else "cls")
                    continue

                # Process the message with RAG enhancement
                asyncio.run(self._process_enhanced_message(user_input))

            except KeyboardInterrupt:
                self.console.print("\n\n👋 Goodbye!", style="cyan")
                break
            except EOFError:
                break
            except Exception as e:
                self.console.print(f"❌ Error: {e}", style="red")

    async def _process_enhanced_message(self, user_message: str):
        """Process message with RAG enhancement"""
        try:
            # Enrich message with command context
            enriched_message = await self._enrich_message_with_context(user_message)

            # Add to conversation history
            self.conversation_context.append(
                {
                    "user": user_message,
                    "timestamp": datetime.now().isoformat(),
                    "enriched": len(enriched_message) > len(user_message),
                }
            )

            # Get AI response
            response = await self._get_ai_response(enriched_message)

            if response:
                self._display_response(response)

                # Extract and highlight any MCLI commands in the response
                await self._highlight_mcli_commands(response)
            else:
                self.console.print("❌ Sorry, I couldn't process that request.", style="red")

        except Exception as e:
            logger.error(f"Message processing failed: {e}")
            self.console.print(f"❌ Error processing message: {e}", style="red")

    async def _get_ai_response(self, message: str) -> Optional[str]:
        """Get AI response using configured provider"""
        try:
            if self.use_remote and config.get("openai_api_key"):
                return await self._get_openai_response(message)
            elif self.use_remote and config.get("anthropic_api_key"):
                return await self._get_anthropic_response(message)
            else:
                return await self._get_local_response(message)
        except Exception as e:
            logger.error(f"AI response failed: {e}")
            return None

    async def _get_openai_response(self, message: str) -> str:
        """Get response from OpenAI"""
        try:
            import openai

            openai.api_key = config.get("openai_api_key")

            response = openai.chat.completions.create(
                model=config.get("model", "gpt-3.5-turbo"),
                messages=[
                    {
                        "role": "system",
                        "content": config.get("system_prompt", ENHANCED_SYSTEM_PROMPT),
                    },
                    {"role": "user", "content": message},
                ],
                temperature=config.get("temperature", 0.7),
                max_tokens=1000,
            )

            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI request failed: {e}")
            return None

    async def _get_anthropic_response(self, message: str) -> str:
        """Get response from Anthropic"""
        try:
            import anthropic

            client = anthropic.Anthropic(api_key=config.get("anthropic_api_key"))

            response = client.messages.create(
                model=config.get("model", "claude-3-sonnet-20240229"),
                max_tokens=1000,
                temperature=config.get("temperature", 0.7),
                system=config.get("system_prompt", ENHANCED_SYSTEM_PROMPT),
                messages=[{"role": "user", "content": message}],
            )

            return response.content[0].text
        except Exception as e:
            logger.error(f"Anthropic request failed: {e}")
            return None

    async def _get_local_response(self, message: str) -> str:
        """Get response from local lightweight model"""
        try:
            # Use improved command matching for local responses
            if hasattr(self, "commands_list") and self.commands_list:
                user_lower = message.lower()
                user_words = [word for word in user_lower.split() if len(word) > 2]
                matching_commands = []

                # Search through all commands for better matching
                for cmd in self.commands_list:
                    score = 0
                    matched_reasons = []

                    # High priority: Check for exact phrase matches in full name
                    cmd_name_clean = cmd.full_name.lower().replace(".", " ")
                    if user_lower in cmd_name_clean:
                        score += 10
                        matched_reasons.append(f"exact phrase match")

                    # High priority: Check if user input matches command structure
                    user_parts = user_lower.split()
                    cmd_parts = cmd.full_name.lower().split(".")

                    # Check if all user words appear in the command path
                    if len(user_parts) >= 2 and all(
                        any(user_word in cmd_part for cmd_part in cmd_parts)
                        for user_word in user_parts
                    ):
                        score += 8
                        matched_reasons.append(f"matches command structure")

                    # Medium priority: Individual word matches in name
                    for word in user_words:
                        if word in cmd.full_name.lower():
                            score += 2
                            matched_reasons.append(f"name contains '{word}'")

                    # Lower priority: Check description for keywords
                    for word in user_words:
                        if word in cmd.description.lower():
                            score += 1
                            matched_reasons.append(f"description contains '{word}'")

                    # Special keyword matching
                    keyword_map = {
                        "video": ["video", "mp4", "avi", "mov", "ffmpeg", "frames"],
                        "redis": ["redis", "cache"],
                        "file": ["file", "convert", "pdf", "oxps"],
                        "daemon": ["daemon", "service", "api"],
                        "workflow": ["workflow", "automation"],
                        "system": ["system", "status", "monitor"],
                    }

                    for query_word in user_words:
                        for category, keywords in keyword_map.items():
                            if query_word in keywords:
                                for keyword in keywords:
                                    if (
                                        keyword in cmd.full_name.lower()
                                        or keyword in cmd.description.lower()
                                    ):
                                        score += 3
                                        matched_reasons.append(f"matches {category} category")
                                        break

                    if score > 0:
                        matching_commands.append((cmd, score, matched_reasons))

                # Sort by score and remove duplicates
                matching_commands.sort(key=lambda x: x[1], reverse=True)

                # Remove duplicates by full_name
                seen = set()
                unique_commands = []
                for cmd, score, reasons in matching_commands:
                    if cmd.full_name not in seen:
                        seen.add(cmd.full_name)
                        unique_commands.append((cmd, score, reasons))

                # Build response
                if unique_commands:
                    response_parts = ["I found these relevant MCLI commands for you:\n"]
                    for i, (cmd, score, reasons) in enumerate(unique_commands[:5], 1):
                        response_parts.append(f"{i}. **mcli {cmd.full_name.replace('.', ' ')}**")
                        response_parts.append(f"   {cmd.description}")
                        response_parts.append(f"   (Score: {score} - {', '.join(reasons[:2])})\n")

                    response_parts.append("You can get more help with: `mcli <command> --help`")
                    return "\n".join(response_parts)
                else:
                    # Suggest broader search
                    return (
                        f"I didn't find specific commands for '{message}', but I can help you explore!\n\n"
                        f"Try these approaches:\n"
                        f"• Use 'commands' to browse all available commands\n"
                        f"• Ask about specific topics like 'video processing', 'file conversion', 'system monitoring'\n"
                        f"• I have {len(self.commands_list)} commands available across categories like workflow, redis, files, and more!"
                    )

            return "I'm ready to help! You can ask me about MCLI commands or use 'commands' to explore available options."

        except Exception as e:
            logger.error(f"Local response failed: {e}")
            return f"I'm here to help with MCLI commands. Try asking about specific tasks like 'video processing' or 'file conversion'."

    def _display_response(self, response: str):
        """Display AI response with enhanced formatting"""
        # Create a panel for the response
        panel = Panel(
            response,
            title="🤖 MCLI Assistant",
            title_align="left",
            border_style="cyan",
            padding=(1, 2),
        )
        self.console.print(panel)

    async def _highlight_mcli_commands(self, response: str):
        """Extract and highlight MCLI commands from response"""
        # Look for command patterns in the response
        command_pattern = r"`mcli\s+([^`]+)`|mcli\s+([\w\s\-\.]+)"
        matches = re.findall(command_pattern, response, re.IGNORECASE)

        if matches:
            self.console.print("\n💡 **Detected Commands:**", style="yellow")
            for match in matches[:3]:  # Show up to 3 commands
                command = match[0] or match[1]
                if command.strip():
                    self.console.print(f"   • `mcli {command.strip()}`", style="green")

    async def _handle_command_search(self, query: str):
        """Handle command search queries"""
        search_term = query[8:].strip() if len(query) > 8 else ""  # Remove "commands"

        if not self.rag_system:
            self.console.print(
                "❌ Command search not available (RAG system not initialized)", style="red"
            )
            return

        if not search_term:
            # Show all categories
            capabilities = self.rag_system.get_system_capabilities()
            self._show_command_categories(capabilities)
        else:
            # Search for specific commands
            await self._search_and_display_commands(search_term)

    def _show_command_categories(self, capabilities: Dict[str, Any]):
        """Show command categories"""
        table = Table(title="📋 MCLI Command Categories")
        table.add_column("Category", style="cyan")
        table.add_column("Commands", justify="right", style="magenta")
        table.add_column("Examples", style="green")

        for category, info in capabilities["categories"].items():
            examples = ", ".join([cmd["name"].split(".")[-1] for cmd in info["commands"][:2]])
            if len(info["commands"]) > 2:
                examples += f", ... (+{len(info['commands']) - 2} more)"

            table.add_row(category, str(info["count"]), examples)

        self.console.print(table)
        self.console.print(
            "\n💡 Use 'commands <search_term>' to find specific commands", style="yellow"
        )

    async def _search_and_display_commands(self, search_term: str):
        """Search and display matching commands"""
        try:
            results = await self.rag_system.search_commands(search_term, limit=8)

            if not results:
                self.console.print(f"❌ No commands found matching: {search_term}", style="red")
                return

            self.console.print(f"\n🔍 **Commands matching '{search_term}':**\n")

            for i, (context, score) in enumerate(results, 1):
                cmd = context.command
                # Create command display
                self.console.print(f"**{i}. {cmd.full_name.replace('.', ' ')}**", style="cyan")
                self.console.print(f"   {cmd.description}", style="white")
                self.console.print(f"   Category: {context.category}", style="yellow")

                if context.examples:
                    self.console.print(f"   Example: `{context.examples[0]}`", style="green")

                self.console.print(f"   Relevance: {score:.2f}\n", style="dim")

        except Exception as e:
            self.console.print(f"❌ Search failed: {e}", style="red")

    async def _show_system_status(self):
        """Show comprehensive system status"""
        try:
            status_info = await self._get_system_status()

            # Create status panel
            status_panel = Panel(status_info, title="📊 System Status", border_style="green")
            self.console.print(status_panel)

            # Show RAG system status
            if self.rag_system:
                capabilities = self.rag_system.get_system_capabilities()
                self.console.print(
                    f"\n🧠 Command Knowledge: {capabilities['total_commands']} commands indexed"
                )
            else:
                self.console.print("\n⚠️ Command search system not available", style="yellow")

        except Exception as e:
            self.console.print(f"❌ Status check failed: {e}", style="red")

    def _show_help(self):
        """Show enhanced help information"""
        help_text = """
🤖 **MCLI Enhanced Chat Assistant Help**

**Basic Commands:**
• Just chat naturally - I'll suggest relevant MCLI commands
• `help` - Show this help message
• `commands` - Browse all available command categories  
• `commands <search>` - Search for specific commands
• `status` - Show system and performance status
• `clear` - Clear the screen
• `quit` - Exit the chat

**What I Can Do:**
✨ **Command Discovery**: Find the right MCLI command for any task
🔍 **Semantic Search**: Search commands by description or intent
💡 **Smart Suggestions**: Get contextual command recommendations
📖 **Usage Examples**: See exact command syntax and parameters
⚡ **Performance Aware**: Know about Rust extensions and Redis status
🔗 **Workflow Building**: Chain commands together for complex tasks

**Example Queries:**
• "How do I start Redis cache?"
• "Show me file conversion commands"  
• "I need to schedule a recurring task"
• "What performance optimizations are available?"
• "Help me automate video processing"

**Tips:**
• Be specific about what you want to accomplish
• Ask for examples if you need exact command syntax
• Use 'commands <keyword>' to explore specific areas
• I can see all available MCLI commands and their capabilities!
"""

        help_panel = Panel(help_text.strip(), title="❓ Help & Usage Guide", border_style="blue")
        self.console.print(help_panel)

    def _handle_quit(self):
        """Handle quit command"""
        self.session_active = False
        self.console.print("\n🎯 **Session Summary:**")
        if self.conversation_context:
            self.console.print(f"   • Processed {len(self.conversation_context)} messages")
            enriched_count = sum(1 for ctx in self.conversation_context if ctx.get("enriched"))
            if enriched_count:
                self.console.print(f"   • Enhanced {enriched_count} messages with command context")

        self.console.print("\n👋 **Thank you for using MCLI Enhanced Chat!**", style="cyan")
        self.console.print(
            "💡 Remember: You can always run `mcli chat` to start a new session.", style="yellow"
        )


# Compatibility function for existing interface
def create_enhanced_chat_client(
    use_remote: bool = False, model_override: str = None
) -> EnhancedChatClient:
    """Create enhanced chat client instance"""
    return EnhancedChatClient(use_remote=use_remote, model_override=model_override)
