# ZERO Voice Assistant - Response Delay Investigation Report

## Executive Summary
The ZERO voice assistant has a clearly defined sequential pipeline from voice input to voice output. The end-to-end latency includes STT (Deepgram API), NLU (intent classification), Entity extraction, Skill execution, and TTS (Coqui) synthesis. Several stages are inherently blocking and could be optimized.

---

## 1. MAIN EXECUTION FLOW

### Entry Point: `main.py`
- Initializes `ZeroAssistant`
- Sets up logging, state manager, UI (CLI/tray)
- Calls `engine.initialize_components()` (BLOCKING - loads all models)
- Runs either `_run_cli_mode()` or `_run_voice_mode()`

### Voice Mode Flow (Primary Path)
```
_run_voice_mode()
  ├─ engine.start() → spawns event loop thread
  ├─ _event_loop() → IDLE state, waits for wake word
  └─ _handle_voice_command() → triggered on wake word
      ├─ Greeting TTS synthesis + playback
      └─ _handle_conversation_loop() → continuous conversation
          ├─ Record audio with pause detection (1 second pause)
          ├─ STT (Deepgram) - BLOCKING
          ├─ _process_conversational()
          │  ├─ Intent classification
          │  ├─ Entity extraction
          │  ├─ Skill execution
          │  └─ LLM chat (if skill fails)
          └─ TTS synthesis + playback
```

### Text/CLI Mode Flow (Secondary Path)
```
_run_cli_mode()
  └─ engine.process_text_command()
      ├─ Intent classification
      ├─ Entity extraction
      ├─ Skill routing & execution
      └─ Context update
```

---

## 2. COMPLETE PIPELINE BREAKDOWN

### Stage 1: Audio Recording (Voice Mode Only)
**File:** `src/audio/audio_io.py::AudioRecorder`
- Chunk-based recording with RMS-based silence detection
- **Key Method:** `_record_with_pause_detection()` (engine.py:614-701)
- **Latency:** 1.0-10.0+ seconds (user-controlled via pause_wait)
  - Waits 1.5s for initial silence
  - Then waits 1.0s pause before finalizing
  - Max duration: 30.0s
- **Blocking:** YES (main thread waits for audio chunks)
- **Potential Issue:** Hard-coded 1.0s pause wait might cause unnecessary delays

### Stage 2: Speech-to-Text (STT)
**File:** `src/audio/stt.py::SpeechToText`
- **Provider:** Deepgram API (prerecorded mode)
- **Model:** nova-2 (default, fastest)
- **Key Method:** `transcribe_bytes()` (line 86-143)
- **Latency:** 0.5-3.0 seconds (network + API processing)
  - Network round-trip: ~100-500ms
  - API processing: ~400-2500ms
  - Timeout: 10 seconds (configurable)
- **Blocking:** YES (waits for HTTP response)
- **Potential Issues:**
  - Network dependency (no offline capability)
  - API rate limits and quota
  - No streaming optimization in voice mode
  - Timeout set to 10s (could cause delays if slow)

### Stage 3: Intent Classification
**File:** `src/brain/intent.py::IntentClassifier`
- **Key Method:** `classify()` (line 263-308)
- **Pipeline:**
  1. Regex pattern matching (FAST) - ~5-50ms
  2. spaCy Matcher if confidence < 0.8 (SLOW) - ~100-500ms
  3. LLM cloud fallback if enabled (VERY SLOW) - 1.0-5.0+ seconds
- **Latency Breakdown:**
  - Pattern matching: ~5-50ms
  - spaCy processing: ~100-500ms
  - Cloud LLM call: 1.0-5.0+ seconds (if triggered)
- **Blocking:** YES
- **Confidence Threshold:** 0.8 (default)
- **Potential Issues:**
  - spaCy model loads on init (one-time cost, ~500ms)
  - Cloud fallback is synchronous (blocks entire pipeline)
  - No caching of classification results
  - LLM calls not rate-limited or cached

### Stage 4: Entity Extraction
**File:** `src/brain/entities.py::EntityExtractor`
- **Key Method:** `extract()` 
- **Methods:**
  1. spaCy NER (if available)
  2. Regex patterns for duration, location, time
  3. Custom extractors
- **Latency:** ~50-300ms
- **Blocking:** YES
- **Potential Issues:**
  - spaCy model inference (one of slowest NLP operations)
  - dateparser library calls (if date extraction needed)
  - All operations sequential

### Stage 5: Context Retrieval
**File:** `src/brain/context.py::ContextManager`
- **Latency:** ~5-20ms (in-memory lookup)
- **Blocking:** YES
- **Operations:**
  - Retrieve conversation history (last 5-10 interactions)
  - Get preferences
  - Get active timers

### Stage 6: Skill Execution
**File:** `src/skills/skill_manager.py::SkillManager` + individual skills
- **Key Method:** `route_intent()` (line 249-293)
- **Pipeline:**
  1. Find skill for intent (cache hit ~1ms, miss ~5-20ms)
  2. Validate entities (1-5ms)
  3. Execute skill (varies widely):
     - **Weather Skill:** OpenWeatherMap API call (~1-3s)
     - **Timer Skill:** In-memory (instant, <1ms)
     - **App Control:** System calls (100-500ms)
     - **Search Skill:** Browser automation (2-10s)
     - **Small Talk Skill:** LLM call if enabled (1-5s)
- **Latency:** 0.1-10.0+ seconds (skill-dependent)
- **Blocking:** YES
- **Potential Issues:**
  - API calls (weather, search) not cached
  - Sequential skill execution only
  - No skill timeout protection
  - No parallel skill processing

### Stage 7: LLM Fallback (Conversational)
**File:** `src/brain/llm.py::LLMClient`
- **Key Method:** `chat()` (line 173-241)
- **Model:** GPT-4 (default)
- **Pipeline:**
  1. Build message list with history (~5 messages)
  2. OpenAI API call (blocking HTTP)
  3. Parse response
- **Latency:** 1.0-5.0+ seconds
- **Blocking:** YES
- **Potential Issues:**
  - Synchronous API calls only
  - No streaming responses
  - History limited to last 5 messages (good)
  - Temperature=0.3 (good, deterministic)
  - No response caching
  - Conversation history not deduped

### Stage 8: Text-to-Speech (TTS)
**File:** `src/audio/tts.py::TextToSpeech` or `CachedTTS`
- **Provider:** Coqui TTS (local, GPU-optional)
- **Model:** tts_models/en/ljspeech/tacotron2-DDC (default)
- **Key Method:** `synthesize()` (line 88-131)
- **Pipeline:**
  1. Check cache if enabled
  2. Temp file creation
  3. TTS synthesis (local neural network)
  4. Read audio data
  5. Clean up temp file
- **Latency:**
  - Cache hit: ~50-100ms
  - Cache miss: 0.5-3.0 seconds (depends on response length)
  - GPU mode: Faster (if available, not enabled by default)
- **Blocking:** YES (main thread waits for synthesis)
- **Potential Issues:**
  - Model loads on init (one-time ~2-5s, GPU adds setup time)
  - Temp file I/O overhead
  - No parallel synthesis
  - **MAJOR BOTTLENECK:** Response time scales linearly with text length
  - Cache only available in `CachedTTS` (enabled by default)

### Stage 9: Audio Playback
**File:** `src/audio/audio_io.py::AudioPlayer`
- **Latency:** Real-time (duration of audio)
- **Blocking:** YES (playback waits for completion)
- **Potential Issues:**
  - Blocks event loop during playback
  - No non-blocking playback option

---

## 3. EXECUTION FLOW DIAGRAM

```
┌─────────────────────────────────────────────────────────────┐
│ VOICE INPUT → WAKE WORD DETECTED                            │
└────────────────────┬────────────────────────────────────────┘
                     ↓
┌──────────────────────────────────┐
│ 1. GREETING TTS                  │  [0.5-1.5s]
│    (Synthesize + Play)           │
└────────────────┬─────────────────┘
                 ↓
┌──────────────────────────────────┐
│ 2. RECORDING                     │  [1.0-30.0s] ⚠️ USER DEPENDENT
│    With pause detection          │
└────────────────┬─────────────────┘
                 ↓
┌──────────────────────────────────┐
│ 3. STT (Deepgram)                │  [0.5-3.0s] 🔴 NETWORK BLOCKING
│    Audio → Text                  │
└────────────────┬─────────────────┘
                 ↓
┌──────────────────────────────────┐
│ 4. INTENT CLASSIFICATION         │  [0.01-5.0s] 🔴 LLM FALLBACK
│    Pattern → spaCy → LLM         │
└────────────────┬─────────────────┘
                 ↓
┌──────────────────────────────────┐
│ 5. ENTITY EXTRACTION             │  [0.05-0.3s]
│    Location, time, duration      │
└────────────────┬─────────────────┘
                 ↓
┌──────────────────────────────────┐
│ 6. CONTEXT RETRIEVAL             │  [0.01-0.02s]
│    History, preferences          │
└────────────────┬─────────────────┘
                 ↓
┌──────────────────────────────────┐
│ 7. SKILL EXECUTION               │  [0.001-10.0s] 🔴 VARIES WIDELY
│    Weather, Timer, App, etc.     │
│    Falls back to LLM if needed   │
└────────────────┬─────────────────┘
                 ↓
┌──────────────────────────────────┐
│ 8. RESPONSE TTS SYNTHESIS        │  [0.5-3.0s] 🔴 SLOW (scales w/ text)
│    Text → Audio (Coqui local)    │
└────────────────┬─────────────────┘
                 ↓
┌──────────────────────────────────┐
│ 9. AUDIO PLAYBACK                │  [REAL-TIME] Blocks further input
│    Speaker output                │
└────────────────┬─────────────────┘
                 ↓
┌──────────────────────────────────┐
│ 10. READY FOR NEXT INPUT         │
│     (Back to recording)          │
└──────────────────────────────────┘

TOTAL LATENCY: 3.5-50+ seconds
(User input to first audio output from assistant)
```

---

## 4. KEY BOTTLENECKS IDENTIFIED

### 🔴 CRITICAL BOTTLENECKS

1. **STT API Latency** (0.5-3.0s)
   - Location: `src/audio/stt.py::transcribe_bytes()` (line 86)
   - Root Cause: Deepgram API network round-trip
   - Impact: Every command waits for STT completion
   - Solution Ideas:
     - Streaming mode instead of prerecorded
     - Local STT fallback (Whisper, etc.)
     - STT result caching

2. **TTS Synthesis Latency** (0.5-3.0s)
   - Location: `src/audio/tts.py::synthesize()` (line 88)
   - Root Cause: Coqui TTS inference (neural network)
   - Impact: Scales linearly with response text length
   - Solution Ideas:
     - GPU acceleration (use_cuda=true in config)
     - Faster model (tacotron2 → vits)
     - Parallel synthesis of multiple responses
     - Pre-synthesized common phrases (cache helps)

3. **LLM Cloud Fallback** (1.0-5.0s+)
   - Location: `src/brain/intent.py::_classify_with_cloud()` (line 390)
   - Root Cause: OpenAI API call is synchronous
   - Impact: Triggered on low-confidence intent, blocks entire pipeline
   - Calls Occur At:
     - Intent classification fallback (when pattern confidence < 0.8)
     - Skill execution fallback (when skill fails)
     - Conversational responses
   - Solution Ideas:
     - Increase pattern matching confidence threshold
     - Async LLM calls with timeout
     - LLM response caching

4. **Pause Detection Delay** (1.0-2.5s)
   - Location: `src/core/engine.py::_record_with_pause_detection()` (line 614)
   - Root Cause: Hard-coded 1.0s pause wait (line 637)
   - Impact: User finishes speaking, waits 1s+ before STT starts
   - Problem Code:
     ```python
     pause_wait_chunks = int(
         pause_wait * self.audio_recorder.sample_rate / self.audio_recorder.chunk_size
     )  # pause_wait defaults to 1.0 seconds
     ```
   - Solution Ideas:
     - Make pause_wait configurable (default 0.5s)
     - Adaptive pause detection based on speech pattern
     - Better VAD (Voice Activity Detection)

### 🟡 MODERATE BOTTLENECKS

5. **spaCy Model Operations** (100-500ms)
   - Location: `src/brain/intent.py` and `src/brain/entities.py`
   - Only triggered if pattern matching confidence < 0.8
   - Impact: Sequential NLU processing
   - Solution Ideas:
     - Cache spaCy doc objects
     - Load spaCy on demand (lazy loading)

6. **Skill Execution Variance** (0.1-10.0s)
   - Location: `src/skills/*.py`
   - Varies widely by skill type:
     - Weather: API call (1-3s)
     - App Control: System calls (100-500ms)
     - Search: Browser automation (2-10s)
   - Solution Ideas:
     - API response caching (TTL-based)
     - Skill execution timeout
     - Parallel skill processing for multi-intent queries

7. **Component Initialization** (~5-10s one-time)
   - Location: `src/core/engine.py::initialize_components()` (line 143)
   - Includes:
     - spaCy model loading
     - TTS model loading
     - Skill discovery
   - Impact: Startup latency only (not per-request)
   - Solution Ideas:
     - Lazy loading of models (defer until needed)
     - Async initialization

---

## 5. TIMING/LOGGING INFRASTRUCTURE

### Existing Latency Tracking
- **Location:** `src/core/engine.py::process_text_command()` (line 777)
  ```python
  start_time = time.time()
  # ... processing ...
  latency_ms = (time.time() - start_time) * 1000
  ```
- **Reported In:** `PipelineResult.latency_ms`
- **Logged In:** `main.py::_run_cli_mode()` (line 259)
  ```python
  self.logger.info(f"Latency: {result.latency_ms:.0f}ms")
  ```

### Existing Logging
- **Logger:** `src/core/logger.py::setup_logger()` with rotating file handler
- **Log Level:** Configurable (DEBUG, INFO, WARNING, ERROR)
- **Log Output:** Console + File (`logs/zero.log`)
- **Granularity:**
  - Engine: State transitions, component initialization
  - Audio: Recording start/stop, silence detection
  - STT: Transcription input size, latency not logged per-call
  - Intent: Intent type, confidence, method
  - Skills: Skill execution, success/failure
  - TTS: Synthesis start, model loading, cache hits
  - LLM: API calls, token usage

### Missing Instrumentation
- No per-stage timing breakdown
- No STT latency logging
- No TTS latency logging
- No skill execution timing
- No LLM call timing
- No thread pool utilization metrics

---

## 6. SEQUENTIAL VS. PARALLEL OPERATIONS

### Currently Sequential (Blocking)
1. Wake word detection → Greeting TTS
2. Audio recording → STT
3. Intent classification → Entity extraction → Context → Skill execution
4. Skill execution → LLM fallback (if needed)
5. Response TTS → Playback
6. Playback completes → Ready for next input

### Opportunities for Parallelization
1. **TTS Preparation During Recording**
   - Start TTS model loading while user is speaking
   - Parallel: Recording + TTS model warm-up

2. **Intent/Entity Parallel Extraction**
   - Run intent classification & entity extraction in parallel
   - spaCy can process both efficiently

3. **Skill Execution Timeout Handling**
   - Skills should run with timeout, not block indefinitely
   - Current: No timeout (could hang)

4. **LLM Response Streaming**
   - OpenAI supports streaming responses
   - Could start TTS while LLM generates response
   - Current: Waits for full response before TTS

5. **Background Recording**
   - Continue recording next input while speaking response
   - Current: Playback blocks recording

---

## 7. SUMMARY TABLE

| Component | Latency | Blocking | Cacheable | Notes |
|-----------|---------|----------|-----------|-------|
| Recording | 1-30s | YES | - | User-controlled |
| STT | 0.5-3s | YES | YES | Network-dependent |
| Intent Classify | 0.01-5s | YES | YES | LLM fallback slow |
| Entity Extract | 0.05-0.3s | YES | PARTIAL | spaCy inference |
| Context Get | 0.01s | YES | - | In-memory |
| Skill Exec | 0.001-10s | YES | YES | Varies by skill |
| LLM Chat | 1-5s | YES | YES | Conversational fallback |
| TTS Synth | 0.5-3s | YES | YES | Scales w/ text length |
| Playback | REAL-TIME | YES | - | Blocks input |
| **TOTAL** | **3.5-50s** | **YES** | - | **Per-turn latency** |

---

## 8. RECOMMENDATIONS FOR INVESTIGATION

### High Priority
1. ✓ Profile STT latency distribution
2. ✓ Profile TTS latency vs. response length
3. ✓ Measure LLM fallback trigger frequency
4. ✓ Check pause_wait impact on perceived latency
5. ✓ Identify longest-running skills

### Medium Priority
1. Check spaCy model initialization cost
2. Measure network latency to APIs
3. Check API rate limiting impact
4. Identify cache hit/miss rates
5. Test GPU acceleration for TTS

### Low Priority
1. Check component initialization parallelization
2. Measure thread pool effectiveness
3. Check memory usage under load
4. Monitor CPU usage per component

---

## Configuration Tuning Points

**Current Config:** `/home/user/zero/config/config.yaml`

Key tuning parameters:
```yaml
stt:
  model: "nova-2"  # ← Already fastest
  timeout: 10      # ← Could reduce to 5
  
tts:
  model: "tacotron2-DDC"  # ← Could try vits for speed
  use_cuda: false  # ← Enable for GPU acceleration
  cache_enabled: true  # ← Already enabled (good)

nlu:
  local:
    confidence_threshold: 0.8  # ← Increase to 0.9 to avoid LLM
  cloud:
    enabled: true  # ← Could disable for faster local-only
    
audio:
  input:
    silence_duration: 1.5  # ← Could reduce to 0.8
```

---

