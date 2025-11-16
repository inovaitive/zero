# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project: ZERO

**ZERO** is an intelligent, voice-driven personal assistant inspired by J.A.R.V.I.S. from Iron Man. It provides natural voice interaction with speech recognition, intent understanding, task execution, and human-like vocal responses.

### Key Design Principles
- **Local-first processing**: Privacy-focused, works offline
- **Modular architecture**: Extensible plugin-based skill system
- **Human-like personality**: Calm, intelligent J.A.R.V.I.S.-inspired tone
- **Sub-3-second latency**: Fast response time target
- **Open-source first**: Prioritize free/open tools, with optional cloud enhancement

---

## Development Commands

### Environment Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Running ZERO
```bash
# Start the assistant
python main.py

# Run with specific config
python main.py --config config/custom_config.yaml

# CLI mode (text input, no voice)
python main.py --cli-only
```

### Testing
```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_audio.py

# Run with coverage
pytest --cov=src tests/

# Run specific test
pytest tests/test_brain.py::test_intent_classification
```

### Code Quality
```bash
# Format code
black src/ tests/

# Lint code
pylint src/

# Type checking (if using mypy)
mypy src/
```

### Development
```bash
# Install in development mode
pip install -e .

# Watch for changes and auto-restart (if using watchdog)
python scripts/dev_watch.py
```

---

## Architecture Overview

### Technology Stack

**Backend (Voice & AI Processing)**
- **Language**: Python 3.9+
- **Wake Word**: pvporcupine (Picovoice)
- **STT**: Deepgram API (streaming + pre-recorded)
- **TTS**: Coqui TTS (local, high-quality neural voices)
- **NLU**: spaCy (local patterns) + OpenAI GPT-4/Ollama (cloud reasoning)
- **Weather**: OpenWeatherMap API
- **App Control**: psutil + platform-specific (AppKit for macOS, pywin32 for Windows)
- **Config**: YAML-based configuration
- **Testing**: pytest

**Frontend (User Interface)**
- **CLI**: Rich library (beautiful terminal UI with live updates)
- **System Tray**: pystray (cross-platform tray icon)
- **Notifications**: plyer (cross-platform notifications)
- **GUI**: PyQt6 or Tkinter (optional)

**Platform Support**
- macOS (10.14+)
- Windows (10/11)

### Project Structure
```
zero/
├── src/                    # Source code
│   ├── core/              # Core engine and configuration
│   │   ├── engine.py      # Main event loop
│   │   ├── config.py      # Configuration handler
│   │   └── state.py       # State management
│   ├── audio/             # Audio processing
│   │   ├── wake_word.py   # Wake word detection
│   │   ├── stt.py         # Speech-to-text
│   │   └── tts.py         # Text-to-speech
│   ├── brain/             # Natural language understanding
│   │   ├── intent.py      # Intent classifier
│   │   ├── entities.py    # Entity extractor
│   │   └── context.py     # Session context manager
│   ├── skills/            # Extensible skills/plugins
│   │   ├── base_skill.py  # Base class for all skills
│   │   ├── skill_manager.py  # Skill registry & router
│   │   ├── weather_skill.py
│   │   ├── timer_skill.py
│   │   ├── search_skill.py
│   │   ├── app_control_skill.py
│   │   └── small_talk_skill.py
│   └── ui/                # User interfaces
│       ├── cli.py         # Command-line interface (Rich-based)
│       ├── tray.py        # System tray integration
│       ├── visualizer.py  # Audio visualizations (optional)
│       └── gui.py         # GUI (optional)
├── config/                # Configuration files
│   ├── config.yaml        # Main configuration
│   └── config.example.yaml
├── tests/                 # Test suite
├── data/                  # Models and assets
│   ├── wake_words/
│   ├── models/
│   └── sounds/
├── main.py               # Entry point
└── requirements.txt
```

### Core Modules and Responsibilities

**1. Core Engine (`src/core/`)**
- Main event loop orchestration
- Component lifecycle management
- Configuration loading and validation
- State machine for conversation flow

**2. Audio Layer (`src/audio/`)**
- **Wake Word**: Always-listening detection with low CPU usage
- **STT**: Converts speech to text with <1s latency
- **TTS**: Generates natural voice output with personality

**3. Brain (`src/brain/`)**
- **Intent Classification**: Maps user commands to actions
- **Entity Extraction**: Extracts parameters (locations, durations, etc.)
- **Context Management**: Tracks conversation state within session

**4. Skills System (`src/skills/`)**
- **Plugin Architecture**: Dynamic skill loading and registration
- **Base Skill Class**: Abstract interface for all skills
- **Skill Manager**: Routes intents to appropriate skills
- **Built-in Skills**: Weather, Timer, Search, App Control, Small Talk

**5. UI (`src/ui/`)**
- CLI interface with live feedback
- Optional GUI for visual users

### Data Flow

```
User Voice Input
    ↓
Wake Word Detection (pvporcupine - always listening)
    ↓
Audio Recording (until silence detected via VAD)
    ↓
Speech-to-Text (Deepgram API)
    ↓
Intent Classification (spaCy patterns + OpenAI GPT/Ollama)
    ↓
Entity Extraction (spaCy NER + custom extractors)
    ↓
Skill Manager (route to appropriate skill)
    ↓
Skill Execution (perform action)
    ↓
Response Generation (format with J.A.R.V.I.S. personality)
    ↓
Text-to-Speech (Coqui TTS)
    ↓
Audio Output (speakers)
    ↓
Frontend Display (CLI/GUI/System Tray updates)
```

### State Management
- **IDLE**: Waiting for wake word
- **LISTENING**: Recording user command
- **PROCESSING**: Understanding intent
- **EXECUTING**: Running skill
- **RESPONDING**: Speaking response
- **ERROR**: Handling failures

### Configuration Management
- YAML-based configuration in `config/config.yaml`
- Environment-specific overrides supported
- API keys stored in environment variables (not in repo)
- User preferences: wake word sensitivity, voice selection, enabled skills

### External Dependencies
- **STT**: Deepgram API (requires API key)
- **Weather**: OpenWeatherMap API (requires free API key)
- **NLU**: OpenAI GPT-4 API or Ollama (local LLM - optional for complex queries)
- **Search**: Web browser automation via `webbrowser` module
- **App Control**:
  - macOS: AppKit, AppleScript (via subprocess)
  - Windows: pywin32, taskkill (via subprocess)
  - Cross-platform: psutil for process management

---

## Development Workflow

### Branch Naming Conventions
- `main` - Stable releases only
- `develop` - Active development branch
- `feature/feature-name` - New features
- `fix/bug-description` - Bug fixes
- `refactor/component-name` - Code refactoring
- `docs/description` - Documentation updates

### Commit Message Standards
Follow conventional commits format:
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code restructuring without feature changes
- `docs`: Documentation updates
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(skills): add weather skill with wttr.in integration

fix(audio): resolve microphone initialization race condition

refactor(brain): optimize intent classification for better performance
```

### Code Review Process
1. Create feature branch from `develop`
2. Implement changes with tests
3. Ensure all tests pass and code is formatted
4. Create pull request with description
5. Address review comments
6. Merge to `develop` after approval

### Testing Requirements
- **Unit tests**: All core modules must have >80% coverage
- **Integration tests**: Test full pipeline (audio → brain → skills → audio)
- **Manual testing**: Voice accuracy, latency, personality
- All tests must pass before merging to `develop`
- Use mocks for external APIs in tests

### Performance Requirements
- End-to-end latency: ≤3 seconds (95th percentile)
- Intent classification accuracy: ≥90%
- Wake word accuracy: ≥95%
- Memory usage: <500MB
- CPU usage (idle): <5%

---

## Adding New Skills

To create a custom skill:

1. **Create skill file** in `src/skills/`
```python
from src.skills.base_skill import BaseSkill

class MySkill(BaseSkill):
    def __init__(self):
        super().__init__(name="my_skill")
        self.keywords = ["keyword1", "keyword2"]

    def can_handle(self, intent: str) -> bool:
        return intent == "my_intent"

    def execute(self, intent: str, entities: dict) -> str:
        # Your logic here
        return "Response with J.A.R.V.I.S. personality"
```

2. **Register intent patterns** in `src/brain/intent.py`
3. **Enable in config** (`config/config.yaml`)
4. **Add tests** in `tests/test_skills.py`

Skills are auto-discovered and loaded on startup.

---

## Troubleshooting

### Common Issues

**Microphone not detected:**
- Check audio permissions
- Verify PyAudio installation
- Test with `python -m pyaudio`

**Wake word not responding:**
- Adjust sensitivity in config
- Check background noise levels
- Verify pvporcupine installation

**Slow STT performance:**
- Check Deepgram API response times
- Verify internet connection speed
- Check Deepgram model selection (nova-2 is fastest)
- Review API quota/usage

**Slow TTS performance:**
- Switch to faster Coqui TTS model
- Enable response caching
- Pre-generate common phrases
- Check CPU usage

**API rate limits:**
- Deepgram: Check usage dashboard
- OpenAI: Monitor token usage
- Implement response caching
- Use local alternatives when possible

**API key issues:**
- Verify .env file is correctly configured
- Check API key validity on provider dashboards
- Ensure proper permissions for API keys

---

## Important Notes for AI Assistants

- **Personality Matters**: All responses should sound like J.A.R.V.I.S. (calm, intelligent, slightly formal)
- **Latency is Critical**: Optimize for speed; 3-second max response time
- **Privacy-First**: Default to local processing; cloud is optional
- **Modular Design**: Keep skills independent and pluggable
- **Error Handling**: Always fail gracefully with personality-appropriate messages
- **Testing**: Don't skip tests; voice systems are hard to debug

---

**For detailed development phases and timeline, see [ROADMAP.md](ROADMAP.md)**
