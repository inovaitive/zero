"""
Audio input/output management using PyAudio.

This module handles microphone input, speaker output, and audio buffering.
Includes Voice Activity Detection (VAD) for automatic silence detection.

Using PyAudio for cross-platform audio support with Deepgram streaming integration.
"""

import wave
import struct
from typing import Optional, List
from pathlib import Path
import numpy as np

try:
    import pyaudio
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False

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
        chunk_size: int = 1024,
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

        Raises:
            RuntimeError: If PyAudio is not available
        """
        if not PYAUDIO_AVAILABLE:
            raise RuntimeError(
                "PyAudio not available. Install with: pip install pyaudio"
            )

        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.device_index = device_index
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration

        # Initialize PyAudio
        self._pyaudio = pyaudio.PyAudio()
        self._stream: Optional[pyaudio.Stream] = None
        self._frames: List[bytes] = []
        self._recording = False

        logger.info(
            f"Audio recorder initialized: {sample_rate}Hz, "
            f"{channels}ch, chunk={chunk_size}"
        )

    def start(self):
        """
        Start recording audio.

        Raises:
            RuntimeError: If stream fails to open
        """
        if self._recording:
            logger.warning("Already recording")
            return

        try:
            # Open audio stream
            self._stream = self._pyaudio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                input_device_index=self.device_index,
                frames_per_buffer=self.chunk_size
            )

            self._frames = []
            self._recording = True

            logger.info("Recording started")

        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            raise RuntimeError(f"Failed to start recording: {e}")

    def record_chunk(self) -> bytes:
        """
        Record one chunk of audio.

        Returns:
            Audio chunk as bytes (int16)

        Raises:
            RuntimeError: If not recording
        """
        if not self._recording or not self._stream:
            raise RuntimeError("Not recording")

        try:
            # Read audio chunk
            data = self._stream.read(self.chunk_size, exception_on_overflow=False)
            self._frames.append(data)

            return data

        except Exception as e:
            logger.error(f"Error recording chunk: {e}")
            raise

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

            # Convert bytes to numpy array for RMS calculation
            chunk_array = np.frombuffer(chunk, dtype=np.int16)

            # Calculate RMS (volume level)
            rms = np.sqrt(np.mean(chunk_array.astype(float) ** 2))

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

        # Stop and close stream
        if self._stream:
            self._stream.stop_stream()
            self._stream.close()
            self._stream = None

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
        return b''.join(self._frames)

    def get_audio_array(self) -> np.ndarray:
        """
        Get recorded audio data as numpy array.

        Returns:
            Complete audio data as numpy array
        """
        audio_bytes = self.get_audio_data()
        if not audio_bytes:
            return np.array([], dtype=np.int16)

        return np.frombuffer(audio_bytes, dtype=np.int16)

    def save_to_wav(self, filename: str):
        """
        Save recorded audio to WAV file.

        Args:
            filename: Output file path
        """
        audio_data = self.get_audio_data()

        if not audio_data:
            logger.warning("No audio data to save")
            return

        # Write WAV file
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(self._pyaudio.get_sample_size(pyaudio.paInt16))
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_data)

        logger.info(f"Audio saved to {filename}")

    def __del__(self):
        """Cleanup on destruction."""
        try:
            if self._stream:
                self._stream.stop_stream()
                self._stream.close()
            if self._pyaudio:
                self._pyaudio.terminate()
        except:
            pass

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

        Raises:
            RuntimeError: If PyAudio is not available
        """
        if not PYAUDIO_AVAILABLE:
            raise RuntimeError(
                "PyAudio not available. Install with: pip install pyaudio"
            )

        self.sample_rate = sample_rate
        self.channels = channels
        self.device_index = device_index

        # Initialize PyAudio
        self._pyaudio = pyaudio.PyAudio()

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

        try:
            # Open output stream
            stream = self._pyaudio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=sample_rate,
                output=True,
                output_device_index=self.device_index
            )

            # Play audio
            stream.write(audio_data)

            # Cleanup
            stream.stop_stream()
            stream.close()

            logger.info(f"Played {len(audio_data)} bytes of audio")

        except Exception as e:
            logger.error(f"Error playing audio: {e}")
            raise

    def play_array(self, audio_array: np.ndarray, sample_rate: Optional[int] = None):
        """
        Play audio from numpy array.

        Args:
            audio_array: Audio data as numpy array (int16)
            sample_rate: Sample rate (uses default if None)
        """
        if sample_rate is None:
            sample_rate = self.sample_rate

        # Convert to int16 if needed
        if audio_array.dtype != np.int16:
            audio_array = (audio_array * 32768.0).astype(np.int16)

        # Convert to bytes
        audio_data = audio_array.tobytes()

        # Play audio
        self.play(audio_data, sample_rate)

        logger.info(f"Played {len(audio_array)} samples")

    def play_file(self, filename: str):
        """
        Play audio from WAV file.

        Args:
            filename: WAV file path
        """
        try:
            # Read WAV file
            with wave.open(filename, 'rb') as wf:
                sample_rate = wf.getframerate()
                channels = wf.getnchannels()
                audio_data = wf.readframes(wf.getnframes())

            # Open output stream
            stream = self._pyaudio.open(
                format=self._pyaudio.get_format_from_width(2),  # 2 bytes = int16
                channels=channels,
                rate=sample_rate,
                output=True,
                output_device_index=self.device_index
            )

            # Play audio
            stream.write(audio_data)

            # Cleanup
            stream.stop_stream()
            stream.close()

            logger.info(f"Played file: {filename}")

        except Exception as e:
            logger.error(f"Error playing file {filename}: {e}")
            raise

    def __del__(self):
        """Cleanup on destruction."""
        try:
            if self._pyaudio:
                self._pyaudio.terminate()
        except:
            pass


def list_audio_devices() -> dict:
    """
    List all available audio devices.

    Returns:
        Dictionary with 'input' and 'output' device lists

    Raises:
        RuntimeError: If PyAudio is not available
    """
    if not PYAUDIO_AVAILABLE:
        raise RuntimeError(
            "PyAudio not available. Install with: pip install pyaudio"
        )

    devices = {
        'input': [],
        'output': []
    }

    p = pyaudio.PyAudio()

    try:
        for i in range(p.get_device_count()):
            device_info = p.get_device_info_by_index(i)

            if device_info['maxInputChannels'] > 0:
                devices['input'].append({
                    'index': i,
                    'name': device_info['name'],
                    'channels': device_info['maxInputChannels'],
                    'sample_rate': int(device_info['defaultSampleRate'])
                })

            if device_info['maxOutputChannels'] > 0:
                devices['output'].append({
                    'index': i,
                    'name': device_info['name'],
                    'channels': device_info['maxOutputChannels'],
                    'sample_rate': int(device_info['defaultSampleRate'])
                })
    finally:
        p.terminate()

    return devices


def get_default_devices() -> dict:
    """
    Get default input and output devices.

    Returns:
        Dictionary with 'input' and 'output' device info

    Raises:
        RuntimeError: If PyAudio is not available
    """
    if not PYAUDIO_AVAILABLE:
        raise RuntimeError(
            "PyAudio not available. Install with: pip install pyaudio"
        )

    p = pyaudio.PyAudio()

    try:
        default_input_index = p.get_default_input_device_info()['index']
        default_output_index = p.get_default_output_device_info()['index']

        default_input = p.get_device_info_by_index(default_input_index)
        default_output = p.get_device_info_by_index(default_output_index)

        return {
            'input': {
                'index': default_input_index,
                'name': default_input['name'],
                'channels': default_input['maxInputChannels'],
                'sample_rate': int(default_input['defaultSampleRate'])
            },
            'output': {
                'index': default_output_index,
                'name': default_output['name'],
                'channels': default_output['maxOutputChannels'],
                'sample_rate': int(default_output['defaultSampleRate'])
            }
        }
    finally:
        p.terminate()
