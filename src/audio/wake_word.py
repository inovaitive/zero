"""
Wake word detection using Picovoice Porcupine.

This module provides always-on wake word detection with low CPU usage.
Supports keywords like "jarvis", "computer", "hey google", etc.
"""

import struct
import threading
from typing import Optional, Callable
import pyaudio

try:
    import pvporcupine
    PORCUPINE_AVAILABLE = True
except ImportError:
    PORCUPINE_AVAILABLE = False

from src.core.logger import get_logger


logger = get_logger(__name__)


class WakeWordDetector:
    """
    Wake word detector using Picovoice Porcupine.

    Continuously listens for a wake word in the background with low CPU usage.
    When the wake word is detected, triggers a callback function.
    """

    def __init__(
        self,
        access_key: str,
        keyword: str = "jarvis",
        sensitivity: float = 0.5,
        on_detected: Optional[Callable] = None
    ):
        """
        Initialize wake word detector.

        Args:
            access_key: Picovoice access key
            keyword: Wake word to detect (jarvis, computer, etc.)
            sensitivity: Detection sensitivity (0.0 to 1.0)
            on_detected: Callback function when wake word is detected

        Raises:
            RuntimeError: If pvporcupine is not available
            ValueError: If access_key is invalid
        """
        if not PORCUPINE_AVAILABLE:
            raise RuntimeError(
                "pvporcupine not available. Install with: pip install pvporcupine"
            )

        self.access_key = access_key
        self.keyword = keyword
        self.sensitivity = sensitivity
        self.on_detected = on_detected

        # Porcupine instance
        self.porcupine: Optional[pvporcupine.Porcupine] = None

        # Audio stream
        self.audio: Optional[pyaudio.PyAudio] = None
        self.stream: Optional[pyaudio.Stream] = None

        # Threading
        self._listening = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()

        logger.info(f"Wake word detector initialized with keyword: {keyword}")

    def start(self):
        """Start listening for wake word in background thread."""
        with self._lock:
            if self._listening:
                logger.warning("Wake word detector already running")
                return

            try:
                # Initialize Porcupine
                self.porcupine = pvporcupine.create(
                    access_key=self.access_key,
                    keywords=[self.keyword],
                    sensitivities=[self.sensitivity]
                )

                logger.info(f"Porcupine initialized with keyword: {self.keyword}")
                logger.info(f"Frame length: {self.porcupine.frame_length}")
                logger.info(f"Sample rate: {self.porcupine.sample_rate}")

                # Initialize PyAudio
                self.audio = pyaudio.PyAudio()

                # Open audio stream
                self.stream = self.audio.open(
                    rate=self.porcupine.sample_rate,
                    channels=1,
                    format=pyaudio.paInt16,
                    input=True,
                    frames_per_buffer=self.porcupine.frame_length
                )

                # Start listening thread
                self._listening = True
                self._thread = threading.Thread(target=self._listen_loop, daemon=True)
                self._thread.start()

                logger.info("Wake word detection started")

            except Exception as e:
                logger.error(f"Failed to start wake word detector: {e}")
                self._cleanup()
                raise

    def stop(self):
        """Stop listening for wake word."""
        with self._lock:
            if not self._listening:
                return

            logger.info("Stopping wake word detection...")
            self._listening = False

            # Wait for thread to finish
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=2.0)

            self._cleanup()
            logger.info("Wake word detection stopped")

    def _listen_loop(self):
        """
        Main listening loop (runs in background thread).

        Continuously reads audio from microphone and checks for wake word.
        """
        logger.info("Wake word listening loop started")

        try:
            while self._listening:
                # Read audio frame
                pcm = self.stream.read(
                    self.porcupine.frame_length,
                    exception_on_overflow=False
                )

                # Convert to int16 array
                pcm = struct.unpack_from(
                    "h" * self.porcupine.frame_length,
                    pcm
                )

                # Check for wake word
                keyword_index = self.porcupine.process(pcm)

                if keyword_index >= 0:
                    logger.info(f"Wake word '{self.keyword}' detected!")

                    # Trigger callback
                    if self.on_detected:
                        try:
                            self.on_detected()
                        except Exception as e:
                            logger.error(f"Error in wake word callback: {e}")

        except Exception as e:
            logger.error(f"Error in wake word listening loop: {e}")
            self._listening = False

        logger.info("Wake word listening loop ended")

    def _cleanup(self):
        """Clean up audio resources."""
        # Close audio stream
        if self.stream:
            try:
                self.stream.stop_stream()
                self.stream.close()
            except Exception as e:
                logger.error(f"Error closing audio stream: {e}")
            finally:
                self.stream = None

        # Terminate PyAudio
        if self.audio:
            try:
                self.audio.terminate()
            except Exception as e:
                logger.error(f"Error terminating PyAudio: {e}")
            finally:
                self.audio = None

        # Delete Porcupine
        if self.porcupine:
            try:
                self.porcupine.delete()
            except Exception as e:
                logger.error(f"Error deleting Porcupine: {e}")
            finally:
                self.porcupine = None

    @property
    def is_listening(self) -> bool:
        """Check if detector is currently listening."""
        return self._listening

    def __del__(self):
        """Cleanup on deletion."""
        self.stop()


def create_wake_word_detector(
    access_key: str,
    keyword: str = "jarvis",
    sensitivity: float = 0.5,
    on_detected: Optional[Callable] = None
) -> WakeWordDetector:
    """
    Create and return a wake word detector instance.

    Args:
        access_key: Picovoice access key
        keyword: Wake word to detect
        sensitivity: Detection sensitivity (0.0 to 1.0)
        on_detected: Callback when wake word detected

    Returns:
        WakeWordDetector instance
    """
    return WakeWordDetector(access_key, keyword, sensitivity, on_detected)
