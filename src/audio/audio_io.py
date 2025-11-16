"""
Audio input/output management using sounddevice.

This module handles microphone input, speaker output, and audio buffering.
Includes Voice Activity Detection (VAD) for automatic silence detection.

Using sounddevice instead of PyAudio for better macOS compatibility.
"""

import wave
import struct
from typing import Optional, List
from pathlib import Path
import sounddevice as sd
import soundfile as sf
import numpy as np

from src.core.logger import get_logger


logger = get_logger(__name__)


class AudioRecorder:
    """
    Records audio from microphone with automatic silence detection.

    Features:
    - Voice Activity Detection (VAD) to auto-stop recording
    - Configurable sample rate and channels
    - Save to WAV file
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        chunk_size: int = 512,
        device_index: Optional[int] = None,
        silence_threshold: float = 0.02,
        silence_duration: float = 1.5
    ):
        """
        Initialize audio recorder.

        Args:
            sample_rate: Audio sample rate (Hz)
            channels: Number of audio channels (1=mono, 2=stereo)
            chunk_size: Audio chunk size (samples per buffer)
            device_index: Microphone device index (None = default)
            silence_threshold: RMS threshold for silence detection
            silence_duration: Duration of silence before auto-stop (seconds)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.device_index = device_index
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration

        self._frames: List[np.ndarray] = []
        self._recording = False

        logger.info(
            f"Audio recorder initialized: {sample_rate}Hz, "
            f"{channels}ch, chunk={chunk_size}"
        )

    def start(self):
        """Start recording audio."""
        if self._recording:
            logger.warning("Already recording")
            return

        self._frames = []
        self._recording = True

        logger.info("Recording started")

    def record_chunk(self) -> np.ndarray:
        """
        Record one chunk of audio.

        Returns:
            Audio chunk as numpy array

        Raises:
            RuntimeError: If not recording
        """
        if not self._recording:
            raise RuntimeError("Not recording")

        # Record audio chunk
        data = sd.rec(
            self.chunk_size,
            samplerate=self.sample_rate,
            channels=self.channels,
            dtype='int16',
            device=self.device_index,
            blocking=True
        )

        # Squeeze to remove extra dimensions if mono
        if self.channels == 1:
            data = data.squeeze()

        self._frames.append(data)

        return data

    def record_until_silence(self, max_duration: float = 10.0) -> bytes:
        """
        Record audio until silence is detected or max duration reached.

        Args:
            max_duration: Maximum recording duration (seconds)

        Returns:
            Complete audio data as bytes (int16)
        """
        if not self._recording:
            self.start()

        logger.info("Recording until silence...")

        silence_chunks = int(self.silence_duration * self.sample_rate / self.chunk_size)
        silent_chunks_count = 0
        max_chunks = int(max_duration * self.sample_rate / self.chunk_size)
        chunks_recorded = 0

        while chunks_recorded < max_chunks:
            # Record chunk
            chunk = self.record_chunk()
            chunks_recorded += 1

            # Calculate RMS (volume level)
            rms = np.sqrt(np.mean(chunk.astype(float) ** 2))

            # Check for silence
            if rms < self.silence_threshold * 32768:  # Scale to int16 range
                silent_chunks_count += 1
                if silent_chunks_count >= silence_chunks:
                    logger.info(f"Silence detected after {chunks_recorded} chunks")
                    break
            else:
                silent_chunks_count = 0

        # Get complete audio data
        audio_data = self.get_audio_data()

        logger.info(
            f"Recording complete: {len(audio_data)} bytes, "
            f"{len(audio_data) / (self.sample_rate * 2):.2f}s"
        )

        return audio_data

    def stop(self):
        """Stop recording audio."""
        if not self._recording:
            return

        self._recording = False
        logger.info("Recording stopped")

    def get_audio_data(self) -> bytes:
        """
        Get recorded audio data as bytes.

        Returns:
            Complete audio data as bytes (int16)
        """
        if not self._frames:
            return b''

        # Concatenate all frames
        audio_array = np.concatenate(self._frames)

        # Convert to bytes
        return audio_array.tobytes()

    def get_audio_array(self) -> np.ndarray:
        """
        Get recorded audio data as numpy array.

        Returns:
            Complete audio data as numpy array
        """
        if not self._frames:
            return np.array([], dtype='int16')

        return np.concatenate(self._frames)

    def save_to_wav(self, filename: str):
        """
        Save recorded audio to WAV file.

        Args:
            filename: Output file path
        """
        audio_array = self.get_audio_array()

        # Convert int16 to float32 for soundfile
        audio_float = audio_array.astype(np.float32) / 32768.0

        sf.write(filename, audio_float, self.sample_rate)

        logger.info(f"Audio saved to {filename}")

    @property
    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self._recording


class AudioPlayer:
    """
    Plays audio through speakers.

    Supports playing from bytes, numpy arrays, or WAV files.
    """

    def __init__(
        self,
        sample_rate: int = 22050,
        channels: int = 1,
        device_index: Optional[int] = None
    ):
        """
        Initialize audio player.

        Args:
            sample_rate: Audio sample rate (Hz)
            channels: Number of audio channels
            device_index: Speaker device index (None = default)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.device_index = device_index

        logger.info(f"Audio player initialized: {sample_rate}Hz, {channels}ch")

    def play(self, audio_data: bytes, sample_rate: Optional[int] = None):
        """
        Play audio data.

        Args:
            audio_data: Audio data as bytes (int16)
            sample_rate: Sample rate (uses default if None)
        """
        if sample_rate is None:
            sample_rate = self.sample_rate

        # Convert bytes to numpy array
        audio_array = np.frombuffer(audio_data, dtype=np.int16)

        # Convert int16 to float32
        audio_float = audio_array.astype(np.float32) / 32768.0

        # Play audio
        sd.play(audio_float, samplerate=sample_rate, device=self.device_index)
        sd.wait()  # Wait until playback finishes

        logger.info(f"Played {len(audio_data)} bytes of audio")

    def play_array(self, audio_array: np.ndarray, sample_rate: Optional[int] = None):
        """
        Play audio from numpy array.

        Args:
            audio_array: Audio data as numpy array
            sample_rate: Sample rate (uses default if None)
        """
        if sample_rate is None:
            sample_rate = self.sample_rate

        # Convert to float if needed
        if audio_array.dtype == np.int16:
            audio_float = audio_array.astype(np.float32) / 32768.0
        else:
            audio_float = audio_array

        # Play audio
        sd.play(audio_float, samplerate=sample_rate, device=self.device_index)
        sd.wait()

        logger.info(f"Played {len(audio_array)} samples")

    def play_file(self, filename: str):
        """
        Play audio from WAV file.

        Args:
            filename: WAV file path
        """
        # Read audio file
        audio_data, sample_rate = sf.read(filename)

        # Play audio
        sd.play(audio_data, samplerate=sample_rate, device=self.device_index)
        sd.wait()

        logger.info(f"Played file: {filename}")


def list_audio_devices() -> dict:
    """
    List all available audio devices.

    Returns:
        Dictionary with 'input' and 'output' device lists
    """
    devices = {
        'input': [],
        'output': []
    }

    for i, device in enumerate(sd.query_devices()):
        if device['max_input_channels'] > 0:
            devices['input'].append({
                'index': i,
                'name': device['name'],
                'channels': device['max_input_channels'],
                'sample_rate': int(device['default_samplerate'])
            })

        if device['max_output_channels'] > 0:
            devices['output'].append({
                'index': i,
                'name': device['name'],
                'channels': device['max_output_channels'],
                'sample_rate': int(device['default_samplerate'])
            })

    return devices


def get_default_devices() -> dict:
    """
    Get default input and output devices.

    Returns:
        Dictionary with 'input' and 'output' device info
    """
    default_input = sd.query_devices(kind='input')
    default_output = sd.query_devices(kind='output')

    return {
        'input': {
            'index': default_input['index'] if isinstance(default_input, dict) else 0,
            'name': default_input['name'],
            'channels': default_input['max_input_channels'],
            'sample_rate': int(default_input['default_samplerate'])
        },
        'output': {
            'index': default_output['index'] if isinstance(default_output, dict) else 0,
            'name': default_output['name'],
            'channels': default_output['max_output_channels'],
            'sample_rate': int(default_output['default_samplerate'])
        }
    }
