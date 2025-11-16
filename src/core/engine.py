"""
Main Engine for ZERO Assistant.

This module implements the core event loop that orchestrates all components:
- Audio pipeline (wake word, STT, TTS)
- Natural language understanding (intent, entities)
- Skill execution
- State management
- Error handling
"""

import logging
import threading
import time
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass

from src.core.state import AssistantState, StateManager, get_state_manager
from src.core.config import Config
from src.skills.skill_manager import SkillManager
from src.skills.base_skill import SkillResponse
from src.brain.intent import IntentClassifier
from src.brain.entities import EntityExtractor
from src.brain.context import ContextManager

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Result from processing a user query through the pipeline."""

    success: bool
    user_input: str
    intent: Optional[str] = None
    entities: Optional[Dict[str, Any]] = None
    context: Optional[Dict[str, Any]] = None
    skill_response: Optional[SkillResponse] = None
    response_text: Optional[str] = None
    error: Optional[str] = None
    latency_ms: Optional[float] = None


class ZeroEngine:
    """
    Main engine for ZERO assistant.

    Orchestrates the complete pipeline:
    1. IDLE → Wake word detected
    2. LISTENING → Record audio until silence
    3. PROCESSING → STT → NLU → Skill routing
    4. EXECUTING → Skill execution
    5. RESPONDING → TTS → Audio output
    6. Return to IDLE
    """

    def __init__(
        self,
        config: Config,
        state_manager: Optional[StateManager] = None,
        intent_classifier: Optional[IntentClassifier] = None,
        entity_extractor: Optional[EntityExtractor] = None,
        context_manager: Optional[ContextManager] = None,
        skill_manager: Optional[SkillManager] = None,
    ):
        """
        Initialize the ZERO engine.

        Args:
            config: Configuration instance
            state_manager: State manager (created if not provided)
            intent_classifier: Intent classifier instance
            entity_extractor: Entity extractor instance
            context_manager: Context manager instance
            skill_manager: Skill manager instance
        """
        self.config = config
        self.state_manager = state_manager or get_state_manager()

        # NLU components
        self.intent_classifier = intent_classifier
        self.entity_extractor = entity_extractor
        self.context_manager = context_manager

        # Skills
        self.skill_manager = skill_manager

        # Audio components (to be initialized)
        self.wake_word_detector = None
        self.stt_engine = None
        self.tts_engine = None
        self.audio_io = None

        # Threading
        self._running = False
        self._event_loop_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()

        # Callbacks for UI updates
        self._on_wake_word: Optional[Callable] = None
        self._on_listening_start: Optional[Callable] = None
        self._on_listening_stop: Optional[Callable] = None
        self._on_processing: Optional[Callable[[str], None]] = None
        self._on_response: Optional[Callable[[str], None]] = None
        self._on_error: Optional[Callable[[str], None]] = None

        logger.info("ZERO engine initialized")

    def set_callbacks(
        self,
        on_wake_word: Optional[Callable] = None,
        on_listening_start: Optional[Callable] = None,
        on_listening_stop: Optional[Callable] = None,
        on_processing: Optional[Callable[[str], None]] = None,
        on_response: Optional[Callable[[str], None]] = None,
        on_error: Optional[Callable[[str], None]] = None,
    ):
        """
        Set callback functions for UI updates.

        Args:
            on_wake_word: Called when wake word is detected
            on_listening_start: Called when listening starts
            on_listening_stop: Called when listening stops
            on_processing: Called with transcribed text
            on_response: Called with response text
            on_error: Called with error message
        """
        self._on_wake_word = on_wake_word
        self._on_listening_start = on_listening_start
        self._on_listening_stop = on_listening_stop
        self._on_processing = on_processing
        self._on_response = on_response
        self._on_error = on_error

    def initialize_components(self):
        """Initialize all engine components."""
        logger.info("Initializing engine components...")

        # Initialize audio components
        self._initialize_audio()

        # Initialize NLU components (if not provided)
        if not self.intent_classifier:
            from src.brain.intent import create_intent_classifier
            self.intent_classifier = create_intent_classifier(self.config.get_all())
            logger.info("Intent classifier initialized")

        if not self.entity_extractor:
            from src.brain.entities import create_entity_extractor
            self.entity_extractor = create_entity_extractor(self.config.get_all())
            logger.info("Entity extractor initialized")

        if not self.context_manager:
            from src.brain.context import create_context_manager
            self.context_manager = create_context_manager(self.config.get_all())
            logger.info("Context manager initialized")

        # Initialize skills (if not provided)
        if not self.skill_manager:
            self.skill_manager = SkillManager(config=self.config.get_all(), auto_discover=True)
            logger.info(f"Skill manager initialized with {len(self.skill_manager.skills)} skills")

        logger.info("All components initialized successfully")

    def _initialize_audio(self):
        """Initialize audio components (wake word, STT, TTS)."""
        # TODO: Initialize wake word detector
        # from src.audio.wake_word import create_wake_word_detector
        # self.wake_word_detector = create_wake_word_detector(self.config)

        # TODO: Initialize STT engine
        # from src.audio.stt import create_stt_engine
        # self.stt_engine = create_stt_engine(self.config)

        # TODO: Initialize TTS engine
        # from src.audio.tts import create_tts_engine
        # self.tts_engine = create_tts_engine(self.config)

        # TODO: Initialize audio I/O
        # from src.audio.audio_io import create_audio_io
        # self.audio_io = create_audio_io(self.config)

        logger.info("Audio components initialized (placeholder - full implementation pending)")

    def start(self):
        """Start the engine and begin event loop."""
        if self._running:
            logger.warning("Engine already running")
            return

        logger.info("Starting ZERO engine...")
        self._running = True
        self._shutdown_event.clear()

        # Start event loop in separate thread
        self._event_loop_thread = threading.Thread(
            target=self._event_loop,
            name="ZeroEngine-EventLoop",
            daemon=True
        )
        self._event_loop_thread.start()

        logger.info("ZERO engine started")

    def stop(self):
        """Stop the engine and cleanup resources."""
        if not self._running:
            return

        logger.info("Stopping ZERO engine...")
        self._running = False
        self._shutdown_event.set()

        # Wait for event loop to finish
        if self._event_loop_thread:
            self._event_loop_thread.join(timeout=5.0)

        # Cleanup components
        self._cleanup_components()

        logger.info("ZERO engine stopped")

    def _cleanup_components(self):
        """Cleanup all components."""
        # TODO: Cleanup audio components
        # if self.wake_word_detector:
        #     self.wake_word_detector.stop()
        # if self.stt_engine:
        #     self.stt_engine.cleanup()
        # if self.tts_engine:
        #     self.tts_engine.cleanup()
        # if self.audio_io:
        #     self.audio_io.close()

        logger.info("Components cleaned up")

    def _event_loop(self):
        """
        Main event loop.

        Continuously monitors for wake word and processes commands.
        """
        logger.info("Event loop started")

        try:
            while self._running and not self._shutdown_event.is_set():
                # State: IDLE - waiting for wake word
                self.state_manager.transition_to(AssistantState.IDLE)

                # Wait for wake word
                # TODO: Implement actual wake word detection
                # For now, just sleep to prevent CPU spinning
                time.sleep(0.1)

                # Check for shutdown
                if not self._running or self._shutdown_event.is_set():
                    break

        except Exception as e:
            logger.error(f"Event loop error: {e}", exc_info=True)
            self.state_manager.transition_to(AssistantState.ERROR)
            if self._on_error:
                self._on_error(str(e))
        finally:
            logger.info("Event loop stopped")

    def process_text_command(self, user_input: str) -> PipelineResult:
        """
        Process a text command through the full pipeline (for CLI mode).

        This bypasses audio components and processes text directly.

        Args:
            user_input: User's text input

        Returns:
            PipelineResult with processing results
        """
        start_time = time.time()

        try:
            # State: PROCESSING
            self.state_manager.transition_to(AssistantState.PROCESSING)

            # Call processing callback
            if self._on_processing:
                self._on_processing(user_input)

            # Step 1: Classify intent
            logger.debug(f"Classifying intent for: {user_input}")
            intent_result = self.intent_classifier.classify(user_input)
            intent = intent_result.intent.value
            confidence = intent_result.confidence

            logger.info(f"Intent: {intent} (confidence: {confidence:.2f}, method: {intent_result.method})")

            # Step 2: Extract entities
            logger.debug("Extracting entities...")
            entity_result = self.entity_extractor.extract(user_input, intent)
            entities = {e.entity_type: e.value for e in entity_result.entities}

            logger.info(f"Entities: {entities}")

            # Step 3: Get context
            context = self.context_manager.get_context_for_query(user_input)
            logger.debug(f"Context: {context}")

            # State: EXECUTING
            self.state_manager.transition_to(AssistantState.EXECUTING)

            # Step 4: Execute skill
            logger.debug(f"Routing to skill manager...")
            skill_response = self.skill_manager.route_intent(
                intent=intent,
                entities=entities,
                context=context
            )

            logger.info(f"Skill executed: {skill_response.message}")

            # Step 5: Update context
            self.context_manager.update(
                user_input=user_input,
                intent=intent,
                entities=entities,
                response=skill_response.message
            )

            # Apply any context updates from skill
            if skill_response.context_update:
                for key, value in skill_response.context_update.items():
                    # Use set_preference for context updates (preferences or other context data)
                    self.context_manager.set_preference(key, value)

            # State: RESPONDING
            self.state_manager.transition_to(AssistantState.RESPONDING)

            # Call response callback
            if self._on_response:
                self._on_response(skill_response.message)

            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000

            # Return to IDLE
            self.state_manager.transition_to(AssistantState.IDLE)

            return PipelineResult(
                success=True,
                user_input=user_input,
                intent=intent,
                entities=entities,
                context=context,
                skill_response=skill_response,
                response_text=skill_response.message,
                latency_ms=latency_ms
            )

        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            self.state_manager.transition_to(AssistantState.ERROR)

            error_msg = f"I encountered an error: {str(e)}"
            if self._on_error:
                self._on_error(error_msg)

            # Return to IDLE after error
            self.state_manager.transition_to(AssistantState.IDLE)

            return PipelineResult(
                success=False,
                user_input=user_input,
                error=str(e),
                response_text=error_msg,
                latency_ms=(time.time() - start_time) * 1000
            )

    def process_voice_command(self, audio_data: bytes) -> PipelineResult:
        """
        Process a voice command through the full pipeline.

        This includes STT → NLU → Skills → TTS

        Args:
            audio_data: Raw audio bytes

        Returns:
            PipelineResult with processing results
        """
        start_time = time.time()

        try:
            # State: PROCESSING (STT)
            self.state_manager.transition_to(AssistantState.PROCESSING)

            # Step 1: Convert speech to text
            # TODO: Implement STT
            # transcription = self.stt_engine.transcribe(audio_data)
            transcription = "[STT not yet implemented]"

            logger.info(f"Transcription: {transcription}")

            # Process as text command
            result = self.process_text_command(transcription)

            # Step 2: Convert response to speech
            if result.success and result.response_text:
                # State: RESPONDING (TTS)
                self.state_manager.transition_to(AssistantState.RESPONDING)

                # TODO: Implement TTS
                # audio_response = self.tts_engine.synthesize(result.response_text)
                # self.audio_io.play(audio_response)

                logger.info("Response synthesized and played (placeholder)")

            return result

        except Exception as e:
            logger.error(f"Voice pipeline error: {e}", exc_info=True)
            self.state_manager.transition_to(AssistantState.ERROR)

            return PipelineResult(
                success=False,
                user_input="[voice input]",
                error=str(e),
                response_text=f"Voice processing error: {str(e)}",
                latency_ms=(time.time() - start_time) * 1000
            )

    def is_running(self) -> bool:
        """Check if engine is running."""
        return self._running

    def get_status(self) -> Dict[str, Any]:
        """
        Get current engine status.

        Returns:
            Status dictionary
        """
        return {
            'running': self._running,
            'state': self.state_manager.state.name,
            'skills_loaded': len(self.skill_manager.skills) if self.skill_manager else 0,
            'components': {
                'intent_classifier': self.intent_classifier is not None,
                'entity_extractor': self.entity_extractor is not None,
                'context_manager': self.context_manager is not None,
                'skill_manager': self.skill_manager is not None,
                'wake_word': self.wake_word_detector is not None,
                'stt': self.stt_engine is not None,
                'tts': self.tts_engine is not None,
                'audio_io': self.audio_io is not None,
            }
        }


def create_engine(
    config: Config,
    state_manager: Optional[StateManager] = None,
    **kwargs
) -> ZeroEngine:
    """
    Create and initialize a ZERO engine instance.

    Args:
        config: Configuration instance
        state_manager: Optional state manager
        **kwargs: Additional arguments for engine initialization

    Returns:
        Initialized ZeroEngine instance
    """
    engine = ZeroEngine(config, state_manager, **kwargs)
    return engine
