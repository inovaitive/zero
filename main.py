#!/usr/bin/env python3
"""
ZERO Voice Assistant - Main Entry Point

A J.A.R.V.I.S.-inspired intelligent voice assistant.
"""

import argparse
import signal
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.config import ConfigError, get_config
from src.core.logger import setup_logger
from src.core.state import AssistantState, get_state_manager
from src.ui.cli import create_cli
from src.ui.tray import TRAY_AVAILABLE, create_tray


class ZeroAssistant:
    """
    Main ZERO assistant application.

    Coordinates all components and manages the application lifecycle.
    """

    def __init__(self, config_path: str = None, cli_only: bool = False):
        """
        Initialize ZERO assistant.

        Args:
            config_path: Path to configuration file
            cli_only: Whether to run in CLI-only mode (no voice)
        """
        # Load configuration
        try:
            self.config = get_config(config_path)
        except ConfigError as e:
            print(f"Configuration Error: {e}")
            sys.exit(1)

        # Set up logging
        self.logger = setup_logger(
            name="zero", log_level=self.config.log_level, console_output=True, file_output=True
        )

        self.logger.info("=" * 60)
        self.logger.info("ZERO Assistant Starting...")
        self.logger.info("=" * 60)

        # Initialize state manager
        self.state_manager = get_state_manager()

        # CLI mode flag
        self.cli_only = cli_only

        # Initialize UI components
        self.cli = None
        self.tray = None

        # Set up signal handlers
        signal.signal(signal.SIGINT, self._handle_shutdown)
        signal.signal(signal.SIGTERM, self._handle_shutdown)

    def _handle_shutdown(self, signum, frame):
        """Handle shutdown signals."""
        self.logger.info("Shutdown signal received")
        self.shutdown()
        sys.exit(0)

    def _initialize_ui(self):
        """Initialize user interface components."""
        # Create CLI
        show_logs = self.config.get("ui.cli.show_logs", True)
        self.cli = create_cli(self.state_manager, show_logs=show_logs)

        # Create system tray (if enabled and available)
        if self.config.get("ui.tray.enabled", True) and TRAY_AVAILABLE:
            self.tray = create_tray(
                self.state_manager,
                on_start=self._handle_start,
                on_stop=self._handle_stop,
                on_exit=self._handle_exit,
            )

    def _handle_start(self):
        """Handle start command from tray."""
        self.logger.info("Start command received from tray")
        # TODO: Implement start logic

    def _handle_stop(self):
        """Handle stop command from tray."""
        self.logger.info("Stop command received from tray")
        # TODO: Implement stop logic

    def _handle_exit(self):
        """Handle exit command from tray."""
        self.logger.info("Exit command received from tray")
        self.shutdown()
        sys.exit(0)

    def start(self):
        """Start the ZERO assistant."""
        self.logger.info("Initializing ZERO assistant...")

        # Initialize UI
        self._initialize_ui()

        # Start system tray (if available)
        if self.tray is not None:
            self.tray.start()
            self.logger.info("System tray initialized")

        # Show welcome message
        if self.cli:
            self.cli.clear()
            self.cli.print_welcome()

        # Log configuration summary
        self.logger.info(f"Assistant Name: {self.config.assistant_name}")
        self.logger.info(f"Log Level: {self.config.log_level}")
        self.logger.info(f"CLI Only Mode: {self.cli_only}")

        # TODO: Initialize audio components
        # TODO: Initialize NLU components
        # TODO: Initialize skills

        self.logger.info("ZERO assistant ready!")

        if self.cli_only:
            self._run_cli_mode()
        else:
            self._run_voice_mode()

    def _run_cli_mode(self):
        """Run in CLI-only mode (text input)."""
        self.logger.info("Running in CLI-only mode")

        if self.cli:
            self.cli.print_info("Running in CLI-only mode (no voice)")
            self.cli.print_info("Type 'exit' to quit, 'help' for commands")

        try:
            while True:
                # Get user input
                user_input = input("\nYou: ").strip()

                if not user_input:
                    continue

                if user_input.lower() in ["exit", "quit"]:
                    break

                if user_input.lower() == "help":
                    self._print_help()
                    continue

                # Add to conversation
                if self.cli:
                    self.cli.add_message("You", user_input)

                # TODO: Process command through NLU
                # For now, just echo
                response = f"I heard you say: {user_input}"

                if self.cli:
                    self.cli.add_message("ZERO", response)

                print(f"ZERO: {response}")

        except KeyboardInterrupt:
            pass

    def _run_voice_mode(self):
        """Run in voice mode (wake word + STT)."""
        self.logger.info("Running in voice mode")

        if self.cli:
            self.cli.add_log("INFO", "Voice mode initialized")

        try:
            # TODO: Start wake word detection
            # TODO: Start main event loop

            # For now, just keep running
            import time

            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            pass

    def _print_help(self):
        """Print help message."""
        help_text = """
Available Commands:
  help    - Show this help message
  exit    - Exit the assistant
  quit    - Exit the assistant
  status  - Show current status
  config  - Show configuration
        """
        print(help_text)

    def shutdown(self):
        """Shutdown the ZERO assistant."""
        self.logger.info("Shutting down ZERO assistant...")

        # Transition to shutdown state
        self.state_manager.transition_to(AssistantState.SHUTDOWN)

        # Stop system tray
        if self.tray:
            self.tray.stop()

        # TODO: Stop all audio components
        # TODO: Save any persistent state
        # TODO: Close all resources

        self.logger.info("ZERO assistant shutdown complete")

    def run(self):
        """Run the ZERO assistant (convenience method)."""
        try:
            self.start()
        except Exception as e:
            self.logger.error(f"Fatal error: {e}", exc_info=True)
            self.shutdown()
            sys.exit(1)


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="ZERO - Intelligent Voice Assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--config",
        type=str,
        metavar="PATH",
        help="Path to configuration file (default: config/config.yaml)",
    )

    parser.add_argument(
        "--cli-only", action="store_true", help="Run in CLI-only mode (text input, no voice)"
    )

    parser.add_argument("--debug", action="store_true", help="Enable debug mode")

    parser.add_argument("--version", action="version", version="ZERO Assistant v1.0.0")

    return parser.parse_args()


def main():
    """Main entry point."""
    # Parse arguments
    args = parse_args()

    # Create and run assistant
    assistant = ZeroAssistant(config_path=args.config, cli_only=args.cli_only)

    assistant.run()


if __name__ == "__main__":
    main()
