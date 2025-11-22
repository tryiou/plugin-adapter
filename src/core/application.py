#!/usr/bin/env python3

import asyncio
import logging
import signal
import time
from aiohttp import web
from multiprocessing import Process
from threading import Thread, Event
from typing import Dict, List, Optional, Any

from src.core.configuration import config_manager
from src.core.error_handling import NetworkError, ProtocolError
from src.networking.tcp_socket import TCPSocket
from src.utils.helpers import get_info

logger = logging.getLogger(__name__)


class HeartbeatManager:
    """
    Thread-safe heartbeat manager that replaces the problematic HeartbeatThread.
    Uses proper async patterns instead of creating new event loops in threads.
    """

    def __init__(self):
        """Initialize the heartbeat manager with thread-safe state."""
        self._running = False
        self._stop_event = Event()
        self._heartbeat_thread: Optional[Thread] = None

    def start(self) -> None:
        """Start the heartbeat monitoring."""
        if self._running:
            logger.warning("[heartbeat] Heartbeat is already running")
            return

        self._running = True
        self._stop_event.clear()
        self._heartbeat_thread = Thread(target=self._run_heartbeat, name="HeartbeatThread")
        self._heartbeat_thread.start()
        logger.info("[heartbeat] Heartbeat manager started")

    def stop(self) -> None:
        """Stop the heartbeat monitoring."""
        if not self._running:
            logger.warning("[heartbeat] Heartbeat is not running")
            return

        logger.info("[heartbeat] Stopping heartbeat manager")
        self._running = False
        self._stop_event.set()

        if self._heartbeat_thread and self._heartbeat_thread.is_alive():
            self._heartbeat_thread.join(timeout=5)
            if self._heartbeat_thread.is_alive():
                logger.warning("[heartbeat] Heartbeat thread did not stop gracefully")

    def _run_heartbeat(self) -> None:
        """Main heartbeat loop running in a separate thread."""
        try:
            # Initial connection check for all currencies
            logger.info("[heartbeat] Performing initial connection checks")

            # Use asyncio.run() to create a proper event loop in this thread
            asyncio.run(self._initial_heartbeat())

            # Main heartbeat loop
            while self._running and not self._stop_event.is_set():
                logger.debug("[heartbeat] Running periodic heartbeat check")
                try:
                    asyncio.run(self._periodic_heartbeat())
                except Exception as e:
                    logger.error(f"[heartbeat] Error in periodic heartbeat: {e}")

                if self._stop_event.wait(timeout=30):
                    break

        except Exception as e:
            logger.error(f"[heartbeat] Fatal error in heartbeat thread: {e}")
        finally:
            logger.info("[heartbeat] Heartbeat thread stopped")

    async def _initial_heartbeat(self) -> None:
        """Perform initial heartbeat for all configured currencies."""
        currencies = config_manager.get_all_currencies()
        if not currencies:
            logger.warning("[heartbeat] No currencies configured for initial heartbeat")
            return

        logger.info(f"[heartbeat] Initial heartbeat for {len(currencies)} currencies: {currencies}")

        # Create coroutines for all currencies
        coroutines = [get_info(currency, initial=True) for currency in currencies]

        # Execute concurrently
        try:
            await asyncio.gather(*coroutines, return_exceptions=True)
        except Exception as e:
            logger.error(f"[heartbeat] Error during initial heartbeat: {e}")

    async def _periodic_heartbeat(self) -> None:
        """Perform periodic heartbeat for all configured currencies."""
        currencies = config_manager.get_all_currencies()
        if not currencies:
            return

        # Create coroutines for all currencies
        coroutines = [get_info(currency, initial=False) for currency in currencies]

        # Execute concurrently
        try:
            await asyncio.gather(*coroutines, return_exceptions=True)
        except Exception as e:
            logger.error(f"[heartbeat] Error during periodic heartbeat: {e}")


class ApplicationServer:
    """
    Main application server that manages the web server and application lifecycle.
    """

    def __init__(self):
        """Initialize the application server."""
        self._app = web.Application()
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None
        self._process: Optional[Process] = None
        self._heartbeat_manager = HeartbeatManager()

    async def setup_routes(self, routes: web.RouteTableDef) -> None:
        """Setup web routes for the application."""
        self._app.add_routes(routes)
        logger.info("[server] Routes configured")

    async def start(self, port: int = 5000) -> None:
        """
        Start the application server.
        
        Args:
            port: Port number to bind the server to
        """
        try:
            # Setup the server
            self._runner = web.AppRunner(self._app)
            await self._runner.setup()

            self._site = web.TCPSite(self._runner, '0.0.0.0', port)
            await self._site.start()

            logger.info(f"[server] Server started on port {port}")

            # Start heartbeat monitoring
            self._heartbeat_manager.start()

        except Exception as e:
            logger.error(f"[server] Failed to start server: {e}")
            raise

    async def stop(self) -> None:
        """Stop the application server."""
        logger.info("[server] Stopping application server")

        # Stop heartbeat first
        self._heartbeat_manager.stop()

        # Stop web server
        if self._site:
            await self._site.stop()

        if self._runner:
            await self._runner.cleanup()

        logger.info("[server] Application server stopped")

    @property
    def app(self) -> web.Application:
        """Get the underlying aiohttp application."""
        return self._app


class PluginAdapterApplication:
    """
    Main application class that orchestrates all components.
    Provides a clean interface for starting and stopping the entire application.
    """

    def __init__(self):
        """Initialize the plugin adapter application."""
        self._server = ApplicationServer()
        self._signal_handlers_installed = False

    async def initialize(self) -> None:
        """Initialize the application by setting up all components."""
        logger.info("[adapter] Initializing plugin adapter application")

        # Load configuration
        config_manager.load_from_environment()

        # Setup network connections
        await self._setup_network_connections()

        logger.info("[adapter] Application initialization complete")

    async def _setup_network_connections(self) -> None:
        """Setup TCP connections to all configured ElectrumX servers."""
        currencies = config_manager.get_all_currencies()
        if not currencies:
            logger.warning("[adapter] No currencies configured, skipping network setup")
            return

        logger.info(f"[adapter] Setting up network connections for {len(currencies)} currencies")

        for currency in currencies:
            coin_config = config_manager.get_coin_config(currency)
            if not coin_config:
                continue

            try:
                # Create socket connection
                socket = TCPSocket(coin_config.host, coin_config.port + 1000)
                await socket.connect()

                # Register socket in configuration
                config_manager.set_coin_socket(currency, socket)

                logger.info(f"[adapter] Registered host {coin_config.host} port {coin_config.port} for coin {currency}")

            except Exception as e:
                logger.error(f"[adapter] Failed to connect to {currency}: {e}")

        logger.info(f"[adapter] Have {len(currencies)} coin/port pair(s)")

    async def start(self, port: int = 5000) -> None:
        """
        Start the application.
        
        Args:
            port: Port number for the web server
        """
        await self.initialize()
        await self._server.start(port)
        self._install_signal_handlers()
        logger.info(f"[server] Starting RPC server on port {port}")

    async def stop(self) -> None:
        """Stop the application."""
        logger.info("[adapter] Stopping plugin adapter application")
        self._remove_signal_handlers()
        await self._server.stop()
        logger.info("[adapter] Application stopped")

    def _signal_handler(self, signum: int, frame: Any) -> None:
        """
        Handle shutdown signals gracefully.
        
        Args:
            signum: Signal number
            frame: Signal frame
        """
        logger.info(f"[adapter] Caught signal {signum}. Shutting down gracefully.")

        # This will be called from the main thread, so we need to stop the server
        # The heartbeat manager will be stopped by the server's stop method
        asyncio.create_task(self._server.stop())

    def _install_signal_handlers(self) -> None:
        """Install signal handlers for graceful shutdown."""
        if self._signal_handlers_installed:
            return

        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        self._signal_handlers_installed = True
        logger.info("[adapter] Signal handlers installed")

    def _remove_signal_handlers(self) -> None:
        """Remove signal handlers."""
        if not self._signal_handlers_installed:
            return

        signal.signal(signal.SIGINT, signal.SIG_DFL)
        signal.signal(signal.SIGTERM, signal.SIG_DFL)
        self._signal_handlers_installed = False
        logger.info("[adapter] Signal handlers removed")

    @property
    def server(self) -> ApplicationServer:
        """Get the application server instance."""
        return self._server

    @property
    def heartbeat_manager(self) -> HeartbeatManager:
        """Get the heartbeat manager instance."""
        return self._server._heartbeat_manager
