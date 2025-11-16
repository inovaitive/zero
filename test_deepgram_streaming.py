#!/usr/bin/env python3
"""
Test script for Deepgram Streaming STT with PyAudio.

This script demonstrates real-time transcription using:
- PyAudio for microphone input
- Deepgram WebSocket API for streaming transcription

Requires:
- DEEPGRAM_API_KEY environment variable
- PyAudio installed
- Deepgram SDK installed
"""

import os
import sys
import asyncio
import time
from src.audio.stt import StreamingSpeechToText, DEEPGRAM_AVAILABLE
from src.audio.audio_io import AudioRecorder, PYAUDIO_AVAILABLE


async def test_streaming_transcription():
    """Test streaming transcription with microphone input."""
    print("=" * 60)
    print("Testing Deepgram Streaming STT with PyAudio")
    print("=" * 60)

    # Check dependencies
    if not PYAUDIO_AVAILABLE:
        print("❌ PyAudio is not available!")
        print("Install with: pip install pyaudio")
        return False

    if not DEEPGRAM_AVAILABLE:
        print("❌ Deepgram SDK is not available!")
        print("Install with: pip install deepgram-sdk")
        return False

    print("✅ PyAudio is available")
    print("✅ Deepgram SDK is available\n")

    # Get API key
    api_key = os.getenv("DEEPGRAM_API_KEY")
    if not api_key:
        print("❌ DEEPGRAM_API_KEY environment variable not set!")
        print("\nSet it with:")
        print("  export DEEPGRAM_API_KEY='your_api_key_here'")
        return False

    print("✅ Deepgram API key found\n")

    try:
        # Create streaming STT
        print("Creating Deepgram Streaming STT...")
        stt = StreamingSpeechToText(
            api_key=api_key,
            model="nova-2",
            language="en-US",
            sample_rate=16000,
            interim_results=True,
            vad_events=True
        )
        print("✅ Streaming STT created\n")

        # Start connection
        print("Connecting to Deepgram...")
        await stt.start()

        # Wait for connection
        await asyncio.sleep(1)

        if not stt.is_connected:
            print("❌ Failed to connect to Deepgram")
            return False

        print("✅ Connected to Deepgram WebSocket\n")

        # Create audio recorder
        print("Creating audio recorder...")
        recorder = AudioRecorder(
            sample_rate=16000,
            channels=1,
            chunk_size=8000  # 0.5 seconds of audio per chunk
        )
        recorder.start()
        print("✅ Audio recorder started\n")

        print("=" * 60)
        print("🎤 Speak into your microphone!")
        print("   Recording for 10 seconds...")
        print("   Interim results will show in real-time")
        print("=" * 60)
        print()

        # Record and stream for 10 seconds
        start_time = time.time()
        chunk_count = 0

        while time.time() - start_time < 10.0:
            # Record chunk
            chunk = recorder.record_chunk()
            chunk_count += 1

            # Send to Deepgram
            await stt.send_audio(chunk)

            # Check for transcripts (non-blocking)
            transcript = stt.get_transcript(timeout=0.01)
            if transcript:
                print(f"[{time.time() - start_time:.1f}s] {transcript}")

            # Small delay to prevent overwhelming
            await asyncio.sleep(0.01)

        print("\n" + "=" * 60)
        print("Recording complete!")
        print("=" * 60)

        # Stop recording
        recorder.stop()

        # Stop streaming
        await stt.stop()

        # Get any remaining transcripts
        await asyncio.sleep(0.5)
        while True:
            transcript = stt.get_transcript(timeout=0.1)
            if not transcript:
                break
            print(f"[final] {transcript}")

        # Get complete final transcript
        final = stt.get_final_transcript()

        print(f"\n✅ Streaming test completed!")
        print(f"   Chunks sent: {chunk_count}")
        print(f"   Duration: {time.time() - start_time:.2f}s")
        print(f"\n📝 Final Transcript:")
        print(f"   {final.strip() if final.strip() else '(no speech detected)'}")

        return True

    except Exception as e:
        print(f"\n❌ Streaming test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_basic_streaming():
    """Test basic streaming STT initialization."""
    print("=" * 60)
    print("Testing Basic Streaming STT")
    print("=" * 60)

    if not DEEPGRAM_AVAILABLE:
        print("❌ Deepgram SDK is not available!")
        return False

    api_key = os.getenv("DEEPGRAM_API_KEY", "test_key")

    try:
        print("Creating Streaming STT instance...")
        stt = StreamingSpeechToText(
            api_key=api_key,
            model="nova-2",
            language="en-US"
        )

        print("✅ Instance created successfully")
        print(f"   Model: {stt.model}")
        print(f"   Language: {stt.language}")
        print(f"   Sample Rate: {stt.sample_rate} Hz")
        print(f"   Connected: {stt.is_connected}")

        return True

    except ValueError as e:
        # Expected with invalid key
        if "Invalid" in str(e) or "API key" in str(e):
            print("✅ Validation working (rejected invalid key)")
            return True
        else:
            raise
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests."""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 8 + "Deepgram Streaming STT Test Suite" + " " * 16 + "║")
    print("╚" + "=" * 58 + "╝")
    print()

    results = []

    # Test 1: Basic initialization
    print("\nTest 1: Basic Initialization")
    results.append(("Basic Initialization", await test_basic_streaming()))

    # Test 2: Full streaming (only if API key available)
    if os.getenv("DEEPGRAM_API_KEY"):
        print("\n\nTest 2: Full Streaming Transcription")
        results.append(("Streaming Transcription", await test_streaming_transcription()))
    else:
        print("\n\n⚠️  Skipping streaming test (no DEEPGRAM_API_KEY)")
        print("   Set DEEPGRAM_API_KEY to run full streaming test")

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
    sys.exit(asyncio.run(main()))
