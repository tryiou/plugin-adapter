#!/usr/bin/env python3
"""
Unit tests for Application Core (src/core/application.py).
Tests application startup, signal handling, web server lifecycle, and error handling.
"""

import asyncio
import signal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.core.application import ApplicationServer, PluginAdapterApplication
from src.core.configuration import config_manager
from src.core.connection_manager import ConnectionManager
from src.core.errors import NetworkError
from src.core.heartbeat_service import HeartbeatService


class TestApplicationServer:
    """Test suite for ApplicationServer class."""

    def setup_method(self):
        """Setup for each test method."""
        self.server = ApplicationServer(max_concurrent_connections=2)

    def teardown_method(self):
        """Cleanup after each test method."""
        # Reset any mock state
        pass

    @pytest.mark.asyncio
    async def test_server_initialization(self):
        """Test ApplicationServer initialization."""
        server = ApplicationServer(max_concurrent_connections=5)

        assert server._app is not None
        assert server._runner is None
        assert server._site is None
        assert isinstance(server._connection_manager, ConnectionManager)
        assert isinstance(server._heartbeat_service, HeartbeatService)

    @pytest.mark.asyncio
    async def test_setup_routes(self):
        """Test route setup for the application."""
        from aiohttp import web

        routes = web.RouteTableDef()
        routes.get('/test')(lambda request: web.Response(text="test"))

        await self.server.setup_routes(routes)

        # Verify route was added
        assert len(self.server._app.router.routes()) > 0

    @pytest.mark.asyncio
    async def test_start_success(self):
        """Test successful server startup."""
        with patch('aiohttp.web.AppRunner') as mock_runner_class, \
                patch('aiohttp.web.TCPSite') as mock_site_class:
            mock_runner = AsyncMock()
            mock_site = AsyncMock()

            mock_runner_class.return_value = mock_runner
            mock_site_class.return_value = mock_site

            # Mock the heartbeat service start method to be an AsyncMock
            with patch.object(self.server._heartbeat_service, 'start', new_callable=AsyncMock) as mock_heartbeat_start:
                shutdown_event = asyncio.Event()

                await self.server.start(port=8080, shutdown_event=shutdown_event)

                # Verify runner setup was called
                mock_runner.setup.assert_called_once()
                # Verify site start was called
                mock_site_class.assert_called_once()
                mock_site.start.assert_called_once()
                # Verify heartbeat service started
                mock_heartbeat_start.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_failure(self):
        """Test server startup failure handling."""
        with patch('aiohttp.web.AppRunner') as mock_runner_class:
            mock_runner = AsyncMock()
            mock_runner_class.return_value = mock_runner
            mock_runner.setup.side_effect = Exception("Startup failed")

            # Mock the heartbeat service start method to be an AsyncMock
            with patch.object(self.server._heartbeat_service, 'start', new_callable=AsyncMock) as mock_heartbeat_start:
                with pytest.raises(Exception):
                    await self.server.start(port=8080)

                # Verify heartbeat service was not started on failure
                mock_heartbeat_start.assert_not_called()

    @pytest.mark.asyncio
    async def test_stop_success(self):
        """Test successful server shutdown."""
        with patch('aiohttp.web.AppRunner') as mock_runner_class, \
                patch('aiohttp.web.TCPSite') as mock_site_class:
            mock_runner = AsyncMock()
            mock_site = AsyncMock()

            mock_runner_class.return_value = mock_runner
            mock_site_class.return_value = mock_site

            # Mock the connection manager close_all method to be an AsyncMock
            with patch.object(self.server._connection_manager, 'close_all', new_callable=AsyncMock) as mock_close_all, \
                    patch.object(config_manager, 'close', new_callable=AsyncMock) as mock_config_close:
                # Start the server first
                await self.server.start(port=8080)

                # Stop the server
                await self.server.stop()

                # Verify connection manager was closed
                mock_close_all.assert_called_once()
                # Verify web server was stopped
                mock_site.stop.assert_called_once()
                # Verify runner was cleaned up
                mock_runner.cleanup.assert_called_once()
                # Verify config manager was closed
                mock_config_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_stop_with_errors(self):
        """Test server shutdown with errors during cleanup."""
        with patch('aiohttp.web.AppRunner') as mock_runner_class, \
                patch('aiohttp.web.TCPSite') as mock_site_class:
            mock_runner = AsyncMock()
            mock_site = AsyncMock()

            mock_runner_class.return_value = mock_runner
            mock_site_class.return_value = mock_site

            # Set the server's site and runner to the mock objects so they get called
            self.server._site = mock_site
            self.server._runner = mock_runner

            # Mock the connection manager close_all method to be an AsyncMock
            with patch.object(self.server._connection_manager, 'close_all', new_callable=AsyncMock) as mock_close_all, \
                    patch.object(config_manager, 'close', new_callable=AsyncMock) as mock_config_close:
                # Mock errors during cleanup
                mock_close_all.side_effect = Exception("Close failed")

                # Should still attempt to continue cleanup gracefully
                await self.server.stop()

                # Verify all cleanup methods were still called
                mock_close_all.assert_called_once()
                mock_site.stop.assert_called_once()
                mock_runner.cleanup.assert_called_once()
                mock_config_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_app_property(self):
        """Test app property access."""
        app = self.server.app
        assert app is not None
        assert app == self.server._app


class TestPluginAdapterApplication:
    """Test suite for PluginAdapterApplication class."""

    def setup_method(self):
        """Setup for each test method."""
        self.app = PluginAdapterApplication(max_concurrent_connections=2)

    def teardown_method(self):
        """Cleanup after each test method."""
        pass

    @pytest.mark.asyncio
    async def test_application_initialization(self):
        """Test application initialization."""
        with patch.object(config_manager, 'load_from_environment') as mock_load_config, \
                patch.object(self.app, '_setup_network_connections') as mock_setup_network:
            await self.app.initialize()

            # Verify configuration was loaded
            mock_load_config.assert_called_once()
            # Verify network setup was called
            mock_setup_network.assert_called_once()

    @pytest.mark.asyncio
    async def test_application_initialization_failure(self):
        """Test application initialization failure handling."""
        with patch.object(config_manager, 'load_from_environment') as mock_load_config:
            mock_load_config.side_effect = Exception("Config load failed")

            with pytest.raises(Exception):
                await self.app.initialize()

    @pytest.mark.asyncio
    async def test_application_start(self):
        """Test application startup."""
        with patch.object(self.app, 'initialize') as mock_init, \
                patch.object(self.app._server, 'start') as mock_server_start, \
                patch.object(self.app, '_install_signal_handlers') as mock_install_signals:
            await self.app.start(port=8080)

            # Verify initialization
            mock_init.assert_called_once()
            # Verify server start
            mock_server_start.assert_called_once_with(8080, None)
            # Verify signal handlers installed
            mock_install_signals.assert_called_once()

    @pytest.mark.asyncio
    async def test_application_stop(self):
        """Test application shutdown."""
        with patch.object(self.app._server._heartbeat_service, 'stop', new_callable=AsyncMock) as mock_heartbeat_stop, \
                patch.object(self.app._server._connection_manager, 'shutdown') as mock_conn_shutdown, \
                patch.object(self.app, '_remove_signal_handlers') as mock_remove_signals, \
                patch.object(self.app._server, 'stop', new_callable=AsyncMock) as mock_server_stop:
            await self.app.stop()

            # Verify shutdown order
            mock_heartbeat_stop.assert_called_once()
            mock_conn_shutdown.assert_called_once()
            mock_remove_signals.assert_called_once()
            mock_server_stop.assert_called_once()

    @pytest.mark.asyncio
    async def test_signal_handler_sigint(self):
        """Test SIGINT signal handling."""
        with patch('asyncio.get_running_loop') as mock_get_loop, \
                patch.object(self.app, '_shutdown_coroutine', new_callable=AsyncMock) as mock_shutdown:
            mock_loop = MagicMock()
            mock_loop.is_running.return_value = True
            mock_get_loop.return_value = mock_loop

            # Simulate SIGINT signal
            self.app._signal_handler(signal.SIGINT, None)

            # Verify shutdown was scheduled
            mock_loop.create_task.assert_called_once()
            # Verify shutdown flag was set
            assert self.app._shutdown_initiated is True

    @pytest.mark.asyncio
    async def test_signal_handler_sigterm(self):
        """Test SIGTERM signal handling."""
        with patch('asyncio.get_running_loop') as mock_get_loop, \
                patch.object(self.app, '_shutdown_coroutine', new_callable=AsyncMock) as mock_shutdown:
            mock_loop = MagicMock()
            mock_loop.is_running.return_value = True
            mock_get_loop.return_value = mock_loop

            # Simulate SIGTERM signal
            self.app._signal_handler(signal.SIGTERM, None)

            # Verify shutdown was scheduled
            mock_loop.create_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_signal_handler_no_running_loop(self):
        """Test signal handling when no event loop is running."""
        with patch('asyncio.get_running_loop') as mock_get_loop, \
                patch('os._exit') as mock_exit:
            mock_get_loop.side_effect = RuntimeError("No running loop")

            # Simulate signal
            self.app._signal_handler(signal.SIGINT, None)

            # Verify immediate exit
            mock_exit.assert_called_once_with(0)

    @pytest.mark.asyncio
    async def test_shutdown_coroutine_immediate_exit(self):
        """Test shutdown coroutine with immediate exit behavior."""
        with patch('asyncio.get_running_loop') as mock_get_loop, \
                patch('os._exit') as mock_exit, \
                patch.object(self.app._server._heartbeat_service, 'stop',
                             new_callable=AsyncMock) as mock_heartbeat_stop, \
                patch.object(self.app._server._connection_manager, 'shutdown') as mock_conn_shutdown, \
                patch.object(self.app, '_remove_signal_handlers') as mock_remove_signals:
            mock_loop = MagicMock()
            mock_get_loop.return_value = mock_loop

            # Mock some tasks to cancel
            mock_task = MagicMock()
            mock_task.cancel = MagicMock()
            mock_loop.all_tasks.return_value = [mock_task]

            # Run shutdown coroutine
            await self.app._shutdown_coroutine()

            # Verify shutdown steps
            mock_heartbeat_stop.assert_called_once()
            mock_conn_shutdown.assert_called_once()
            mock_remove_signals.assert_called_once()
            # Verify immediate exit (the application exits immediately without waiting for task cancellation)
            mock_exit.assert_called_once_with(0)

    @pytest.mark.asyncio
    async def test_install_signal_handlers(self):
        """Test signal handler installation."""
        with patch('signal.signal') as mock_signal:
            self.app._install_signal_handlers()

            # Verify both SIGINT and SIGTERM handlers were installed
            assert mock_signal.call_count == 2
            mock_signal.assert_any_call(signal.SIGINT, self.app._signal_handler)
            mock_signal.assert_any_call(signal.SIGTERM, self.app._signal_handler)
            assert self.app._signal_handlers_installed is True

    @pytest.mark.asyncio
    async def test_install_signal_handlers_already_installed(self):
        """Test signal handler installation when already installed."""
        with patch('signal.signal') as mock_signal:
            self.app._signal_handlers_installed = True
            self.app._install_signal_handlers()

            # Verify no additional signal handlers were installed
            mock_signal.assert_not_called()

    @pytest.mark.asyncio
    async def test_remove_signal_handlers(self):
        """Test signal handler removal."""
        with patch('signal.signal') as mock_signal:
            self.app._signal_handlers_installed = True
            self.app._remove_signal_handlers()

            # Verify both signal handlers were removed
            assert mock_signal.call_count == 2
            mock_signal.assert_any_call(signal.SIGINT, signal.SIG_DFL)
            mock_signal.assert_any_call(signal.SIGTERM, signal.SIG_DFL)
            assert self.app._signal_handlers_installed is False

    @pytest.mark.asyncio
    async def test_remove_signal_handlers_not_installed(self):
        """Test signal handler removal when not installed."""
        with patch('signal.signal') as mock_signal:
            self.app._signal_handlers_installed = False
            self.app._remove_signal_handlers()

            # Verify no signal handlers were removed
            mock_signal.assert_not_called()

    @pytest.mark.asyncio
    async def test_setup_network_connections_success(self):
        """Test successful network connection setup."""
        with patch.object(config_manager, 'get_all_currencies') as mock_get_currencies, \
                patch.object(self.app._server._connection_manager, 'get_socket',
                             new_callable=AsyncMock) as mock_get_socket:
            mock_get_currencies.return_value = ['BTC', 'LTC']
            mock_get_socket.return_value = AsyncMock()

            await self.app._setup_network_connections()

            # Verify connections were attempted for all currencies
            assert mock_get_socket.call_count == 2
            mock_get_socket.assert_any_call('BTC')
            mock_get_socket.assert_any_call('LTC')

    @pytest.mark.asyncio
    async def test_setup_network_connections_no_currencies(self):
        """Test network setup when no currencies are configured."""
        with patch.object(config_manager, 'get_all_currencies') as mock_get_currencies, \
                patch.object(self.app._server._connection_manager, 'get_socket',
                             new_callable=AsyncMock) as mock_get_socket:
            mock_get_currencies.return_value = []

            await self.app._setup_network_connections()

            # Verify no connections were attempted
            mock_get_socket.assert_not_called()

    @pytest.mark.asyncio
    async def test_setup_network_connections_with_failures(self):
        """Test network setup with some connection failures."""
        with patch.object(config_manager, 'get_all_currencies') as mock_get_currencies, \
                patch.object(self.app._server._connection_manager, 'get_socket',
                             new_callable=AsyncMock) as mock_get_socket:
            mock_get_currencies.return_value = ['BTC', 'LTC']
            mock_get_socket.side_effect = [AsyncMock(), NetworkError("Connection failed")]

            # Should not raise exception, just log errors
            await self.app._setup_network_connections()

            # Verify both connections were attempted
            assert mock_get_socket.call_count == 2

    def test_server_property(self):
        """Test server property access."""
        server = self.app.server
        assert server is not None
        assert server == self.app._server

    def test_heartbeat_service_property(self):
        """Test heartbeat service property access."""
        heartbeat_service = self.app.heartbeat_service
        assert heartbeat_service is not None
        assert heartbeat_service == self.app._server._heartbeat_service

    def test_connection_manager_property(self):
        """Test connection manager property access."""
        conn_manager = self.app.connection_manager
        assert conn_manager is not None
        assert conn_manager == self.app._server._connection_manager
