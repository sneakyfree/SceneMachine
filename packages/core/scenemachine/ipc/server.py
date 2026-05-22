"""IPC server for Electron communication."""

import asyncio
import json
import logging
import os
import sys
from collections.abc import Callable, Coroutine
from pathlib import Path
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

# Default ports for Windows TCP fallback
DEFAULT_TCP_HOST = "127.0.0.1"
DEFAULT_TCP_PORT = 19847  # SceneMachine IPC port

# Type alias for async handler functions
HandlerFunc = Callable[..., Coroutine[Any, Any, Any]]


class IPCMessage:
    """IPC message format for communication with Electron."""

    def __init__(
        self,
        type: str,
        method: str,
        params: dict[str, Any] | None = None,
        id: str | None = None,
        result: Any | None = None,
        error: dict[str, Any] | None = None,
    ) -> None:
        """Initialize IPC message.

        Args:
            type: Message type (request, response, notification, stream)
            method: Method name to invoke
            params: Method parameters
            id: Unique message ID for correlation
            result: Result data (for responses)
            error: Error information (for error responses)
        """
        self.type = type
        self.method = method
        self.params = params or {}
        self.id = id or str(uuid4())
        self.result = result
        self.error = error

    def to_json(self) -> str:
        """Serialize message to JSON string."""
        data: dict[str, Any] = {
            "type": self.type,
            "method": self.method,
            "id": self.id,
        }
        if self.params:
            data["params"] = self.params
        if self.result is not None:
            data["result"] = self.result
        if self.error:
            data["error"] = self.error
        return json.dumps(data)

    @classmethod
    def from_json(cls, data: str) -> "IPCMessage":
        """Deserialize message from JSON string."""
        obj = json.loads(data)
        return cls(
            type=obj.get("type", "request"),
            method=obj.get("method", ""),
            params=obj.get("params"),
            id=obj.get("id"),
            result=obj.get("result"),
            error=obj.get("error"),
        )


class IPCServer:
    """IPC server for Electron communication.

    Uses Unix domain sockets on Linux/macOS, TCP sockets on Windows.
    Implements a simple request/response protocol with JSON messages.
    """

    def __init__(
        self,
        socket_path: str,
        host: str = DEFAULT_TCP_HOST,
        port: int = DEFAULT_TCP_PORT,
    ) -> None:
        """Initialize IPC server.

        Args:
            socket_path: Path to Unix socket (ignored on Windows)
            host: TCP host for Windows (default: 127.0.0.1)
            port: TCP port for Windows (default: 19847)
        """
        self.socket_path = socket_path
        self.host = host
        self.port = port
        self.handlers: dict[str, HandlerFunc] = {}
        self.server: asyncio.Server | None = None
        self._running = False
        self._is_windows = sys.platform == "win32"

    def register_handler(self, method: str, handler: HandlerFunc) -> None:
        """Register a method handler.

        Args:
            method: Method name
            handler: Async function to handle the method
        """
        self.handlers[method] = handler
        logger.debug(f"Registered IPC handler: {method}")

    def handler(self, method: str) -> Callable[[HandlerFunc], HandlerFunc]:
        """Decorator to register a method handler.

        Example:
            @ipc_server.handler("projects.list")
            async def handle_list_projects():
                return projects
        """

        def decorator(func: HandlerFunc) -> HandlerFunc:
            self.register_handler(method, func)
            return func

        return decorator

    async def start(self) -> None:
        """Start the IPC server."""
        if self._is_windows:
            # Windows: Use TCP socket on localhost
            self.server = await asyncio.start_server(
                self._handle_client,
                host=self.host,
                port=self.port,
            )
            address = f"{self.host}:{self.port}"
            logger.info(f"IPC server started at tcp://{address}")
            # Signal to parent process with connection info
            print(f"IPC server started tcp://{address}", flush=True)
        else:
            # Unix: Use domain socket
            # Clean up existing socket
            path = Path(self.socket_path)
            if path.exists():
                path.unlink()

            # Ensure parent directory exists
            path.parent.mkdir(parents=True, exist_ok=True)

            self.server = await asyncio.start_unix_server(
                self._handle_client,
                path=self.socket_path,
            )
            logger.info(f"IPC server started at unix://{self.socket_path}")
            # Signal to parent process with connection info
            print(f"IPC server started unix://{self.socket_path}", flush=True)

        self._running = True

    async def serve_forever(self) -> None:
        """Serve requests until stopped."""
        if self.server:
            async with self.server:
                await self.server.serve_forever()

    async def stop(self) -> None:
        """Stop the IPC server."""
        self._running = False
        if self.server:
            self.server.close()
            await self.server.wait_closed()

        # Clean up Unix socket file if not Windows
        if not self._is_windows:
            path = Path(self.socket_path)
            if path.exists():
                path.unlink()

        logger.info("IPC server stopped")

    def get_connection_info(self) -> dict[str, Any]:
        """Get connection information for clients.

        Returns:
            Dict with connection type and address info
        """
        if self._is_windows:
            return {
                "type": "tcp",
                "host": self.host,
                "port": self.port,
            }
        else:
            return {
                "type": "unix",
                "path": self.socket_path,
            }

    async def _handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle a client connection."""
        peer = writer.get_extra_info("peername")
        logger.debug(f"New IPC connection from {peer}")

        try:
            while self._running:
                # Read message length (4 bytes, big-endian)
                length_bytes = await reader.read(4)
                if not length_bytes or len(length_bytes) < 4:
                    break

                length = int.from_bytes(length_bytes, "big")
                if length == 0 or length > 10_000_000:  # 10MB limit
                    logger.warning(f"Invalid message length: {length}")
                    break

                # Read message data
                data = await reader.read(length)
                if not data or len(data) < length:
                    break

                # Process message
                try:
                    message = IPCMessage.from_json(data.decode("utf-8"))
                    response = await self._process_message(message)
                except json.JSONDecodeError as e:
                    response = IPCMessage(
                        type="response",
                        method="error",
                        id="unknown",
                        error={
                            "code": "PARSE_ERROR",
                            "message": f"Invalid JSON: {e}",
                        },
                    )

                # Send response
                response_data = response.to_json().encode("utf-8")
                writer.write(len(response_data).to_bytes(4, "big"))
                writer.write(response_data)
                await writer.drain()

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.exception(f"Error handling IPC client: {e}")
        finally:
            writer.close()
            await writer.wait_closed()
            logger.debug(f"IPC connection closed: {peer}")

    async def _process_message(self, message: IPCMessage) -> IPCMessage:
        """Process an incoming message and return response."""
        handler = self.handlers.get(message.method)

        if not handler:
            return IPCMessage(
                type="response",
                method=message.method,
                id=message.id,
                error={
                    "code": "METHOD_NOT_FOUND",
                    "message": f"Unknown method: {message.method}",
                },
            )

        try:
            result = await handler(**message.params)
            return IPCMessage(
                type="response",
                method=message.method,
                id=message.id,
                result=result,
            )
        except Exception as e:
            logger.exception(f"Error processing {message.method}: {e}")
            return IPCMessage(
                type="response",
                method=message.method,
                id=message.id,
                error={
                    "code": "HANDLER_ERROR",
                    "message": str(e),
                },
            )


def create_ipc_server(
    socket_path: str | None = None,
    host: str | None = None,
    port: int | None = None,
) -> IPCServer:
    """Create an IPC server instance.

    Args:
        socket_path: Optional custom socket path (Unix)
        host: Optional custom host (Windows, default: 127.0.0.1)
        port: Optional custom port (Windows, default: 19847)

    Returns:
        Configured IPCServer instance
    """
    if socket_path is None:
        socket_path = os.environ.get("SCENEMACHINE_SOCKET_PATH", "/tmp/scenemachine.sock")

    if host is None:
        host = os.environ.get("SCENEMACHINE_IPC_HOST", DEFAULT_TCP_HOST)

    if port is None:
        port = int(os.environ.get("SCENEMACHINE_IPC_PORT", str(DEFAULT_TCP_PORT)))

    return IPCServer(socket_path, host=host, port=port)


# IPC Client for connecting to the server (useful for testing)
class IPCClient:
    """IPC client for connecting to the server."""

    def __init__(
        self,
        socket_path: str = "/tmp/scenemachine.sock",
        host: str = DEFAULT_TCP_HOST,
        port: int = DEFAULT_TCP_PORT,
    ) -> None:
        """Initialize IPC client.

        Args:
            socket_path: Unix socket path
            host: TCP host for Windows
            port: TCP port for Windows
        """
        self.socket_path = socket_path
        self.host = host
        self.port = port
        self._is_windows = sys.platform == "win32"
        self.reader: asyncio.StreamReader | None = None
        self.writer: asyncio.StreamWriter | None = None

    async def connect(self) -> None:
        """Connect to the IPC server."""
        if self._is_windows:
            self.reader, self.writer = await asyncio.open_connection(self.host, self.port)
        else:
            self.reader, self.writer = await asyncio.open_unix_connection(self.socket_path)

    async def disconnect(self) -> None:
        """Disconnect from the IPC server."""
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            self.writer = None
            self.reader = None

    async def call(self, method: str, **params: Any) -> Any:
        """Call a method on the IPC server.

        Args:
            method: Method name
            **params: Method parameters

        Returns:
            Result from the server

        Raises:
            RuntimeError: If not connected
            Exception: If server returns an error
        """
        if not self.writer or not self.reader:
            raise RuntimeError("Not connected to IPC server")

        # Create request message
        message = IPCMessage(type="request", method=method, params=params)
        data = message.to_json().encode("utf-8")

        # Send request
        self.writer.write(len(data).to_bytes(4, "big"))
        self.writer.write(data)
        await self.writer.drain()

        # Read response
        length_bytes = await self.reader.read(4)
        if not length_bytes or len(length_bytes) < 4:
            raise RuntimeError("Connection closed")

        length = int.from_bytes(length_bytes, "big")
        response_data = await self.reader.read(length)

        # Parse response
        response = IPCMessage.from_json(response_data.decode("utf-8"))

        if response.error:
            raise Exception(
                f"IPC Error [{response.error.get('code')}]: {response.error.get('message')}"
            )

        return response.result

    async def __aenter__(self) -> "IPCClient":
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, *args: Any) -> None:
        """Async context manager exit."""
        await self.disconnect()
