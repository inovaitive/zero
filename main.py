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
from src.core.engine import create_engine, ZeroEngine
from src.ui.cli import create_cli
from src.ui.tray import TRAY_AVAILABLE, create_tray


class ZeroAssistant:
    """
    Main ZERO assistant application.

    Coordinates all components and manages the application lifecycle.
    """

    def __init__(self, config_path: str = None, cli_only: bool = False, debug_nlu: bool = False):
        """
        Initialize ZERO assistant.

        Args:
            config_path: Path to configuration file
            cli_only: Whether to run in CLI-only mode (no voice)
            debug_nlu: Whether to enable NLU debug mode
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
        self.debug_nlu = debug_nlu

        # Initialize UI components
        self.cli = None
        self.tray = None

        # Initialize engine
        self.engine: Optional[ZeroEngine] = None

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
        self.cli = create_cli(self.state_manager, show_logs=show_logs, debug_nlu=self.debug_nlu)

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
        if self.engine and not self.engine.is_running():
            self.engine.start()
            self.logger.info("Engine started via tray")
        else:
            self.logger.warning("Engine already running or not initialized")

    def _handle_stop(self):
        """Handle stop command from tray."""
        self.logger.info("Stop command received from tray")
        if self.engine and self.engine.is_running():
            self.engine.stop()
            self.logger.info("Engine stopped via tray")
        else:
            self.logger.warning("Engine not running or not initialized")

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
        self.logger.info(f"NLU Debug Mode: {self.debug_nlu}")

        # Initialize engine
        self._initialize_engine()

        self.logger.info("ZERO assistant ready!")

        # Run appropriate mode
        if self.cli_only:
            self._run_cli_mode()
        else:
            self._run_voice_mode()

    def _initialize_engine(self):
        """Initialize the main ZERO engine."""
        self.logger.info("Initializing ZERO engine...")

        # Create engine
        self.engine = create_engine(
            config=self.config,
            state_manager=self.state_manager
        )

        # Initialize all components (NLU, skills, audio)
        self.engine.initialize_components()

        # Set up engine callbacks for UI updates
        self.engine.set_callbacks(
            on_wake_word=self._on_wake_word,
            on_listening_start=self._on_listening_start,
            on_listening_stop=self._on_listening_stop,
            on_processing=self._on_processing,
            on_response=self._on_response,
            on_error=self._on_error
        )

        self.logger.info("ZERO engine ready")

    def _on_wake_word(self):
        """Callback when wake word is detected."""
        self.logger.info("Wake word detected!")
        if self.cli:
            self.cli.add_log("INFO", "Wake word detected")

    def _on_listening_start(self):
        """Callback when listening starts."""
        self.logger.info("Listening started")
        if self.cli:
            self.cli.add_log("INFO", "Listening...")

    def _on_listening_stop(self):
        """Callback when listening stops."""
        self.logger.info("Listening stopped")
        if self.cli:
            self.cli.add_log("INFO", "Processing...")

    def _on_processing(self, text: str):
        """Callback when processing text."""
        self.logger.info(f"Processing: {text}")
        if self.cli:
            self.cli.add_message("You", text)

    def _on_response(self, text: str):
        """Callback when response is ready."""
        self.logger.info(f"Response: {text}")
        if self.cli:
            self.cli.add_message("ZERO", text)

    def _on_error(self, error: str):
        """Callback when error occurs."""
        self.logger.error(f"Error: {error}")
        if self.cli:
            self.cli.add_log("ERROR", error)

    def _run_cli_mode(self):
        """Run in CLI-only mode (text input)."""
        self.logger.info("Running in CLI-only mode")

        if self.cli:
            self.cli.print_info("Running in CLI-only mode (no voice)")
            self.cli.print_info("Type 'exit' to quit, 'help' for commands")
            if self.debug_nlu:
                self.cli.print_info("NLU debug mode enabled - watch the debug panel!")

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

                if user_input.lower() == "status":
                    self._print_status()
                    continue

                # Process command through engine
                result = self.engine.process_text_command(user_input)

                # Update CLI with NLU debug info
                if self.cli and self.debug_nlu:
                    self.cli.update_nlu_debug(
                        intent=result.intent,
                        confidence=result.skill_response.data.get('confidence', 0.0) if result.skill_response else 0.0,
                        entities=result.entities or {},
                        context=result.context or {},
                        method="engine"
                    )

                # Display response
                if result.success:
                    print(f"ZERO: {result.response_text}")
                    self.logger.info(f"Latency: {result.latency_ms:.0f}ms")
                else:
                    print(f"ZERO (Error): {result.response_text}")

        except KeyboardInterrupt:
            pass

    def _print_status(self):
        """Print current status."""
        if not self.engine:
            print("Engine not initialized")
            return

        status = self.engine.get_status()
        print("\n=== ZERO Status ===")
        print(f"Running: {status['running']}")
        print(f"State: {status['state']}")
        print(f"Skills Loaded: {status['skills_loaded']}")
        print("\nComponents:")
        for component, loaded in status['components'].items():
            status_icon = "✓" if loaded else "✗"
            print(f"  {status_icon} {component}")
        print("==================\n")

    def _run_voice_mode(self):
        """Run in voice mode (wake word + STT)."""
        self.logger.info("Running in voice mode")

        if self.cli:
            self.cli.add_log("INFO", "Voice mode initialized")
            self.cli.print_info("Voice mode not fully implemented yet")
            self.cli.print_info("Audio components (wake word, STT, TTS) pending")
            self.cli.print_info("Use --cli-only mode for testing")

        try:
            # Start engine event loop
            self.engine.start()

            # Keep main thread alive
            import time
            while self.engine.is_running():
                time.sleep(0.5)

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

Example Queries:
  "What's the weather in New York?"
  "Set a timer for 5 minutes"
  "Tell me about yourself"
  "Thank you"
        """
        print(help_text)

    def shutdown(self):
        """Shutdown the ZERO assistant."""
        self.logger.info("Shutting down ZERO assistant...")

        # Transition to shutdown state
        self.state_manager.transition_to(AssistantState.SHUTDOWN)

        # Stop engine
        if self.engine and self.engine.is_running():
            self.engine.stop()

        # Stop system tray
        if self.tray:
            self.tray.stop()

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

    parser.add_argument(
        "--debug-nlu",
        action="store_true",
        help="Enable NLU debug mode (show intent, entities, context)"
    )

    parser.add_argument("--version", action="version", version="ZERO Assistant v1.0.0")

    return parser.parse_args()


def main():
    """Main entry point."""
    # Parse arguments
    args = parse_args()

    # Create and run assistant
    assistant = ZeroAssistant(
        config_path=args.config,
        cli_only=args.cli_only,
        debug_nlu=args.debug_nlu
    )

    assistant.run()


if __name__ == "__main__":
    main()
