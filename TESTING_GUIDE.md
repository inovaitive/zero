# ZERO Testing Guide

This guide explains how to run and test the ZERO voice assistant project.

## Prerequisites

- **Python 3.10+** (required)
- **uv** package manager (recommended) or pip
- **System audio libraries** (for sounddevice)

## Installation

### Option 1: Using uv (Recommended - 10-100x faster)

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Sync dependencies
cd /home/user/zero
uv sync

# Download spaCy language model
uv run python -m spacy download en_core_web_sm
```

### Option 2: Using pip

```bash
cd /home/user/zero

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -e ".[dev]"

# Download spaCy language model
python -m spacy download en_core_web_sm
```

### System Dependencies (for sounddevice)

#### macOS
```bash
# Install PortAudio (required by sounddevice)
brew install portaudio
```

#### Linux (Ubuntu/Debian)
```bash
# Install PortAudio
sudo apt-get update
sudo apt-get install -y portaudio19-dev python3-pyaudio
```

#### Windows
No additional system dependencies required - sounddevice works out of the box.

---

## Running Tests

### 1. Run All Tests

```bash
# Using uv (recommended)
uv run pytest

# Using pip
pytest
```

### 2. Run Specific Test Suites

```bash
# Test skills system only
uv run pytest tests/test_skills.py -v

# Test audio system
uv run pytest tests/test_audio.py -v

# Test brain/NLU system
uv run pytest tests/test_brain.py -v

# Test core modules
uv run pytest tests/test_core.py -v
```

### 3. Run Tests with Coverage

```bash
# Get coverage report
uv run pytest --cov=src tests/

# Generate HTML coverage report
uv run pytest --cov=src --cov-report=html tests/
# Then open htmlcov/index.html in your browser
```

### 4. Run Specific Test Categories

```bash
# Run only unit tests (fast)
uv run pytest -m unit

# Run only integration tests
uv run pytest -m integration

# Skip slow tests
uv run pytest -m "not slow"

# Skip tests requiring audio hardware
uv run pytest -m "not audio"

# Skip tests requiring API keys
uv run pytest -m "not api"
```

---

## Manual Component Testing

### Test Skills System (Phase 3)

```bash
python3 << 'EOF'
import sys
sys.path.insert(0, '/home/user/zero')

from src.skills.base_skill import BaseSkill, SkillResponse
from src.skills.skill_manager import SkillManager
from typing import Dict, Any

# Create test skill
class WeatherSkill(BaseSkill):
    def __init__(self):
        super().__init__(name="weather", description="Weather info")

    def can_handle(self, intent: str) -> bool:
        return intent.startswith("weather.")

    def execute(self, intent: str, entities: Dict[str, Any], context: Dict[str, Any]) -> SkillResponse:
        location = entities.get('location', 'your area')
        return self._create_success_response(
            message=f"The weather in {location} is sunny and 72°F.",
            data={'temp': 72, 'condition': 'sunny'}
        )

# Test
manager = SkillManager(auto_discover=False)
manager.register_skill(WeatherSkill())

response = manager.route_intent(
    intent="weather.query",
    entities={'location': 'San Francisco'},
    context={}
)

print(f"Success: {response.success}")
print(f"Message: {response.message}")
print(f"Data: {response.data}")
EOF
```

### Test Intent Classification

```bash
python3 << 'EOF'
import sys
sys.path.insert(0, '/home/user/zero')

from src.brain.intent import IntentClassifier

classifier = IntentClassifier(use_spacy=False, use_cloud_fallback=False)

# Test various queries
queries = [
    "What's the weather in New York?",
    "Set a timer for 5 minutes",
    "Open Chrome",
    "Hello",
]

for query in queries:
    result = classifier.classify(query)
    print(f"Query: '{query}'")
    print(f"  Intent: {result.intent.value}")
    print(f"  Confidence: {result.confidence:.2f}")
    print()
EOF
```

### Test Entity Extraction

```bash
python3 << 'EOF'
import sys
sys.path.insert(0, '/home/user/zero')

from src.brain.entities import EntityExtractor

extractor = EntityExtractor(use_spacy=False)

# Test entity extraction
text = "Set a timer for 10 minutes in New York"
result = extractor.extract(text)

print(f"Text: '{text}'")
print(f"Entities found: {len(result.entities)}")
for entity in result.entities:
    print(f"  - {entity.entity_type}: {entity.value} (confidence: {entity.confidence:.2f})")
EOF
```

### Test Audio System (requires audio hardware)

```bash
python3 << 'EOF'
import sys
sys.path.insert(0, '/home/user/zero')

from src.audio.audio_io import list_audio_devices, get_default_devices

print("Available Audio Devices:")
print("-" * 60)

devices = list_audio_devices()

print("\nInput Devices:")
for device in devices['input']:
    print(f"  [{device['index']}] {device['name']}")
    print(f"      Channels: {device['channels']}, Sample Rate: {device['sample_rate']}Hz")

print("\nOutput Devices:")
for device in devices['output']:
    print(f"  [{device['index']}] {device['name']}")
    print(f"      Channels: {device['channels']}, Sample Rate: {device['sample_rate']}Hz")

print("\nDefault Devices:")
defaults = get_default_devices()
print(f"  Input: {defaults['input']['name']}")
print(f"  Output: {defaults['output']['name']}")
EOF
```

---

## Code Quality Checks

### Format Code

```bash
# Format with Black
uv run black src/ tests/

# Check formatting (without modifying)
uv run black --check src/ tests/
```

### Lint Code

```bash
# Lint with Ruff
uv run ruff check src/ tests/

# Auto-fix issues
uv run ruff check --fix src/ tests/
```

### Type Checking

```bash
# Type check with mypy
uv run mypy src/
```

---

## Project Structure

```
zero/
├── src/                    # Source code
│   ├── core/              # Core engine and configuration
│   ├── audio/             # Audio processing (sounddevice-based)
│   ├── brain/             # NLU (intent & entity extraction)
│   ├── skills/            # Extensible skills system
│   └── ui/                # User interfaces
├── tests/                 # Test suite
│   ├── test_skills.py    # Skills system tests ✅
│   ├── test_brain.py     # NLU tests
│   ├── test_audio.py     # Audio tests
│   └── test_core.py      # Core module tests
├── config/                # Configuration files
├── data/                  # Models and cache
└── docs/                  # Documentation
```

---

## Verification Checklist

After installation, verify everything is working:

- [ ] Dependencies installed: `uv sync` completes without errors
- [ ] spaCy model downloaded: `python -m spacy download en_core_web_sm`
- [ ] Skills system works: `python3 tests/test_skills.py`
- [ ] No PyAudio dependency: `grep -r "import pyaudio" src/` returns nothing
- [ ] sounddevice working: Run audio device listing test above
- [ ] All tests pass: `uv run pytest`

---

## Common Issues

### Issue: "ModuleNotFoundError: No module named 'dotenv'"
**Solution:** Install dependencies with `uv sync` or `pip install -e ".[dev]"`

### Issue: "OSError: PortAudio library not found"
**Solution:** Install system audio libraries:
- macOS: `brew install portaudio`
- Linux: `sudo apt-get install portaudio19-dev`
- Windows: Should work out of the box

### Issue: "spaCy model 'en_core_web_sm' not found"
**Solution:** Download spaCy model:
```bash
uv run python -m spacy download en_core_web_sm
```

### Issue: Tests fail with import errors
**Solution:** Make sure you're running from the project root:
```bash
cd /home/user/zero
uv run pytest
```

---

## Quick Test Commands

```bash
# Quick verification (no audio hardware needed)
python3 -c "
import sys
sys.path.insert(0, '/home/user/zero')
from src.skills.base_skill import BaseSkill, SkillResponse
from src.skills.skill_manager import SkillManager
from src.brain.intent import IntentClassifier
from src.brain.entities import EntityExtractor
print('✅ All core imports successful!')
"

# Verify no PyAudio dependency
python3 -c "
with open('/home/user/zero/pyproject.toml', 'r') as f:
    content = f.read()
    if 'pyaudio' in content.lower():
        print('❌ PyAudio still in dependencies')
        exit(1)
print('✅ PyAudio successfully removed')
"

# Test skills system
cd /home/user/zero
python3 << 'EOF'
import sys
sys.path.insert(0, '/home/user/zero')
from src.skills.base_skill import BaseSkill, SkillResponse
from src.skills.skill_manager import SkillManager

class TestSkill(BaseSkill):
    def __init__(self):
        super().__init__(name="test")
    def can_handle(self, intent):
        return intent == "test.run"
    def execute(self, intent, entities, context):
        return self._create_success_response("Test passed!")

manager = SkillManager(auto_discover=False)
manager.register_skill(TestSkill())
response = manager.route_intent("test.run", {}, {})
assert response.success, "Test failed"
print("✅ Skills system working perfectly!")
EOF
```

---

## Next Steps

1. **Phase 4**: Implement Weather Skill
2. **Phase 5**: Implement Timer Skill
3. **Phase 6**: Implement App Control Skill
4. **Phase 7**: Implement Small Talk Skill
5. **Phase 8**: Integrate all components into main engine

---

## Support

For issues or questions:
- Check the [README.md](README.md) for setup instructions
- Check the [CLAUDE.md](CLAUDE.md) for architecture details
- Review [ROADMAP.md](ROADMAP.md) for development phases
- Check [docs/PHASE_3_COMPLETION.md](docs/PHASE_3_COMPLETION.md) for Phase 3 details

---

**Last Updated:** 2025-11-16
**Status:** Phase 3 Complete - PyAudio Removed ✅
