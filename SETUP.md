# ZERO Assistant - Setup Guide

## Phase 0 Complete! ✅

The project foundation has been set up successfully. Here's what's been created:

### Project Structure
```
zero/
├── src/                     # Source code
│   ├── core/                # Core modules
│   │   ├── config.py        # Configuration management ✅
│   │   ├── state.py         # State management ✅
│   │   └── logger.py        # Logging infrastructure ✅
│   ├── audio/               # Audio components (empty - Phase 1)
│   ├── brain/               # NLU components (empty - Phase 2)
│   ├── skills/              # Skills (empty - Phase 3-7)
│   └── ui/                  # User interfaces
│       ├── cli.py           # Rich CLI ✅
│       └── tray.py          # System tray ✅
├── config/                  # Configuration files
│   ├── config.yaml          # Main config ✅
│   └── config.example.yaml  # Example config ✅
├── tests/                   # Tests
│   ├── test_config.py       # Config tests ✅
│   └── test_state.py        # State tests ✅
├── data/                    # Data directories
│   ├── wake_words/          # Wake word models
│   ├── models/              # ML models
│   ├── sounds/              # Sound files
│   └── cache/               # Cache
├── logs/                    # Log files
├── .env.example             # Environment variables template ✅
├── .gitignore               # Git ignore ✅
├── requirements.txt         # Dependencies ✅
├── pytest.ini               # Pytest configuration ✅
├── main.py                  # Entry point ✅
├── README.md                # Project README
├── ROADMAP.md               # Development roadmap
├── CLAUDE.md                # Claude instructions
└── SETUP.md                 # This file
```

### What's Working

#### 1. Configuration System (`src/core/config.py`)
- ✅ YAML-based configuration with environment variable substitution
- ✅ Validates required API keys
- ✅ Dot notation access (e.g., `config.get('general.name')`)
- ✅ Type-safe configuration properties
- ✅ Global config instance

#### 2. State Management (`src/core/state.py`)
- ✅ Thread-safe state machine
- ✅ Valid state transitions (IDLE → LISTENING → PROCESSING → EXECUTING → RESPONDING → IDLE)
- ✅ State callbacks for event handling
- ✅ State history tracking
- ✅ Metadata support for each state

#### 3. Logging Infrastructure (`src/core/logger.py`)
- ✅ Colored console output with different log levels
- ✅ File logging with rotation (max 10MB, 5 backups)
- ✅ Separate formatters for console and file
- ✅ Configurable log levels

#### 4. CLI Interface (`src/ui/cli.py`)
- ✅ Rich-based beautiful terminal UI
- ✅ Header with logo and status
- ✅ Conversation panel with history
- ✅ Logs panel (optional)
- ✅ Status bar with current state
- ✅ Real-time updates with live refresh

#### 5. System Tray (`src/ui/tray.py`)
- ✅ Cross-platform system tray icon
- ✅ Menu with Start/Stop/Settings/Exit
- ✅ Status display
- ✅ Notification support

#### 6. Main Entry Point (`main.py`)
- ✅ Command-line argument parsing
- ✅ CLI-only mode support
- ✅ Signal handling (Ctrl+C graceful shutdown)
- ✅ Component initialization
- ✅ Error handling

#### 7. Testing Infrastructure
- ✅ pytest configuration
- ✅ Coverage reporting (HTML + terminal)
- ✅ Test markers for categorization
- ✅ Sample tests for config and state

### Configuration Files

#### `config/config.yaml`
Complete configuration with sections for:
- General settings (name, personality, log level)
- Wake word detection (pvporcupine)
- STT (Deepgram)
- TTS (Coqui TTS - female voice)
- NLU (spaCy + OpenAI)
- Skills (Weather, Timer, App Control, Search, Small Talk)
- UI (CLI + System Tray)
- Audio settings
- Performance settings
- Development settings

#### `.env.example`
Template for API keys:
- `PICOVOICE_ACCESS_KEY`
- `DEEPGRAM_API_KEY`
- `OPENAI_API_KEY`
- `OPENWEATHERMAP_API_KEY`

### Next Steps - Installation

1. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Download spaCy model:**
   ```bash
   python -m spacy download en_core_web_sm
   ```

4. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

5. **Test the setup:**
   ```bash
   # Run tests
   pytest

   # Run in CLI-only mode
   python main.py --cli-only

   # Run in voice mode (after Phase 1 complete)
   python main.py
   ```

### API Keys Required

Before running ZERO, you'll need to obtain these API keys:

1. **Picovoice** (Wake Word Detection)
   - Sign up at: https://console.picovoice.ai/
   - Get free access key
   - Add to `.env` as `PICOVOICE_ACCESS_KEY`

2. **Deepgram** (Speech-to-Text)
   - Sign up at: https://console.deepgram.com/
   - Get API key
   - Add to `.env` as `DEEPGRAM_API_KEY`

3. **OpenAI** (Natural Language Understanding)
   - Sign up at: https://platform.openai.com/
   - Create API key
   - Add to `.env` as `OPENAI_API_KEY`

4. **OpenWeatherMap** (Weather Skill)
   - Sign up at: https://openweathermap.org/api
   - Get free API key
   - Add to `.env` as `OPENWEATHERMAP_API_KEY`

### What's Next - Phase 1

The next phase will implement the audio pipeline:
- Wake word detection (pvporcupine)
- Speech-to-text (Deepgram)
- Text-to-speech (Coqui TTS with female voice)
- Audio I/O management

See `ROADMAP.md` for the complete development plan.

### Testing

Run tests:
```bash
# All tests
pytest

# With coverage
pytest --cov=src --cov-report=html

# Specific test file
pytest tests/test_config.py

# Verbose output
pytest -v

# Skip slow tests
pytest -m "not slow"
```

### Development

```bash
# Format code
black src/ tests/

# Lint code
pylint src/

# Type checking
mypy src/

# Run in debug mode
python main.py --debug
```

---

## Phase 0 Summary

✅ **Project Structure** - Complete directory hierarchy
✅ **Configuration** - Full config system with validation
✅ **State Management** - Thread-safe state machine
✅ **Logging** - Colored console + file logging
✅ **CLI Interface** - Rich terminal UI
✅ **System Tray** - Cross-platform tray integration
✅ **Main Entry Point** - Argument parsing and initialization
✅ **Testing** - pytest setup with sample tests
✅ **Documentation** - Comprehensive configuration files

**Status**: Ready for Phase 1 (Audio Pipeline) 🚀
