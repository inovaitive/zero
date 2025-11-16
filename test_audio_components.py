#!/usr/bin/env python3
"""
Manual test script for audio components.

Tests each audio component individually to verify setup.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.config import get_config
from src.core.logger import setup_logger
from src.audio.audio_io import AudioRecorder, AudioPlayer, list_audio_devices, get_default_devices
from src.audio.wake_word import WakeWordDetector, PORCUPINE_AVAILABLE
from src.audio.stt import SpeechToText, DEEPGRAM_AVAILABLE
from src.audio.tts import TextToSpeech, TTS_AVAILABLE


def test_audio_devices():
    """Test 1: List available audio devices."""
    print("\n" + "="*60)
    print("TEST 1: Audio Devices")
    print("="*60)

    print("\n📋 Listing audio devices...")

    devices = list_audio_devices()

    print(f"\n🎤 Input devices ({len(devices['input'])}):")
    for i, device in enumerate(devices['input']):
        print(f"  [{device['index']}] {device['name']}")
        print(f"      Channels: {device['channels']}, Sample rate: {device['sample_rate']}Hz")

    print(f"\n🔊 Output devices ({len(devices['output'])}):")
    for i, device in enumerate(devices['output']):
        print(f"  [{device['index']}] {device['name']}")
        print(f"      Channels: {device['channels']}, Sample rate: {device['sample_rate']}Hz")

    print("\n📌 Default devices:")
    defaults = get_default_devices()
    print(f"  Input: {defaults['input']['name']}")
    print(f"  Output: {defaults['output']['name']}")

    print("\n✅ Audio devices test complete")


def test_audio_recording():
    """Test 2: Record and playback audio."""
    print("\n" + "="*60)
    print("TEST 2: Audio Recording & Playback")
    print("="*60)

    print("\n🎤 Recording 3 seconds of audio...")
    print("Say something!")

    recorder = AudioRecorder(sample_rate=16000)
    recorder.start()

    import time
    for i in range(3, 0, -1):
        print(f"  {i}...")
        time.sleep(1)

    recorder.stop()
    audio_data = recorder.get_audio_data()

    print(f"\n✅ Recorded {len(audio_data)} bytes")

    # Save to file
    test_file = "data/cache/test_recording.wav"
    recorder.save_to_wav(test_file)
    print(f"📁 Saved to {test_file}")

    # Playback
    print("\n🔊 Playing back recording...")
    player = AudioPlayer(sample_rate=16000)
    player.play(audio_data, sample_rate=16000)

    print("\n✅ Audio recording test complete")


def test_wake_word():
    """Test 3: Wake word detection."""
    print("\n" + "="*60)
    print("TEST 3: Wake Word Detection")
    print("="*60)

    if not PORCUPINE_AVAILABLE:
        print("\n❌ pvporcupine not installed")
        print("   Install with: uv pip install pvporcupine")
        return

    try:
        config = get_config()
        access_key = config.get('wake_word.access_key')

        if not access_key or access_key.startswith('your_'):
            print("\n❌ Picovoice access key not configured")
            print("   Set PICOVOICE_ACCESS_KEY in .env file")
            return

        print("\n👂 Initializing wake word detector...")
        print(f"   Keyword: jarvis")
        print(f"   Sensitivity: 0.5")

        detected = [False]

        def on_detected():
            detected[0] = True
            print("\n🎯 WAKE WORD DETECTED!")

        detector = WakeWordDetector(
            access_key=access_key,
            keyword="jarvis",
            sensitivity=0.5,
            on_detected=on_detected
        )

        detector.start()

        print("\n🎤 Listening for wake word 'jarvis'...")
        print("   Say 'jarvis' to test detection")
        print("   Press Ctrl+C to stop")

        import time
        try:
            while not detected[0]:
                time.sleep(0.1)

            detector.stop()
            print("\n✅ Wake word detection test complete")

        except KeyboardInterrupt:
            print("\n\n⏹️  Stopped by user")
            detector.stop()

    except Exception as e:
        print(f"\n❌ Wake word test failed: {e}")


def test_stt():
    """Test 4: Speech-to-text."""
    print("\n" + "="*60)
    print("TEST 4: Speech-to-Text (Deepgram)")
    print("="*60)

    if not DEEPGRAM_AVAILABLE:
        print("\n❌ deepgram-sdk not installed")
        print("   Install with: uv pip install deepgram-sdk")
        return

    try:
        config = get_config()
        api_key = config.get('stt.api_key')

        if not api_key or api_key.startswith('your_'):
            print("\n❌ Deepgram API key not configured")
            print("   Set DEEPGRAM_API_KEY in .env file")
            return

        print("\n🎤 Recording audio for transcription...")
        print("Say something (will auto-stop after silence):")

        # Record audio
        recorder = AudioRecorder(sample_rate=16000)
        audio_data = recorder.record_until_silence(max_duration=10.0)
        recorder.stop()

        print(f"\n✅ Recorded {len(audio_data)} bytes")

        # Transcribe
        print("\n📝 Transcribing with Deepgram...")

        stt = SpeechToText(api_key=api_key, model="nova-2")
        transcript = stt.transcribe_bytes(audio_data, sample_rate=16000)

        if transcript:
            print(f"\n✨ Transcription: '{transcript}'")
            print("\n✅ Speech-to-text test complete")
        else:
            print("\n❌ No transcription returned")

    except Exception as e:
        print(f"\n❌ STT test failed: {e}")


def test_tts():
    """Test 5: Text-to-speech."""
    print("\n" + "="*60)
    print("TEST 5: Text-to-Speech (Coqui TTS)")
    print("="*60)

    if not TTS_AVAILABLE:
        print("\n❌ TTS not installed")
        print("   Install with: uv pip install TTS")
        return

    try:
        print("\n🗣️  Initializing TTS (female voice)...")
        print("   Model: ljspeech/tacotron2-DDC")
        print("   This may take a minute on first run (downloading model)...")

        tts = TextToSpeech(
            model_name="tts_models/en/ljspeech/tacotron2-DDC",
            use_cuda=False,
            speed=1.0
        )

        test_texts = [
            "Hello. I am ZERO, your personal AI assistant.",
            "All systems are operational, sir.",
            "How may I assist you today?"
        ]

        for i, text in enumerate(test_texts, 1):
            print(f"\n🔊 Speaking ({i}/{len(test_texts)}): '{text}'")
            success = tts.speak(text)

            if not success:
                print(f"   ❌ Failed to speak")
            else:
                print(f"   ✅ Complete")

            import time
            time.sleep(1)

        print("\n✅ Text-to-speech test complete")

    except Exception as e:
        print(f"\n❌ TTS test failed: {e}")


def main():
    """Run all audio tests."""
    print("\n╔══════════════════════════════════════════════════════╗")
    print("║      ZERO Audio Components - Manual Tests           ║")
    print("╚══════════════════════════════════════════════════════╝")

    # Setup logging
    setup_logger('zero', 'WARNING')

    tests = [
        ("Audio Devices", test_audio_devices),
        ("Recording & Playback", test_audio_recording),
        ("Wake Word Detection", test_wake_word),
        ("Speech-to-Text", test_stt),
        ("Text-to-Speech", test_tts),
    ]

    print("\nAvailable tests:")
    for i, (name, _) in enumerate(tests, 1):
        print(f"  {i}. {name}")
    print("  0. Run all tests")

    try:
        choice = input("\nSelect test (0-5): ").strip()

        if choice == "0":
            for name, test_func in tests:
                test_func()
        elif choice.isdigit() and 1 <= int(choice) <= len(tests):
            _, test_func = tests[int(choice) - 1]
            test_func()
        else:
            print("Invalid choice")

    except KeyboardInterrupt:
        print("\n\nAborted by user")

    print("\n" + "="*60)
    print("Tests complete!")
    print("="*60)


if __name__ == '__main__':
    main()
