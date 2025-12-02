#!/usr/bin/env python3

import asyncio
import logging
import os
import signal
from multiprocessing import Process
from typing import Any, Optional

from aiohttp import web

from src.core.configuration import config_manager
from src.core.connection_manager import ConnectionManager
from src.core.constants import ConfigConstants
from src.core.heartbeat_service import HeartbeatService
from src.utils.operation_logger import OperationLogger

logger = logging.getLogger(__name__)


class ApplicationServer:
    """
    Main application server that manages the web server and application lifecycle.
    """

    def __init__(self, max_concurrent_connections: int = 3):
        """Initialize the application server."""
        self._app = web.Application()
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None
        self._process: Optional[Process] = None
        self._connection_manager = ConnectionManager(max_concurrent_connections)
        self._heartbeat_service = HeartbeatService(self._connection_manager)

    async def setup_routes(self, routes: web.RouteTableDef) -> None:
        """Setup web routes for the application."""
        start = OperationLogger.start("configure_routes", "server")
        self._app.add_routes(routes)
        OperationLogger.end("configure_routes", start, "server")

    async def start(self, port: int = ConfigConstants.DEFAULT_SERVER_PORT,
                    shutdown_event: Optional[asyncio.Event] = None) -> None:
        """
        Start the application server.
        
        Args:
            port: Port number to bind the server to
            shutdown_event: Event to signal shutdown (optional)
        """
        start = OperationLogger.start("server_start", "server")

        try:
            # Setup the server - disable access logging to reduce noise
            self._runner = web.AppRunner(self._app, access_log=None)
            await self._runner.setup()

            self._site = web.TCPSite(self._runner, '0.0.0.0', port)
            await self._site.start()

            # Start heartbeat monitoring
            await self._heartbeat_service.start()

            # Store shutdown event for coordination
            self._shutdown_event = shutdown_event

            OperationLogger.end("server_start", start, "server")

        except Exception as e:
            OperationLogger.error("server_start", "server", e)
            raise

    async def stop(self) -> None:
        """Enhanced stop method with proper shutdown coordination."""
        start = OperationLogger.start("stop", "server")

        try:
            # Close all connections with proper error handling
            try:
                await self._connection_manager.close_all()
                OperationLogger.end("connections_close", start, "server")
            except Exception as e:
                OperationLogger.error("connections_close", "server", e)

            # Stop web server with proper cleanup
            if self._site:
                try:
                    await self._site.stop()
                    OperationLogger.end("web_server_stop", start, "server")
                except Exception as e:
                    OperationLogger.error("web_server_stop", "server", e)

            if self._runner:
                try:
                    await self._runner.cleanup()
                    OperationLogger.end("web_runner_cleanup", start, "server")
                except Exception as e:
                    OperationLogger.error("web_runner_cleanup", "server", e)

            # Close configuration manager resources
            try:
                await config_manager.close()
                OperationLogger.end("config_manager_close", start, "server")
            except Exception as e:
                OperationLogger.error("config_manager_close", "server", e)

            OperationLogger.end("stop", start, "server")

        except Exception as e:
            OperationLogger.error("stop", "server", e)
            # Continue with shutdown even if there are errors
            pass

    @property
    def app(self) -> web.Application:
        """Get the underlying aiohttp application."""
        return self._app


class PluginAdapterApplication:
    """
    Main application class that orchestrates all components.
    Provides a clean interface for starting and stopping the entire application.
    """

    def __init__(self, max_concurrent_connections: int = 3):
        """Initialize the plugin adapter application."""
        self._server = ApplicationServer(max_concurrent_connections)
        self._signal_handlers_installed = False
        self._shutdown_initiated = False

    async def initialize(self) -> None:
        """Initialize the application by setting up all components."""
        start = OperationLogger.start("initialize", "adapter")

        try:
            # Load configuration
            config_manager.load_from_environment()

            # Setup network connections
            await self._setup_network_connections()

            OperationLogger.end("initialize", start, "adapter")
        except (asyncio.CancelledError, KeyboardInterrupt):
            OperationLogger.end("initialize", start, "adapter")
            # Re-raise to allow proper cleanup
            raise
        except Exception as e:
            OperationLogger.error("initialize", "adapter", e)
            raise

    async def _setup_network_connections(self) -> None:
        """Setup TCP connections to all configured ElectrumX servers using ConnectionManager."""
        currencies = config_manager.get_all_currencies()
        if not currencies:
            OperationLogger.error("setup_network", "adapter",
                                  Exception("No currencies configured, skipping network setup"))
            return

        start = OperationLogger.start("setup_network", "adapter")

        # Use ConnectionManager to establish all connections
        for currency in currencies:
            try:
                socket = await self._server._connection_manager.get_socket(currency)
            except Exception as e:
                OperationLogger.error("setup_network", currency, e)

        OperationLogger.end("setup_network", start, "adapter")

    async def start(self, port: int = ConfigConstants.DEFAULT_SERVER_PORT,
                    shutdown_event: Optional[asyncio.Event] = None) -> None:
        """
        Start the application.
        
        Args:
            port: Port number for the web server
            shutdown_event: Event to signal shutdown (optional)
        """
        await self.initialize()
        await self._server.start(port, shutdown_event)
        self._install_signal_handlers()

    async def stop(self) -> None:
        """Stop the application."""
        start = OperationLogger.start("stop", "adapter")

        # Stop heartbeat service first to prevent new connections
        await self._server._heartbeat_service.stop()

        # Shutdown connection manager to prevent new connections
        self._server._connection_manager.shutdown()

        # Remove signal handlers
        self._remove_signal_handlers()

        # Stop the server
        await self._server.stop()
        OperationLogger.end("stop", start, "adapter")

    def _signal_handler(self, signum: int, frame: Any) -> None:
        """
        Handle shutdown signals immediately and aggressively.
        This runs in the main thread, so we need to schedule shutdown in the event loop.
        
        Args:
            signum: Signal number
            frame: Signal frame
        """
        start = OperationLogger.start("signal_caught", "adapter")

        # Set shutdown flag
        self._shutdown_initiated = True

        # Schedule shutdown in the event loop thread
        try:
            loop = asyncio.get_running_loop()
            if loop.is_running():
                # Schedule shutdown coroutine
                shutdown_task = loop.create_task(self._shutdown_coroutine())
                OperationLogger.end("shutdown_scheduled", start, "adapter")

                # Cancel ALL tasks immediately for instant shutdown
                for task in asyncio.all_tasks(loop):
                    if task is not asyncio.current_task(loop):
                        task.cancel()

        except RuntimeError:
            # No running loop, signal received during startup
            OperationLogger.end("signal_during_startup", start, "adapter")
            os._exit(0)
        except Exception as e:
            OperationLogger.error("schedule_shutdown", "adapter", e)
            os._exit(1)

    async def _shutdown_coroutine(self) -> None:
        """
        Immediate shutdown coroutine with aggressive task cancellation.
        """
        start = OperationLogger.start("async_shutdown_start", "adapter")

        try:
            # Step 1: Stop accepting new requests - IMMEDIATE EXIT
            OperationLogger.start("stopping_web_server", "adapter")

            # Stop heartbeat service first to prevent new connections
            await self._server._heartbeat_service.stop()

            # Shutdown connection manager to prevent new connections
            self._server._connection_manager.shutdown()

            # Remove signal handlers
            self._remove_signal_handlers()

            # Step 2: Cancel ALL remaining tasks immediately
            OperationLogger.start("cancelling_tasks", "adapter")
            loop = asyncio.get_running_loop()
            tasks = [t for t in asyncio.all_tasks(loop) if t is not asyncio.current_task(loop)]

            if tasks:
                OperationLogger.start("cancelling_remaining_tasks", "adapter")
                for task in tasks:
                    if hasattr(task, 'cancel'):
                        task.cancel()

                # Don't wait - just exit immediately
                OperationLogger.end("tasks_cancelled_immediately", start, "adapter")

            # Step 3: Signal shutdown event if available
            if hasattr(self, '_shutdown_event') and self._shutdown_event:
                self._shutdown_event.set()
                OperationLogger.end("shutdown_event_signaled", start, "adapter")

            OperationLogger.end("async_shutdown_complete", start, "adapter")

            # IMMEDIATE EXIT - no waiting for anything
            os._exit(0)

        except Exception as e:
            OperationLogger.error("shutdown", "adapter", e)
            # Force exit if shutdown fails
            os._exit(1)

    def _install_signal_handlers(self) -> None:
        """Install signal handlers for graceful shutdown."""
        start = OperationLogger.start("install_signal_handlers", "adapter")

        if self._signal_handlers_installed:
            OperationLogger.end("install_signal_handlers", start, "adapter")
            return

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        self._signal_handlers_installed = True
        OperationLogger.end("install_signal_handlers", start, "adapter")

    def _remove_signal_handlers(self) -> None:
        """Remove signal handlers."""
        start = OperationLogger.start("remove_signal_handlers", "adapter")

        if not self._signal_handlers_installed:
            OperationLogger.end("remove_signal_handlers", start, "adapter")
            return

        signal.signal(signal.SIGINT, signal.SIG_DFL)
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        self._signal_handlers_installed = False
        OperationLogger.end("remove_signal_handlers", start, "adapter")

    @property
    def server(self) -> ApplicationServer:
        """Get the application server instance."""
        return self._server

    @property
    def heartbeat_service(self) -> HeartbeatService:
        """Get the heartbeat service instance."""
        return self._server._heartbeat_service

    @property
    def connection_manager(self) -> 'ConnectionManager':
        """Get the connection manager instance."""
        return self._server._connection_manager
