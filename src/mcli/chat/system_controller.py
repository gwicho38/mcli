"""
System Controller for MCLI Chat
Allows the chat interface to directly control system applications and execute commands
"""

import os
import platform
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcli.lib.logger.logger import get_logger

logger = get_logger(__name__)


class SystemController:
    """Handles real-time system control for MCLI chat"""

    def __init__(self):
        self.system = platform.system()
        self.enabled = True
        self.current_directory = os.getcwd()  # Track current working directory

    def execute_command(self, command: str, description: str = "") -> Dict[str, Any]:
        """Execute a system command and return results"""
        try:
            logger.info(f"Executing: {description or command}")

            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)

            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
                "command": command,
                "description": description,
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "error": "Command timed out after 30 seconds",
                "command": command,
                "description": description,
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "command": command,
                "description": description,
            }

    def open_textedit_and_write(self, text: str, filename: str = None) -> Dict[str, Any]:
        """Open TextEdit, write text, and optionally save to file"""
        if self.system != "Darwin":
            return {
                "success": False,
                "error": "TextEdit is only available on macOS",
                "description": "Open TextEdit and write text",
            }

        # Escape quotes in text for AppleScript
        escaped_text = text.replace('"', '\\"').replace("'", "\\'")

        if filename:
            # Save to specified file
            save_path = f'(path to desktop as string) & "{filename}"'
            save_command = f"save front document in {save_path}"
        else:
            # Just create new document without saving
            save_command = ""

        applescript = f"""
        tell application "TextEdit"
            activate
            delay 0.5
            make new document
            delay 0.5
            set text of front document to "{escaped_text}"
            delay 1
            {save_command}
        end tell
        """

        return self.execute_command(
            f"osascript -e '{applescript}'", f"Open TextEdit and write: {text[:50]}..."
        )

    def control_application(self, app_name: str, action: str, **kwargs) -> Dict[str, Any]:
        """Control various applications with different actions"""

        if self.system == "Darwin":  # macOS
            return self._control_macos_app(app_name, action, **kwargs)
        elif self.system == "Windows":
            return self._control_windows_app(app_name, action, **kwargs)
        else:  # Linux
            return self._control_linux_app(app_name, action, **kwargs)

    def _control_macos_app(self, app_name: str, action: str, **kwargs) -> Dict[str, Any]:
        """Control macOS applications using AppleScript"""

        if action == "open":
            applescript = f'tell application "{app_name}" to activate'

        elif action == "close":
            applescript = f'tell application "{app_name}" to quit'

        elif action == "write_text" and app_name.lower() == "textedit":
            text = kwargs.get("text", "Hello, World!")
            filename = kwargs.get("filename")
            return self.open_textedit_and_write(text, filename)

        elif action == "new_document":
            if app_name.lower() == "textedit":
                applescript = f"""
                tell application "{app_name}"
                    activate
                    delay 0.5
                    make new document
                end tell
                """
            else:
                applescript = f'tell application "{app_name}" to make new document'

        elif action == "type_text":
            text = kwargs.get("text", "Hello, World!")
            escaped_text = text.replace('"', '\\"')
            applescript = f"""
            tell application "System Events"
                tell process "{app_name}"
                    keystroke "{escaped_text}"
                end tell
            end tell
            """

        else:
            return {
                "success": False,
                "error": f"Unknown action '{action}' for {app_name}",
                "description": f"Control {app_name}",
            }

        return self.execute_command(f"osascript -e '{applescript}'", f"{action} {app_name}")

    def _control_windows_app(self, app_name: str, action: str, **kwargs) -> Dict[str, Any]:
        """Control Windows applications using PowerShell"""

        if action == "open":
            # Try to start the application
            command = f"powershell -Command \"Start-Process '{app_name}'\""

        elif action == "close":
            command = f"powershell -Command \"Stop-Process -Name '{app_name}' -Force\""

        elif action == "write_text":
            text = kwargs.get("text", "Hello, World!")
            # This is a simplified version - would need more complex implementation
            command = f"powershell -Command \"Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.SendKeys]::SendWait('{text}')\""

        else:
            return {
                "success": False,
                "error": f"Action '{action}' not implemented for Windows",
                "description": f"Control {app_name}",
            }

        return self.execute_command(command, f"{action} {app_name}")

    def _control_linux_app(self, app_name: str, action: str, **kwargs) -> Dict[str, Any]:
        """Control Linux applications using various tools"""

        if action == "open":
            # Try different methods to open applications
            commands = [
                f"{app_name.lower()}",
                f"gtk-launch {app_name.lower()}",
                f"xdg-open {app_name.lower()}",
            ]

            for cmd in commands:
                result = self.execute_command(cmd, f"Open {app_name}")
                if result["success"]:
                    return result

            return {
                "success": False,
                "error": f"Could not open {app_name}",
                "description": f"Open {app_name}",
            }

        elif action == "close":
            command = f"pkill -f {app_name.lower()}"

        elif action == "write_text":
            text = kwargs.get("text", "Hello, World!")
            # Use xdotool if available
            command = f'xdotool type "{text}"'

        else:
            return {
                "success": False,
                "error": f"Action '{action}' not implemented for Linux",
                "description": f"Control {app_name}",
            }

        return self.execute_command(command, f"{action} {app_name}")

    def get_system_info(self) -> Dict[str, Any]:
        """Get comprehensive system information"""
        try:
            import platform
            from datetime import datetime

            import psutil

            # Basic system info
            info = {
                "timestamp": datetime.now().isoformat(),
                "system": platform.system(),
                "platform": platform.platform(),
                "machine": platform.machine(),
                "processor": platform.processor(),
                "python_version": platform.python_version(),
            }

            # CPU information
            cpu_info = {
                "physical_cores": psutil.cpu_count(logical=False) or 0,
                "logical_cores": psutil.cpu_count(logical=True) or 0,
                "cpu_usage_percent": psutil.cpu_percent(
                    interval=0.1
                ),  # Shorter interval to avoid hanging
                "cpu_frequency": None,
            }

            # Try to get CPU frequency safely
            try:
                freq = psutil.cpu_freq()
                if freq:
                    cpu_info["cpu_frequency"] = freq._asdict()
            except Exception:
                pass
            info["cpu"] = cpu_info

            # Memory information
            memory = psutil.virtual_memory()
            memory_info = {
                "total_gb": round(memory.total / (1024**3), 2),
                "available_gb": round(memory.available / (1024**3), 2),
                "used_gb": round(memory.used / (1024**3), 2),
                "usage_percent": memory.percent,
                "free_gb": round(memory.free / (1024**3), 2),
            }
            info["memory"] = memory_info

            # Disk information
            disk_info = []
            try:
                for partition in psutil.disk_partitions():
                    try:
                        partition_usage = psutil.disk_usage(partition.mountpoint)
                        disk_info.append(
                            {
                                "device": partition.device,
                                "mountpoint": partition.mountpoint,
                                "filesystem": partition.fstype,
                                "total_gb": round(partition_usage.total / (1024**3), 2),
                                "used_gb": round(partition_usage.used / (1024**3), 2),
                                "free_gb": round(partition_usage.free / (1024**3), 2),
                                "usage_percent": round(
                                    (partition_usage.used / partition_usage.total) * 100, 1
                                ),
                            }
                        )
                    except (PermissionError, OSError):
                        # Skip partitions we can't access
                        continue
            except Exception:
                pass
            info["disks"] = disk_info

            # Network information
            network_info = {
                "interfaces": {},
                "connections": 0,
            }

            try:
                network_info["connections"] = len(psutil.net_connections())
            except Exception:
                pass

            try:
                for interface, addresses in psutil.net_if_addrs().items():
                    network_info["interfaces"][interface] = []
                    for addr in addresses:
                        try:
                            network_info["interfaces"][interface].append(
                                {
                                    "family": str(addr.family),
                                    "address": addr.address,
                                    "netmask": addr.netmask,
                                    "broadcast": addr.broadcast,
                                }
                            )
                        except Exception:
                            continue
            except Exception:
                pass

            info["network"] = network_info

            # Process information
            process_info = {
                "total_processes": 0,
                "running_processes": 0,
            }

            try:
                process_info["total_processes"] = len(psutil.pids())
                # Count running processes more safely
                running_count = 0
                for proc in psutil.process_iter(["status"]):
                    try:
                        if proc.info["status"] == psutil.STATUS_RUNNING:
                            running_count += 1
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                process_info["running_processes"] = running_count
            except Exception:
                pass
            info["processes"] = process_info

            # Boot time
            try:
                import datetime

                boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
                info["boot_time"] = boot_time.isoformat()
                uptime_seconds = (datetime.datetime.now() - boot_time).total_seconds()
                info["uptime_hours"] = round(uptime_seconds / 3600, 2)
            except Exception:
                info["boot_time"] = None
                info["uptime_hours"] = 0

            return {
                "success": True,
                "data": info,
                "description": "System information retrieved successfully",
            }

        except ImportError:
            return {
                "success": False,
                "error": "psutil library not available. Install with: pip install psutil",
                "description": "Get system information",
            }
        except Exception as e:
            return {"success": False, "error": str(e), "description": "Get system information"}

    def get_system_time(self) -> Dict[str, Any]:
        """Get current system time and timezone information"""
        try:
            import time
            from datetime import datetime

            now = datetime.now()

            time_info = {
                "current_time": now.strftime("%Y-%m-%d %H:%M:%S"),
                "timezone": time.tzname,
                "timestamp": now.timestamp(),
                "iso_format": now.isoformat(),
                "day_of_week": now.strftime("%A"),
                "day_of_year": now.timetuple().tm_yday,
                "week_number": now.isocalendar().week,
            }

            return {"success": True, "data": time_info, "description": "Current system time"}

        except Exception as e:
            return {"success": False, "error": str(e), "description": "Get system time"}

    def get_memory_usage(self) -> Dict[str, Any]:
        """Get detailed memory usage information"""
        try:
            import psutil

            # Virtual memory
            memory = psutil.virtual_memory()

            # Swap memory
            swap = psutil.swap_memory()

            memory_info = {
                "virtual_memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "used_gb": round(memory.used / (1024**3), 2),
                    "free_gb": round(memory.free / (1024**3), 2),
                    "usage_percent": memory.percent,
                    "buffers_gb": round(getattr(memory, "buffers", 0) / (1024**3), 2),
                    "cached_gb": round(getattr(memory, "cached", 0) / (1024**3), 2),
                },
                "swap_memory": {
                    "total_gb": round(swap.total / (1024**3), 2),
                    "used_gb": round(swap.used / (1024**3), 2),
                    "free_gb": round(swap.free / (1024**3), 2),
                    "usage_percent": swap.percent,
                },
                "recommendations": [],
            }

            # Add cleanup recommendations
            if memory.percent > 80:
                memory_info["recommendations"].append(
                    "High memory usage detected - consider closing unused applications"
                )

            if memory.percent > 90:
                memory_info["recommendations"].append(
                    "Critical memory usage - immediate cleanup recommended"
                )

            if swap.percent > 50:
                memory_info["recommendations"].append("High swap usage - consider adding more RAM")

            return {"success": True, "data": memory_info, "description": "Memory usage information"}

        except ImportError:
            return {
                "success": False,
                "error": "psutil library not available",
                "description": "Get memory usage",
            }
        except Exception as e:
            return {"success": False, "error": str(e), "description": "Get memory usage"}

    def get_disk_usage(self) -> Dict[str, Any]:
        """Get detailed disk usage information"""
        try:
            import psutil

            disk_info = {
                "partitions": [],
                "total_disk_gb": 0,
                "total_used_gb": 0,
                "total_free_gb": 0,
                "recommendations": [],
            }

            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)

                    partition_info = {
                        "device": partition.device,
                        "mountpoint": partition.mountpoint,
                        "filesystem": partition.fstype,
                        "total_gb": round(usage.total / (1024**3), 2),
                        "used_gb": round(usage.used / (1024**3), 2),
                        "free_gb": round(usage.free / (1024**3), 2),
                        "usage_percent": round((usage.used / usage.total) * 100, 1),
                    }

                    disk_info["partitions"].append(partition_info)

                    # Add to totals (main disk only)
                    if partition.mountpoint == "/" or partition.mountpoint == "C:\\":
                        disk_info["total_disk_gb"] = partition_info["total_gb"]
                        disk_info["total_used_gb"] = partition_info["used_gb"]
                        disk_info["total_free_gb"] = partition_info["free_gb"]

                        # Add recommendations
                        if partition_info["usage_percent"] > 85:
                            disk_info["recommendations"].append(
                                f"Disk {partition.mountpoint} is {partition_info['usage_percent']}% full - cleanup recommended"
                            )

                        if partition_info["usage_percent"] > 95:
                            disk_info["recommendations"].append(
                                f"Critical: Disk {partition.mountpoint} is nearly full!"
                            )

                except PermissionError:
                    continue

            return {"success": True, "data": disk_info, "description": "Disk usage information"}

        except ImportError:
            return {
                "success": False,
                "error": "psutil library not available",
                "description": "Get disk usage",
            }
        except Exception as e:
            return {"success": False, "error": str(e), "description": "Get disk usage"}

    def clear_system_caches(self) -> Dict[str, Any]:
        """Clear system caches and temporary files"""
        try:
            cleared_items = []
            total_freed_mb = 0

            if self.system == "Darwin":  # macOS
                # Clear user caches
                cache_dirs = [
                    "~/Library/Caches",
                    "~/Library/Application Support/CrashReporter",
                    "/tmp",
                ]

                for cache_dir in cache_dirs:
                    expanded_dir = os.path.expanduser(cache_dir)
                    if os.path.exists(expanded_dir):
                        try:
                            # Calculate size before clearing
                            size_before = self._get_directory_size(expanded_dir)

                            # Clear cache (be careful with system directories)
                            if cache_dir == "/tmp":
                                self.execute_command(
                                    "find /tmp -type f -atime +1 -delete 2>/dev/null || true",
                                    "Clear old temp files",
                                )
                            else:
                                # Just clear user cache files that are safe to delete
                                self.execute_command(
                                    f"find '{expanded_dir}' -name '*.cache' -delete 2>/dev/null || true",
                                    f"Clear {cache_dir}",
                                )

                            size_after = self._get_directory_size(expanded_dir)
                            freed_mb = max(0, (size_before - size_after) / (1024 * 1024))

                            if freed_mb > 0:
                                cleared_items.append(f"Cleared {cache_dir}: {freed_mb:.1f} MB")
                                total_freed_mb += freed_mb

                        except Exception as e:
                            cleared_items.append(f"Could not clear {cache_dir}: {e}")

                # Clear DNS cache
                dns_result = self.execute_command(
                    "sudo dscacheutil -flushcache 2>/dev/null || dscacheutil -flushcache",
                    "Flush DNS cache",
                )
                if dns_result.get("success"):
                    cleared_items.append("Flushed DNS cache")

            elif self.system == "Windows":
                # Windows cache clearing
                commands = [
                    ("del /q /f /s %TEMP%\\*", "Clear temp files"),
                    ("del /q /f /s C:\\Windows\\Temp\\*", "Clear Windows temp"),
                    ("ipconfig /flushdns", "Flush DNS cache"),
                ]

                for cmd, desc in commands:
                    result = self.execute_command(cmd, desc)
                    if result.get("success"):
                        cleared_items.append(desc)

            else:  # Linux
                # Linux cache clearing
                commands = [
                    (
                        "find /tmp -type f -atime +1 -delete 2>/dev/null || true",
                        "Clear old temp files",
                    ),
                    (
                        "sync && echo 3 > /proc/sys/vm/drop_caches 2>/dev/null || true",
                        "Clear page cache",
                    ),
                ]

                for cmd, desc in commands:
                    result = self.execute_command(cmd, desc)
                    if result.get("success"):
                        cleared_items.append(desc)

            return {
                "success": True,
                "data": {
                    "cleared_items": cleared_items,
                    "total_freed_mb": round(total_freed_mb, 1),
                },
                "description": "System cache clearing",
            }

        except Exception as e:
            return {"success": False, "error": str(e), "description": "Clear system caches"}

    def _get_directory_size(self, path: str) -> int:
        """Get total size of directory in bytes"""
        total_size = 0
        try:
            for dirpath, dirnames, filenames in os.walk(path):
                for filename in filenames:
                    file_path = os.path.join(dirpath, filename)
                    try:
                        total_size += os.path.getsize(file_path)
                    except (OSError, FileNotFoundError):
                        continue
        except Exception:
            pass
        return total_size

    def get_running_applications(self) -> List[str]:
        """Get list of currently running applications"""
        try:
            if self.system == "Darwin":
                result = subprocess.run(
                    [
                        "osascript",
                        "-e",
                        'tell application "System Events" to get name of every process whose background only is false',
                    ],
                    capture_output=True,
                    text=True,
                )

                if result.returncode == 0:
                    # Parse the AppleScript result
                    apps = result.stdout.strip().split(", ")
                    return [app.strip() for app in apps if app.strip()]

            elif self.system == "Windows":
                result = subprocess.run(
                    [
                        "powershell",
                        "-Command",
                        "Get-Process | Where-Object {$_.MainWindowTitle -ne ''} | Select-Object -ExpandProperty ProcessName",
                    ],
                    capture_output=True,
                    text=True,
                )

                if result.returncode == 0:
                    return [line.strip() for line in result.stdout.split("\n") if line.strip()]

            else:  # Linux
                result = subprocess.run(["ps", "aux"], capture_output=True, text=True)

                if result.returncode == 0:
                    lines = result.stdout.split("\n")[1:]  # Skip header
                    processes = []
                    for line in lines:
                        if line.strip():
                            parts = line.split()
                            if len(parts) > 10:
                                processes.append(parts[10])  # Command name
                    return list(set(processes))

        except Exception as e:
            logger.error(f"Error getting running applications: {e}")

        return []

    def take_screenshot(self, filename: str = None) -> Dict[str, Any]:
        """Take a screenshot and save it"""
        if not filename:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = f"mcli_screenshot_{timestamp}.png"

        desktop_path = Path.home() / "Desktop" / filename

        try:
            if self.system == "Darwin":
                command = f"screencapture -x '{desktop_path}'"
            elif self.system == "Windows":
                command = f"powershell -Command \"Add-Type -AssemblyName System.Windows.Forms; [System.Windows.Forms.Screen]::PrimaryScreen.Bounds | Out-Null; [System.Drawing.Bitmap]::new([System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Width, [System.Windows.Forms.Screen]::PrimaryScreen.Bounds.Height).Save('{desktop_path}', [System.Drawing.Imaging.ImageFormat]::Png)\""
            else:  # Linux
                command = f"gnome-screenshot -f '{desktop_path}'"

            result = self.execute_command(command, f"Take screenshot: {filename}")

            if result["success"]:
                result["screenshot_path"] = str(desktop_path)

            return result

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "description": f"Take screenshot: {filename}",
            }

    def open_file_or_url(self, path_or_url: str) -> Dict[str, Any]:
        """Open a file or URL using the system default application"""
        try:
            if self.system == "Darwin":
                command = f"open '{path_or_url}'"
            elif self.system == "Windows":
                command = f'start "" "{path_or_url}"'
            else:  # Linux
                command = f"xdg-open '{path_or_url}'"

            return self.execute_command(command, f"Open: {path_or_url}")

        except Exception as e:
            return {"success": False, "error": str(e), "description": f"Open: {path_or_url}"}

    def change_directory(self, path: str) -> Dict[str, Any]:
        """Navigate to a directory and update current working directory"""
        try:
            # Expand user path and resolve relative paths
            expanded_path = os.path.expanduser(path)
            resolved_path = os.path.abspath(expanded_path)

            if not os.path.exists(resolved_path):
                return {
                    "success": False,
                    "error": f"Directory does not exist: {resolved_path}",
                    "current_directory": self.current_directory,
                }

            if not os.path.isdir(resolved_path):
                return {
                    "success": False,
                    "error": f"Path is not a directory: {resolved_path}",
                    "current_directory": self.current_directory,
                }

            # Change directory
            os.chdir(resolved_path)
            self.current_directory = resolved_path

            return {
                "success": True,
                "current_directory": self.current_directory,
                "message": f"Changed to directory: {self.current_directory}",
                "description": f"Navigate to {path}",
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "current_directory": self.current_directory,
                "description": f"Navigate to {path}",
            }

    def list_directory(
        self, path: str = None, show_hidden: bool = False, detailed: bool = False
    ) -> Dict[str, Any]:
        """List contents of a directory"""
        try:
            target_path = path if path else self.current_directory
            expanded_path = os.path.expanduser(target_path)
            resolved_path = os.path.abspath(expanded_path)

            if not os.path.exists(resolved_path):
                return {
                    "success": False,
                    "error": f"Directory does not exist: {resolved_path}",
                    "current_directory": self.current_directory,
                }

            if not os.path.isdir(resolved_path):
                return {
                    "success": False,
                    "error": f"Path is not a directory: {resolved_path}",
                    "current_directory": self.current_directory,
                }

            # Get directory contents
            entries = []
            try:
                for item in os.listdir(resolved_path):
                    if not show_hidden and item.startswith("."):
                        continue

                    item_path = os.path.join(resolved_path, item)
                    stat_info = os.stat(item_path)

                    entry = {
                        "name": item,
                        "type": "directory" if os.path.isdir(item_path) else "file",
                        "size": stat_info.st_size if not os.path.isdir(item_path) else None,
                        "modified": datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                    }

                    if detailed:
                        entry.update(
                            {
                                "permissions": oct(stat_info.st_mode)[-3:],
                                "owner": stat_info.st_uid,
                                "group": stat_info.st_gid,
                            }
                        )

                    entries.append(entry)

                # Sort: directories first, then files
                entries.sort(key=lambda x: (x["type"] != "directory", x["name"]))

            except PermissionError:
                return {
                    "success": False,
                    "error": f"Permission denied accessing: {resolved_path}",
                    "current_directory": self.current_directory,
                }

            return {
                "success": True,
                "path": resolved_path,
                "entries": entries,
                "current_directory": self.current_directory,
                "description": f"List directory: {resolved_path}",
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "current_directory": self.current_directory,
                "description": f"List directory: {path or 'current'}",
            }

    def clean_simulator_data(self) -> Dict[str, Any]:
        """Clean iOS/watchOS simulator data specifically"""
        try:
            if self.system != "Darwin":
                return {
                    "success": False,
                    "error": "Simulator cleanup is only available on macOS",
                    "description": "Clean simulator data",
                }

            simulator_base = os.path.expanduser("~/Library/Developer/CoreSimulator")
            if not os.path.exists(simulator_base):
                return {
                    "success": False,
                    "error": "No simulator data found",
                    "description": "Clean simulator data",
                }

            cleaned_items = []
            total_freed_bytes = 0

            # Paths to clean
            cleanup_paths = [
                "Devices/*/data/Containers/Data/Application/*/Library/Caches",
                "Devices/*/data/Containers/Data/Application/*/tmp",
                "Devices/*/data/Library/Caches",
                "Devices/*/data/tmp",
            ]

            import glob

            for pattern in cleanup_paths:
                full_pattern = os.path.join(simulator_base, pattern)
                matching_paths = glob.glob(full_pattern)

                for cache_path in matching_paths:
                    try:
                        # Calculate size before deletion
                        size_before = self._get_directory_size(cache_path)

                        # Remove cache contents but keep directory structure
                        if os.path.isdir(cache_path):
                            import shutil

                            for item in os.listdir(cache_path):
                                item_path = os.path.join(cache_path, item)
                                if os.path.isfile(item_path):
                                    os.remove(item_path)
                                elif os.path.isdir(item_path):
                                    shutil.rmtree(item_path, ignore_errors=True)

                            total_freed_bytes += size_before
                            cleaned_items.append(f"Cleaned {cache_path}")

                    except Exception as e:
                        cleaned_items.append(f"Could not clean {cache_path}: {e}")

            # Also run xcrun simctl to clean old unavailable simulators
            try:
                unavailable_result = self.execute_command(
                    "xcrun simctl delete unavailable", "Remove unavailable simulators"
                )
                if unavailable_result.get("success"):
                    cleaned_items.append("Removed unavailable simulator runtimes")
            except Exception:
                pass

            # Convert bytes to MB
            total_freed_mb = total_freed_bytes / (1024 * 1024)

            return {
                "success": True,
                "data": {
                    "cleaned_items": cleaned_items,
                    "total_freed_mb": round(total_freed_mb, 1),
                    "freed_bytes": total_freed_bytes,
                },
                "message": f"Simulator cleanup completed. Freed {total_freed_mb:.1f} MB",
                "description": "Clean simulator data",
            }

        except Exception as e:
            return {"success": False, "error": str(e), "description": "Clean simulator data"}

    def execute_shell_command(self, command: str, working_directory: str = None) -> Dict[str, Any]:
        """Execute a shell command in a specific directory"""
        try:
            # Use working directory if specified, otherwise use current directory
            cwd = working_directory if working_directory else self.current_directory

            logger.info(f"Executing shell command in {cwd}: {command}")

            result = subprocess.run(
                command, shell=True, capture_output=True, text=True, timeout=60, cwd=cwd
            )

            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
                "command": command,
                "working_directory": cwd,
                "current_directory": self.current_directory,
                "description": f"Execute: {command}",
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "output": "",
                "error": "Command timed out after 60 seconds",
                "command": command,
                "working_directory": cwd,
                "current_directory": self.current_directory,
                "description": f"Execute: {command}",
            }
        except Exception as e:
            return {
                "success": False,
                "output": "",
                "error": str(e),
                "command": command,
                "working_directory": cwd if "cwd" in locals() else self.current_directory,
                "current_directory": self.current_directory,
                "description": f"Execute: {command}",
            }


# Global instance for use in chat
system_controller = SystemController()


# Helper functions for easy use in chat
def open_textedit_and_write(text: str, filename: str = None) -> Dict[str, Any]:
    """Helper function to open TextEdit and write text"""
    return system_controller.open_textedit_and_write(text, filename)


def control_app(app_name: str, action: str, **kwargs) -> Dict[str, Any]:
    """Helper function to control applications"""
    return system_controller.control_application(app_name, action, **kwargs)


def execute_system_command(command: str, description: str = "") -> Dict[str, Any]:
    """Helper function to execute system commands"""
    return system_controller.execute_command(command, description)


def take_screenshot(filename: str = None) -> Dict[str, Any]:
    """Helper function to take screenshots"""
    return system_controller.take_screenshot(filename)


def open_file_or_url(path_or_url: str) -> Dict[str, Any]:
    """Helper function to open files or URLs"""
    return system_controller.open_file_or_url(path_or_url)


def change_directory(path: str) -> Dict[str, Any]:
    """Helper function to navigate to a directory"""
    return system_controller.change_directory(path)


def list_directory(
    path: str = None, show_hidden: bool = False, detailed: bool = False
) -> Dict[str, Any]:
    """Helper function to list directory contents"""
    return system_controller.list_directory(path, show_hidden, detailed)


def clean_simulator_data() -> Dict[str, Any]:
    """Helper function to clean iOS/watchOS simulator data"""
    return system_controller.clean_simulator_data()


def execute_shell_command(command: str, working_directory: str = None) -> Dict[str, Any]:
    """Helper function to execute shell commands"""
    return system_controller.execute_shell_command(command, working_directory)


def get_current_directory() -> str:
    """Helper function to get current working directory"""
    return system_controller.current_directory
