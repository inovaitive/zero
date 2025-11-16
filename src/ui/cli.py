"""
Command-line interface for ZERO assistant.

Provides a beautiful terminal UI using Rich library with live updates,
status display, and conversation history.
"""

from typing import Optional, List, Tuple
from datetime import datetime
import sys

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.table import Table
from rich import box
from rich.align import Align

from src.core.state import AssistantState, StateManager


class ZeroCLI:
    """
    Command-line interface for ZERO assistant.

    Provides a rich terminal UI with:
    - Header with logo and status
    - Main conversation panel
    - Status bar with current state
    - Optional debug/logs panel
    """

    def __init__(self, state_manager: StateManager, show_logs: bool = True):
        """
        Initialize CLI.

        Args:
            state_manager: State manager instance
            show_logs: Whether to show logs panel
        """
        self.console = Console()
        self.state_manager = state_manager
        self.show_logs = show_logs

        # Conversation history: [(timestamp, speaker, message)]
        self.conversation: List[Tuple[datetime, str, str]] = []

        # Log messages: [(timestamp, level, message)]
        self.logs: List[Tuple[datetime, str, str]] = []

        # Current transcription (live)
        self.current_transcription = ""

        # Layout
        self.layout = self._create_layout()

    def _create_layout(self) -> Layout:
        """
        Create Rich layout for the CLI.

        Returns:
            Layout instance
        """
        layout = Layout()

        layout.split_column(
            Layout(name="header", size=5),
            Layout(name="main"),
            Layout(name="footer", size=3)
        )

        if self.show_logs:
            layout["main"].split_row(
                Layout(name="conversation"),
                Layout(name="logs", ratio=1)
            )
        else:
            layout["main"].update(Layout(name="conversation"))

        return layout

    def _create_header(self) -> Panel:
        """
        Create header panel with logo and status.

        Returns:
            Header panel
        """
        # ASCII art logo
        logo = Text()
        logo.append("╔══════════════════════════════════════════╗\n", style="bold cyan")
        logo.append("║         Z E R O  Assistant v1.0          ║\n", style="bold cyan")
        logo.append("║     Intelligent Voice Assistant          ║\n", style="bold cyan")
        logo.append("╚══════════════════════════════════════════╝", style="bold cyan")

        return Panel(
            Align.center(logo),
            box=box.ROUNDED,
            style="cyan"
        )

    def _create_conversation_panel(self) -> Panel:
        """
        Create conversation panel with history.

        Returns:
            Conversation panel
        """
        # Create conversation table
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Time", style="dim", width=8)
        table.add_column("Speaker", width=8)
        table.add_column("Message")

        # Add recent conversation (last 10 messages)
        for timestamp, speaker, message in self.conversation[-10:]:
            time_str = timestamp.strftime("%H:%M:%S")

            if speaker == "You":
                speaker_style = "bold green"
                message_style = "green"
            else:
                speaker_style = "bold cyan"
                message_style = "cyan"

            table.add_row(
                time_str,
                Text(speaker, style=speaker_style),
                Text(message, style=message_style)
            )

        # Add current transcription if listening
        if self.state_manager.is_listening() and self.current_transcription:
            table.add_row(
                "...",
                Text("You", style="bold green"),
                Text(self.current_transcription + "...", style="dim green italic")
            )

        return Panel(
            table,
            title="[bold]Conversation",
            border_style="blue",
            box=box.ROUNDED
        )

    def _create_logs_panel(self) -> Panel:
        """
        Create logs panel with recent log messages.

        Returns:
            Logs panel
        """
        # Create logs table
        table = Table(show_header=False, box=None, padding=(0, 1))
        table.add_column("Time", style="dim", width=8)
        table.add_column("Level", width=8)
        table.add_column("Message")

        # Add recent logs (last 15)
        for timestamp, level, message in self.logs[-15:]:
            time_str = timestamp.strftime("%H:%M:%S")

            # Color based on log level
            if level == "ERROR":
                level_style = "bold red"
            elif level == "WARNING":
                level_style = "bold yellow"
            elif level == "INFO":
                level_style = "bold green"
            else:
                level_style = "dim"

            table.add_row(
                time_str,
                Text(level, style=level_style),
                Text(message, style="dim")
            )

        return Panel(
            table,
            title="[bold]Logs",
            border_style="yellow",
            box=box.ROUNDED
        )

    def _create_footer(self) -> Panel:
        """
        Create footer panel with current state and help.

        Returns:
            Footer panel
        """
        state = self.state_manager.state

        # State indicator with color
        state_colors = {
            AssistantState.IDLE: "green",
            AssistantState.LISTENING: "yellow",
            AssistantState.PROCESSING: "cyan",
            AssistantState.EXECUTING: "blue",
            AssistantState.RESPONDING: "magenta",
            AssistantState.ERROR: "red",
        }

        state_color = state_colors.get(state, "white")
        state_text = Text()
        state_text.append("● ", style=f"bold {state_color}")
        state_text.append(f"{state.name}", style=f"bold {state_color}")

        # Help text
        help_text = Text("  |  ", style="dim")
        help_text.append("Ctrl+C", style="bold")
        help_text.append(" to exit  |  ", style="dim")
        help_text.append("Say 'Jarvis' to activate", style="dim")

        footer_text = Text()
        footer_text.append(state_text)
        footer_text.append(help_text)

        return Panel(
            Align.center(footer_text),
            box=box.ROUNDED,
            style="dim"
        )

    def update(self):
        """Update the layout with current content."""
        self.layout["header"].update(self._create_header())
        self.layout["footer"].update(self._create_footer())

        if self.show_logs:
            self.layout["conversation"].update(self._create_conversation_panel())
            self.layout["logs"].update(self._create_logs_panel())
        else:
            self.layout["conversation"].update(self._create_conversation_panel())

    def add_message(self, speaker: str, message: str):
        """
        Add a message to conversation history.

        Args:
            speaker: Who is speaking ('You' or 'ZERO')
            message: Message content
        """
        self.conversation.append((datetime.now(), speaker, message))

    def add_log(self, level: str, message: str):
        """
        Add a log message.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR)
            message: Log message
        """
        self.logs.append((datetime.now(), level, message))

    def update_transcription(self, text: str):
        """
        Update current transcription (for live STT).

        Args:
            text: Current transcription text
        """
        self.current_transcription = text

    def clear(self):
        """Clear the terminal."""
        self.console.clear()

    def print(self, *args, **kwargs):
        """Print to console (for non-layout output)."""
        self.console.print(*args, **kwargs)

    def print_welcome(self):
        """Print welcome message."""
        self.console.print("\n")
        self.console.print("╔══════════════════════════════════════════╗", style="bold cyan")
        self.console.print("║         Z E R O  Assistant v1.0          ║", style="bold cyan")
        self.console.print("║     Intelligent Voice Assistant          ║", style="bold cyan")
        self.console.print("╚══════════════════════════════════════════╝", style="bold cyan")
        self.console.print("\n")
        self.console.print("✓ System initialized", style="green")
        self.console.print("✓ Listening for wake word: [bold]'Jarvis'[/bold]", style="green")
        self.console.print("\nSay [bold cyan]'Jarvis'[/bold cyan] to activate...\n", style="dim")

    def print_error(self, error: str):
        """
        Print error message.

        Args:
            error: Error message
        """
        self.console.print(f"[bold red]Error:[/bold red] {error}")

    def print_info(self, message: str):
        """
        Print info message.

        Args:
            message: Info message
        """
        self.console.print(f"[cyan]ℹ[/cyan] {message}")

    def run_live(self, update_callback: Optional[callable] = None):
        """
        Run CLI in live mode with auto-refresh.

        Args:
            update_callback: Optional callback function called on each update
        """
        with Live(self.layout, console=self.console, refresh_per_second=4) as live:
            try:
                while True:
                    self.update()
                    if update_callback:
                        update_callback()
            except KeyboardInterrupt:
                pass


def create_cli(state_manager: StateManager, show_logs: bool = True) -> ZeroCLI:
    """
    Create CLI instance.

    Args:
        state_manager: State manager instance
        show_logs: Whether to show logs panel

    Returns:
        ZeroCLI instance
    """
    return ZeroCLI(state_manager, show_logs)
