"""
Speech-to-Text using Deepgram API.

This module provides high-accuracy speech transcription with sub-second latency.
Supports both streaming and pre-recorded audio.
"""

from typing import Optional, Dict, Any
import asyncio
from pathlib import Path

try:
    from deepgram import (
        DeepgramClient,
        PrerecordedOptions,
        FileSource,
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
