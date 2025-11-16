"""
System tray integration for ZERO assistant.

Provides a system tray icon with menu for controlling the assistant.
"""

from typing import Optional, Callable
import sys
from pathlib import Path

try:
    from pystray import Icon, Menu, MenuItem
    from PIL import Image, ImageDraw
    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False

from src.core.state import AssistantState, StateManager


class ZeroTray:
    """
    System tray integration for ZERO assistant.

    Provides a tray icon with menu for:
    - Starting/stopping the assistant
    - Opening settings
    - Viewing status
    - Exiting the application
    """

    def __init__(
        self,
        state_manager: StateManager,
        on_start: Optional[Callable] = None,
        on_stop: Optional[Callable] = None,
        on_exit: Optional[Callable] = None
    ):
        """
        Initialize system tray.

        Args:
            state_manager: State manager instance
            on_start: Callback for start action
            on_stop: Callback for stop action
            on_exit: Callback for exit action
        """
        if not TRAY_AVAILABLE:
            raise RuntimeError(
                "pystray not available. Install with: pip install pystray Pillow"
            )

        self.state_manager = state_manager
        self.on_start = on_start
        self.on_stop = on_stop
        self.on_exit = on_exit

        self.icon: Optional[Icon] = None
        self._running = False

    def _create_icon_image(self) -> Image.Image:
        """
        Create tray icon image.

        Returns:
            PIL Image for tray icon
        """
        # Create a simple icon (circle with 'Z')
        width = 64
        height = 64
        image = Image.new('RGB', (width, height), color='black')
        draw = ImageDraw.Draw(image)

        # Draw circle
        draw.ellipse([(4, 4), (width-4, height-4)], fill='#00D9FF', outline='#00A8CC')

        # Draw 'Z' (simplified)
        # Top horizontal line
        draw.line([(16, 18), (48, 18)], fill='black', width=4)
        # Diagonal
        draw.line([(48, 18), (16, 46)], fill='black', width=4)
        # Bottom horizontal line
        draw.line([(16, 46), (48, 46)], fill='black', width=4)

        return image

    def _get_menu(self) -> Menu:
        """
        Create tray menu.

        Returns:
            pystray Menu instance
        """
        return Menu(
            MenuItem(
                'ZERO Assistant',
                None,  # No action for title
                enabled=False
            ),
            Menu.SEPARATOR,
            MenuItem(
                'Status',
                self._show_status
            ),
            Menu.SEPARATOR,
            MenuItem(
                'Start Listening',
                self._handle_start,
                enabled=lambda item: not self._running,
                default=True
            ),
            MenuItem(
                'Stop Listening',
                self._handle_stop,
                enabled=lambda item: self._running
            ),
            Menu.SEPARATOR,
            MenuItem(
                'Settings',
                self._show_settings
            ),
            MenuItem(
                'About',
                self._show_about
            ),
            Menu.SEPARATOR,
            MenuItem(
                'Exit',
                self._handle_exit
            )
        )

    def _handle_start(self, icon, item):
        """Handle start action."""
        self._running = True
        if self.on_start:
            self.on_start()

    def _handle_stop(self, icon, item):
        """Handle stop action."""
        self._running = False
        if self.on_stop:
            self.on_stop()

    def _handle_exit(self, icon, item):
        """Handle exit action."""
        if self.on_exit:
            self.on_exit()
        self.stop()

    def _show_status(self, icon, item):
        """Show current status."""
        state = self.state_manager.state
        # TODO: Show notification with current status
        print(f"Current state: {state.name}")

    def _show_settings(self, icon, item):
        """Show settings dialog."""
        # TODO: Implement settings dialog
        print("Settings dialog not yet implemented")

    def _show_about(self, icon, item):
        """Show about dialog."""
        # TODO: Show about dialog
        print("ZERO Assistant v1.0\nIntelligent Voice Assistant")

    def start(self):
        """Start the system tray icon."""
        if self.icon is not None:
            return

        # Create icon
        image = self._create_icon_image()
        menu = self._get_menu()

        self.icon = Icon(
            name="ZERO",
            icon=image,
            title="ZERO Assistant",
            menu=menu
        )

        # Run in separate thread
        self.icon.run_detached()

    def stop(self):
        """Stop the system tray icon."""
        if self.icon is not None:
            self.icon.stop()
            self.icon = None

    def update_tooltip(self, text: str):
        """
        Update tray icon tooltip.

        Args:
            text: New tooltip text
        """
        if self.icon is not None:
            self.icon.title = f"ZERO - {text}"

    def show_notification(self, title: str, message: str):
        """
        Show system notification.

        Args:
            title: Notification title
            message: Notification message
        """
        if self.icon is not None:
            self.icon.notify(message, title)


def create_tray(
    state_manager: StateManager,
    on_start: Optional[Callable] = None,
    on_stop: Optional[Callable] = None,
    on_exit: Optional[Callable] = None
) -> Optional[ZeroTray]:
    """
    Create system tray instance.

    Args:
        state_manager: State manager instance
        on_start: Callback for start action
        on_stop: Callback for stop action
        on_exit: Callback for exit action

    Returns:
        ZeroTray instance, or None if pystray not available
    """
    if not TRAY_AVAILABLE:
        return None

    return ZeroTray(state_manager, on_start, on_stop, on_exit)
