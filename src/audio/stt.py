"""
Speech-to-Text using Deepgram API.

This module provides high-accuracy speech transcription with sub-second latency.
Supports both streaming and pre-recorded audio.
"""

from typing import Optional, Dict, Any, Callable
import asyncio
import threading
from pathlib import Path
import queue

try:
    from deepgram import (
        DeepgramClient,
        PrerecordedOptions,
        FileSource,
        LiveTranscriptionEvents,
        LiveOptions,
    )
    DEEPGRAM_AVAILABLE = True
except ImportError:
    DEEPGRAM_AVAILABLE = False

from src.core.logger import get_logger


logger = get_logger(__name__)


class SpeechToText:
    """
    Speech-to-Text using Deepgram API.

    Converts audio (bytes or file) to text with high accuracy and low latency.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "nova-2",
        language: str = "en-US",
        smart_format: bool = True,
        punctuate: bool = True,
        profanity_filter: bool = False,
        timeout: float = 10.0
    ):
        """
        Initialize Speech-to-Text.

        Args:
            api_key: Deepgram API key
            model: Model to use (nova-2, whisper, base, etc.)
            language: Language code (en-US, es, fr, etc.)
            smart_format: Enable smart formatting
            punctuate: Add punctuation
            profanity_filter: Filter profanity
            timeout: Request timeout (seconds)

        Raises:
            RuntimeError: If deepgram-sdk is not available
            ValueError: If api_key is invalid
        """
        if not DEEPGRAM_AVAILABLE:
            raise RuntimeError(
                "deepgram-sdk not available. Install with: pip install deepgram-sdk"
            )

        self.api_key = api_key
        self.model = model
        self.language = language
        self.smart_format = smart_format
        self.punctuate = punctuate
        self.profanity_filter = profanity_filter
        self.timeout = timeout

        # Initialize Deepgram client
        try:
            self.client = DeepgramClient(api_key)
            logger.info(f"Deepgram STT initialized with model: {model}")
        except Exception as e:
            logger.error(f"Failed to initialize Deepgram client: {e}")
            raise ValueError(f"Invalid Deepgram API key: {e}")

    def transcribe_bytes(
        self,
        audio_data: bytes,
        sample_rate: int = 16000,
        channels: int = 1,
        encoding: str = "linear16"
    ) -> Optional[str]:
        """
        Transcribe audio from bytes.

        Args:
            audio_data: Audio data as bytes
            sample_rate: Audio sample rate (Hz)
            channels: Number of audio channels
            encoding: Audio encoding (linear16, opus, etc.)

        Returns:
            Transcribed text, or None if transcription failed
        """
        try:
            # Prepare options
            options = PrerecordedOptions(
                model=self.model,
                language=self.language,
                smart_format=self.smart_format,
                punctuate=self.punctuate,
                profanity_filter=self.profanity_filter,
                encoding=encoding,
                sample_rate=sample_rate,
                channels=channels
            )

            # Prepare payload
            payload = {
                "buffer": audio_data
            }

            # Transcribe
            logger.debug(f"Transcribing {len(audio_data)} bytes...")
            response = self.client.listen.prerecorded.v("1").transcribe_file(
                payload,
                options,
                timeout=self.timeout
            )

            # Extract transcript
            transcript = self._extract_transcript(response)

            if transcript:
                logger.info(f"Transcription: '{transcript}'")
            else:
                logger.warning("No transcription returned")

            return transcript

        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return None

    def transcribe_file(self, filename: str) -> Optional[str]:
        """
        Transcribe audio from file.

        Args:
            filename: Path to audio file (WAV, MP3, etc.)

        Returns:
            Transcribed text, or None if transcription failed
        """
        try:
            # Read file
            with open(filename, "rb") as audio_file:
                audio_data = audio_file.read()

            # Prepare options
            options = PrerecordedOptions(
                model=self.model,
                language=self.language,
                smart_format=self.smart_format,
                punctuate=self.punctuate,
                profanity_filter=self.profanity_filter
            )

            # Prepare payload
            payload = {
                "buffer": audio_data
            }

            # Transcribe
            logger.debug(f"Transcribing file: {filename}")
            response = self.client.listen.prerecorded.v("1").transcribe_file(
                payload,
                options,
                timeout=self.timeout
            )

            # Extract transcript
            transcript = self._extract_transcript(response)

            if transcript:
                logger.info(f"Transcription from {filename}: '{transcript}'")
            else:
                logger.warning(f"No transcription from {filename}")

            return transcript

        except FileNotFoundError:
            logger.error(f"Audio file not found: {filename}")
            return None
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return None

    def _extract_transcript(self, response: Any) -> Optional[str]:
        """
        Extract transcript text from Deepgram response.

        Args:
            response: Deepgram API response

        Returns:
            Transcript text, or None if not found
        """
        try:
            # Access the response structure
            # Deepgram response: response.results.channels[0].alternatives[0].transcript
            if hasattr(response, 'results'):
                channels = response.results.channels
                if channels and len(channels) > 0:
                    alternatives = channels[0].alternatives
                    if alternatives and len(alternatives) > 0:
                        transcript = alternatives[0].transcript
                        confidence = alternatives[0].confidence

                        logger.debug(f"Confidence: {confidence:.2f}")

                        # Return transcript if not empty
                        if transcript and transcript.strip():
                            return transcript.strip()

            return None

        except Exception as e:
            logger.error(f"Error extracting transcript: {e}")
            return None

    def get_confidence(self, response: Any) -> float:
        """
        Get confidence score from response.

        Args:
            response: Deepgram API response

        Returns:
            Confidence score (0.0 to 1.0), or 0.0 if not found
        """
        try:
            if hasattr(response, 'results'):
                channels = response.results.channels
                if channels and len(channels) > 0:
                    alternatives = channels[0].alternatives
                    if alternatives and len(alternatives) > 0:
                        return alternatives[0].confidence
        except Exception as e:
            logger.error(f"Error getting confidence: {e}")

        return 0.0


class StreamingSpeechToText:
    """
    Streaming Speech-to-Text using Deepgram WebSocket API.

    Provides real-time transcription with live audio streaming.
    Uses WebSocket connection for bidirectional communication.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "nova-2",
        language: str = "en-US",
        smart_format: bool = True,
        punctuate: bool = True,
        interim_results: bool = True,
        vad_events: bool = True,
        encoding: str = "linear16",
        sample_rate: int = 16000,
        channels: int = 1
    ):
        """
        Initialize Streaming Speech-to-Text.

        Args:
            api_key: Deepgram API key
            model: Model to use (nova-2, whisper, base, etc.)
            language: Language code (en-US, es, fr, etc.)
            smart_format: Enable smart formatting
            punctuate: Add punctuation
            interim_results: Return interim results before final
            vad_events: Enable Voice Activity Detection events
            encoding: Audio encoding (linear16, opus, etc.)
            sample_rate: Audio sample rate (Hz)
            channels: Number of audio channels

        Raises:
            RuntimeError: If deepgram-sdk is not available
            ValueError: If api_key is invalid
        """
        if not DEEPGRAM_AVAILABLE:
            raise RuntimeError(
                "deepgram-sdk not available. Install with: pip install deepgram-sdk"
            )

        self.api_key = api_key
        self.model = model
        self.language = language
        self.smart_format = smart_format
        self.punctuate = punctuate
        self.interim_results = interim_results
        self.vad_events = vad_events
        self.encoding = encoding
        self.sample_rate = sample_rate
        self.channels = channels

        # Initialize Deepgram client
        try:
            self.client = DeepgramClient(api_key)
            logger.info(f"Deepgram Streaming STT initialized with model: {model}")
        except Exception as e:
            logger.error(f"Failed to initialize Deepgram client: {e}")
            raise ValueError(f"Invalid Deepgram API key: {e}")

        # Connection state
        self.connection = None
        self.is_connected = False
        self.is_recording = False

        # Transcription results
        self.transcript_queue = queue.Queue()
        self.final_transcript = ""

    async def start(self):
        """
        Start the streaming connection.

        Raises:
            RuntimeError: If connection fails
        """
        if self.is_connected:
            logger.warning("Already connected")
            return

        try:
            # Configure options
            options = LiveOptions(
                model=self.model,
                language=self.language,
                smart_format=self.smart_format,
                punctuate=self.punctuate,
                interim_results=self.interim_results,
                vad_events=self.vad_events,
                encoding=self.encoding,
                sample_rate=self.sample_rate,
                channels=self.channels
            )

            # Create WebSocket connection
            self.connection = self.client.listen.websocket.v("1")

            # Register event handlers
            self.connection.on(LiveTranscriptionEvents.Open, self._on_open)
            self.connection.on(LiveTranscriptionEvents.Transcript, self._on_message)
            self.connection.on(LiveTranscriptionEvents.Error, self._on_error)
            self.connection.on(LiveTranscriptionEvents.Close, self._on_close)

            # Start connection
            await self.connection.start(options)

            logger.info("Streaming connection started")

        except Exception as e:
            logger.error(f"Failed to start streaming: {e}")
            raise RuntimeError(f"Failed to start streaming: {e}")

    async def send_audio(self, audio_data: bytes):
        """
        Send audio data to Deepgram for transcription.

        Args:
            audio_data: Audio data as bytes

        Raises:
            RuntimeError: If not connected
        """
        if not self.is_connected:
            raise RuntimeError("Not connected. Call start() first.")

        try:
            await self.connection.send(audio_data)
        except Exception as e:
            logger.error(f"Error sending audio: {e}")
            raise

    async def stop(self):
        """Stop the streaming connection."""
        if not self.is_connected:
            return

        try:
            # Send finish message
            if self.connection:
                await self.connection.finish()

            self.is_connected = False
            self.is_recording = False

            logger.info("Streaming connection stopped")

        except Exception as e:
            logger.error(f"Error stopping stream: {e}")

    def get_transcript(self, timeout: float = 1.0) -> Optional[str]:
        """
        Get a transcript from the queue.

        Args:
            timeout: Maximum time to wait for transcript (seconds)

        Returns:
            Transcript text, or None if timeout
        """
        try:
            return self.transcript_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def get_final_transcript(self) -> str:
        """
        Get the accumulated final transcript.

        Returns:
            Complete final transcript
        """
        return self.final_transcript

    def _on_open(self, *args, **kwargs):
        """Handle connection open event."""
        self.is_connected = True
        logger.info("WebSocket connection opened")

    def _on_message(self, *args, **kwargs):
        """Handle transcript message event."""
        try:
            # Extract result from args
            result = args[0] if args else kwargs.get('result')

            if not result:
                return

            # Extract transcript
            channel = result.channel
            if not channel or not channel.alternatives:
                return

            alternative = channel.alternatives[0]
            transcript = alternative.transcript

            if not transcript:
                return

            # Check if final result
            is_final = result.is_final if hasattr(result, 'is_final') else False

            if is_final:
                # Final result - accumulate
                self.final_transcript += " " + transcript
                logger.info(f"Final: '{transcript}'")
            else:
                # Interim result
                logger.debug(f"Interim: '{transcript}'")

            # Add to queue for consumers
            self.transcript_queue.put(transcript)

        except Exception as e:
            logger.error(f"Error processing message: {e}")

    def _on_error(self, *args, **kwargs):
        """Handle error event."""
        error = args[0] if args else kwargs.get('error', 'Unknown error')
        logger.error(f"WebSocket error: {error}")

    def _on_close(self, *args, **kwargs):
        """Handle connection close event."""
        self.is_connected = False
        logger.info("WebSocket connection closed")


def create_stt(
    api_key: str,
    model: str = "nova-2",
    language: str = "en-US"
) -> SpeechToText:
    """
    Create and return a Speech-to-Text instance.

    Args:
        api_key: Deepgram API key
        model: Model to use
        language: Language code

    Returns:
        SpeechToText instance
    """
    return SpeechToText(api_key, model, language)


def create_streaming_stt(
    api_key: str,
    model: str = "nova-2",
    language: str = "en-US",
    sample_rate: int = 16000
) -> StreamingSpeechToText:
    """
    Create and return a Streaming Speech-to-Text instance.

    Args:
        api_key: Deepgram API key
        model: Model to use
        language: Language code
        sample_rate: Audio sample rate (Hz)

    Returns:
        StreamingSpeechToText instance
    """
    return StreamingSpeechToText(
        api_key=api_key,
        model=model,
        language=language,
        sample_rate=sample_rate
    )
