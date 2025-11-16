"""
Audio input/output management.

This module handles microphone input, speaker output, and audio buffering.
Includes Voice Activity Detection (VAD) for automatic silence detection.
"""

import wave
import struct
from typing import Optional, List
from pathlib import Path
import pyaudio
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
        silence_threshold: float = 500.0,
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

        self.audio: Optional[pyaudio.PyAudio] = None
        self.stream: Optional[pyaudio.Stream] = None

        self._frames: List[bytes] = []
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

        # Initialize PyAudio
        self.audio = pyaudio.PyAudio()

        # Open stream
        self.stream = self.audio.open(
            format=pyaudio.paInt16,
            channels=self.channels,
            rate=self.sample_rate,
            input=True,
            input_device_index=self.device_index,
            frames_per_buffer=self.chunk_size
        )

        logger.info("Recording started")

    def record_chunk(self) -> bytes:
        """
        Record one chunk of audio.

        Returns:
            Audio chunk as bytes

        Raises:
            RuntimeError: If not recording
        """
        if not self._recording or not self.stream:
            raise RuntimeError("Not recording")

        data = self.stream.read(self.chunk_size, exception_on_overflow=False)
        self._frames.append(data)

        return data

    def record_until_silence(self, max_duration: float = 10.0) -> bytes:
        """
        Record audio until silence is detected or max duration reached.

        Args:
            max_duration: Maximum recording duration (seconds)

        Returns:
            Complete audio data as bytes
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
            rms = self._calculate_rms(chunk)

            # Check for silence
            if rms < self.silence_threshold:
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

        # Close stream
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None

        # Terminate PyAudio
        if self.audio:
            self.audio.terminate()
            self.audio = None

        logger.info("Recording stopped")

    def get_audio_data(self) -> bytes:
        """
        Get recorded audio data.

        Returns:
            Complete audio data as bytes
        """
        return b''.join(self._frames)

    def save_to_wav(self, filename: str):
        """
        Save recorded audio to WAV file.

        Args:
            filename: Output file path
        """
        audio_data = self.get_audio_data()

        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # 16-bit = 2 bytes
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_data)

        logger.info(f"Audio saved to {filename}")

    def _calculate_rms(self, audio_chunk: bytes) -> float:
        """
        Calculate RMS (Root Mean Square) of audio chunk.

        Args:
            audio_chunk: Audio data

        Returns:
            RMS value (volume level)
        """
        # Convert bytes to int16 array
        count = len(audio_chunk) // 2
        format_str = f"{count}h"
        shorts = struct.unpack(format_str, audio_chunk)

        # Calculate RMS
        sum_squares = sum(s ** 2 for s in shorts)
        rms = np.sqrt(sum_squares / count)

        return rms

    @property
    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self._recording

    def __del__(self):
        """Cleanup on deletion."""
        self.stop()


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

        # Initialize PyAudio
        audio = pyaudio.PyAudio()

        try:
            # Open stream
            stream = audio.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=sample_rate,
                output=True,
                output_device_index=self.device_index
            )

            # Play audio
            stream.write(audio_data)

            # Close stream
            stream.stop_stream()
            stream.close()

            logger.info(f"Played {len(audio_data)} bytes of audio")

        finally:
            audio.terminate()

    def play_file(self, filename: str):
        """
        Play audio from WAV file.

        Args:
            filename: WAV file path
        """
        with wave.open(filename, 'rb') as wf:
            # Read parameters
            channels = wf.getnchannels()
            sample_rate = wf.getframerate()
            audio_data = wf.readframes(wf.getnframes())

        # Initialize PyAudio
        audio = pyaudio.PyAudio()

        try:
            # Open stream
            stream = audio.open(
                format=audio.get_format_from_width(wf.getsampwidth()),
                channels=channels,
                rate=sample_rate,
                output=True,
                output_device_index=self.device_index
            )

            # Play audio
            stream.write(audio_data)

            # Close stream
            stream.stop_stream()
            stream.close()

            logger.info(f"Played file: {filename}")

        finally:
            audio.terminate()


def list_audio_devices() -> dict:
    """
    List all available audio devices.

    Returns:
        Dictionary with 'input' and 'output' device lists
    """
    audio = pyaudio.PyAudio()

    devices = {
        'input': [],
        'output': []
    }

    try:
        for i in range(audio.get_device_count()):
            device_info = audio.get_device_info_by_index(i)

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
        audio.terminate()

    return devices


def get_default_devices() -> dict:
    """
    Get default input and output devices.

    Returns:
        Dictionary with 'input' and 'output' device info
    """
    audio = pyaudio.PyAudio()

    try:
        default_input = audio.get_default_input_device_info()
        default_output = audio.get_default_output_device_info()

        return {
            'input': {
                'index': default_input['index'],
                'name': default_input['name'],
                'channels': default_input['maxInputChannels'],
                'sample_rate': int(default_input['defaultSampleRate'])
            },
            'output': {
                'index': default_output['index'],
                'name': default_output['name'],
                'channels': default_output['maxOutputChannels'],
                'sample_rate': int(default_output['defaultSampleRate'])
            }
        }
    finally:
        audio.terminate()
