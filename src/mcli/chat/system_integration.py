"""
System Integration for MCLI Chat
Provides system control capabilities directly within chat conversations
"""

import json
from typing import Any, Dict, List

from mcli.lib.logger.logger import get_logger

from .system_controller import (
    change_directory,
    clean_simulator_data,
    control_app,
    execute_shell_command,
    execute_system_command,
    get_current_directory,
    list_directory,
    open_file_or_url,
    open_textedit_and_write,
    system_controller,
    take_screenshot,
)

logger = get_logger(__name__)


class ChatSystemIntegration:
    """Integration layer between chat and system control"""

    def __init__(self):
        self.system_controller = system_controller
        self.enabled = True

        # Define available system functions
        self.system_functions = {
            "open_textedit_and_write": {
                "function": open_textedit_and_write,
                "description": "Open TextEdit and write specified text",
                "parameters": {
                    "text": "Text to write in TextEdit",
                    "filename": "Optional filename to save (will save to Desktop)",
                },
                "examples": [
                    "Open TextEdit and write 'Hello, World!'",
                    "Write 'My notes' in TextEdit and save as 'notes.txt'",
                ],
            },
            "control_application": {
                "function": control_app,
                "description": "Control system applications (open, close, interact)",
                "parameters": {
                    "app_name": "Name of the application (e.g., 'TextEdit', 'Calculator')",
                    "action": "Action to perform (open, close, new_document, write_text)",
                    "**kwargs": "Additional parameters like text, filename",
                },
                "examples": ["Open Calculator", "Close TextEdit", "Open new document in TextEdit"],
            },
            "execute_command": {
                "function": execute_system_command,
                "description": "Execute shell/terminal commands",
                "parameters": {
                    "command": "Shell command to execute",
                    "description": "Optional description of what the command does",
                },
                "examples": [
                    "List files in current directory",
                    "Check system uptime",
                    "Create a new folder",
                ],
            },
            "take_screenshot": {
                "function": take_screenshot,
                "description": "Take a screenshot and save to Desktop",
                "parameters": {
                    "filename": "Optional filename (will auto-generate if not provided)"
                },
                "examples": ["Take a screenshot", "Take screenshot and save as 'my_screen.png'"],
            },
            "open_file_or_url": {
                "function": open_file_or_url,
                "description": "Open files or URLs with default system application",
                "parameters": {"path_or_url": "File path or URL to open"},
                "examples": [
                    "Open https://google.com",
                    "Open ~/Documents/file.txt",
                    "Open current directory in Finder",
                ],
            },
            "get_system_info": {
                "function": self.system_controller.get_system_info,
                "description": "Get comprehensive system information (CPU, memory, disk, etc.)",
                "parameters": {},
                "examples": [
                    "What is my system information?",
                    "Show system specs",
                    "How much RAM do I have?",
                ],
            },
            "get_system_time": {
                "function": self.system_controller.get_system_time,
                "description": "Get current system time and date",
                "parameters": {},
                "examples": [
                    "What time is it?",
                    "What is the current time?",
                    "Show me the date and time",
                ],
            },
            "get_memory_usage": {
                "function": self.system_controller.get_memory_usage,
                "description": "Get detailed memory usage information",
                "parameters": {},
                "examples": ["How much memory am I using?", "Show memory usage", "Check RAM usage"],
            },
            "get_disk_usage": {
                "function": self.system_controller.get_disk_usage,
                "description": "Get disk space and usage information",
                "parameters": {},
                "examples": [
                    "How much disk space do I have?",
                    "Show disk usage",
                    "Check storage space",
                ],
            },
            "clear_system_caches": {
                "function": self.system_controller.clear_system_caches,
                "description": "Clear system caches and temporary files",
                "parameters": {},
                "examples": ["Clear system caches", "Clean up temporary files", "Free up space"],
            },
            "change_directory": {
                "function": change_directory,
                "description": "Navigate to a directory",
                "parameters": {"path": "Directory path to navigate to"},
                "examples": [
                    "Navigate to /System/Volumes/Data",
                    "Go to ~/Documents",
                    "Change to /tmp",
                ],
            },
            "list_directory": {
                "function": list_directory,
                "description": "List contents of a directory",
                "parameters": {
                    "path": "Directory path to list (optional, defaults to current)",
                    "show_hidden": "Show hidden files (optional)",
                    "detailed": "Show detailed file information (optional)",
                },
                "examples": [
                    "List current directory",
                    "Show files in /System/Volumes/Data",
                    "List all files including hidden ones",
                ],
            },
            "clean_simulator_data": {
                "function": clean_simulator_data,
                "description": "Clean iOS/watchOS simulator cache and temporary data",
                "parameters": {},
                "examples": [
                    "Clean simulator data",
                    "Remove iOS simulator caches",
                    "Free up simulator storage",
                ],
            },
            "execute_shell_command": {
                "function": execute_shell_command,
                "description": "Execute shell commands with full terminal access",
                "parameters": {
                    "command": "Shell command to execute",
                    "working_directory": "Directory to run command in (optional)",
                },
                "examples": ["Run ls -la", "Execute find command", "Run custom shell scripts"],
            },
            "get_current_directory": {
                "function": get_current_directory,
                "description": "Get current working directory",
                "parameters": {},
                "examples": ["Where am I?", "Show current directory", "What's my current path?"],
            },
        }

    def handle_system_request(self, request: str) -> Dict[str, Any]:
        """
        Analyze user request and execute appropriate system function
        This is the main entry point for chat system integration
        """

        if not self.enabled:
            return {
                "success": False,
                "error": "System control is disabled",
                "suggestion": "Enable system control to use this feature",
            }

        # Parse the request and determine action
        request_lower = request.lower()

        # System information requests
        if any(
            phrase in request_lower
            for phrase in ["what time", "current time", "system time", "what is the time"]
        ):
            return self._handle_system_time_request(request)

        elif any(
            phrase in request_lower
            for phrase in ["system info", "system information", "system specs", "hardware info"]
        ):
            return self._handle_system_info_request(request)

        # Hardware devices requests
        elif any(
            phrase in request_lower
            for phrase in [
                "hardware devices",
                "connected devices",
                "list hardware",
                "show devices",
                "connected hardware",
            ]
        ):
            return self._handle_hardware_devices_request(request)

        elif any(
            phrase in request_lower
            for phrase in [
                "memory usage",
                "ram usage",
                "how much memory",
                "how much ram",
                "memory info",
            ]
        ):
            return self._handle_memory_request(request)

        elif any(
            phrase in request_lower
            for phrase in [
                "disk usage",
                "disk space",
                "storage space",
                "how much space",
                "free space",
            ]
        ):
            return self._handle_disk_request(request)

        elif any(
            phrase in request_lower
            for phrase in [
                "clear cache",
                "clean cache",
                "clear temp",
                "free up space",
                "clean system",
                "clear system cache",
            ]
        ):
            return self._handle_cache_clear_request(request)

        # Navigation requests
        elif any(
            phrase in request_lower
            for phrase in ["navigate to", "go to", "change to", "cd to", "move to"]
        ):
            return self._handle_navigation_request(request)

        # Directory listing requests (more specific to avoid false positives)
        elif any(
            phrase in request_lower
            for phrase in ["list files", "list directory", "show files", "ls", "dir", "what's in"]
        ):
            return self._handle_directory_listing_request(request)

        # Simulator cleanup requests
        elif any(
            phrase in request_lower
            for phrase in ["clean simulator", "simulator data", "clean ios", "clean watchos"]
        ):
            return self._handle_simulator_cleanup_request(request)

        # Shell command requests
        elif any(
            phrase in request_lower for phrase in ["run command", "execute", "shell", "terminal"]
        ):
            return self._handle_shell_command_request(request)

        # Current directory requests
        elif any(
            phrase in request_lower
            for phrase in ["where am i", "current directory", "pwd", "current path"]
        ):
            return self._handle_current_directory_request(request)

        # TextEdit operations
        elif "textedit" in request_lower and ("write" in request_lower or "type" in request_lower):
            return self._handle_textedit_request(request)

        # Application control
        elif any(word in request_lower for word in ["open", "close", "launch", "quit"]):
            return self._handle_app_control_request(request)

        # Screenshot
        elif "screenshot" in request_lower or "screen capture" in request_lower:
            return self._handle_screenshot_request(request)

        # File/URL opening
        elif "open" in request_lower and (
            "file" in request_lower or "url" in request_lower or "http" in request_lower
        ):
            return self._handle_open_request(request)

        # Command execution
        elif any(word in request_lower for word in ["run", "execute", "command", "terminal"]):
            return self._handle_command_request(request)

        else:
            return {
                "success": False,
                "error": "Could not understand system request",
                "available_functions": list(self.system_functions.keys()),
                "suggestion": "Try: 'Open TextEdit and write Hello World' or 'Take a screenshot'",
            }

    def _handle_textedit_request(self, request: str) -> Dict[str, Any]:
        """Handle TextEdit-specific requests"""
        try:
            # Extract text to write
            text = "Hello, World!"  # default
            filename = None

            # Simple text extraction patterns
            if '"' in request:
                # Extract text in quotes
                parts = request.split('"')
                if len(parts) >= 2:
                    text = parts[1]
            elif "write " in request.lower():
                # Extract text after "write"
                parts = request.lower().split("write ")
                if len(parts) > 1:
                    text_part = parts[1]
                    # Remove common words
                    for word in ["in textedit", "to textedit", "and save", "then save"]:
                        text_part = text_part.replace(word, "")
                    text = text_part.strip()

            # Extract filename if mentioned
            if "save as" in request.lower():
                parts = request.lower().split("save as")
                if len(parts) > 1:
                    filename_part = parts[1].strip()
                    # Extract filename (remove quotes and common words)
                    filename = filename_part.replace('"', "").replace("'", "").split()[0]
                    if not filename.endswith(".txt"):
                        filename += ".txt"

            result = open_textedit_and_write(text, filename)

            if result["success"]:
                message = f"✅ Opened TextEdit and wrote: '{text}'"
                if filename:
                    message += f" (saved as {filename})"
                result["message"] = message

            return result

        except Exception as e:
            return {
                "success": False,
                "error": f"Error handling TextEdit request: {e}",
                "request": request,
            }

    def _handle_app_control_request(self, request: str) -> Dict[str, Any]:
        """Handle application control requests"""
        try:
            request_lower = request.lower()

            # Determine action
            if "open" in request_lower or "launch" in request_lower:
                action = "open"
            elif "close" in request_lower or "quit" in request_lower:
                action = "close"
            elif "new document" in request_lower:
                action = "new_document"
            else:
                action = "open"  # default

            # Extract app name
            app_name = "TextEdit"  # default

            common_apps = {
                "textedit": "TextEdit",
                "calculator": "Calculator",
                "finder": "Finder",
                "safari": "Safari",
                "chrome": "Google Chrome",
                "firefox": "Firefox",
                "terminal": "Terminal",
                "preview": "Preview",
                "notes": "Notes",
                "mail": "Mail",
            }

            for app_key, app_value in common_apps.items():
                if app_key in request_lower:
                    app_name = app_value
                    break

            result = control_app(app_name, action)

            if result["success"]:
                result["message"] = f"✅ {action.title()} {app_name}"

            return result

        except Exception as e:
            return {
                "success": False,
                "error": f"Error handling app control request: {e}",
                "request": request,
            }

    def _handle_screenshot_request(self, request: str) -> Dict[str, Any]:
        """Handle screenshot requests"""
        try:
            filename = None

            # Extract filename if specified
            if "save as" in request.lower() or "name" in request.lower():
                # Simple filename extraction
                words = request.split()
                for i, word in enumerate(words):
                    if word.lower() in ["as", "name"] and i < len(words) - 1:
                        filename = words[i + 1].replace('"', "").replace("'", "")
                        if not filename.endswith(".png"):
                            filename += ".png"
                        break

            result = take_screenshot(filename)

            if result["success"]:
                path = result.get("screenshot_path", "Desktop")
                result["message"] = f"✅ Screenshot saved to: {path}"

            return result

        except Exception as e:
            return {"success": False, "error": f"Error taking screenshot: {e}", "request": request}

    def _handle_open_request(self, request: str) -> Dict[str, Any]:
        """Handle file/URL opening requests"""
        try:
            # Extract URL or file path
            words = request.split()
            path_or_url = None

            for word in words:
                if word.startswith("http") or word.startswith("www.") or "/" in word:
                    path_or_url = word
                    break

            if not path_or_url:
                # Look for common patterns
                if "google" in request.lower():
                    path_or_url = "https://google.com"
                elif "current directory" in request.lower() or "this folder" in request.lower():
                    path_or_url = "."
                else:
                    return {
                        "success": False,
                        "error": "Could not determine what to open",
                        "suggestion": "Specify a URL (like https://google.com) or file path",
                    }

            result = open_file_or_url(path_or_url)

            if result["success"]:
                result["message"] = f"✅ Opened: {path_or_url}"

            return result

        except Exception as e:
            return {"success": False, "error": f"Error opening file/URL: {e}", "request": request}

    def _handle_command_request(self, request: str) -> Dict[str, Any]:
        """Handle command execution requests"""
        try:
            # Extract command (this is simplified - in practice you'd want more security)
            command = None

            if "run " in request.lower():
                parts = request.lower().split("run ")
                if len(parts) > 1:
                    command = parts[1].strip()
            elif "execute " in request.lower():
                parts = request.lower().split("execute ")
                if len(parts) > 1:
                    command = parts[1].strip()

            if not command:
                return {
                    "success": False,
                    "error": "Could not extract command to execute",
                    "suggestion": "Try: 'Run ls' or 'Execute date'",
                }

            # Basic security check (you'd want more comprehensive checks)
            dangerous_commands = ["rm -rf", "sudo", "format", "del /", "> /dev"]
            if any(dangerous in command.lower() for dangerous in dangerous_commands):
                return {
                    "success": False,
                    "error": "Command blocked for security reasons",
                    "command": command,
                }

            result = execute_system_command(command, f"User requested: {command}")

            if result["success"]:
                result["message"] = f"✅ Executed: {command}"

            return result

        except Exception as e:
            return {"success": False, "error": f"Error executing command: {e}", "request": request}

    def _handle_system_time_request(self, request: str) -> Dict[str, Any]:
        """Handle system time requests"""
        try:
            result = self.system_controller.get_system_time()

            if result["success"]:
                time_data = result["data"]
                result["message"] = (
                    f"⏰ Current time: {time_data['current_time']} ({time_data['timezone'][0]})"
                )

            return result

        except Exception as e:
            return {
                "success": False,
                "error": f"Error getting system time: {e}",
                "request": request,
            }

    def _handle_system_info_request(self, request: str) -> Dict[str, Any]:
        """Handle system information requests"""
        try:
            result = self.system_controller.get_system_info()

            if result["success"]:
                info_data = result["data"]
                summary = [
                    f"💻 System: {info_data['system']} {info_data['machine']}",
                    f"🧠 CPU: {info_data['cpu']['logical_cores']} cores, {info_data['cpu']['cpu_usage_percent']}% usage",
                    f"💾 RAM: {info_data['memory']['used_gb']:.1f}GB used / {info_data['memory']['total_gb']:.1f}GB total ({info_data['memory']['usage_percent']}%)",
                    f"⏰ Uptime: {info_data['uptime_hours']:.1f} hours",
                ]
                result["message"] = "\n".join(summary)

            return result

        except Exception as e:
            return {
                "success": False,
                "error": f"Error getting system information: {e}",
                "request": request,
            }

    def _handle_hardware_devices_request(self, request: str) -> Dict[str, Any]:
        """Handle hardware devices listing requests"""
        try:
            # Use shell command to get hardware information
            import subprocess

            summary = ["🔌 Connected Hardware Devices:"]

            try:
                # Get USB devices
                result = subprocess.run(
                    ["system_profiler", "SPUSBDataType"], capture_output=True, text=True, timeout=10
                )

                if result.returncode == 0:
                    usb_lines = result.stdout.split("\n")
                    usb_devices = []
                    for line in usb_lines:
                        line = line.strip()
                        if ":" in line and not line.startswith("USB") and len(line) < 100:
                            if any(
                                keyword in line.lower()
                                for keyword in [
                                    "mouse",
                                    "keyboard",
                                    "disk",
                                    "camera",
                                    "audio",
                                    "hub",
                                ]
                            ):
                                device_name = line.split(":")[0].strip()
                                if device_name and len(device_name) > 3:
                                    usb_devices.append(device_name)

                    if usb_devices:
                        summary.append("💾 USB Devices:")
                        for device in usb_devices[:8]:  # Limit to 8 devices
                            summary.append(f"  • {device}")

            except Exception:
                pass

            try:
                # Get network interfaces
                result = subprocess.run(
                    ["ifconfig", "-a"], capture_output=True, text=True, timeout=5
                )

                if result.returncode == 0:
                    interfaces = []
                    for line in result.stdout.split("\n"):
                        if line and not line.startswith("\t") and not line.startswith(" "):
                            interface_name = line.split(":")[0].strip()
                            if interface_name and interface_name not in ["lo0", "gif0", "stf0"]:
                                interfaces.append(interface_name)

                    if interfaces:
                        summary.append("🌐 Network Interfaces:")
                        for interface in interfaces[:6]:  # Limit to 6 interfaces
                            summary.append(f"  • {interface}")

            except Exception:
                pass

            try:
                # Get audio devices
                result = subprocess.run(
                    ["system_profiler", "SPAudioDataType"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                if result.returncode == 0:
                    audio_devices = []
                    for line in result.stdout.split("\n"):
                        line = line.strip()
                        if ":" in line and (
                            "Built-in" in line or "USB" in line or "Bluetooth" in line
                        ):
                            device_name = line.split(":")[0].strip()
                            if device_name and len(device_name) > 3:
                                audio_devices.append(device_name)

                    if audio_devices:
                        summary.append("🔊 Audio Devices:")
                        for device in audio_devices[:4]:  # Limit to 4 devices
                            summary.append(f"  • {device}")

            except Exception:
                pass

            if len(summary) == 1:  # Only has header
                summary.append("ℹ️  No specific hardware devices detected via system profiler")
                summary.append("💡 Try: 'system info' for general hardware information")

            return {
                "success": True,
                "message": "\n".join(summary),
                "description": "List connected hardware devices",
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Error getting hardware devices: {e}",
                "suggestion": "Try 'system info' for general hardware information",
                "request": request,
            }

    def _handle_memory_request(self, request: str) -> Dict[str, Any]:
        """Handle memory usage requests"""
        try:
            result = self.system_controller.get_memory_usage()

            if result["success"]:
                memory_data = result["data"]
                vm = memory_data["virtual_memory"]
                swap = memory_data["swap_memory"]

                summary = [
                    f"💾 Memory Usage:",
                    f"  RAM: {vm['used_gb']:.1f}GB used / {vm['total_gb']:.1f}GB total ({vm['usage_percent']}%)",
                    f"  Available: {vm['available_gb']:.1f}GB",
                    f"  Swap: {swap['used_gb']:.1f}GB used / {swap['total_gb']:.1f}GB total ({swap['usage_percent']}%)",
                ]

                # Add recommendations if any
                if memory_data["recommendations"]:
                    summary.append("📋 Recommendations:")
                    for rec in memory_data["recommendations"]:
                        summary.append(f"  • {rec}")

                result["message"] = "\n".join(summary)

            return result

        except Exception as e:
            return {
                "success": False,
                "error": f"Error getting memory usage: {e}",
                "request": request,
            }

    def _handle_disk_request(self, request: str) -> Dict[str, Any]:
        """Handle disk usage requests"""
        try:
            result = self.system_controller.get_disk_usage()

            if result["success"]:
                disk_data = result["data"]

                summary = [f"💽 Disk Usage:"]

                # Show main disk first
                if disk_data["total_disk_gb"] > 0:
                    usage_pct = (disk_data["total_used_gb"] / disk_data["total_disk_gb"]) * 100
                    summary.append(
                        f"  Main: {disk_data['total_used_gb']:.1f}GB used / {disk_data['total_disk_gb']:.1f}GB total ({usage_pct:.1f}%)"
                    )
                    summary.append(f"  Free: {disk_data['total_free_gb']:.1f}GB available")

                # Show other partitions
                if len(disk_data["partitions"]) > 1:
                    summary.append("  Other partitions:")
                    for partition in disk_data["partitions"]:
                        if partition["mountpoint"] not in ["/", "C:\\"]:
                            summary.append(
                                f"    {partition['mountpoint']}: {partition['used_gb']:.1f}GB / {partition['total_gb']:.1f}GB ({partition['usage_percent']}%)"
                            )

                # Add recommendations if any
                if disk_data["recommendations"]:
                    summary.append("📋 Recommendations:")
                    for rec in disk_data["recommendations"]:
                        summary.append(f"  • {rec}")

                result["message"] = "\n".join(summary)

            return result

        except Exception as e:
            return {"success": False, "error": f"Error getting disk usage: {e}", "request": request}

    def _handle_cache_clear_request(self, request: str) -> Dict[str, Any]:
        """Handle cache clearing requests"""
        try:
            result = self.system_controller.clear_system_caches()

            if result["success"]:
                cache_data = result["data"]

                summary = [f"🧹 Cache Cleanup Results:"]

                if cache_data["cleared_items"]:
                    for item in cache_data["cleared_items"]:
                        summary.append(f"  ✅ {item}")
                else:
                    summary.append("  ℹ️ No cache items found to clear")

                if cache_data["total_freed_mb"] > 0:
                    summary.append(f"💾 Total space freed: {cache_data['total_freed_mb']:.1f} MB")

                result["message"] = "\n".join(summary)

            return result

        except Exception as e:
            return {"success": False, "error": f"Error clearing caches: {e}", "request": request}

    def _handle_navigation_request(self, request: str) -> Dict[str, Any]:
        """Handle directory navigation requests"""
        try:
            # Extract path from request
            request_lower = request.lower()
            path = None

            # Common patterns to extract path
            if "navigate to " in request_lower:
                path = request[request_lower.find("navigate to ") + 12 :].strip()
            elif "go to " in request_lower:
                path = request[request_lower.find("go to ") + 6 :].strip()
            elif "change to " in request_lower:
                path = request[request_lower.find("change to ") + 10 :].strip()
            elif "cd to " in request_lower:
                path = request[request_lower.find("cd to ") + 6 :].strip()
            elif "move to " in request_lower:
                path = request[request_lower.find("move to ") + 8 :].strip()

            if not path:
                return {
                    "success": False,
                    "error": "Could not extract directory path from request",
                    "suggestion": "Try: 'navigate to /path/to/directory' or 'cd to ~/Documents'",
                }

            # Clean up path (remove quotes, extra text)
            path = path.replace('"', "").replace("'", "")
            if ":" in path and not path.startswith("/"):
                # Handle "navigate to /path:" format
                path = path.split(":")[0]

            result = change_directory(path)

            if result["success"]:
                # Also list the directory contents after navigation
                list_result = list_directory()
                if list_result["success"]:
                    entries = list_result["entries"]
                    entry_summary = []
                    dirs = [e for e in entries if e["type"] == "directory"]
                    files = [e for e in entries if e["type"] == "file"]

                    if dirs:
                        entry_summary.append(f"{len(dirs)} directories")
                    if files:
                        entry_summary.append(f"{len(files)} files")

                    result["message"] = (
                        f"✅ {result['message']}\n📁 Contains: {', '.join(entry_summary)}"
                    )
                    result["directory_contents"] = entries[:10]  # Show first 10 items

            return result

        except Exception as e:
            return {"success": False, "error": f"Navigation error: {e}", "request": request}

    def _handle_directory_listing_request(self, request: str) -> Dict[str, Any]:
        """Handle directory listing requests"""
        try:
            request_lower = request.lower()

            # Extract path if specified
            path = None
            show_hidden = False
            detailed = False

            if "list " in request_lower:
                after_list = request[request_lower.find("list ") + 5 :].strip()
                if after_list and not after_list.startswith(("current", "this", "files")):
                    path = after_list
            elif "show files in " in request_lower:
                path = request[request_lower.find("show files in ") + 14 :].strip()
            elif "what's in " in request_lower:
                path = request[request_lower.find("what's in ") + 10 :].strip()

            if "hidden" in request_lower or "all files" in request_lower:
                show_hidden = True
            if "detailed" in request_lower or "details" in request_lower:
                detailed = True

            # Clean up path
            if path:
                path = path.replace('"', "").replace("'", "")
                if path.endswith(":"):
                    path = path[:-1]

            result = list_directory(path, show_hidden, detailed)

            if result["success"]:
                entries = result["entries"]
                dirs = [e for e in entries if e["type"] == "directory"]
                files = [e for e in entries if e["type"] == "file"]

                summary = []
                if dirs:
                    summary.append(f"📁 {len(dirs)} directories")
                if files:
                    summary.append(f"📄 {len(files)} files")

                result["message"] = f"📂 {result['path']}\n{', '.join(summary)}"

                # Format entries for display
                display_entries = []
                for entry in entries[:20]:  # Show first 20
                    if entry["type"] == "directory":
                        display_entries.append(f"📁 {entry['name']}/")
                    else:
                        size_str = ""
                        if entry.get("size") is not None:
                            size_kb = entry["size"] / 1024
                            if size_kb < 1024:
                                size_str = f" ({size_kb:.1f} KB)"
                            else:
                                size_str = f" ({size_kb/1024:.1f} MB)"
                        display_entries.append(f"📄 {entry['name']}{size_str}")

                if display_entries:
                    result["display_entries"] = display_entries
                    if len(entries) > 20:
                        result["message"] += f"\n(showing first 20 of {len(entries)} items)"

            return result

        except Exception as e:
            return {"success": False, "error": f"Directory listing error: {e}", "request": request}

    def _handle_simulator_cleanup_request(self, request: str) -> Dict[str, Any]:
        """Handle iOS/watchOS simulator cleanup requests"""
        try:
            result = clean_simulator_data()

            if result["success"]:
                data = result["data"]
                result["message"] = (
                    f"🧹 Simulator cleanup completed!\n💾 Freed {data['total_freed_mb']} MB of storage"
                )

                if data["cleaned_items"]:
                    result["cleaned_summary"] = data["cleaned_items"][:5]  # Show first 5 items

            return result

        except Exception as e:
            return {"success": False, "error": f"Simulator cleanup error: {e}", "request": request}

    def _handle_shell_command_request(self, request: str) -> Dict[str, Any]:
        """Handle shell command execution requests"""
        try:
            request_lower = request.lower()

            # Extract command
            command = None
            if "run command " in request_lower:
                command = request[request_lower.find("run command ") + 12 :].strip()
            elif "execute " in request_lower:
                command = request[request_lower.find("execute ") + 8 :].strip()
            elif "shell " in request_lower:
                command = request[request_lower.find("shell ") + 6 :].strip()
            elif "terminal " in request_lower:
                command = request[request_lower.find("terminal ") + 9 :].strip()

            if not command:
                return {
                    "success": False,
                    "error": "Could not extract command from request",
                    "suggestion": "Try: 'run command ls -la' or 'execute find /path -name pattern'",
                }

            # Basic security check
            dangerous_commands = ["rm -rf /", "sudo rm", "format", "mkfs", "> /dev/null"]
            if any(dangerous in command.lower() for dangerous in dangerous_commands):
                return {
                    "success": False,
                    "error": "Command blocked for security reasons",
                    "command": command,
                }

            result = execute_shell_command(command)

            if result["success"]:
                result["message"] = f"✅ Executed: {command}"
                if result.get("output"):
                    # Truncate long output
                    output = result["output"]
                    if len(output) > 2000:
                        result["output"] = output[:2000] + "\n... (output truncated)"

            return result

        except Exception as e:
            return {"success": False, "error": f"Shell command error: {e}", "request": request}

    def _handle_current_directory_request(self, request: str) -> Dict[str, Any]:
        """Handle current directory requests"""
        try:
            current_dir = get_current_directory()

            return {
                "success": True,
                "current_directory": current_dir,
                "message": f"📍 Current directory: {current_dir}",
                "description": "Get current directory",
            }

        except Exception as e:
            return {"success": False, "error": f"Current directory error: {e}", "request": request}

    def get_capabilities(self) -> Dict[str, Any]:
        """Get information about available system capabilities"""
        return {
            "enabled": self.enabled,
            "system": self.system_controller.system,
            "functions": {
                name: {"description": info["description"], "examples": info["examples"]}
                for name, info in self.system_functions.items()
            },
        }


# Global instance for use in chat
chat_system_integration = ChatSystemIntegration()


def handle_system_request(request: str) -> Dict[str, Any]:
    """Main function for handling system requests from chat"""
    return chat_system_integration.handle_system_request(request)


def get_system_capabilities() -> Dict[str, Any]:
    """Get available system capabilities"""
    return chat_system_integration.get_capabilities()
