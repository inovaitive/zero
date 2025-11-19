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
from src.core.profiler import profile_method, get_profiler
from src.audio.audio_io import AudioPlayer
import io
import wave


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
        use_cuda: bool = False,
        speed: float = 1.0
    ):
        """
        Initialize Text-to-Speech.

        Args:
            model_name: TTS model name (female voice recommended)
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
        self.use_cuda = use_cuda
        self.speed = speed

        # Initialize TTS
        try:
            logger.info(f"Loading TTS model: {model_name}")

            # Suppress TTS logs
            os.environ["TTS_LOG_LEVEL"] = "ERROR"

            # Initialize TTS (vocoder is automatically selected in TTS 0.22.0+)
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

    @profile_method("tts.synthesize")
    def synthesize(self, text: str) -> Optional[bytes]:
        """
        Synthesize speech from text using in-memory processing.

        Args:
            text: Text to convert to speech

        Returns:
            Audio data as bytes (PCM), or None if synthesis failed
        """
        if not text or not text.strip():
            logger.warning("Empty text provided for TTS")
            return None

        profiler = get_profiler()

        try:
            logger.info(f"Synthesizing: '{text}'")

            with profiler.measure("tts.synthesis"):
                # Synthesize to numpy array (in-memory, faster)
                try:
                    # Try to synthesize to numpy array directly (TTS 0.22.0+)
                    wav_audio = self.tts.tts(text=text, speed=self.speed)

                    # Convert to bytes
                    if wav_audio is not None:
                        # wav_audio is a numpy array, convert to PCM bytes
                        import numpy as np
                        # Normalize to 16-bit PCM range
                        audio_int16 = (wav_audio * 32767).astype(np.int16)
                        audio_data = audio_int16.tobytes()

                        logger.info(f"Synthesized {len(audio_data)} bytes of audio (in-memory)")
                        return audio_data
                    else:
                        raise ValueError("TTS returned None")

                except (AttributeError, TypeError):
                    # Fallback to file-based synthesis for older TTS versions
                    logger.debug("Using file-based synthesis (fallback)")
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

                    logger.info(f"Synthesized {len(audio_data)} bytes of audio (file-based)")
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
            filename: Output WAV file path (relative paths default to data/cache/)

        Returns:
            True if successful, False otherwise
        """
        try:
            # Default to data/cache/ for relative paths
            filepath = Path(filename)
            if not filepath.is_absolute():
                # Ensure data/cache directory exists
                cache_dir = Path("data/cache")
                cache_dir.mkdir(parents=True, exist_ok=True)
                # Use data/cache/ as default location for relative paths
                filepath = cache_dir / filepath.name
                filename = str(filepath)

            # Ensure parent directory exists
            filepath.parent.mkdir(parents=True, exist_ok=True)

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
    Supports pre-warming cache with common phrases for instant responses.
    """

    # Common phrases to pre-cache for J.A.R.V.I.S. personality
    COMMON_PHRASES = [
        "Certainly, sir.",
        "Certainly.",
        "Right away, sir.",
        "Of course.",
        "One moment, sir.",
        "I'm on it.",
        "Processing.",
        "Understood.",
        "My apologies, sir.",
        "I'm afraid I don't have that information.",
        "How may I assist you?",
        "Good morning, sir.",
        "Good afternoon, sir.",
        "Good evening, sir.",
        "At your service.",
        "I'm ready when you are.",
        "Will there be anything else?",
        "Very well, sir.",
    ]

    def __init__(
        self,
        model_name: str = "tts_models/en/ljspeech/tacotron2-DDC",
        use_cuda: bool = False,
        speed: float = 1.0,
        cache_dir: Optional[str] = None,
        pre_cache_common: bool = True
    ):
        """
        Initialize cached TTS.

        Args:
            model_name: TTS model name
            use_cuda: Use GPU acceleration
            speed: Speech speed multiplier
            cache_dir: Directory for cache files (None = use data/cache/tts)
            pre_cache_common: Pre-cache common phrases on init
        """
        super().__init__(model_name, use_cuda, speed)

        # Cache directory
        if cache_dir is None:
            cache_dir = Path(__file__).parent.parent.parent / "data" / "cache" / "tts"
        else:
            cache_dir = Path(cache_dir)

        cache_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir = cache_dir
        self.cache_hits = 0
        self.cache_misses = 0

        logger.info(f"TTS cache directory: {cache_dir}")

        # Pre-cache common phrases for instant responses
        if pre_cache_common:
            self.warm_cache()

    @profile_method("tts.synthesize_cached")
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
            self.cache_hits += 1
            logger.debug(f"TTS cache hit ({self.cache_hits}/{self.cache_hits + self.cache_misses}): '{text}'")
            with open(cache_file, "rb") as f:
                return f.read()

        # Cache miss - synthesize
        self.cache_misses += 1
        audio_data = super().synthesize(text)

        # Save to cache
        if audio_data:
            with open(cache_file, "wb") as f:
                f.write(audio_data)
            logger.debug(f"TTS cached: '{text}'")

        return audio_data

    def warm_cache(self, phrases: Optional[list] = None):
        """
        Pre-cache common phrases for instant responses.

        Args:
            phrases: List of phrases to cache (None = use COMMON_PHRASES)
        """
        if phrases is None:
            phrases = self.COMMON_PHRASES

        logger.info(f"Warming TTS cache with {len(phrases)} common phrases...")

        cached_count = 0
        for phrase in phrases:
            # Check if already cached
            import hashlib
            cache_key = hashlib.md5(phrase.encode()).hexdigest()
            cache_file = self.cache_dir / f"{cache_key}.raw"

            if not cache_file.exists():
                # Synthesize and cache
                audio_data = super().synthesize(phrase)
                if audio_data:
                    with open(cache_file, "wb") as f:
                        f.write(audio_data)
                    cached_count += 1

        logger.info(f"TTS cache warmed: {cached_count} new phrases cached")

    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        total_files = len(list(self.cache_dir.glob("*.raw")))
        return {
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'total_cached_phrases': total_files,
            'hit_rate': self.cache_hits / (self.cache_hits + self.cache_misses) if (self.cache_hits + self.cache_misses) > 0 else 0.0
        }


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
    if use_cache:
        return CachedTTS(
            model_name=model_name,
            use_cuda=use_cuda,
            speed=speed
        )
    else:
        return TextToSpeech(
            model_name=model_name,
            use_cuda=use_cuda,
            speed=speed
        )
