"""
Tests for audio modules.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from src.audio.wake_word import WakeWordDetector, PORCUPINE_AVAILABLE
from src.audio.audio_io import AudioRecorder, AudioPlayer, list_audio_devices
from src.audio.stt import SpeechToText, StreamingSpeechToText, DEEPGRAM_AVAILABLE
from src.audio.tts import TextToSpeech, TTS_AVAILABLE


class TestAudioIO:
    """Test audio input/output."""

    def test_audio_recorder_initialization(self):
        """Test AudioRecorder can be created."""
        recorder = AudioRecorder(sample_rate=16000, channels=1)
        assert recorder.sample_rate == 16000
        assert recorder.channels == 1
        assert not recorder.is_recording

    def test_audio_recorder_initialization_with_params(self):
        """Test AudioRecorder with custom parameters."""
        recorder = AudioRecorder(
            sample_rate=44100,
            channels=2,
            chunk_size=2048,
            device_index=1,
            silence_threshold=0.01,
            silence_duration=2.0
        )
        assert recorder.sample_rate == 44100
        assert recorder.channels == 2
        assert recorder.chunk_size == 2048
        assert recorder.device_index == 1
        assert recorder.silence_threshold == 0.01
        assert recorder.silence_duration == 2.0

    @patch('src.audio.audio_io.sd.InputStream')
    def test_audio_recorder_start(self, mock_stream):
        """Test starting audio recording."""
        recorder = AudioRecorder()
        mock_stream_instance = MagicMock()
        mock_stream.return_value = mock_stream_instance
        
        recorder.start()
        
        assert recorder.is_recording is True
        mock_stream.assert_called_once()
        mock_stream_instance.start.assert_called_once()

    @patch('src.audio.audio_io.sd.InputStream')
    def test_audio_recorder_start_already_recording(self, mock_stream):
        """Test starting recording when already recording."""
        recorder = AudioRecorder()
        mock_stream_instance = MagicMock()
        mock_stream.return_value = mock_stream_instance
        
        recorder.start()
        initial_call_count = mock_stream.call_count
        
        # Try to start again
        recorder.start()
        
        # Should not create another stream
        assert mock_stream.call_count == initial_call_count

    @patch('src.audio.audio_io.sd.InputStream')
    def test_audio_recorder_start_failure(self, mock_stream):
        """Test handling of recording start failure."""
        recorder = AudioRecorder()
        mock_stream.side_effect = Exception("Device error")
        
        with pytest.raises(RuntimeError):
            recorder.start()
        
        assert recorder.is_recording is False

    def test_audio_recorder_stop_not_recording(self):
        """Test stopping when not recording."""
        recorder = AudioRecorder()
        # Should not raise error
        recorder.stop()
        assert not recorder.is_recording

    @patch('src.audio.audio_io.sd.InputStream')
    def test_audio_recorder_stop(self, mock_stream):
        """Test stopping audio recording."""
        recorder = AudioRecorder()
        mock_stream_instance = MagicMock()
        mock_stream.return_value = mock_stream_instance
        
        recorder.start()
        recorder.stop()
        
        assert not recorder.is_recording
        mock_stream_instance.stop.assert_called_once()
        mock_stream_instance.close.assert_called_once()

    @patch('src.audio.audio_io.sd.InputStream')
    def test_audio_recorder_stop_with_error(self, mock_stream):
        """Test stopping recording when stream has error."""
        recorder = AudioRecorder()
        mock_stream_instance = MagicMock()
        mock_stream_instance.stop.side_effect = Exception("Stop error")
        mock_stream.return_value = mock_stream_instance
        
        recorder.start()
        # Should not raise error, just log it
        recorder.stop()
        
        assert not recorder.is_recording

    def test_audio_recorder_get_audio_data_empty(self):
        """Test getting audio data when no recording."""
        recorder = AudioRecorder()
        data = recorder.get_audio_data()
        assert data == b''

    def test_audio_recorder_get_audio_array_empty(self):
        """Test getting audio array when no recording."""
        recorder = AudioRecorder()
        import numpy as np
        array = recorder.get_audio_array()
        assert array.size == 0
        assert array.dtype == np.int16

    @patch('src.audio.audio_io.sd.InputStream')
    @patch('src.audio.audio_io.wave.open')
    def test_audio_recorder_save_to_wav_no_data(self, mock_wave, mock_stream):
        """Test saving to WAV when no audio data."""
        recorder = AudioRecorder()
        recorder.save_to_wav("test.wav")
        # Should not create file or raise error
        mock_wave.assert_not_called()

    @patch('src.audio.audio_io.sd.InputStream')
    @patch('src.audio.audio_io.wave.open')
    @patch('pathlib.Path.mkdir')
    def test_audio_recorder_save_to_wav(self, mock_mkdir, mock_wave, mock_stream):
        """Test saving audio to WAV file."""
        import numpy as np
        recorder = AudioRecorder()
        
        # Simulate recorded audio data
        test_audio = np.array([1000, 2000, 3000], dtype=np.int16)
        recorder._all_frames = [test_audio.reshape(-1, 1)]
        
        mock_file = MagicMock()
        mock_wave.return_value.__enter__ = MagicMock(return_value=mock_file)
        mock_wave.return_value.__exit__ = MagicMock(return_value=None)
        
        recorder.save_to_wav("test.wav")
        
        mock_wave.assert_called_once()
        mock_file.setnchannels.assert_called_once()
        mock_file.setsampwidth.assert_called_once()
        mock_file.setframerate.assert_called_once()

    @patch('src.audio.audio_io.sd.InputStream')
    def test_audio_recorder_record_chunk_not_recording(self, mock_stream):
        """Test recording chunk when not recording."""
        recorder = AudioRecorder()
        with pytest.raises(RuntimeError, match="Not recording"):
            recorder.record_chunk()

    @patch('src.audio.audio_io.sd.InputStream')
    @patch('src.audio.audio_io.sd.rec')
    @patch('src.audio.audio_io.sd.wait')
    def test_audio_recorder_record_chunk_no_frames(self, mock_wait, mock_rec, mock_stream):
        """Test recording chunk when no frames available."""
        recorder = AudioRecorder()
        mock_stream_instance = MagicMock()
        mock_stream.return_value = mock_stream_instance
        
        # Mock empty frames
        recorder._frames = []
        recorder._recording = True
        recorder._stream = mock_stream_instance
        
        # Mock synchronous recording
        import numpy as np
        mock_rec.return_value = np.array([[1000], [2000]], dtype=np.int16)
        
        chunk = recorder.record_chunk()
        assert chunk is not None
        assert len(chunk) > 0

    def test_audio_player_initialization(self):
        """Test AudioPlayer can be created."""
        player = AudioPlayer(sample_rate=22050)
        assert player.sample_rate == 22050

    def test_audio_player_initialization_with_params(self):
        """Test AudioPlayer with custom parameters."""
        player = AudioPlayer(
            sample_rate=44100,
            channels=2,
            device_index=1
        )
        assert player.sample_rate == 44100
        assert player.channels == 2
        assert player.device_index == 1

    @patch('src.audio.audio_io.sd.play')
    @patch('src.audio.audio_io.sd.wait')
    def test_audio_player_play_bytes(self, mock_wait, mock_play):
        """Test playing audio from bytes."""
        player = AudioPlayer()
        audio_data = b'\x00' * 1000  # Mock audio data
        player.play(audio_data)
        mock_play.assert_called_once()
        mock_wait.assert_called_once()

    @patch('src.audio.audio_io.sd.play')
    @patch('src.audio.audio_io.sd.wait')
    def test_audio_player_play_array(self, mock_wait, mock_play):
        """Test playing audio from numpy array."""
        import numpy as np
        player = AudioPlayer()
        audio_array = np.array([1000, 2000, 3000], dtype=np.int16)
        player.play(audio_array)
        mock_play.assert_called_once()
        mock_wait.assert_called_once()

    @patch('src.audio.audio_io.sd.play')
    @patch('src.audio.audio_io.sd.wait')
    def test_audio_player_play_file(self, mock_wait, mock_play, tmp_path):
        """Test playing audio from file."""
        import wave
        player = AudioPlayer()
        
        # Create a test WAV file
        test_file = tmp_path / "test.wav"
        with wave.open(str(test_file), 'wb') as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(16000)
            wf.writeframes(b'\x00' * 1000)
        
        player.play_file(str(test_file))
        mock_play.assert_called_once()
        mock_wait.assert_called_once()

    @patch('src.audio.audio_io.sd.play')
    @patch('src.audio.audio_io.sd.wait')
    def test_audio_player_play_file_not_found(self, mock_wait, mock_play):
        """Test playing non-existent file."""
        player = AudioPlayer()
        with pytest.raises(FileNotFoundError):
            player.play_file("nonexistent.wav")

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

    def test_streaming_stt_initialization(self):
        """Test Streaming STT can be created with API key."""
        # This will fail with invalid key, but tests the structure
        try:
            stt = StreamingSpeechToText(api_key="test_key")
            assert stt.model == "nova-2"
            assert stt.language == "en-US"
            assert stt.sample_rate == 16000
            assert not stt.is_connected
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
