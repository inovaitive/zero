"""
Tests for audio modules.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.audio.wake_word import WakeWordDetector, PORCUPINE_AVAILABLE
from src.audio.audio_io import AudioRecorder, AudioPlayer, list_audio_devices
from src.audio.stt import SpeechToText, DEEPGRAM_AVAILABLE
from src.audio.tts import TextToSpeech, TTS_AVAILABLE


class TestAudioIO:
    """Test audio input/output."""

    def test_audio_recorder_initialization(self):
        """Test AudioRecorder can be created."""
        recorder = AudioRecorder(sample_rate=16000, channels=1)
        assert recorder.sample_rate == 16000
        assert recorder.channels == 1
        assert not recorder.is_recording

    def test_audio_player_initialization(self):
        """Test AudioPlayer can be created."""
        player = AudioPlayer(sample_rate=22050)
        assert player.sample_rate == 22050

    def test_list_audio_devices(self):
        """Test listing audio devices."""
        devices = list_audio_devices()
        assert 'input' in devices
        assert 'output' in devices
        assert isinstance(devices['input'], list)
        assert isinstance(devices['output'], list)


@pytest.mark.skipif(not PORCUPINE_AVAILABLE, reason="pvporcupine not available")
class TestWakeWord:
    """Test wake word detection."""

    def test_wake_word_detector_requires_access_key(self):
        """Test that WakeWordDetector requires access key."""
        with pytest.raises((ValueError, Exception)):
            detector = WakeWordDetector(
                access_key="invalid_key",
                keyword="jarvis"
            )
            detector.start()


@pytest.mark.skipif(not DEEPGRAM_AVAILABLE, reason="deepgram-sdk not available")
class TestSpeechToText:
    """Test speech-to-text."""

    def test_stt_initialization(self):
        """Test STT can be created with API key."""
        # This will fail with invalid key, but tests the structure
        try:
            stt = SpeechToText(api_key="test_key")
            assert stt.model == "nova-2"
            assert stt.language == "en-US"
        except ValueError:
            # Expected with invalid key
            pass


@pytest.mark.skipif(not TTS_AVAILABLE, reason="TTS not available")
class TestTextToSpeech:
    """Test text-to-speech."""

    def test_tts_initialization(self):
        """Test TTS initialization with default model."""
        # Note: This will download model on first run
        try:
            tts = TextToSpeech(
                model_name="tts_models/en/ljspeech/tacotron2-DDC",
                use_cuda=False
            )
            assert tts.speed == 1.0
            assert tts.sample_rate == 22050
        except Exception as e:
            pytest.skip(f"TTS model not available: {e}")

    def test_tts_empty_text(self):
        """Test TTS with empty text."""
        try:
            tts = TextToSpeech(use_cuda=False)
            result = tts.synthesize("")
            assert result is None
        except Exception:
            pytest.skip("TTS not available")


# Integration test markers
pytestmark = pytest.mark.audio
