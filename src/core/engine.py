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
from dataclasses import dataclass
from typing import Any, Callable, Optional

import numpy as np

from src.brain.context import ContextManager
from src.brain.entities import EntityExtractor
from src.brain.intent import IntentClassifier
from src.core.config import Config
from src.core.state import AssistantState, StateManager, get_state_manager
from src.skills.base_skill import SkillResponse
from src.skills.skill_manager import SkillManager

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    """Result from processing a user query through the pipeline."""

    success: bool
    user_input: str
    intent: Optional[str] = None
    entities: Optional[dict[str, Any]] = None
    context: Optional[dict[str, Any]] = None
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

        # LLM client (for conversational mode)
        self.llm_client = None

        # Audio components (to be initialized)
        self.wake_word_detector = None
        self.stt_engine = None
        self.tts_engine = None
        self.audio_recorder = None
        self.audio_player = None

        # Threading
        self._running = False
        self._event_loop_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()
        self._wake_word_detected = threading.Event()

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

        # Initialize LLM client for conversational mode
        from src.brain.llm import create_llm_client

        self.llm_client = create_llm_client(self.config.get_all())
        if self.llm_client and self.llm_client.is_available():
            logger.info("LLM client initialized for conversational mode")
        else:
            logger.warning("LLM client not available - conversational mode will be limited")

        # Set up timer skill callback for TTS alerts
        self._setup_timer_callback()

        logger.info("All components initialized successfully")

    def _setup_timer_callback(self):
        """Set up timer completion callback to use TTS."""
        # Get the timer skill
        timer_skill = self.skill_manager.get_skill("timer")
        if not timer_skill:
            logger.debug("Timer skill not found - skipping callback setup")
            return

        # Create callback function that uses TTS to speak the completion message
        def timer_completion_callback(message: str):
            """Callback function called when a timer completes."""
            logger.info(f"Timer completion callback: {message}")

            # Use TTS to speak the timer completion message
            if self.tts_engine and self.audio_player:
                try:
                    logger.info(f"Speaking timer completion: {message}")
                    audio_response = self.tts_engine.synthesize(message)

                    if audio_response:
                        self.audio_player.play(
                            audio_response, sample_rate=self.tts_engine.sample_rate
                        )
                        logger.info("Timer completion message spoken")
                    else:
                        logger.warning("TTS synthesis failed for timer completion")
                except Exception as e:
                    logger.error(f"Error speaking timer completion: {e}")
            else:
                logger.debug("TTS or audio player not available - timer completion not spoken")

        # Set the callback on the timer skill
        timer_skill.set_alert_callback(timer_completion_callback)
        logger.info("Timer completion callback configured")

    def _initialize_audio(self):
        """Initialize audio components (wake word, STT, TTS)."""
        try:
            # Initialize wake word detector
            if self.config.get("wake_word.enabled", True):
                from src.audio.wake_word import create_wake_word_detector

                access_key = self.config.get("wake_word.access_key")
                keyword = self.config.get("wake_word.keyword", "jarvis")
                sensitivity = self.config.get("wake_word.sensitivity", 0.5)

                if access_key:
                    self.wake_word_detector = create_wake_word_detector(
                        access_key=access_key,
                        keyword=keyword,
                        sensitivity=sensitivity,
                        on_detected=self._on_wake_word_detected,
                    )
                    logger.info(f"Wake word detector initialized with keyword: {keyword}")
                else:
                    logger.warning("Wake word access key not found - wake word detection disabled")
            else:
                logger.info("Wake word detection disabled in config")

            # Initialize STT engine
            from src.audio.stt import create_stt

            stt_api_key = self.config.get("stt.api_key")
            if stt_api_key:
                self.stt_engine = create_stt(
                    api_key=stt_api_key,
                    model=self.config.get("stt.model", "nova-2"),
                    language=self.config.get("stt.language", "en-US"),
                )
                logger.info("STT engine initialized")
            else:
                logger.warning("STT API key not found - speech-to-text disabled")

            # Initialize TTS engine
            from src.audio.tts import create_tts

            tts_model = self.config.get("tts.model", "tts_models/en/ljspeech/tacotron2-DDC")
            use_cuda = self.config.get("tts.use_cuda", False)
            use_cache = self.config.get("tts.cache_enabled", True)
            speed = self.config.get("tts.speed", 1.0)

            self.tts_engine = create_tts(
                model_name=tts_model, use_cuda=use_cuda, use_cache=use_cache, speed=speed
            )
            logger.info("TTS engine initialized")

            # Initialize audio I/O
            from src.audio.audio_io import AudioPlayer, AudioRecorder

            audio_input_config = self.config.get("audio.input", {})
            audio_output_config = self.config.get("audio.output", {})

            self.audio_recorder = AudioRecorder(
                sample_rate=audio_input_config.get("sample_rate", 16000),
                channels=audio_input_config.get("channels", 1),
                chunk_size=audio_input_config.get("chunk_size", 512),
                device_index=audio_input_config.get("device_index"),
                silence_threshold=audio_input_config.get("silence_threshold", 0.02),
                silence_duration=audio_input_config.get("silence_duration", 1.5),
            )

            self.audio_player = AudioPlayer(
                sample_rate=audio_output_config.get("sample_rate", 22050),
                channels=1,
                device_index=audio_output_config.get("device_index"),
            )
            logger.info("Audio I/O initialized")

        except Exception as e:
            logger.error(f"Failed to initialize audio components: {e}", exc_info=True)
            # Don't raise - allow engine to continue without audio (for CLI mode)
            logger.warning("Continuing without audio components (CLI mode may still work)")

    def start(self):
        """Start the engine and begin event loop."""
        if self._running:
            logger.warning("Engine already running")
            return

        logger.info("Starting ZERO engine...")
        self._running = True
        self._shutdown_event.clear()
        self._wake_word_detected.clear()

        # Start wake word detector if available
        if self.wake_word_detector:
            try:
                self.wake_word_detector.start()
                logger.info("Wake word detector started")
            except Exception as e:
                logger.error(f"Failed to start wake word detector: {e}")
                logger.warning("Continuing without wake word detection")

        # Start event loop in separate thread
        self._event_loop_thread = threading.Thread(
            target=self._event_loop, name="ZeroEngine-EventLoop", daemon=True
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
        # Cleanup audio components
        if self.wake_word_detector:
            try:
                self.wake_word_detector.stop()
            except Exception as e:
                logger.error(f"Error stopping wake word detector: {e}")

        if self.audio_recorder:
            try:
                self.audio_recorder.stop()
            except Exception as e:
                logger.error(f"Error stopping audio recorder: {e}")

        logger.info("Components cleaned up")

    def _on_wake_word_detected(self):
        """Callback when wake word is detected."""
        logger.info("Wake word detected in engine")
        self._wake_word_detected.set()
        if self._on_wake_word:
            try:
                self._on_wake_word()
            except Exception as e:
                logger.error(f"Error in wake word callback: {e}")

    def _get_greeting(self) -> str:
        """Get a contextual greeting message."""
        import datetime

        hour = datetime.datetime.now().hour

        if 5 <= hour < 12:
            greeting = "Good morning, sir. How may I assist you today?"
        elif 12 <= hour < 17:
            greeting = "Good afternoon, sir. How may I help you?"
        elif 17 <= hour < 21:
            greeting = "Good evening, sir. What can I do for you?"
        else:
            greeting = "Good evening, sir. How may I assist you?"

        return greeting

    def _event_loop(self):
        """
        Main event loop.

        Continuously monitors for wake word and processes commands.
        Pipeline: Wake word → Record → STT → NLU → Skills → TTS → Play
        """
        logger.info("Event loop started")

        try:
            while self._running and not self._shutdown_event.is_set():
                # State: IDLE - waiting for wake word
                self.state_manager.transition_to(AssistantState.IDLE)

                # Wait for wake word detection
                if self.wake_word_detector:
                    # Wait for wake word event (with timeout to check shutdown)
                    if self._wake_word_detected.wait(timeout=0.5):
                        self._wake_word_detected.clear()
                        # Wake word detected - proceed with voice command
                        self._handle_voice_command()
                else:
                    # No wake word detector - sleep to prevent CPU spinning
                    time.sleep(0.5)

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

    def _handle_voice_command(self):
        """
        Handle a complete voice command cycle with conversational LLM.

        Pipeline: Greeting → Record (with pause detection) → STT → LLM → TTS → Continuous listening
        """
        try:
            # First, provide a greeting when wake word is detected
            greeting = self._get_greeting()
            logger.info(f"Greeting: {greeting}")

            # Play greeting
            if self.tts_engine and self.audio_player:
                greeting_audio = self.tts_engine.synthesize(greeting)
                if greeting_audio:
                    self.audio_player.play(greeting_audio, sample_rate=self.tts_engine.sample_rate)

            # Small delay after greeting
            time.sleep(0.3)

            # Now handle the conversation loop
            self._handle_conversation_loop()

        except Exception as e:
            logger.error(f"Error handling voice command: {e}", exc_info=True)
            self.state_manager.transition_to(AssistantState.ERROR)
            if self._on_error:
                self._on_error(str(e))
            # Return to IDLE after error
            self.state_manager.transition_to(AssistantState.IDLE)

    def _handle_conversation_loop(self):
        """
        Handle continuous conversation loop - keeps listening until user says thank you.

        Continuously listens for user input, responds after 1 second pause,
        and continues until user says "thank you" or similar farewell.
        """
        max_conversation_rounds = 50  # Prevent infinite loops (safety limit)
        round_count = 0

        while round_count < max_conversation_rounds:
            round_count += 1
            round_start_time = time.time()
            stage_timings = {}

            # State: LISTENING
            self.state_manager.transition_to(AssistantState.LISTENING)
            if self._on_listening_start:
                self._on_listening_start()

            # Record audio with pause detection (1 second pause)
            if not self.audio_recorder:
                logger.error("Audio recorder not initialized")
                return

            logger.info("Recording audio with pause detection (1 second pause)...")
            recording_start = time.time()
            audio_data = self._record_with_pause_detection(max_duration=30.0, pause_wait=1.0)
            stage_timings['recording'] = (time.time() - recording_start) * 1000

            if not audio_data or len(audio_data) < 500:  # Minimum audio length check
                logger.info("No audio recorded - continuing to listen...")
                # Continue listening instead of breaking
                continue

            if self._on_listening_stop:
                self._on_listening_stop()

            # State: PROCESSING (STT)
            self.state_manager.transition_to(AssistantState.PROCESSING)

            # Convert speech to text
            if not self.stt_engine:
                logger.error("STT engine not initialized")
                return

            logger.info("Transcribing audio...")
            stt_start = time.time()
            transcription = self.stt_engine.transcribe_bytes(
                audio_data=audio_data,
                sample_rate=self.audio_recorder.sample_rate,
                channels=self.audio_recorder.channels,
                encoding="linear16",
            )
            stage_timings['stt'] = (time.time() - stt_start) * 1000

            if not transcription or not transcription.strip():
                logger.warning("No transcription received - continuing to listen...")
                # Continue listening
                continue

            logger.info(f"Transcription: '{transcription}'")
            if self._on_processing:
                self._on_processing(transcription)

            # Check if user said thank you or goodbye (end conversation)
            if self._is_farewell(transcription):
                logger.info("User said farewell - ending conversation")
                # Give a farewell response
                farewell_response = self._get_farewell_response()
                if farewell_response and self.tts_engine and self.audio_player:
                    farewell_audio = self.tts_engine.synthesize(farewell_response)
                    if farewell_audio:
                        self.audio_player.play(
                            farewell_audio, sample_rate=self.tts_engine.sample_rate
                        )
                break

            # Process through conversational LLM
            processing_start = time.time()
            response_text = self._process_conversational(transcription)
            stage_timings['processing'] = (time.time() - processing_start) * 1000

            # State: RESPONDING (TTS)
            if response_text:
                self.state_manager.transition_to(AssistantState.RESPONDING)

                # Synthesize and play response
                if self.tts_engine and self.audio_player:
                    logger.info("Synthesizing response...")
                    tts_start = time.time()
                    audio_response = self.tts_engine.synthesize(response_text)
                    stage_timings['tts'] = (time.time() - tts_start) * 1000

                    if audio_response:
                        logger.info("Playing response...")
                        playback_start = time.time()
                        self.audio_player.play(
                            audio_response, sample_rate=self.tts_engine.sample_rate
                        )
                        stage_timings['playback'] = (time.time() - playback_start) * 1000
                    else:
                        logger.warning("TTS synthesis failed")
                else:
                    logger.warning("TTS or audio player not available - response not spoken")

                # Log round timing breakdown
                total_round_time = (time.time() - round_start_time) * 1000
                logger.info(
                    f"✓ CONVERSATION ROUND {round_count} COMPLETE: {total_round_time:.0f}ms total | "
                    f"Recording: {stage_timings.get('recording', 0):.0f}ms, "
                    f"STT: {stage_timings.get('stt', 0):.0f}ms, "
                    f"Processing: {stage_timings.get('processing', 0):.0f}ms, "
                    f"TTS: {stage_timings.get('tts', 0):.0f}ms, "
                    f"Playback: {stage_timings.get('playback', 0):.0f}ms"
                )

                # Update context with this interaction
                self.context_manager.update(
                    user_input=transcription,
                    intent="conversational",
                    entities={},
                    response=response_text,
                )

                # After response, immediately continue listening (no delay)
                logger.info("Response complete - continuing to listen...")
                # Loop continues immediately to listen for next input
            else:
                # No response - continue listening anyway
                logger.info("No response generated - continuing to listen...")
                continue

        # Return to IDLE
        self.state_manager.transition_to(AssistantState.IDLE)
        logger.info("Conversation ended")

    def _is_farewell(self, text: str) -> bool:
        """
        Check if user input is a farewell/thank you message.

        Args:
            text: User's input text

        Returns:
            True if it's a farewell message
        """
        text_lower = text.lower().strip()

        # Farewell patterns
        farewell_patterns = [
            r"\b(thank\s+you|thanks|thx|ty)\b",
            r"\b(goodbye|bye|see\s+you|farewell)\b",
            r"\b(that\'?s\s+all|that\'?s\s+it|done|finished)\b",
            r"\b(no\s+more|nothing\s+else|all\s+set)\b",
        ]

        import re

        for pattern in farewell_patterns:
            if re.search(pattern, text_lower):
                return True

        return False

    def _get_farewell_response(self) -> str:
        """Get a farewell response."""
        import random

        farewells = [
            "You're welcome, sir. Have a good day.",
            "You're most welcome, sir. Feel free to call on me anytime.",
            "My pleasure, sir. I'm here whenever you need me.",
            "You're welcome, sir. Take care.",
        ]

        return random.choice(farewells)

    def _record_with_pause_detection(
        self, max_duration: float = 10.0, pause_wait: float = 1.0
    ) -> bytes:
        """
        Record audio with pause detection - waits a bit after silence to see if user continues.

        Args:
            max_duration: Maximum recording duration (seconds)
            pause_wait: Time to wait after silence before finalizing (seconds)

        Returns:
            Complete audio data as bytes
        """
        if not self.audio_recorder._recording:
            self.audio_recorder.start()

        logger.info("Recording with pause detection...")

        silence_chunks = int(
            self.audio_recorder.silence_duration
            * self.audio_recorder.sample_rate
            / self.audio_recorder.chunk_size
        )
        pause_wait_chunks = int(
            pause_wait * self.audio_recorder.sample_rate / self.audio_recorder.chunk_size
        )
        silent_chunks_count = 0
        max_chunks = int(
            max_duration * self.audio_recorder.sample_rate / self.audio_recorder.chunk_size
        )
        chunks_recorded = 0

        while chunks_recorded < max_chunks:
            # Record chunk
            chunk = self.audio_recorder.record_chunk()
            chunks_recorded += 1

            # Convert bytes to numpy array for RMS calculation
            chunk_array = np.frombuffer(chunk, dtype=np.int16)

            # Calculate RMS (volume level)
            rms = np.sqrt(np.mean(chunk_array.astype(float) ** 2))

            # Check for silence
            if rms < self.audio_recorder.silence_threshold * 32768:  # Scale to int16 range
                silent_chunks_count += 1
                if silent_chunks_count >= silence_chunks:
                    # Silence detected - wait a bit to see if user continues
                    logger.info("Silence detected, waiting to see if user continues...")
                    additional_silent_chunks = 0

                    # Wait for pause_wait duration to see if user continues speaking
                    for _ in range(pause_wait_chunks):
                        try:
                            wait_chunk = self.audio_recorder.record_chunk()
                            wait_array = np.frombuffer(wait_chunk, dtype=np.int16)
                            wait_rms = np.sqrt(np.mean(wait_array.astype(float) ** 2))

                            if wait_rms < self.audio_recorder.silence_threshold * 32768:
                                additional_silent_chunks += 1
                            else:
                                # User continued speaking - reset silence counter
                                logger.info("User continued speaking")
                                silent_chunks_count = 0
                                additional_silent_chunks = 0
                                break
                        except Exception as e:
                            logger.warning(f"Error during pause detection: {e}")
                            break

                    # If we waited the full pause duration and still silence, finalize recording
                    if additional_silent_chunks >= pause_wait_chunks:
                        logger.info(
                            f"Recording finalized after pause (total: {chunks_recorded} chunks)"
                        )
                        break
            else:
                silent_chunks_count = 0

        # Get complete audio data
        audio_data = self.audio_recorder.get_audio_data()

        logger.info(
            f"Recording complete: {len(audio_data)} bytes, "
            f"{len(audio_data) / (self.audio_recorder.sample_rate * 2):.2f}s"
        )

        return audio_data

    def _listen_for_follow_up(self, duration: float = 5.0) -> bytes:
        """
        Listen for follow-up input after response.

        Args:
            duration: How long to listen (seconds)

        Returns:
            Audio data if detected, empty bytes otherwise
        """
        if not self.audio_recorder._recording:
            self.audio_recorder.start()

        logger.info(f"Listening for follow-up for {duration} seconds...")

        max_chunks = int(
            duration * self.audio_recorder.sample_rate / self.audio_recorder.chunk_size
        )
        chunks_recorded = 0
        has_audio = False

        # Clear previous audio data
        self.audio_recorder._all_frames = []

        while chunks_recorded < max_chunks:
            chunk = self.audio_recorder.record_chunk()
            chunks_recorded += 1

            # Check if there's actual audio (not just silence)
            chunk_array = np.frombuffer(chunk, dtype=np.int16)
            rms = np.sqrt(np.mean(chunk_array.astype(float) ** 2))

            if rms >= self.audio_recorder.silence_threshold * 32768:
                has_audio = True
                # Continue recording until silence
                silence_chunks = int(
                    1.5 * self.audio_recorder.sample_rate / self.audio_recorder.chunk_size
                )
                silent_count = 0

                while chunks_recorded < max_chunks * 2:  # Allow extension
                    chunk = self.audio_recorder.record_chunk()
                    chunks_recorded += 1

                    chunk_array = np.frombuffer(chunk, dtype=np.int16)
                    rms = np.sqrt(np.mean(chunk_array.astype(float) ** 2))

                    if rms < self.audio_recorder.silence_threshold * 32768:
                        silent_count += 1
                        if silent_count >= silence_chunks:
                            break
                    else:
                        silent_count = 0

        if has_audio:
            audio_data = self.audio_recorder.get_audio_data()
            logger.info(f"Follow-up audio detected: {len(audio_data)} bytes")
            return audio_data
        else:
            logger.info("No follow-up audio detected")
            return b""

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
        stage_timings = {}

        try:
            # State: PROCESSING
            self.state_manager.transition_to(AssistantState.PROCESSING)

            # Call processing callback
            if self._on_processing:
                self._on_processing(user_input)

            # Step 1: Classify intent
            logger.debug(f"Classifying intent for: {user_input}")
            step_start = time.time()
            intent_result = self.intent_classifier.classify(user_input)
            stage_timings['intent_classification'] = (time.time() - step_start) * 1000
            intent = intent_result.intent.value
            confidence = intent_result.confidence

            logger.info(
                f"Intent: {intent} (confidence: {confidence:.2f}, method: {intent_result.method})"
            )

            # Step 2: Extract entities
            logger.debug("Extracting entities...")
            step_start = time.time()
            entity_result = self.entity_extractor.extract(user_input, intent)
            stage_timings['entity_extraction'] = (time.time() - step_start) * 1000
            entities = {e.entity_type: e.value for e in entity_result.entities}

            logger.info(f"Entities: {entities}")

            # Step 3: Get context
            step_start = time.time()
            context = self.context_manager.get_context_for_query(user_input)
            stage_timings['context_retrieval'] = (time.time() - step_start) * 1000
            logger.debug(f"Context: {context}")

            # State: EXECUTING
            self.state_manager.transition_to(AssistantState.EXECUTING)

            # Step 4: Execute skill
            logger.debug("Routing to skill manager...")
            step_start = time.time()
            skill_response = self.skill_manager.route_intent(
                intent=intent, entities=entities, context=context
            )
            stage_timings['skill_execution'] = (time.time() - step_start) * 1000

            logger.info(f"Skill executed: {skill_response.message}")

            # Step 5: Update context
            step_start = time.time()
            self.context_manager.update(
                user_input=user_input,
                intent=intent,
                entities=entities,
                response=skill_response.message,
            )

            # Apply any context updates from skill
            if skill_response.context_update:
                for key, value in skill_response.context_update.items():
                    # Use set_preference for context updates (preferences or other context data)
                    self.context_manager.set_preference(key, value)
            stage_timings['context_update'] = (time.time() - step_start) * 1000

            # State: RESPONDING
            self.state_manager.transition_to(AssistantState.RESPONDING)

            # Call response callback
            if self._on_response:
                self._on_response(skill_response.message)

            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000

            # Log detailed timing breakdown
            logger.info(
                f"✓ PIPELINE COMPLETE: {latency_ms:.0f}ms total | "
                f"Intent: {stage_timings.get('intent_classification', 0):.0f}ms, "
                f"Entities: {stage_timings.get('entity_extraction', 0):.0f}ms, "
                f"Context: {stage_timings.get('context_retrieval', 0):.0f}ms, "
                f"Skill: {stage_timings.get('skill_execution', 0):.0f}ms, "
                f"Update: {stage_timings.get('context_update', 0):.0f}ms"
            )

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
                latency_ms=latency_ms,
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
                latency_ms=(time.time() - start_time) * 1000,
            )

    def _process_conversational(self, user_input: str) -> str:
        """
        Process user input through hybrid approach: Skills first, then LLM for conversation.

        Args:
            user_input: User's transcribed speech

        Returns:
            Response text (from skill or LLM)
        """
        # Step 1: Try to classify intent and extract entities
        logger.debug(f"Classifying intent for: {user_input}")
        intent_result = self.intent_classifier.classify(user_input)
        intent = intent_result.intent.value
        confidence = intent_result.confidence

        logger.info(
            f"Intent: {intent} (confidence: {confidence:.2f}, method: {intent_result.method})"
        )

        # Step 2: Extract entities
        logger.debug("Extracting entities...")
        entity_result = self.entity_extractor.extract(user_input, intent)
        entities = {e.entity_type: e.value for e in entity_result.entities}
        entities["user_input"] = user_input  # Include original input for context

        logger.info(f"Entities: {entities}")

        # Step 3: Get context
        context = self.context_manager.get_context_for_query(user_input)
        logger.debug(f"Context: {context}")

        # Step 4: Check if a skill can handle this intent
        skill = self.skill_manager._find_skill_for_intent(intent) if self.skill_manager else None

        if skill and skill.is_enabled() and confidence > 0.5:
            # Skill can handle this - execute it
            logger.info(f"Executing skill '{skill.name}' for intent '{intent}'")
            try:
                skill_response = self.skill_manager.route_intent(
                    intent=intent, entities=entities, context=context
                )

                if skill_response.success:
                    logger.info(f"Skill executed successfully: {skill_response.message}")
                    # Update context with skill execution
                    self.context_manager.update(
                        user_input=user_input,
                        intent=intent,
                        entities=entities,
                        response=skill_response.message,
                    )
                    # Apply context updates from skill
                    if skill_response.context_update:
                        for key, value in skill_response.context_update.items():
                            self.context_manager.set_preference(key, value)
                    return skill_response.message
                else:
                    logger.warning(f"Skill execution failed: {skill_response.message}")
                    # Fall through to LLM for error handling
            except Exception as e:
                logger.error(f"Error executing skill: {e}", exc_info=True)
                # Fall through to LLM for error handling

        # Step 5: Use LLM for general conversation or when skills can't handle it
        if not self.llm_client or not self.llm_client.is_available():
            logger.warning("LLM not available - using fallback response")
            if skill:
                return "I apologize, but I encountered an error processing that request."
            else:
                return (
                    "I'm not sure how to handle that request. "
                    "I can help with weather, timers, opening apps, and general questions."
                )

        # Get conversation history in LLM format
        conversation_history = self._get_conversation_history_for_llm()

        # Build enhanced system prompt with context and skill information
        system_prompt = self._build_conversational_system_prompt(context, intent, entities)

        # Get LLM response
        logger.info("Sending to LLM with conversation history...")
        llm_response = self.llm_client.chat(
            user_message=user_input,
            conversation_history=conversation_history,
            system_prompt=system_prompt,
        )

        response_text = (
            llm_response.content
            if llm_response.content
            else "I apologize, but I couldn't generate a response."
        )

        logger.info(f"LLM response: '{response_text[:100]}...'")
        return response_text

    def _get_conversation_history_for_llm(self) -> list[dict[str, str]]:
        """
        Convert conversation history from ContextManager to LLM format.

        Returns:
            List of messages in format [{"role": "user", "content": "..."}, ...]
        """
        history = []
        interactions = self.context_manager.get_history(count=10)  # Last 10 interactions

        for interaction in interactions:
            # Add user message
            history.append({"role": "user", "content": interaction.user_input})
            # Add assistant response
            history.append({"role": "assistant", "content": interaction.response})

        return history

    def _build_conversational_system_prompt(
        self,
        context: dict[str, Any],
        intent: str = None,
        entities: dict[str, Any] = None,
    ) -> str:
        """
        Build enhanced system prompt with context and available capabilities.

        Args:
            context: Current conversation context
            intent: Detected intent (if any)
            entities: Extracted entities (if any)

        Returns:
            Enhanced system prompt string
        """
        # Base J.A.R.V.I.S. prompt
        base_prompt = """You are ZERO, a personal AI assistant inspired by J.A.R.V.I.S. from Iron Man.

Personality traits:
- Calm, intelligent, and composed
- Slightly formal but not robotic
- Address the user as "sir" or "madam" when appropriate
- Professional and helpful
- Occasional dry humor when appropriate
- Concise and to the point
- Never overly enthusiastic or use excessive emojis

Communication style:
- Keep responses brief (2-3 sentences max unless asked for details)
- Be direct and informative
- Use "I" statements ("I can help with that")
- Acknowledge limitations honestly
- Respond naturally to voice conversations"""

        # Add available capabilities with descriptions
        capabilities = []
        if self.skill_manager:
            skill_descriptions = []
            for skill in self.skill_manager.skills.values():
                if skill.is_enabled():
                    skill_name = skill.__class__.__name__.replace("Skill", "").lower()
                    skill_desc = skill.description or skill_name
                    skill_descriptions.append(f"- {skill_name}: {skill_desc}")

            if skill_descriptions:
                capabilities.append("Available capabilities:\n" + "\n".join(skill_descriptions))
                capabilities.append(
                    "\nWhen users ask about these capabilities, acknowledge that I can help with them."
                )

        # Add context information
        context_info = []
        if context.get("current_location"):
            context_info.append(f"Current location context: {context['current_location']}")
        if context.get("active_timers"):
            context_info.append(f"Active timers: {', '.join(context['active_timers'])}")
        if context.get("preferences"):
            prefs = context["preferences"]
            if "preferred_location" in prefs:
                context_info.append(f"User's preferred location: {prefs['preferred_location']}")

        # Add detected intent and entities if available
        if intent and intent != "unknown":
            context_info.append(f"Detected intent: {intent}")
        if entities:
            relevant_entities = {k: v for k, v in entities.items() if k != "user_input"}
            if relevant_entities:
                context_info.append(f"Extracted entities: {relevant_entities}")

        # Combine into final prompt
        if capabilities:
            base_prompt += f"\n\n{capabilities[0]}"
        if context_info:
            base_prompt += f"\n\nContext: {'; '.join(context_info)}"

        base_prompt += (
            "\n\nRespond naturally and conversationally to the user's voice input. "
            "If the user asks about capabilities I have (weather, timers, apps, search), "
            "acknowledge that I can help with those tasks."
        )

        return base_prompt

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
            if not self.stt_engine:
                raise RuntimeError("STT engine not initialized")

            # Get audio parameters from recorder or use defaults
            sample_rate = self.audio_recorder.sample_rate if self.audio_recorder else 16000
            channels = self.audio_recorder.channels if self.audio_recorder else 1

            transcription = self.stt_engine.transcribe_bytes(
                audio_data=audio_data,
                sample_rate=sample_rate,
                channels=channels,
                encoding="linear16",
            )

            if not transcription or not transcription.strip():
                raise ValueError("No transcription received from STT")

            logger.info(f"Transcription: {transcription}")

            # Process as text command
            result = self.process_text_command(transcription)

            # Step 2: Convert response to speech
            if result.success and result.response_text:
                # State: RESPONDING (TTS)
                self.state_manager.transition_to(AssistantState.RESPONDING)

                if self.tts_engine and self.audio_player:
                    # Synthesize response
                    audio_response = self.tts_engine.synthesize(result.response_text)

                    if audio_response:
                        # Play response
                        self.audio_player.play(
                            audio_response, sample_rate=self.tts_engine.sample_rate
                        )
                        logger.info("Response synthesized and played")
                    else:
                        logger.warning("TTS synthesis failed")
                else:
                    logger.warning("TTS or audio player not available")

            return result

        except Exception as e:
            logger.error(f"Voice pipeline error: {e}", exc_info=True)
            self.state_manager.transition_to(AssistantState.ERROR)

            return PipelineResult(
                success=False,
                user_input="[voice input]",
                error=str(e),
                response_text=f"Voice processing error: {str(e)}",
                latency_ms=(time.time() - start_time) * 1000,
            )

    def is_running(self) -> bool:
        """Check if engine is running."""
        return self._running

    def get_status(self) -> dict[str, Any]:
        """
        Get current engine status.

        Returns:
            Status dictionary
        """
        return {
            "running": self._running,
            "state": self.state_manager.state.name,
            "skills_loaded": len(self.skill_manager.skills) if self.skill_manager else 0,
            "components": {
                "intent_classifier": self.intent_classifier is not None,
                "entity_extractor": self.entity_extractor is not None,
                "context_manager": self.context_manager is not None,
                "skill_manager": self.skill_manager is not None,
                "wake_word": self.wake_word_detector is not None,
                "stt": self.stt_engine is not None,
                "tts": self.tts_engine is not None,
                "audio_recorder": self.audio_recorder is not None,
                "audio_player": self.audio_player is not None,
            },
        }


def create_engine(
    config: Config, state_manager: Optional[StateManager] = None, **kwargs
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
