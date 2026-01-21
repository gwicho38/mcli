"""
MCLI Chat System
Real-time system control and interaction capabilities for MCLI chat
"""

from .system_controller import (
    SystemController,
    control_app,
    execute_system_command,
    open_file_or_url,
    open_textedit_and_write,
    system_controller,
    take_screenshot,
)
from .system_integration import (
    ChatSystemIntegration,
    chat_system_integration,
    get_system_capabilities,
    handle_system_request,
)

__all__ = [
    "SystemController",
    "system_controller",
    "ChatSystemIntegration",
    "chat_system_integration",
    "handle_system_request",
    "get_system_capabilities",
    "open_textedit_and_write",
    "control_app",
    "execute_system_command",
    "take_screenshot",
    "open_file_or_url",
]
