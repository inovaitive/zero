"""
Text-to-Speech using Coqui TTS.

This module provides high-quality neural text-to-speech synthesis
with female voice and J.A.R.V.I.S.-appropriate tone.
"""

import os
from typing import Optional
from pathlib import Path
import numpy as np
import tempfile

try:
    from TTS.api import TTS
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False

from src.core.logger import get_logger
from src.audio.audio_io import AudioPlayer


logger = get_logger(__name__)


class TextToSpeech:
    """
    Text-to-Speech using Coqui TTS.

    Generates natural-sounding speech from text with configurable voice,
    speed, and quality settings.
    """

    def __init__(
        self,
        model_name: str = "tts_models/en/ljspeech/tacotron2-DDC",
        vocoder_name: Optional[str] = "vocoder_models/en/ljspeech/hifigan_v2",
        use_cuda: bool = False,
        speed: float = 1.0
    ):
        """
        Initialize Text-to-Speech.

        Args:
            model_name: TTS model name (female voice recommended)
            vocoder_name: Vocoder model name (for quality)
            use_cuda: Use GPU acceleration if available
            speed: Speech speed multiplier (0.5 = slower, 2.0 = faster)

        Raises:
            RuntimeError: If TTS is not available
        """
        if not TTS_AVAILABLE:
            raise RuntimeError(
                "TTS (Coqui) not available. Install with: pip install TTS"
            )

        self.model_name = model_name
        self.vocoder_name = vocoder_name
        self.use_cuda = use_cuda
        self.speed = speed

        # Initialize TTS
        try:
            logger.info(f"Loading TTS model: {model_name}")

            # Suppress TTS logs
            os.environ["TTS_LOG_LEVEL"] = "ERROR"

            # Initialize TTS with model and vocoder
            if vocoder_name:
                self.tts = TTS(model_name=model_name, vocoder_name=vocoder_name)
            else:
                self.tts = TTS(model_name=model_name)

            # Move to GPU if requested
            if use_cuda:
                try:
                    self.tts.to("cuda")
                    logger.info("TTS using GPU acceleration")
                except Exception as e:
                    logger.warning(f"Could not use CUDA: {e}")

            logger.info("TTS initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize TTS: {e}")
            raise RuntimeError(f"TTS initialization failed: {e}")

        # Audio player for playback
        self.player = AudioPlayer(sample_rate=22050)

    def synthesize(self, text: str) -> Optional[bytes]:
        """
        Synthesize speech from text.

        Args:
            text: Text to convert to speech

        Returns:
            Audio data as bytes, or None if synthesis failed
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for TTS")
            return None

        try:
            logger.info(f"Synthesizing: '{text}'")

            # Create temporary file for output
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_path = temp_file.name

            # Synthesize to WAV file
            self.tts.tts_to_file(
                text=text,
                file_path=temp_path,
                speed=self.speed
            )

            # Read audio data
            with open(temp_path, "rb") as f:
                # Skip WAV header (44 bytes)
                f.seek(44)
                audio_data = f.read()

            # Clean up temp file
            os.unlink(temp_path)

            logger.info(f"Synthesized {len(audio_data)} bytes of audio")

            return audio_data

        except Exception as e:
            logger.error(f"TTS synthesis error: {e}")
            return None

    def speak(self, text: str) -> bool:
        """
        Synthesize and play speech from text.

        Args:
            text: Text to speak

        Returns:
            True if successful, False otherwise
        """
        audio_data = self.synthesize(text)

        if audio_data:
            try:
                self.player.play(audio_data)
                return True
            except Exception as e:
                logger.error(f"Error playing audio: {e}")
                return False

        return False

    def save_to_file(self, text: str, filename: str) -> bool:
        """
        Synthesize speech and save to WAV file.

        Args:
            text: Text to convert to speech
            filename: Output WAV file path

        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Saving TTS to {filename}")

            self.tts.tts_to_file(
                text=text,
                file_path=filename,
                speed=self.speed
            )

            logger.info(f"TTS saved to {filename}")
            return True

        except Exception as e:
            logger.error(f"Error saving TTS: {e}")
            return False

    def list_available_models(self) -> list:
        """
        List all available TTS models.

        Returns:
            List of model names
        """
        try:
            return TTS().list_models()
        except Exception as e:
            logger.error(f"Error listing models: {e}")
            return []

    @property
    def sample_rate(self) -> int:
        """Get TTS output sample rate."""
        return 22050  # Standard for most TTS models


class CachedTTS(TextToSpeech):
    """
    Text-to-Speech with response caching.

    Caches synthesized audio to avoid re-generating common phrases.
    """

    def __init__(
        self,
        model_name: str = "tts_models/en/ljspeech/tacotron2-DDC",
        vocoder_name: Optional[str] = "vocoder_models/en/ljspeech/hifigan_v2",
        use_cuda: bool = False,
        speed: float = 1.0,
        cache_dir: Optional[str] = None
    ):
        """
        Initialize cached TTS.

        Args:
            model_name: TTS model name
            vocoder_name: Vocoder model name
            use_cuda: Use GPU acceleration
            speed: Speech speed multiplier
            cache_dir: Directory for cache files (None = use data/cache/tts)
        """
        super().__init__(model_name, vocoder_name, use_cuda, speed)

        # Cache directory
        if cache_dir is None:
            cache_dir = Path(__file__).parent.parent.parent / "data" / "cache" / "tts"
        else:
            cache_dir = Path(cache_dir)

        cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir = cache_dir

        logger.info(f"TTS cache directory: {cache_dir}")

    def synthesize(self, text: str) -> Optional[bytes]:
        """
        Synthesize speech with caching.

        Args:
            text: Text to convert to speech

        Returns:
            Audio data as bytes, or None if synthesis failed
        """
        if not text or not text.strip():
            return None

        # Generate cache key (hash of text)
        import hashlib
        cache_key = hashlib.md5(text.encode()).hexdigest()
        cache_file = self.cache_dir / f"{cache_key}.raw"

        # Check cache
        if cache_file.exists():
            logger.debug(f"TTS cache hit for: '{text}'")
            with open(cache_file, "rb") as f:
                return f.read()

        # Synthesize
        audio_data = super().synthesize(text)

        # Save to cache
        if audio_data:
            with open(cache_file, "wb") as f:
                f.write(audio_data)
            logger.debug(f"TTS cached: '{text}'")

        return audio_data


def create_tts(
    model_name: str = "tts_models/en/ljspeech/tacotron2-DDC",
    use_cuda: bool = False,
    use_cache: bool = True,
    speed: float = 1.0
) -> TextToSpeech:
    """
    Create and return a TTS instance.

    Args:
        model_name: TTS model name (female voice)
        use_cuda: Use GPU acceleration
        use_cache: Use caching for common phrases
        speed: Speech speed multiplier

    Returns:
        TextToSpeech or CachedTTS instance
    """
    vocoder_name = "vocoder_models/en/ljspeech/hifigan_v2"

    if use_cache:
        return CachedTTS(
            model_name=model_name,
            vocoder_name=vocoder_name,
            use_cuda=use_cuda,
            speed=speed
        )
    else:
        return TextToSpeech(
            model_name=model_name,
            vocoder_name=vocoder_name,
            use_cuda=use_cuda,
            speed=speed
        )
