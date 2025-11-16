"""
Tests for UI modules (CLI and System Tray).

Tests cover:
- CLI initialization and layout creation
- Message and log handling
- NLU debug panel
- System tray initialization and menu
- Error handling
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

# Check if rich is available
try:
    from rich.console import Console
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

try:
    from src.ui.cli import ZeroCLI, create_cli
    CLI_AVAILABLE = True
except ImportError:
    CLI_AVAILABLE = False

try:
    from src.ui.tray import ZeroTray, create_tray, TRAY_AVAILABLE
except (ImportError, NameError):
    TRAY_AVAILABLE = False
    ZeroTray = None
    create_tray = None

from src.core.state import AssistantState, StateManager


@pytest.mark.skipif(not CLI_AVAILABLE, reason="CLI module not available (rich not installed)")
class TestZeroCLI:
    """Test ZeroCLI functionality."""

    @pytest.fixture
    def state_manager(self):
        """Create a state manager for testing."""
        return StateManager()

    @pytest.fixture
    def cli(self, state_manager):
        """Create a CLI instance for testing."""
        return ZeroCLI(state_manager, show_logs=True, debug_nlu=False)

    def test_cli_initialization(self, state_manager):
        """Test CLI can be initialized."""
        cli = ZeroCLI(state_manager)
        assert cli is not None
        assert cli.state_manager == state_manager
        assert cli.show_logs is True
        assert cli.debug_nlu is False
        assert len(cli.conversation) == 0
        assert len(cli.logs) == 0

    def test_cli_initialization_with_options(self, state_manager):
        """Test CLI initialization with custom options."""
        cli = ZeroCLI(state_manager, show_logs=False, debug_nlu=True)
        assert cli.show_logs is False
        assert cli.debug_nlu is True

    def test_add_message(self, cli):
        """Test adding messages to conversation."""
        cli.add_message("You", "Hello")
        assert len(cli.conversation) == 1
        assert cli.conversation[0][1] == "You"
        assert cli.conversation[0][2] == "Hello"

        cli.add_message("ZERO", "Hi there!")
        assert len(cli.conversation) == 2
        assert cli.conversation[1][1] == "ZERO"
        assert cli.conversation[1][2] == "Hi there!"

    def test_add_log(self, cli):
        """Test adding log messages."""
        cli.add_log("INFO", "Test log message")
        assert len(cli.logs) == 1
        assert cli.logs[0][1] == "INFO"
        assert cli.logs[0][2] == "Test log message"

        cli.add_log("ERROR", "Error occurred")
        assert len(cli.logs) == 2
        assert cli.logs[1][1] == "ERROR"

    def test_update_transcription(self, cli):
        """Test updating transcription."""
        assert cli.current_transcription == ""
        cli.update_transcription("Hello world")
        assert cli.current_transcription == "Hello world"

    def test_update_nlu_debug(self, cli):
        """Test updating NLU debug information."""
        cli.update_nlu_debug(
            intent="weather.query",
            confidence=0.95,
            entities={'location': 'New York'},
            context={'current_location': 'New York'},
            method="local"
        )

        assert cli.nlu_debug['intent'] == "weather.query"
        assert cli.nlu_debug['confidence'] == 0.95
        assert cli.nlu_debug['entities']['location'] == 'New York'
        assert cli.nlu_debug['context']['current_location'] == 'New York'
        assert cli.nlu_debug['method'] == "local"

    def test_update_nlu_debug_partial(self, cli):
        """Test updating NLU debug with partial information."""
        cli.update_nlu_debug(intent="timer.set")
        assert cli.nlu_debug['intent'] == "timer.set"
        # Other fields should remain unchanged
        assert cli.nlu_debug['confidence'] == 0.0

    def test_toggle_nlu_debug(self, cli):
        """Test toggling NLU debug panel."""
        assert cli.debug_nlu is False
        cli.toggle_nlu_debug()
        assert cli.debug_nlu is True
        cli.toggle_nlu_debug()
        assert cli.debug_nlu is False

    def test_create_layout_single_column(self, state_manager):
        """Test layout creation with conversation only."""
        cli = ZeroCLI(state_manager, show_logs=False, debug_nlu=False)
        layout = cli._create_layout()
        assert layout is not None

    def test_create_layout_with_logs(self, state_manager):
        """Test layout creation with logs panel."""
        cli = ZeroCLI(state_manager, show_logs=True, debug_nlu=False)
        layout = cli._create_layout()
        assert layout is not None

    def test_create_layout_with_nlu_debug(self, state_manager):
        """Test layout creation with NLU debug panel."""
        cli = ZeroCLI(state_manager, show_logs=False, debug_nlu=True)
        layout = cli._create_layout()
        assert layout is not None

    def test_create_layout_with_both_panels(self, state_manager):
        """Test layout creation with both logs and NLU debug."""
        cli = ZeroCLI(state_manager, show_logs=True, debug_nlu=True)
        layout = cli._create_layout()
        assert layout is not None

    def test_create_header(self, cli):
        """Test header panel creation."""
        header = cli._create_header()
        assert header is not None

    def test_create_conversation_panel_empty(self, cli):
        """Test conversation panel with no messages."""
        panel = cli._create_conversation_panel()
        assert panel is not None

    def test_create_conversation_panel_with_messages(self, cli):
        """Test conversation panel with messages."""
        cli.add_message("You", "Hello")
        cli.add_message("ZERO", "Hi there!")
        panel = cli._create_conversation_panel()
        assert panel is not None

    def test_create_conversation_panel_with_transcription(self, cli, state_manager):
        """Test conversation panel with live transcription."""
        state_manager.transition_to(AssistantState.LISTENING)
        cli.update_transcription("Hello world")
        panel = cli._create_conversation_panel()
        assert panel is not None

    def test_create_logs_panel_empty(self, cli):
        """Test logs panel with no logs."""
        panel = cli._create_logs_panel()
        assert panel is not None

    def test_create_logs_panel_with_logs(self, cli):
        """Test logs panel with log messages."""
        cli.add_log("INFO", "Test message")
        cli.add_log("ERROR", "Error message")
        cli.add_log("WARNING", "Warning message")
        panel = cli._create_logs_panel()
        assert panel is not None

    def test_create_nlu_debug_panel(self, cli):
        """Test NLU debug panel creation."""
        cli.update_nlu_debug(
            intent="weather.query",
            confidence=0.95,
            entities={'location': 'New York'},
            context={'current_location': 'New York'}
        )
        panel = cli._create_nlu_debug_panel()
        assert panel is not None

    def test_create_nlu_debug_panel_empty(self, cli):
        """Test NLU debug panel with no data."""
        panel = cli._create_nlu_debug_panel()
        assert panel is not None

    def test_create_footer(self, cli):
        """Test footer panel creation."""
        footer = cli._create_footer()
        assert footer is not None

    def test_create_footer_different_states(self, cli, state_manager):
        """Test footer with different states."""
        state_manager.transition_to(AssistantState.LISTENING)
        footer1 = cli._create_footer()
        assert footer1 is not None

        state_manager.transition_to(AssistantState.PROCESSING)
        footer2 = cli._create_footer()
        assert footer2 is not None

    def test_update(self, cli):
        """Test updating the layout."""
        cli.add_message("You", "Test")
        cli.add_log("INFO", "Test log")
        cli.update()
        # Should not raise any errors

    def test_clear(self, cli):
        """Test clearing the console."""
        cli.clear()
        # Should not raise any errors

    def test_print(self, cli):
        """Test printing to console."""
        with patch.object(cli.console, 'print') as mock_print:
            cli.print("Test message")
            mock_print.assert_called_once_with("Test message")

    def test_print_welcome(self, cli):
        """Test printing welcome message."""
        with patch.object(cli.console, 'print') as mock_print:
            cli.print_welcome()
            assert mock_print.call_count > 0

    def test_print_error(self, cli):
        """Test printing error message."""
        with patch.object(cli.console, 'print') as mock_print:
            cli.print_error("Test error")
            mock_print.assert_called_once()
            call_args = str(mock_print.call_args)
            assert "Error" in call_args or "error" in call_args.lower()

    def test_print_info(self, cli):
        """Test printing info message."""
        with patch.object(cli.console, 'print') as mock_print:
            cli.print_info("Test info")
            mock_print.assert_called_once()

    @patch('src.ui.cli.Live')
    def test_run_live(self, mock_live, cli):
        """Test running CLI in live mode."""
        mock_live_instance = MagicMock()
        mock_live.return_value.__enter__ = MagicMock(return_value=mock_live_instance)
        mock_live.return_value.__exit__ = MagicMock(return_value=None)

        # Mock KeyboardInterrupt to exit loop
        def side_effect():
            raise KeyboardInterrupt()

        cli.update = MagicMock(side_effect=side_effect)

        try:
            cli.run_live()
        except KeyboardInterrupt:
            pass

        # Should have called update at least once
        assert cli.update.called

    def test_create_cli_function(self, state_manager):
        """Test create_cli factory function."""
        if CLI_AVAILABLE:
            cli = create_cli(state_manager, show_logs=True, debug_nlu=False)
            assert isinstance(cli, ZeroCLI)
            assert cli.state_manager == state_manager


@pytest.mark.skipif(not TRAY_AVAILABLE or ZeroTray is None, reason="pystray not available")
class TestZeroTray:
    """Test ZeroTray functionality."""

    @pytest.fixture
    def state_manager(self):
        """Create a state manager for testing."""
        return StateManager()

    def test_tray_initialization(self, state_manager):
        """Test tray can be initialized."""
        tray = ZeroTray(state_manager)
        assert tray is not None
        assert tray.state_manager == state_manager
        assert tray._running is False

    @pytest.mark.skipif(not TRAY_AVAILABLE, reason="pystray not available")
    def test_tray_initialization_with_callbacks(self, state_manager):
        """Test tray initialization with callbacks."""
        on_start = Mock()
        on_stop = Mock()
        on_exit = Mock()

        tray = ZeroTray(state_manager, on_start=on_start, on_stop=on_stop, on_exit=on_exit)
        assert tray.on_start == on_start
        assert tray.on_stop == on_stop
        assert tray.on_exit == on_exit

    @pytest.mark.skipif(not TRAY_AVAILABLE, reason="pystray not available")
    def test_create_icon_image(self, state_manager):
        """Test icon image creation."""
        tray = ZeroTray(state_manager)
        image = tray._create_icon_image()
        assert image is not None
        assert image.size == (64, 64)

    @pytest.mark.skipif(not TRAY_AVAILABLE, reason="pystray not available")
    def test_get_menu(self, state_manager):
        """Test menu creation."""
        tray = ZeroTray(state_manager)
        menu = tray._get_menu()
        assert menu is not None

    @pytest.mark.skipif(not TRAY_AVAILABLE, reason="pystray not available")
    def test_handle_start(self, state_manager):
        """Test start handler."""
        on_start = Mock()
        tray = ZeroTray(state_manager, on_start=on_start)
        tray._handle_start(None, None)
        assert tray._running is True
        on_start.assert_called_once()

    @pytest.mark.skipif(not TRAY_AVAILABLE, reason="pystray not available")
    def test_handle_stop(self, state_manager):
        """Test stop handler."""
        on_stop = Mock()
        tray = ZeroTray(state_manager, on_stop=on_stop)
        tray._running = True
        tray._handle_stop(None, None)
        assert tray._running is False
        on_stop.assert_called_once()

    @pytest.mark.skipif(not TRAY_AVAILABLE, reason="pystray not available")
    def test_handle_exit(self, state_manager):
        """Test exit handler."""
        on_exit = Mock()
        tray = ZeroTray(state_manager, on_exit=on_exit)
        with patch.object(tray, 'stop'):
            tray._handle_exit(None, None)
            on_exit.assert_called_once()

    @pytest.mark.skipif(not TRAY_AVAILABLE, reason="pystray not available")
    def test_show_status(self, state_manager):
        """Test show status handler."""
        tray = ZeroTray(state_manager)
        with patch('builtins.print') as mock_print:
            tray._show_status(None, None)
            mock_print.assert_called_once()

    @pytest.mark.skipif(not TRAY_AVAILABLE, reason="pystray not available")
    def test_show_settings(self, state_manager):
        """Test show settings handler."""
        tray = ZeroTray(state_manager)
        with patch('builtins.print') as mock_print:
            tray._show_settings(None, None)
            mock_print.assert_called_once()

    @pytest.mark.skipif(not TRAY_AVAILABLE, reason="pystray not available")
    def test_show_about(self, state_manager):
        """Test show about handler."""
        tray = ZeroTray(state_manager)
        with patch('builtins.print') as mock_print:
            tray._show_about(None, None)
            mock_print.assert_called_once()

    @pytest.mark.skipif(not TRAY_AVAILABLE, reason="pystray not available")
    def test_start(self, state_manager):
        """Test starting the tray."""
        tray = ZeroTray(state_manager)
        with patch('src.ui.tray.Icon') as mock_icon_class:
            mock_icon = MagicMock()
            mock_icon_class.return_value = mock_icon
            tray.start()
            assert tray.icon is not None

    @pytest.mark.skipif(not TRAY_AVAILABLE, reason="pystray not available")
    def test_start_already_started(self, state_manager):
        """Test starting tray when already started."""
        tray = ZeroTray(state_manager)
        mock_icon = MagicMock()
        tray.icon = mock_icon
        tray.start()
        # Should return early without creating new icon

    @pytest.mark.skipif(not TRAY_AVAILABLE, reason="pystray not available")
    def test_stop(self, state_manager):
        """Test stopping the tray."""
        tray = ZeroTray(state_manager)
        mock_icon = MagicMock()
        tray.icon = mock_icon
        tray.stop()
        mock_icon.stop.assert_called_once()
        assert tray.icon is None

    @pytest.mark.skipif(not TRAY_AVAILABLE, reason="pystray not available")
    def test_update_tooltip(self, state_manager):
        """Test updating tooltip."""
        tray = ZeroTray(state_manager)
        mock_icon = MagicMock()
        tray.icon = mock_icon
        tray.update_tooltip("Test status")
        assert mock_icon.title == "ZERO - Test status"

    @pytest.mark.skipif(not TRAY_AVAILABLE, reason="pystray not available")
    def test_update_tooltip_no_icon(self, state_manager):
        """Test updating tooltip when icon not started."""
        tray = ZeroTray(state_manager)
        # Should not raise error
        tray.update_tooltip("Test status")

    @pytest.mark.skipif(not TRAY_AVAILABLE, reason="pystray not available")
    def test_show_notification(self, state_manager):
        """Test showing notification."""
        tray = ZeroTray(state_manager)
        mock_icon = MagicMock()
        tray.icon = mock_icon
        tray.show_notification("Title", "Message")
        mock_icon.notify.assert_called_once_with("Message", "Title")

    @pytest.mark.skipif(not TRAY_AVAILABLE, reason="pystray not available")
    def test_show_notification_no_icon(self, state_manager):
        """Test showing notification when icon not started."""
        tray = ZeroTray(state_manager)
        # Should not raise error
        tray.show_notification("Title", "Message")

    def test_tray_not_available(self, state_manager):
        """Test tray creation when pystray not available."""
        with patch('src.ui.tray.TRAY_AVAILABLE', False):
            with pytest.raises(RuntimeError):
                ZeroTray(state_manager)

    def test_create_tray_function(self, state_manager):
        """Test create_tray factory function."""
        if TRAY_AVAILABLE:
            tray = create_tray(state_manager)
            assert isinstance(tray, ZeroTray)
        else:
            tray = create_tray(state_manager)
            assert tray is None

    def test_create_tray_function_not_available(self, state_manager):
        """Test create_tray when pystray not available."""
        with patch('src.ui.tray.TRAY_AVAILABLE', False):
            tray = create_tray(state_manager)
            assert tray is None

