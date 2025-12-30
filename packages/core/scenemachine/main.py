"""Main entry point for SceneMachine backend."""

import asyncio
import logging
import os
import signal
import sys
from typing import Optional

from scenemachine.config import get_settings
from scenemachine.database import get_db_manager
from scenemachine.ipc import create_ipc_server, register_handlers

logger = logging.getLogger(__name__)


async def run_ipc_server() -> None:
    """Run the IPC server for Electron communication."""
    settings = get_settings()
    socket_path = os.environ.get("SCENEMACHINE_SOCKET_PATH", settings.ipc_socket_path)

    # Initialize database
    db_manager = get_db_manager()
    await db_manager.initialize()
    logger.info("Database initialized")

    # Create and configure IPC server
    server = create_ipc_server(socket_path)
    register_handlers(server)

    # Set up signal handlers for graceful shutdown
    stop_event = asyncio.Event()

    def signal_handler() -> None:
        logger.info("Received shutdown signal")
        stop_event.set()

    if sys.platform != "win32":
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, signal_handler)

    # Start server
    await server.start()

    try:
        # Run until stop signal
        server_task = asyncio.create_task(server.serve_forever())
        stop_task = asyncio.create_task(stop_event.wait())

        done, pending = await asyncio.wait(
            [server_task, stop_task],
            return_when=asyncio.FIRST_COMPLETED,
        )

        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

    finally:
        await server.stop()
        await db_manager.close()
        logger.info("Shutdown complete")


def main() -> None:
    """Main entry point."""
    settings = get_settings()

    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG if settings.debug else logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    logger.info(f"Starting SceneMachine v{settings.version}")
    logger.info(f"Environment: {settings.environment}")

    # Run the IPC server
    try:
        asyncio.run(run_ipc_server())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
