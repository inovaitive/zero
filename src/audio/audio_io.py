"""
Audio input/output management using sounddevice.

This module handles microphone input, speaker output, and audio buffering.
Includes Voice Activity Detection (VAD) for automatic silence detection.

Using sounddevice for better macOS compatibility and cross-platform support.
"""

import wave
import struct
import time
from typing import Optional, List
from pathlib import Path
from collections import deque
import numpy as np
import sounddevice as sd

from src.core.logger import get_logger


logger = get_logger(__name__)

# Audio backend is sounddevice (cross-platform)
SOUNDDEVICE_AVAILABLE = True


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
            RuntimeError: If sounddevice is not available
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size
        self.device_index = device_index
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration

        # Audio stream for chunked recording
        self._stream: Optional[sd.InputStream] = None
        self._frames: deque = deque()  # Store chunks as numpy arrays in a queue
        self._all_frames: List[np.ndarray] = []  # Keep all frames for get_audio_data()
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
            # Open audio input stream with callback for chunked recording
            self._frames = deque()
            self._all_frames = []  # Keep all frames
            self._recording = True
            
            def audio_callback(indata, frames, time, status):
                """Callback to collect audio chunks."""
                if status:
                    logger.warning(f"Audio callback status: {status}")
                if self._recording:  # Access self directly (closure works in Python)
                    # Copy the data (indata is read-only) and add to both queues
                    frame_copy = indata.copy()
                    self._frames.append(frame_copy)
                    self._all_frames.append(frame_copy)  # Keep all frames

            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype='int16',
                blocksize=self.chunk_size,
                device=self.device_index,
                callback=audio_callback
            )
            
            self._stream.start()

            logger.info("Recording started")

        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            self._recording = False
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
            # Wait a bit to ensure we have data from callback
            max_wait = 0.1  # Maximum wait time in seconds
            wait_time = 0
            while not self._frames and wait_time < max_wait:
                time.sleep(0.01)
                wait_time += 0.01
            
            # Get a chunk from the queue
            if self._frames:
                # Pop the oldest chunk and convert to bytes
                chunk_array = self._frames.popleft()
                return chunk_array.flatten().astype(np.int16).tobytes()
            else:
                # If no frames yet, record synchronously for one chunk
                chunk_array = sd.rec(
                    int(self.chunk_size),
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    dtype='int16',
                    device=self.device_index
                )
                sd.wait()
                return chunk_array.flatten().astype(np.int16).tobytes()

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
            try:
                self._stream.stop()
                self._stream.close()
            except Exception as e:
                logger.error(f"Error stopping stream: {e}")
            finally:
                self._stream = None

        self._recording = False
        logger.info("Recording stopped")

    def get_audio_data(self) -> bytes:
        """
        Get recorded audio data as bytes.

        Returns:
            Complete audio data as bytes (int16)
        """
        # Use _all_frames which contains all recorded frames (not popped)
        if not self._all_frames:
            return b''

        # Concatenate all frames into a single array
        if self.channels == 1:
            # Mono: frames are shape (chunk_size, 1)
            audio_array = np.concatenate([frame.flatten() for frame in self._all_frames])
        else:
            # Stereo: frames are shape (chunk_size, channels)
            audio_array = np.concatenate(self._all_frames)
            audio_array = audio_array.flatten()

        # Ensure int16 dtype and convert to bytes
        return audio_array.astype(np.int16).tobytes()

    def get_audio_array(self) -> np.ndarray:
        """
        Get recorded audio data as numpy array.

        Returns:
            Complete audio data as numpy array
        """
        # Use _all_frames which contains all recorded frames (not popped)
        if not self._all_frames:
            return np.array([], dtype=np.int16)

        # Concatenate all frames
        if self.channels == 1:
            audio_array = np.concatenate([frame.flatten() for frame in self._all_frames])
        else:
            audio_array = np.concatenate(self._all_frames)
            audio_array = audio_array.flatten()

        return audio_array.astype(np.int16)

    def save_to_wav(self, filename: str):
        """
        Save recorded audio to WAV file.

        Args:
            filename: Output file path (relative paths default to data/cache/)
        """
        audio_data = self.get_audio_data()

        if not audio_data:
            logger.warning("No audio data to save")
            return

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

        # Write WAV file
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # int16 = 2 bytes
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_data)

        logger.info(f"Audio saved to {filename}")

    def __del__(self):
        """Cleanup on destruction."""
        try:
            self.stop()
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
            RuntimeError: If sounddevice is not available
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

        try:
            # Convert bytes to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            
            # Reshape for channels
            if self.channels > 1:
                audio_array = audio_array.reshape(-1, self.channels)
            
            # Play audio
            sd.play(audio_array, samplerate=sample_rate, device=self.device_index)
            sd.wait()  # Wait until playback is finished

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

        # Ensure correct shape
        if len(audio_array.shape) == 1 and self.channels > 1:
            # Reshape 1D array for multi-channel
            audio_array = audio_array.reshape(-1, self.channels)

        try:
            # Play audio
            sd.play(audio_array, samplerate=sample_rate, device=self.device_index)
            sd.wait()  # Wait until playback is finished

            logger.info(f"Played {len(audio_array)} samples")
        except Exception as e:
            logger.error(f"Error playing audio array: {e}")
            raise

    def play_file(self, filename: str):
        """
        Play audio from WAV file.

        Args:
            filename: WAV file path (relative or absolute)
        """
        try:
            # Convert to Path and resolve relative paths correctly
            filepath = Path(filename)
            
            # If relative path, check if it exists as-is first
            if filepath.exists():
                # Use as-is (might be relative or absolute)
                pass
            elif filepath.is_absolute() and not filepath.exists():
                # Absolute path doesn't exist
                raise FileNotFoundError(f"Audio file not found: {filename}")
            else:
                # Try resolving relative path
                resolved = filepath.resolve()
                if resolved.exists():
                    filepath = resolved
                else:
                    raise FileNotFoundError(f"Audio file not found: {filename}")
            
            # Read WAV file
            with wave.open(str(filepath), 'rb') as wf:
                sample_rate = wf.getframerate()
                channels = wf.getnchannels()
                audio_data = wf.readframes(wf.getnframes())

            # Convert to numpy array
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            
            # Reshape for channels
            if channels > 1:
                audio_array = audio_array.reshape(-1, channels)

            # Play audio
            sd.play(audio_array, samplerate=sample_rate, device=self.device_index)
            sd.wait()  # Wait until playback is finished

            logger.info(f"Played file: {filepath}")

        except Exception as e:
            logger.error(f"Error playing file {filename}: {e}")
            raise


def list_audio_devices() -> dict:
    """
    List all available audio devices.

    Returns:
        Dictionary with 'input' and 'output' device lists

    Raises:
        RuntimeError: If sounddevice is not available
    """
    devices = {
        'input': [],
        'output': []
    }

    try:
        # Query all devices
        all_devices = sd.query_devices()
        
        for i, device in enumerate(all_devices):
            # Check if input device
            if device['max_input_channels'] > 0:
                devices['input'].append({
                    'index': i,
                    'name': device['name'],
                    'channels': device['max_input_channels'],
                    'sample_rate': int(device['default_samplerate'])
                })

            # Check if output device
            if device['max_output_channels'] > 0:
                devices['output'].append({
                    'index': i,
                    'name': device['name'],
                    'channels': device['max_output_channels'],
                    'sample_rate': int(device['default_samplerate'])
                })

    except Exception as e:
        logger.error(f"Error querying audio devices: {e}")
        raise RuntimeError(f"Failed to list audio devices: {e}")

    return devices


def get_default_devices() -> dict:
    """
    Get default input and output devices.

    Returns:
        Dictionary with 'input' and 'output' device info

    Raises:
        RuntimeError: If sounddevice is not available
    """
    try:
        # Get default devices
        default_input = sd.query_devices(kind='input')
        default_output = sd.query_devices(kind='output')

        # Get device info
        all_devices = sd.query_devices()
        
        # Find indices of default devices
        input_index = None
        output_index = None
        
        for i, device in enumerate(all_devices):
            if device['name'] == default_input['name'] and device['hostapi'] == default_input['hostapi']:
                input_index = i
            if device['name'] == default_output['name'] and device['hostapi'] == default_output['hostapi']:
                output_index = i

        return {
            'input': {
                'index': input_index if input_index is not None else default_input['index'],
                'name': default_input['name'],
                'channels': default_input['max_input_channels'],
                'sample_rate': int(default_input['default_samplerate'])
            },
            'output': {
                'index': output_index if output_index is not None else default_output['index'],
                'name': default_output['name'],
                'channels': default_output['max_output_channels'],
                'sample_rate': int(default_output['default_samplerate'])
            }
        }
    except Exception as e:
        logger.error(f"Error getting default devices: {e}")
        raise RuntimeError(f"Failed to get default devices: {e}")
