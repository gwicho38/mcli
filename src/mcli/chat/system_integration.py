"""
System Integration for MCLI Chat
Provides system control capabilities directly within chat conversations
"""

from typing import Any, Dict

from mcli.lib.constants import SystemIntegrationMessages as SysMsg
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
                "description": SysMsg.DESC_TEXTEDIT,
                "parameters": {
                    "text": SysMsg.PARAM_TEXT,
                    "filename": SysMsg.PARAM_FILENAME,
                },
                "examples": SysMsg.EXAMPLES_TEXTEDIT,
            },
            "control_application": {
                "function": control_app,
                "description": SysMsg.DESC_CONTROL_APP,
                "parameters": {
                    "app_name": SysMsg.PARAM_APP_NAME,
                    "action": SysMsg.PARAM_ACTION,
                    SysMsg.PARAM_KWARGS_KEY: SysMsg.PARAM_KWARGS,
                },
                "examples": SysMsg.EXAMPLES_CONTROL_APP,
            },
            "execute_command": {
                "function": execute_system_command,
                "description": SysMsg.DESC_EXECUTE_COMMAND,
                "parameters": {
                    "command": SysMsg.PARAM_COMMAND,
                    "description": SysMsg.PARAM_COMMAND_DESC,
                },
                "examples": SysMsg.EXAMPLES_EXECUTE_COMMAND,
            },
            "take_screenshot": {
                "function": take_screenshot,
                "description": SysMsg.DESC_TAKE_SCREENSHOT,
                "parameters": {
                    "filename": SysMsg.PARAM_SCREENSHOT_FN,
                },
                "examples": SysMsg.EXAMPLES_SCREENSHOT,
            },
            "open_file_or_url": {
                "function": open_file_or_url,
                "description": SysMsg.DESC_OPEN_FILE_URL,
                "parameters": {"path_or_url": SysMsg.PARAM_PATH_OR_URL},
                "examples": SysMsg.EXAMPLES_OPEN_FILE_URL,
            },
            "get_system_info": {
                "function": self.system_controller.get_system_info,
                "description": SysMsg.DESC_SYSTEM_INFO,
                "parameters": {},
                "examples": SysMsg.EXAMPLES_SYSTEM_INFO,
            },
            "get_system_time": {
                "function": self.system_controller.get_system_time,
                "description": SysMsg.DESC_SYSTEM_TIME,
                "parameters": {},
                "examples": SysMsg.EXAMPLES_SYSTEM_TIME,
            },
            "get_memory_usage": {
                "function": self.system_controller.get_memory_usage,
                "description": SysMsg.DESC_MEMORY_USAGE,
                "parameters": {},
                "examples": SysMsg.EXAMPLES_MEMORY_USAGE,
            },
            "get_disk_usage": {
                "function": self.system_controller.get_disk_usage,
                "description": SysMsg.DESC_DISK_USAGE,
                "parameters": {},
                "examples": SysMsg.EXAMPLES_DISK_USAGE,
            },
            "clear_system_caches": {
                "function": self.system_controller.clear_system_caches,
                "description": SysMsg.DESC_CLEAR_CACHES,
                "parameters": {},
                "examples": SysMsg.EXAMPLES_CLEAR_CACHES,
            },
            "change_directory": {
                "function": change_directory,
                "description": SysMsg.DESC_CHANGE_DIR,
                "parameters": {"path": SysMsg.PARAM_DIR_PATH},
                "examples": SysMsg.EXAMPLES_CHANGE_DIR,
            },
            "list_directory": {
                "function": list_directory,
                "description": SysMsg.DESC_LIST_DIR,
                "parameters": {
                    "path": SysMsg.PARAM_LIST_PATH,
                    "show_hidden": SysMsg.PARAM_SHOW_HIDDEN,
                    "detailed": SysMsg.PARAM_DETAILED,
                },
                "examples": SysMsg.EXAMPLES_LIST_DIR,
            },
            "clean_simulator_data": {
                "function": clean_simulator_data,
                "description": SysMsg.DESC_CLEAN_SIMULATOR,
                "parameters": {},
                "examples": SysMsg.EXAMPLES_CLEAN_SIMULATOR,
            },
            "execute_shell_command": {
                "function": execute_shell_command,
                "description": SysMsg.DESC_SHELL_COMMAND,
                "parameters": {
                    "command": SysMsg.PARAM_COMMAND,
                    "working_directory": SysMsg.PARAM_WORKING_DIR,
                },
                "examples": SysMsg.EXAMPLES_SHELL_COMMAND,
            },
            "get_current_directory": {
                "function": get_current_directory,
                "description": SysMsg.DESC_CURRENT_DIR,
                "parameters": {},
                "examples": SysMsg.EXAMPLES_CURRENT_DIR,
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
                "error": SysMsg.SYSTEM_CONTROL_DISABLED,
                "suggestion": SysMsg.ENABLE_SYSTEM_CONTROL,
            }

        # Parse the request and determine action
        request_lower = request.lower()

        # System information requests
        if any(phrase in request_lower for phrase in SysMsg.PATTERNS_TIME):
            return self._handle_system_time_request(request)

        elif any(phrase in request_lower for phrase in SysMsg.PATTERNS_SYSTEM_INFO):
            return self._handle_system_info_request(request)

        # Hardware devices requests
        elif any(phrase in request_lower for phrase in SysMsg.PATTERNS_HARDWARE):
            return self._handle_hardware_devices_request(request)

        elif any(phrase in request_lower for phrase in SysMsg.PATTERNS_MEMORY):
            return self._handle_memory_request(request)

        elif any(phrase in request_lower for phrase in SysMsg.PATTERNS_DISK):
            return self._handle_disk_request(request)

        elif any(phrase in request_lower for phrase in SysMsg.PATTERNS_CACHE):
            return self._handle_cache_clear_request(request)

        # Navigation requests
        elif any(phrase in request_lower for phrase in SysMsg.PATTERNS_NAVIGATION):
            return self._handle_navigation_request(request)

        # Directory listing requests (more specific to avoid false positives)
        elif any(phrase in request_lower for phrase in SysMsg.PATTERNS_DIR_LIST):
            return self._handle_directory_listing_request(request)

        # Simulator cleanup requests
        elif any(phrase in request_lower for phrase in SysMsg.PATTERNS_SIMULATOR):
            return self._handle_simulator_cleanup_request(request)

        # Shell command requests
        elif any(phrase in request_lower for phrase in SysMsg.PATTERNS_SHELL):
            return self._handle_shell_command_request(request)

        # Current directory requests
        elif any(phrase in request_lower for phrase in SysMsg.PATTERNS_CURRENT_DIR):
            return self._handle_current_directory_request(request)

        # TextEdit operations
        elif SysMsg.PATTERN_TEXTEDIT in request_lower and (
            SysMsg.PATTERN_WRITE in request_lower or SysMsg.PATTERN_TYPE in request_lower
        ):
            return self._handle_textedit_request(request)

        # Application control
        elif any(word in request_lower for word in SysMsg.KEYWORDS_APP_CONTROL):
            return self._handle_app_control_request(request)

        # Screenshot
        elif (
            SysMsg.PATTERN_SCREENSHOT in request_lower
            or SysMsg.PATTERN_SCREEN_CAPTURE in request_lower
        ):
            return self._handle_screenshot_request(request)

        # File/URL opening
        elif SysMsg.PATTERN_OPEN in request_lower and (
            SysMsg.PATTERN_FILE in request_lower
            or SysMsg.PATTERN_URL in request_lower
            or SysMsg.PATTERN_HTTP in request_lower
        ):
            return self._handle_open_request(request)

        # Command execution
        elif any(word in request_lower for word in SysMsg.KEYWORDS_COMMAND_EXEC):
            return self._handle_command_request(request)

        else:
            return {
                "success": False,
                "error": SysMsg.COULD_NOT_UNDERSTAND_REQUEST,
                "available_functions": list(self.system_functions.keys()),
                "suggestion": SysMsg.TRY_TEXTEDIT_EXAMPLE,
            }

    def _handle_textedit_request(self, request: str) -> Dict[str, Any]:
        """Handle TextEdit-specific requests"""
        try:
            # Extract text to write
            text = SysMsg.DEFAULT_TEXT  # default
            filename = None

            # Simple text extraction patterns
            if '"' in request:
                # Extract text in quotes
                parts = request.split('"')
                if len(parts) >= 2:
                    text = parts[1]
            elif SysMsg.PATTERN_WRITE + " " in request.lower():
                # Extract text after "write"
                parts = request.lower().split(SysMsg.PATTERN_WRITE + " ")
                if len(parts) > 1:
                    text_part = parts[1]
                    # Remove common words
                    for word in SysMsg.WORDS_TO_REMOVE_TEXTEDIT:
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
                message = SysMsg.TEXTEDIT_SUCCESS.format(text=text)
                if filename:
                    message += SysMsg.TEXTEDIT_SAVED.format(filename=filename)
                result["message"] = message

            return result

        except Exception as e:
            return {
                "success": False,
                "error": SysMsg.ERROR_TEXTEDIT.format(error=e),
                "request": request,
            }

    def _handle_app_control_request(self, request: str) -> Dict[str, Any]:
        """Handle application control requests"""
        try:
            request_lower = request.lower()

            # Determine action
            if SysMsg.PATTERN_OPEN in request_lower or "launch" in request_lower:
                action = "open"
            elif "close" in request_lower or "quit" in request_lower:
                action = "close"
            elif SysMsg.PATTERN_NEW_DOCUMENT in request_lower:
                action = "new_document"
            else:
                action = "open"  # default

            # Extract app name
            app_name = SysMsg.DEFAULT_APP  # default

            for app_key, app_value in SysMsg.COMMON_APPS.items():
                if app_key in request_lower:
                    app_name = app_value
                    break

            result = control_app(app_name, action)

            if result["success"]:
                result["message"] = SysMsg.APP_CONTROL_SUCCESS.format(
                    action=action.title(), app_name=app_name
                )

            return result

        except Exception as e:
            return {
                "success": False,
                "error": SysMsg.ERROR_APP_CONTROL.format(error=e),
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
                result["message"] = SysMsg.SCREENSHOT_SUCCESS.format(path=path)

            return result

        except Exception as e:
            return {
                "success": False,
                "error": SysMsg.ERROR_SCREENSHOT.format(error=e),
                "request": request,
            }

    def _handle_open_request(self, request: str) -> Dict[str, Any]:
        """Handle file/URL opening requests"""
        try:
            # Extract URL or file path
            words = request.split()
            path_or_url = None

            for word in words:
                if word.startswith("http") or word.startswith(SysMsg.URL_PREFIX_WWW) or "/" in word:
                    path_or_url = word
                    break

            if not path_or_url:
                # Look for common patterns
                if SysMsg.PATTERN_GOOGLE in request.lower():
                    path_or_url = SysMsg.URL_GOOGLE
                elif (
                    SysMsg.PATTERN_CURRENT_DIR in request.lower()
                    or SysMsg.PATTERN_THIS_FOLDER in request.lower()
                ):
                    path_or_url = "."
                else:
                    return {
                        "success": False,
                        "error": SysMsg.COULD_NOT_DETERMINE_OPEN,
                        "suggestion": SysMsg.SPECIFY_URL_OR_PATH,
                    }

            result = open_file_or_url(path_or_url)

            if result["success"]:
                result["message"] = SysMsg.OPENED_SUCCESS.format(path=path_or_url)

            return result

        except Exception as e:
            return {
                "success": False,
                "error": SysMsg.ERROR_OPEN.format(error=e),
                "request": request,
            }

    def _handle_command_request(self, request: str) -> Dict[str, Any]:
        """Handle command execution requests"""
        try:
            # Extract command (this is simplified - in practice you'd want more security)
            command = None

            if SysMsg.PATTERN_RUN in request.lower():
                parts = request.lower().split(SysMsg.PATTERN_RUN)
                if len(parts) > 1:
                    command = parts[1].strip()
            elif SysMsg.PATTERN_EXECUTE in request.lower():
                parts = request.lower().split(SysMsg.PATTERN_EXECUTE)
                if len(parts) > 1:
                    command = parts[1].strip()

            if not command:
                return {
                    "success": False,
                    "error": SysMsg.COULD_NOT_EXTRACT_COMMAND,
                    "suggestion": SysMsg.TRY_RUN_EXAMPLE,
                }

            # Basic security check (you'd want more comprehensive checks)
            if any(dangerous in command.lower() for dangerous in SysMsg.DANGEROUS_COMMANDS):
                return {
                    "success": False,
                    "error": SysMsg.COMMAND_BLOCKED_SECURITY,
                    "command": command,
                }

            result = execute_system_command(command, f"User requested: {command}")

            if result["success"]:
                result["message"] = SysMsg.EXECUTED_SUCCESS.format(command=command)

            return result

        except Exception as e:
            return {
                "success": False,
                "error": SysMsg.ERROR_COMMAND.format(error=e),
                "request": request,
            }

    def _handle_system_time_request(self, request: str) -> Dict[str, Any]:
        """Handle system time requests"""
        try:
            result = self.system_controller.get_system_time()

            if result["success"]:
                time_data = result["data"]
                result["message"] = SysMsg.SYSTEM_TIME_FMT.format(
                    time=time_data["current_time"], timezone=time_data["timezone"][0]
                )

            return result

        except Exception as e:
            return {
                "success": False,
                "error": SysMsg.ERROR_SYSTEM_TIME.format(error=e),
                "request": request,
            }

    def _handle_system_info_request(self, request: str) -> Dict[str, Any]:
        """Handle system information requests"""
        try:
            result = self.system_controller.get_system_info()

            if result["success"]:
                info_data = result["data"]
                summary = [
                    SysMsg.SYSTEM_SUMMARY_SYSTEM.format(
                        system=info_data["system"], machine=info_data["machine"]
                    ),
                    SysMsg.SYSTEM_SUMMARY_CPU.format(
                        cores=info_data["cpu"]["logical_cores"],
                        usage=info_data["cpu"]["cpu_usage_percent"],
                    ),
                    SysMsg.SYSTEM_SUMMARY_RAM.format(
                        used=info_data["memory"]["used_gb"],
                        total=info_data["memory"]["total_gb"],
                        percent=info_data["memory"]["usage_percent"],
                    ),
                    SysMsg.SYSTEM_SUMMARY_UPTIME.format(hours=info_data["uptime_hours"]),
                ]
                result["message"] = "\n".join(summary)

            return result

        except Exception as e:
            return {
                "success": False,
                "error": SysMsg.ERROR_SYSTEM_INFO.format(error=e),
                "request": request,
            }

    def _handle_hardware_devices_request(self, request: str) -> Dict[str, Any]:
        """Handle hardware devices listing requests"""
        try:
            # Use shell command to get hardware information
            import subprocess

            summary = [SysMsg.HARDWARE_HEADER]

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
                                keyword in line.lower() for keyword in SysMsg.USB_DEVICE_KEYWORDS
                            ):
                                device_name = line.split(":")[0].strip()
                                if device_name and len(device_name) > 3:
                                    usb_devices.append(device_name)

                    if usb_devices:
                        summary.append(SysMsg.USB_DEVICES_HEADER)
                        for device in usb_devices[:8]:  # Limit to 8 devices
                            summary.append(SysMsg.DEVICE_ITEM.format(name=device))

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
                        summary.append(SysMsg.NETWORK_INTERFACES_HEADER)
                        for interface in interfaces[:6]:  # Limit to 6 interfaces
                            summary.append(SysMsg.DEVICE_ITEM.format(name=interface))

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
                        if ":" in line and any(kw in line for kw in SysMsg.AUDIO_DEVICE_KEYWORDS):
                            device_name = line.split(":")[0].strip()
                            if device_name and len(device_name) > 3:
                                audio_devices.append(device_name)

                    if audio_devices:
                        summary.append(SysMsg.AUDIO_DEVICES_HEADER)
                        for device in audio_devices[:4]:  # Limit to 4 devices
                            summary.append(SysMsg.DEVICE_ITEM.format(name=device))

            except Exception:
                pass

            if len(summary) == 1:  # Only has header
                summary.append(SysMsg.NO_HARDWARE_DETECTED)
                summary.append(SysMsg.HARDWARE_HINT)

            return {
                "success": True,
                "message": "\n".join(summary),
                "description": SysMsg.DESCRIPTION_HARDWARE_DEVICES,
            }

        except Exception as e:
            return {
                "success": False,
                "error": SysMsg.ERROR_HARDWARE_DEVICES.format(error=e),
                "suggestion": SysMsg.TRY_SYSTEM_INFO,
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
                    SysMsg.MEMORY_HEADER,
                    SysMsg.MEMORY_RAM_FMT.format(
                        used=vm["used_gb"],
                        total=vm["total_gb"],
                        percent=vm["usage_percent"],
                    ),
                    SysMsg.MEMORY_AVAILABLE_FMT.format(available=vm["available_gb"]),
                    SysMsg.MEMORY_SWAP_FMT.format(
                        used=swap["used_gb"],
                        total=swap["total_gb"],
                        percent=swap["usage_percent"],
                    ),
                ]

                # Add recommendations if any
                if memory_data["recommendations"]:
                    summary.append(SysMsg.RECOMMENDATIONS_HEADER)
                    for rec in memory_data["recommendations"]:
                        summary.append(SysMsg.RECOMMENDATION_ITEM.format(rec=rec))

                result["message"] = "\n".join(summary)

            return result

        except Exception as e:
            return {
                "success": False,
                "error": SysMsg.ERROR_MEMORY.format(error=e),
                "request": request,
            }

    def _handle_disk_request(self, request: str) -> Dict[str, Any]:
        """Handle disk usage requests"""
        try:
            result = self.system_controller.get_disk_usage()

            if result["success"]:
                disk_data = result["data"]

                summary = [SysMsg.DISK_HEADER]

                # Show main disk first
                if disk_data["total_disk_gb"] > 0:
                    usage_pct = (disk_data["total_used_gb"] / disk_data["total_disk_gb"]) * 100
                    summary.append(
                        SysMsg.DISK_MAIN_FMT.format(
                            used=disk_data["total_used_gb"],
                            total=disk_data["total_disk_gb"],
                            percent=usage_pct,
                        )
                    )
                    summary.append(SysMsg.DISK_FREE_FMT.format(free=disk_data["total_free_gb"]))

                # Show other partitions
                if len(disk_data["partitions"]) > 1:
                    summary.append(SysMsg.DISK_OTHER_HEADER)
                    for partition in disk_data["partitions"]:
                        if partition["mountpoint"] not in ["/", "C:\\"]:
                            summary.append(
                                SysMsg.DISK_PARTITION_FMT.format(
                                    mount=partition["mountpoint"],
                                    used=partition["used_gb"],
                                    total=partition["total_gb"],
                                    percent=partition["usage_percent"],
                                )
                            )

                # Add recommendations if any
                if disk_data["recommendations"]:
                    summary.append(SysMsg.RECOMMENDATIONS_HEADER)
                    for rec in disk_data["recommendations"]:
                        summary.append(SysMsg.RECOMMENDATION_ITEM.format(rec=rec))

                result["message"] = "\n".join(summary)

            return result

        except Exception as e:
            return {
                "success": False,
                "error": SysMsg.ERROR_DISK.format(error=e),
                "request": request,
            }

    def _handle_cache_clear_request(self, request: str) -> Dict[str, Any]:
        """Handle cache clearing requests"""
        try:
            result = self.system_controller.clear_system_caches()

            if result["success"]:
                cache_data = result["data"]

                summary = [SysMsg.CACHE_CLEANUP_HEADER]

                if cache_data["cleared_items"]:
                    for item in cache_data["cleared_items"]:
                        summary.append(SysMsg.CACHE_ITEM_SUCCESS.format(item=item))
                else:
                    summary.append(SysMsg.NO_CACHE_ITEMS)

                if cache_data["total_freed_mb"] > 0:
                    summary.append(SysMsg.TOTAL_SPACE_FREED.format(mb=cache_data["total_freed_mb"]))

                result["message"] = "\n".join(summary)

            return result

        except Exception as e:
            return {
                "success": False,
                "error": SysMsg.ERROR_CACHE.format(error=e),
                "request": request,
            }

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
                    "error": SysMsg.COULD_NOT_EXTRACT_PATH,
                    "suggestion": SysMsg.TRY_NAVIGATE_EXAMPLE,
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

                    nav_msg = SysMsg.NAVIGATION_SUCCESS.format(summary=", ".join(entry_summary))
                    result["message"] = f"✅ {result['message']}\n{nav_msg}"
                    result["directory_contents"] = entries[:10]  # Show first 10 items

            return result

        except Exception as e:
            return {
                "success": False,
                "error": SysMsg.ERROR_NAVIGATION.format(error=e),
                "request": request,
            }

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
            elif SysMsg.PATTERN_WHATS_IN in request_lower:
                path = request[
                    request_lower.find(SysMsg.PATTERN_WHATS_IN) + len(SysMsg.PATTERN_WHATS_IN) :
                ].strip()

            if "hidden" in request_lower or SysMsg.PATTERN_ALL_FILES in request_lower:
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
                    summary.append(SysMsg.DIR_SUMMARY_DIRS.format(count=len(dirs)))
                if files:
                    summary.append(SysMsg.DIR_SUMMARY_FILES.format(count=len(files)))

                result["message"] = (
                    f"{SysMsg.DIR_LISTING_HEADER.format(path=result['path'])}\n{', '.join(summary)}"
                )

                # Format entries for display
                display_entries = []
                for entry in entries[:20]:  # Show first 20
                    if entry["type"] == "directory":
                        display_entries.append(SysMsg.DIR_ENTRY.format(name=entry["name"]))
                    else:
                        size_str = ""
                        if entry.get("size") is not None:
                            size_kb = entry["size"] / 1024
                            if size_kb < 1024:
                                size_str = f" ({size_kb:.1f} KB)"
                            else:
                                size_str = f" ({size_kb/1024:.1f} MB)"
                        display_entries.append(
                            SysMsg.FILE_ENTRY.format(name=entry["name"], size=size_str)
                        )

                if display_entries:
                    result["display_entries"] = display_entries
                    if len(entries) > 20:
                        result[
                            "message"
                        ] += f"\n{SysMsg.SHOWING_FIRST_N.format(shown=20, total=len(entries))}"

            return result

        except Exception as e:
            return {
                "success": False,
                "error": SysMsg.ERROR_DIR_LISTING.format(error=e),
                "request": request,
            }

    def _handle_simulator_cleanup_request(self, request: str) -> Dict[str, Any]:
        """Handle iOS/watchOS simulator cleanup requests"""
        try:
            result = clean_simulator_data()

            if result["success"]:
                data = result["data"]
                result["message"] = SysMsg.SIMULATOR_CLEANUP_SUCCESS.format(
                    mb=data["total_freed_mb"]
                )

                if data["cleaned_items"]:
                    result["cleaned_summary"] = data["cleaned_items"][:5]  # Show first 5 items

            return result

        except Exception as e:
            return {
                "success": False,
                "error": SysMsg.ERROR_SIMULATOR_CLEANUP.format(error=e),
                "request": request,
            }

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
                    "error": SysMsg.COULD_NOT_EXTRACT_COMMAND,
                    "suggestion": SysMsg.TRY_SHELL_EXAMPLE,
                }

            # Basic security check
            if any(dangerous in command.lower() for dangerous in SysMsg.SHELL_DANGEROUS_COMMANDS):
                return {
                    "success": False,
                    "error": SysMsg.COMMAND_BLOCKED_SECURITY,
                    "command": command,
                }

            result = execute_shell_command(command)

            if result["success"]:
                result["message"] = SysMsg.EXECUTED_SUCCESS.format(command=command)
                if result.get("output"):
                    # Truncate long output
                    output = result["output"]
                    if len(output) > 2000:
                        result["output"] = output[:2000] + SysMsg.OUTPUT_TRUNCATED

            return result

        except Exception as e:
            return {
                "success": False,
                "error": SysMsg.ERROR_SHELL_COMMAND.format(error=e),
                "request": request,
            }

    def _handle_current_directory_request(self, request: str) -> Dict[str, Any]:
        """Handle current directory requests"""
        try:
            current_dir = get_current_directory()

            return {
                "success": True,
                "current_directory": current_dir,
                "message": SysMsg.CURRENT_DIR_SUCCESS.format(path=current_dir),
                "description": SysMsg.DESC_CURRENT_DIR,
            }

        except Exception as e:
            return {
                "success": False,
                "error": SysMsg.ERROR_CURRENT_DIR.format(error=e),
                "request": request,
            }

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
