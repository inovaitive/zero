# ZERO - Intelligent Voice Assistant

<div align="center">

**A J.A.R.V.I.S.-inspired personal AI assistant with voice interaction and extensible capabilities**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-In%20Development-yellow.svg)]()

</div>

---

## 🎯 Overview

**ZERO** is an intelligent, voice-driven personal assistant designed to interact with users in a natural, human-like tone — inspired by J.A.R.V.I.S. from the Iron Man universe.

The MVP demonstrates core voice assistant functionality:
- 🎤 **Speech Recognition** - Natural voice input processing
- 🧠 **Intent Understanding** - Intelligent command interpretation
- ⚡ **Task Execution** - Real-world action execution
- 🗣️ **Human-like Response** - Vocal feedback with personality

ZERO focuses on **simplicity**, **modularity**, and **extensibility**, ensuring it can evolve into a full-fledged AI companion with memory, personality, and contextual understanding.

---

## ✨ Features (MVP)

### Core Capabilities
- ✅ **Wake Word Activation** - Always-listening with "Hey Zero" trigger
- ✅ **Voice Commands** - Natural language speech input
- ✅ **Local Processing** - Privacy-focused local STT/TTS
- ✅ **Fast Response** - Sub-3-second total latency
- ✅ **Extensible Skills** - Plugin-based architecture

### Skills
- 🌤️ **Weather Queries** - "What's the weather in London?"
- ⏲️ **Timers & Reminders** - "Set a timer for 5 minutes"
- 🔍 **Web Search** - "Search for Python tutorials"
- 💻 **App Control** - "Open Chrome" / "Launch Spotify"
- 💬 **Small Talk** - Casual conversation with personality

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                    ZERO Engine                       │
├─────────────────────────────────────────────────────┤
│                                                      │
│  ┌──────────┐   ┌──────────┐   ┌──────────┐       │
│  │  Wake    │──▶│  Speech  │──▶│   NLU    │       │
│  │  Word    │   │  to Text │   │  Brain   │       │
│  └──────────┘   └──────────┘   └────┬─────┘       │
│                                       │              │
│                              ┌────────▼────────┐    │
│                              │ Skills Manager  │    │
│                              └────────┬────────┘    │
│                                       │              │
│  ┌──────────┐   ┌──────────┐   ┌────▼─────┐       │
│  │  Voice   │◀──│ Response │◀──│  Skills  │       │
│  │  Output  │   │Generator │   │  Engine  │       │
│  └──────────┘   └──────────┘   └──────────┘       │
│       (TTS)                      Weather, Timer,    │
│                                  Search, Apps, etc. │
└─────────────────────────────────────────────────────┘
```

### Component Breakdown

- **Audio Layer** (`src/audio/`)
  - Wake word detection (pvporcupine)
  - Speech-to-Text (Faster-Whisper / Vosk)
  - Text-to-Speech (pyttsx3 / Coqui TTS)

- **Brain** (`src/brain/`)
  - Intent classification (spaCy + patterns / GPT-3.5)
  - Entity extraction
  - Context management

- **Skills System** (`src/skills/`)
  - Plugin architecture
  - Skill modules (Weather, Timer, Search, App Control, Small Talk)
  - Skill registration & routing

- **Core Engine** (`src/core/`)
  - Main event loop
  - State management
  - Configuration handler

- **UI** (`src/ui/`)
  - CLI interface (MVP)
  - Optional GUI (future)

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.8+**
- **pip** package manager
- **Microphone** for voice input
- **Speakers/Headphones** for audio output

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/zero.git
cd zero

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure settings (optional)
cp config/config.example.yaml config/config.yaml
# Edit config.yaml with your preferences
```

### Quick Start

```bash
# Run ZERO
python main.py

# Wait for "ZERO ready" message
# Say "Hey Zero" to activate
# Speak your command
# Listen to response
```

---

## 📖 Usage Examples

```
User: "Hey Zero"
ZERO: *activation sound*

User: "What's the weather in New York?"
ZERO: "Certainly. The current temperature in New York is 72°F with partly cloudy skies."

User: "Set a timer for 10 minutes"
ZERO: "Timer set for 10 minutes, sir."

User: "Open Spotify"
ZERO: "Launching Spotify now."

User: "Search for best pizza near me"
ZERO: "Opening search results in your browser."

User: "How are you today?"
ZERO: "Functioning optimally, thank you for asking."
```

---

## ⚙️ Configuration

Edit `config/config.yaml`:

```yaml
# Wake Word Settings
wake_word:
  keyword: "zero"
  sensitivity: 0.5

# Speech Recognition
stt:
  engine: "faster-whisper"  # Options: faster-whisper, vosk, whisper-api
  model: "base"             # Options: tiny, base, small, medium
  language: "en"

# Text-to-Speech
tts:
  engine: "pyttsx3"         # Options: pyttsx3, coqui, elevenlabs
  voice_id: 0               # Voice selection
  rate: 175                 # Speaking rate

# NLU/Brain
brain:
  mode: "local"             # Options: local, hybrid, cloud
  gpt_api_key: ""           # Optional for cloud mode

# Skills
skills:
  enabled:
    - weather
    - timer
    - search
    - app_control
    - small_talk
```

---

## 🧩 Extending ZERO

### Creating a Custom Skill

```python
# src/skills/my_custom_skill.py

from src.skills.base_skill import BaseSkill

class MyCustomSkill(BaseSkill):
    def __init__(self):
        super().__init__(name="custom_skill")
        self.keywords = ["custom", "special"]

    def can_handle(self, intent: str) -> bool:
        return intent == "custom_action"

    def execute(self, intent: str, entities: dict) -> str:
        # Your logic here
        return "Custom action executed successfully."

# Skills are auto-registered on startup
```

---

## 🛣️ Roadmap

See [ROADMAP.md](ROADMAP.md) for detailed development phases and timeline.

**MVP Timeline**: 2-3 weeks
**v1.0 Polish**: 4 weeks

---

## 🔧 Technology Stack

| Component | Primary (Open-Source) | Optional (Cloud) |
|-----------|----------------------|------------------|
| Wake Word | pvporcupine | - |
| STT | Faster-Whisper / Vosk | OpenAI Whisper API |
| NLU | spaCy + patterns | GPT-3.5-turbo |
| TTS | pyttsx3 | ElevenLabs / Google TTS |
| Weather | wttr.in | OpenWeatherMap |
| Search | webbrowser | SerpAPI |

---

## 📊 Performance Targets

- **Latency**: ≤3 seconds (end-to-end)
  - STT: <1s
  - Processing: <1s
  - TTS: <1s
- **Accuracy**: >90% intent recognition
- **Memory**: <500MB RAM
- **CPU**: Minimal when idle

---

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

---

## 📝 License

This project is licensed under the MIT License - see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- Inspired by **J.A.R.V.I.S.** from Iron Man
- Built with open-source AI/ML tools
- Community-driven development

---

## 📧 Contact

For questions, suggestions, or collaboration:
- **Issues**: [GitHub Issues](https://github.com/yourusername/zero/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/zero/discussions)

---

<div align="center">

**Built with ❤️ for the AI community**

*"Sometimes you gotta run before you can walk."* - Tony Stark

</div>
