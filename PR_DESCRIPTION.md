# Pull Request: Fix PyAudio to sounddevice Migration

## Problem

Phase 1 audio components were using PyAudio, which caused import errors on macOS:
```
ImportError: dlopen(.../_portaudio.cpython-39-darwin.so, 0x0002):
symbol not found in flat namespace '_PaMacCore_SetupChannelMap'
```

Initial attempts to fix with `brew install portaudio` didn't resolve the issue. The root cause is complex PortAudio C library linking issues on macOS.

## Solution

Migrated entire audio stack from PyAudio to **sounddevice**, which provides:
- ✅ Better cross-platform compatibility (especially macOS)
- ✅ No C library compilation/linking issues
- ✅ Cleaner API with numpy arrays
- ✅ Active maintenance and better documentation
- ✅ Same functionality with simpler code

## Changes

### Dependencies
- **Removed**: `pyaudio==0.2.14`
- **Added**: `sounddevice==0.4.6`, `soundfile==0.12.1`, `numpy>=1.20.0`
- Updated: `pyproject.toml`, `requirements.txt`

### Code Changes

**`src/audio/audio_io.py` (358 lines rewritten)**
- `AudioRecorder`: Now uses `sd.rec()` instead of PyAudio stream
- `AudioPlayer`: Now uses `sd.play()` instead of PyAudio stream
- Changed internal data format from `bytes` to `numpy.ndarray`
- Added `get_audio_array()` method for numpy array access
- Added `play_array()` method for numpy array playback
- Simplified `list_audio_devices()` and `get_default_devices()`
- Maintained same public API for backward compatibility

**`src/audio/wake_word.py` (216 lines rewritten)**
- Replaced PyAudio stream with `sd.InputStream`
- Changed from polling loop to callback-based processing
- Removed `_listen_loop()` thread (sounddevice handles threading)
- Added `_audio_callback()` for real-time audio processing
- Cleaner resource management

**`PHASE1_COMPLETE.md`**
- Removed PortAudio installation instructions
- Updated troubleshooting section
- Added note about sounddevice advantages

### API Compatibility
All public APIs remain unchanged:
- `AudioRecorder.start()`, `stop()`, `record_until_silence()`
- `AudioRecorder.get_audio_data()` still returns bytes
- `AudioPlayer.play()`, `play_file()`
- `WakeWordDetector.start()`, `stop()`

## Test Plan

### Manual Testing
```bash
# 1. Sync dependencies
uv sync

# 2. Run comprehensive audio tests
uv run python test_audio_components.py

# Test individual components:
# - Option 1: Audio Devices (verify mic/speaker detection)
# - Option 2: Recording & Playback (3-second test)
# - Option 3: Wake Word Detection (requires Picovoice key)
# - Option 4: Speech-to-Text (requires Deepgram key)
# - Option 5: Text-to-Speech (auto-downloads model)
```

### Expected Results
- ✅ No import errors on macOS
- ✅ All audio devices detected correctly
- ✅ Recording and playback work smoothly
- ✅ Wake word detection responds to "jarvis"
- ✅ No performance degradation

## Benefits

1. **Fixes macOS compatibility** - No more PortAudio linking errors
2. **Simplified installation** - No system dependencies needed
3. **Better performance** - sounddevice uses efficient callbacks
4. **Cleaner code** - 65 fewer lines, simpler logic
5. **Future-proof** - Active library with better maintenance

## Migration Notes

For developers:
- If using `AudioRecorder.get_audio_data()`, it still returns `bytes`
- New method `get_audio_array()` returns `numpy.ndarray` for advanced use
- No changes needed in existing code that uses these classes

---

## Recent Updates

**Python Version Fix (commit 9ec3b03)**
- Upgraded Python requirement from 3.9 to 3.10+
- Deepgram SDK 3.2.0 requires Python 3.10+ for `match` statement support
- Fixes `SyntaxError: invalid syntax` on line 252 of deepgram/client.py

---

**Tested on**: macOS with sounddevice 0.4.6, Python 3.10+
**Related commits**: 9d7ab3f, 9ec3b03
**Branch**: `claude/zero-assistant-planning-01LgqqSKyNncLLBjUjrNJwu9` → `main`
