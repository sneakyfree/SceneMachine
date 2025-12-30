"""IPC communication with Electron frontend."""

from scenemachine.ipc.handlers import register_handlers
from scenemachine.ipc.server import IPCMessage, IPCServer, create_ipc_server

__all__ = [
    "IPCServer",
    "IPCMessage",
    "create_ipc_server",
    "register_handlers",
]
