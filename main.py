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

        # Initialize NLU components
        self.intent_classifier = None
        self.entity_extractor = None
        self.context_manager = None
        self.llm_client = None

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
        self.logger.info(f"NLU Debug Mode: {self.debug_nlu}")

        # Initialize NLU components
        self._initialize_nlu()

        # TODO: Initialize audio components
        # TODO: Initialize skills

        self.logger.info("ZERO assistant ready!")

    def _initialize_nlu(self):
        """Initialize NLU (Natural Language Understanding) components."""
        from src.brain.intent import create_intent_classifier
        from src.brain.entities import create_entity_extractor
        from src.brain.context import create_context_manager
        from src.brain.llm import create_llm_client

        self.logger.info("Initializing NLU components...")

        # Create intent classifier
        self.intent_classifier = create_intent_classifier(self.config.data)
        self.logger.info("Intent classifier initialized")

        # Create entity extractor
        self.entity_extractor = create_entity_extractor(self.config.data)
        self.logger.info("Entity extractor initialized")

        # Create context manager
        self.context_manager = create_context_manager(self.config.data)
        self.logger.info("Context manager initialized")

        # Create LLM client (optional, only if configured)
        self.llm_client = create_llm_client(self.config.data)
        if self.llm_client:
            self.logger.info("LLM client initialized")
        else:
            self.logger.info("LLM client disabled (no API key or disabled in config)")

        self.logger.info("NLU components ready")

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

                # Add to conversation
                if self.cli:
                    self.cli.add_message("You", user_input)

                # Process command through NLU
                response = self._process_nlu_command(user_input)

                if self.cli:
                    self.cli.add_message("ZERO", response)

                print(f"ZERO: {response}")

        except KeyboardInterrupt:
            pass

    def _process_nlu_command(self, user_input: str) -> str:
        """
        Process user command through NLU pipeline.

        Args:
            user_input: User's text input

        Returns:
            Response string
        """
        # Classify intent
        intent_result = self.intent_classifier.classify(user_input)
        self.logger.debug(f"Intent: {intent_result.intent.value} ({intent_result.confidence:.2f})")

        # Extract entities
        entity_result = self.entity_extractor.extract(user_input, intent_result.intent.value)
        entities_dict = {e.entity_type: e.value for e in entity_result.entities}
        self.logger.debug(f"Entities: {entities_dict}")

        # Get context
        context = self.context_manager.get_context_for_query(user_input)
        self.logger.debug(f"Context: {context}")

        # Update CLI debug panel if enabled
        if self.cli and self.debug_nlu:
            self.cli.update_nlu_debug(
                intent=intent_result.intent.value,
                confidence=intent_result.confidence,
                entities=entities_dict,
                context=context,
                method=intent_result.method
            )

        # Generate response based on intent
        response = self._generate_response(intent_result, entity_result, context)

        # Update context with this interaction
        self.context_manager.update(
            user_input=user_input,
            intent=intent_result.intent.value,
            entities=entities_dict,
            response=response
        )

        return response

    def _generate_response(self, intent_result, entity_result, context) -> str:
        """
        Generate response based on intent and entities.

        Args:
            intent_result: Intent classification result
            entity_result: Entity extraction result
            context: Current context

        Returns:
            Response string
        """
        intent = intent_result.intent.value

        # Handle different intents
        if intent.startswith("weather."):
            location = entity_result.get_entity('location')
            if location:
                return f"I would check the weather in {location.value}, but the weather skill is not yet implemented."
            elif 'implied_location' in context:
                return f"I would check the weather in {context['implied_location']}, but the weather skill is not yet implemented."
            else:
                return "I would check the weather, but I need a location. Where would you like to know about?"

        elif intent.startswith("timer."):
            if intent == "timer.set":
                duration = entity_result.get_entity('duration')
                if duration:
                    minutes = duration.value // 60
                    seconds = duration.value % 60
                    return f"I would set a timer for {minutes}m {seconds}s, but the timer skill is not yet implemented."
                else:
                    return "I would set a timer, but I need a duration. How long should it be?"
            elif intent == "timer.cancel":
                return "I would cancel the timer, but the timer skill is not yet implemented."
            elif intent == "timer.list":
                return "I would list active timers, but the timer skill is not yet implemented."

        elif intent.startswith("app."):
            app_name = entity_result.get_entity('app_name')
            if intent == "app.open":
                if app_name:
                    return f"I would open {app_name.value}, but the app control skill is not yet implemented."
                else:
                    return "I would open an app, but which one would you like?"
            elif intent == "app.close":
                if app_name:
                    return f"I would close {app_name.value}, but the app control skill is not yet implemented."
                else:
                    return "I would close an app, but which one?"

        elif intent == "search.web":
            return "I would search the web, but the search skill is not yet implemented."

        elif intent.startswith("smalltalk."):
            if intent == "smalltalk.greeting":
                return "Good day, sir. How may I assist you today?"
            elif intent == "smalltalk.thanks":
                return "You're most welcome, sir."
            elif intent == "smalltalk.farewell":
                return "Farewell, sir. Until next time."
            elif intent == "smalltalk.question":
                return "I am ZERO, your personal AI assistant. I'm functioning normally and ready to assist."
            elif intent == "smalltalk.help":
                return ("I can help you with weather queries, timers, app control, web searches, and general conversation. "
                       "Try asking me about the weather, setting a timer, or opening an app.")

        # Default/unknown
        return f"I understood your intent as '{intent}', but I'm not sure how to help with that yet. Skills are still being implemented."

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
