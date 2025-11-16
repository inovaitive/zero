#!/usr/bin/env python3
"""
Quick test script for PyAudio audio recording.

This script tests the basic audio I/O functionality without requiring
Deepgram API credentials.
"""

import sys
import time
from src.audio.audio_io import (
    AudioRecorder,
    AudioPlayer,
    list_audio_devices,
    get_default_devices,
    SOUNDDEVICE_AVAILABLE,
    PYAUDIO_AVAILABLE,  # Backward compatibility
)


def test_audio_devices():
    """Test listing audio devices."""
    print("=" * 60)
    print("Testing Audio Device Enumeration")
    print("=" * 60)

    if not SOUNDDEVICE_AVAILABLE:
        print("❌ SoundDevice is not available!")
        print("Install with: uv pip install sounddevice")
        return False

    print("✅ SoundDevice is available\n")

    # List all devices
    devices = list_audio_devices()

    print(f"Found {len(devices['input'])} input device(s):")
    for dev in devices["input"]:
        print(f"  [{dev['index']}] {dev['name']}")
        print(f"      Channels: {dev['channels']}, Sample Rate: {dev['sample_rate']} Hz")

    print(f"\nFound {len(devices['output'])} output device(s):")
    for dev in devices["output"]:
        print(f"  [{dev['index']}] {dev['name']}")
        print(f"      Channels: {dev['channels']}, Sample Rate: {dev['sample_rate']} Hz")

    # Get default devices
    try:
        defaults = get_default_devices()
        print(f"\n✅ Default input: {defaults['input']['name']}")
        print(f"✅ Default output: {defaults['output']['name']}")
    except Exception as e:
        print(f"\n⚠️  Could not get default devices: {e}")

    print()
    return True


def test_recording():
    """Test audio recording."""
    print("=" * 60)
    print("Testing Audio Recording")
    print("=" * 60)

    if not SOUNDDEVICE_AVAILABLE:
        print("❌ SoundDevice is not available!")
        return False, None

    try:
        # Create recorder
        print("Creating AudioRecorder...")
        recorder = AudioRecorder(sample_rate=16000, channels=1, chunk_size=1024)
        print("✅ AudioRecorder created successfully\n")

        # Test recording
        print("🎤 Recording for 3 seconds (speak something)...")
        print("Starting in 1 second...")
        time.sleep(1)

        recorder.start()
        print("Recording NOW!")

        # Record for 3 seconds
        start_time = time.time()
        chunks_recorded = 0

        while time.time() - start_time < 3.0:
            chunk = recorder.record_chunk()
            chunks_recorded += 1

        recorder.stop()

        # Get recorded data
        audio_data = recorder.get_audio_data()
        audio_array = recorder.get_audio_array()

        print(f"\n✅ Recording completed!")
        print(f"   Chunks recorded: {chunks_recorded}")
        print(f"   Total bytes: {len(audio_data)}")
        print(f"   Array shape: {audio_array.shape}")
        print(f"   Duration: {len(audio_data) / (16000 * 2):.2f} seconds")

        # Save to file (will default to data/cache/)
        output_file = "test_recording.wav"
        recorder.save_to_wav(output_file)
        print(f"✅ Saved to {output_file}")

        return True, output_file

    except Exception as e:
        print(f"\n❌ Recording test failed: {e}")
        import traceback

        traceback.print_exc()
        return False, None


def test_playback(audio_file):
    """Test audio playback."""
    print("\n" + "=" * 60)
    print("Testing Audio Playback")
    print("=" * 60)

    if not SOUNDDEVICE_AVAILABLE:
        print("❌ SoundDevice is not available!")
        return False

    try:
        # Create player
        print("Creating AudioPlayer...")
        player = AudioPlayer(sample_rate=16000, channels=1)
        print("✅ AudioPlayer created successfully\n")

        # Play the recorded file
        print(f"🔊 Playing back {audio_file}...")
        player.play_file(audio_file)
        print("✅ Playback completed!")

        return True

    except Exception as e:
        print(f"\n❌ Playback test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_silence_detection():
    """Test recording with silence detection."""
    print("\n" + "=" * 60)
    print("Testing Voice Activity Detection (VAD)")
    print("=" * 60)

    if not SOUNDDEVICE_AVAILABLE:
        print("❌ SoundDevice is not available!")
        return False

    try:
        print("Creating AudioRecorder with VAD...")
        recorder = AudioRecorder(
            sample_rate=16000, channels=1, silence_threshold=0.02, silence_duration=1.5
        )
        print("✅ AudioRecorder created with VAD\n")

        print("🎤 Speak something, then stay silent for 1.5 seconds...")
        print("Starting in 1 second...")
        time.sleep(1)

        print("Recording NOW! (max 10 seconds)")
        audio_data = recorder.record_until_silence(max_duration=10.0)
        recorder.stop()

        duration = len(audio_data) / (16000 * 2)
        print(f"\n✅ VAD test completed!")
        print(f"   Recording stopped after silence detected")
        print(f"   Duration: {duration:.2f} seconds")

        # Save (will default to data/cache/)
        output_file = "test_vad_recording.wav"
        recorder.save_to_wav(output_file)
        print(f"✅ Saved to {output_file}")

        return True

    except Exception as e:
        print(f"\n❌ VAD test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "SoundDevice Audio I/O Test Suite" + " " * 18 + "║")
    print("╚" + "=" * 58 + "╝")
    print()

    results = []

    # Test 1: Device enumeration
    results.append(("Device Enumeration", test_audio_devices()))

    # Test 2: Recording
    recording_result, audio_file = test_recording()
    results.append(("Audio Recording", recording_result))

    # Test 3: Playback (if recording succeeded)
    if recording_result and audio_file:
        results.append(("Audio Playback", test_playback(audio_file)))

    # Test 4: VAD
    results.append(("Voice Activity Detection", test_silence_detection()))

    # Summary
    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    passed = sum(1 for _, r in results if r)
    total = len(results)

    print(f"\nPassed: {passed}/{total}")

    if passed == total:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
