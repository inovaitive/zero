# Key Files Involved in Response Pipeline

## Core Engine & Orchestration

| File | Purpose | Key Methods/Functions |
|------|---------|----------------------|
| `/home/user/zero/main.py` | Entry point, CLI/voice mode selection | `ZeroAssistant.start()`, `_run_voice_mode()`, `_run_cli_mode()` |
| `/home/user/zero/src/core/engine.py` | Main event loop, pipeline orchestration | `ZeroEngine._event_loop()`, `process_text_command()`, `_handle_conversation_loop()` |

## Audio Pipeline

| File | Purpose | Key Methods/Functions | Latency |
|------|---------|----------------------|---------|
| `/home/user/zero/src/audio/audio_io.py` | Microphone input, speaker output | `AudioRecorder.start()`, `record_chunk()`, `AudioPlayer.play()` | 0-30s recording, real-time playback |
| `/home/user/zero/src/audio/stt.py` | Deepgram API speech-to-text | `transcribe_bytes()`, `transcribe_file()` | 0.5-3.0s |
| `/home/user/zero/src/audio/tts.py` | Coqui TTS text-to-speech | `synthesize()`, `CachedTTS.synthesize()` | 0.5-3.0s (cache hit: 50-100ms) |
| `/home/user/zero/src/audio/wake_word.py` | pvporcupine wake word detection | `detect()`, `start()` | Background continuous |

## Natural Language Understanding (Brain)

| File | Purpose | Key Methods/Functions | Latency |
|------|---------|----------------------|---------|
| `/home/user/zero/src/brain/intent.py` | Intent classification (pattern → spaCy → LLM) | `classify()`, `_classify_with_patterns()`, `_classify_with_spacy()`, `_classify_with_cloud()` | 0.01-5.0s |
| `/home/user/zero/src/brain/entities.py` | Entity extraction (locations, times, durations) | `extract()`, `_extract_duration()`, `_extract_location()` | 0.05-0.3s |
| `/home/user/zero/src/brain/context.py` | Conversation context & history management | `get_context_for_query()`, `update()`, `get_history()` | 0.01-0.02s |
| `/home/user/zero/src/brain/llm.py` | OpenAI GPT integration for conversational fallback | `chat()`, `classify_intent()` | 1.0-5.0s+ |

## Skills System

| File | Purpose | Key Methods/Functions | Latency |
|------|---------|----------------------|---------|
| `/home/user/zero/src/skills/skill_manager.py` | Skill routing & execution | `route_intent()`, `_find_skill_for_intent()`, `_execute_skill()` | 0.001-0.1s (routing only) |
| `/home/user/zero/src/skills/base_skill.py` | Base class for all skills | `execute()`, `validate_entities()` | - |
| `/home/user/zero/src/skills/weather_skill.py` | Weather info (OpenWeatherMap API) | `execute()` | 1-3s (API call) |
| `/home/user/zero/src/skills/timer_skill.py` | Timer/alarm management | `execute()` | <1ms (in-memory) |
| `/home/user/zero/src/skills/app_control_skill.py` | Open/close/list applications | `execute()` | 100-500ms (system calls) |
| `/home/user/zero/src/skills/search_skill.py` | Web search | `execute()` | 2-10s (browser automation) |
| `/home/user/zero/src/skills/small_talk_skill.py` | Small talk & general conversation | `execute()` | 0.1s-5.0s (LLM if enabled) |

## State & Configuration

| File | Purpose | Key Methods/Functions |
|------|---------|----------------------|
| `/home/user/zero/src/core/state.py` | State machine (IDLE, LISTENING, PROCESSING, etc.) | `transition_to()`, `get_state()` |
| `/home/user/zero/src/core/config.py` | Configuration loading & validation | `get_config()`, `Config.get()` |
| `/home/user/zero/src/core/logger.py` | Logging infrastructure | `setup_logger()`, `ColoredFormatter` |

## User Interface

| File | Purpose | Key Methods/Functions |
|------|---------|----------------------|
| `/home/user/zero/src/ui/cli.py` | Rich terminal UI | `create_cli()`, `add_message()`, `add_log()` |
| `/home/user/zero/src/ui/tray.py` | System tray integration | `create_tray()` |

## Configuration Files

| File | Purpose |
|------|---------|
| `/home/user/zero/config/config.yaml` | Main configuration (models, APIs, thresholds) |

## Test Files (for latency measurement)

| File | Purpose |
|------|---------|
| `/home/user/zero/tests/test_integration.py` | Integration tests with latency tracking |
| `/home/user/zero/demo_phase8.py` | Interactive demo showing latency metrics |

---

## Critical Bottleneck File Locations

### 1. **STT Latency Bottleneck**
   - **File:** `src/audio/stt.py::transcribe_bytes()` (line 86-143)
   - **Issue:** Deepgram API call blocks entire pipeline

### 2. **TTS Latency Bottleneck**
   - **File:** `src/audio/tts.py::synthesize()` (line 88-131)
   - **Issue:** Scales linearly with response text, blocks audio playback

### 3. **Pause Detection Latency**
   - **File:** `src/core/engine.py::_record_with_pause_detection()` (line 614-701)
   - **Issue:** Hard-coded 1.0s pause wait (line 637)

### 4. **LLM Fallback Latency**
   - **File:** `src/brain/intent.py::_classify_with_cloud()` (line 390-454)
   - **Issue:** Synchronous OpenAI API call
   - **Also:** `src/brain/llm.py::chat()` (line 173-241) for conversational responses

### 5. **spaCy NLU Latency**
   - **Files:** `src/brain/intent.py` (line 236-245, 346-388)
   - **Files:** `src/brain/entities.py` (line 90-96)
   - **Issue:** Model inference only when pattern confidence < 0.8

---

## Key Performance Configuration Points

**File:** `/home/user/zero/config/config.yaml`

```yaml
# Lines 26-34: STT Configuration
stt:
  model: "nova-2"           # Latency: ~1-2s
  timeout: 10               # Max wait for API response
  
# Lines 39-49: TTS Configuration  
tts:
  model: "tacotron2-DDC"    # Latency: ~1-3s (scales w/ text)
  use_cuda: false           # GPU disabled (could speed up ~2-3x)
  cache_enabled: true       # Cache hit: 50-100ms
  
# Lines 54-67: NLU Configuration
nlu:
  local:
    confidence_threshold: 0.8    # Triggers LLM fallback if below
  cloud:
    enabled: true                # Enable/disable GPT fallback
    model: "gpt-4"               # Change to gpt-3.5-turbo for speed
    
# Lines 144-154: Audio Configuration
audio:
  input:
    silence_duration: 1.5        # 1.5s before recording stops
    
# Lines 158-162: Performance Settings
performance:
  max_latency: 3.0  # Target (not enforced, informational)
```

