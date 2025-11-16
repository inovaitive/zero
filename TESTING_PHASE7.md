# Phase 7 Testing Guide - Small Talk Skill

Complete guide for testing the ZERO Small Talk Skill implementation.

---

## 🚀 Quick Start - 3 Ways to Test

### 1. **Automated Showcase** (Recommended First)
See all capabilities in action automatically:

```bash
python3 demo_showcase.py
```

**What it does:**
- Demonstrates all 9 intent types
- Shows J.A.R.V.I.S. personality responses
- Displays conversation history tracking
- Takes ~10 seconds to complete

---

### 2. **Interactive Chat Demo**
Have a real conversation with ZERO:

```bash
python3 demo_small_talk.py
```

**Try saying:**
- "Hello Zero"
- "How are you?"
- "Who are you?"
- "What can you do?"
- "Tell me a joke"
- "Tell me a fact"
- "Give me a quote"
- "Thank you"
- "Goodbye"

**Special commands:**
- `help` - Show available queries
- `history` - View conversation history
- `clear` - Clear conversation history
- `quit` or `exit` - Exit demo

---

### 3. **Basic Verification Tests**
Run the automated test suite:

```bash
python3 test_small_talk_basic.py
```

**Tests:**
- ✅ Import and initialization
- ✅ Intent handling
- ✅ Response generation
- ✅ Conversation history
- ✅ All 7 intent types

---

## 🧪 Advanced Testing

### Run Full Pytest Suite (with uv)

If you want to run the comprehensive 40+ test cases:

```bash
# Install dependencies with uv (one-time setup)
uv sync

# Run all small talk tests
uv run pytest tests/test_small_talk_skill.py -v

# Run specific test class
uv run pytest tests/test_small_talk_skill.py::TestGreetings -v

# Run with coverage
uv run pytest tests/test_small_talk_skill.py --cov=src/skills/small_talk_skill
```

**Note:** This will download ~3GB of dependencies (torch, transformers, etc.) for the full ZERO environment.

---

### Manual Python Testing

Test individual features directly in Python:

```python
# Add to Python path
import sys
sys.path.insert(0, 'src')

from skills.small_talk_skill import SmallTalkSkill

# Create skill instance
config = {
    'skills': {
        'small_talk': {
            'enable_llm': False,
            'enable_jokes': True,
        }
    }
}
skill = SmallTalkSkill(config=config)

# Test greeting
response = skill.execute(
    intent="smalltalk.greeting",
    entities={"user_input": "Hello"},
    context={}
)
print(response.message)
# Output: "Good afternoon, sir. How may I assist you today?"

# Test joke
response = skill.execute(
    intent="smalltalk.joke",
    entities={"user_input": "Tell me a joke"},
    context={}
)
print(response.message)
# Output: A J.A.R.V.I.S.-style programming joke

# Check conversation history
history = skill.get_conversation_history()
print(f"Exchanges: {len(history) // 2}")
```

---

## 📋 Test Coverage

### What's Tested

**Basic Functionality:**
- ✅ Skill initialization and configuration
- ✅ Intent recognition (11 intent types)
- ✅ Response generation
- ✅ Conversation history tracking
- ✅ History limits and clearing

**Intent Types:**
- ✅ Greetings (time-of-day aware)
- ✅ Gratitude responses
- ✅ Farewells
- ✅ Status queries
- ✅ Identity questions
- ✅ Help requests
- ✅ Jokes
- ✅ Facts
- ✅ Quotes
- ✅ General conversation
- ✅ Questions

**J.A.R.V.I.S. Personality:**
- ✅ Uses "sir" in responses
- ✅ Professional, calm tone
- ✅ Slightly formal but helpful
- ✅ Appropriate humor

**Advanced Features:**
- ✅ LLM integration (with mocking)
- ✅ Configuration options
- ✅ Error handling
- ✅ Context updates

---

## 🎯 Expected Results

### Greeting Examples
```
You: "Hello"
ZERO: "Good morning, sir. How may I assist you today?"

You: "Hi Zero"
ZERO: "Hello, sir. I'm at your service."
```

### Status Query
```
You: "How are you?"
ZERO: "All systems are running smoothly, sir. Thank you for asking."
```

### Identity
```
You: "Who are you?"
ZERO: "I am ZERO, your personal AI assistant, sir. Inspired by J.A.R.V.I.S.,
       I'm here to help with weather information, timers, application control,
       and general assistance."
```

### Joke
```
You: "Tell me a joke"
ZERO: "I would tell you a UDP joke, but you might not get it.
       TCP jokes, however, I'll keep telling until you acknowledge them, sir."
```

### Fact
```
You: "Tell me a fact"
ZERO: "The human brain processes information at approximately 120 meters per second, sir.
       Quite impressive, though still measurably slower than modern computing."
```

---

## 🔍 Troubleshooting

### Issue: Import errors
**Solution:**
```bash
# Make sure you're in the project root
cd /home/user/zero

# Run tests from project root
python3 test_small_talk_basic.py
```

### Issue: "LLM not available" warning
**Expected behavior** - The skill works fine without LLM using rule-based responses.

To enable LLM (optional):
```bash
# Set OpenAI API key
export OPENAI_API_KEY="your-api-key"

# Update config
config = {
    'skills': {
        'small_talk': {
            'enable_llm': True,
            'api_key': 'your-api-key'
        }
    },
    'nlu': {
        'cloud': {
            'api_key': 'your-api-key',
            'model': 'gpt-4'
        }
    }
}
```

### Issue: Tests taking too long
**Solution:** Use the basic verification test instead:
```bash
python3 test_small_talk_basic.py
# Takes ~2 seconds instead of minutes
```

---

## 📊 Test Results

### Basic Verification (test_small_talk_basic.py)
- **Tests:** 6
- **Duration:** ~2 seconds
- **Status:** ✅ All passing

### Full Pytest Suite (tests/test_small_talk_skill.py)
- **Tests:** 40+
- **Coverage:** Comprehensive
- **Test Classes:**
  - TestSmallTalkSkillBasics
  - TestGreetings
  - TestGratitude
  - TestFarewells
  - TestStatus
  - TestIdentity
  - TestHelp
  - TestJokes
  - TestFacts
  - TestQuotes
  - TestGeneralConversation
  - TestConversationHistory
  - TestTimeOfDay
  - TestErrorHandling
  - TestContextUpdates
  - TestSkillConfiguration
  - TestJARVISPersonality

---

## 🎓 Next Steps

After testing Phase 7:

1. **Integrate with other skills:**
   - Weather Skill (Phase 4)
   - Timer Skill (Phase 5)
   - App Control Skill (Phase 6)

2. **Test with SkillManager:**
   ```python
   from skills.skill_manager import SkillManager
   manager = SkillManager()
   # Small talk skill should be auto-discovered
   ```

3. **Add to main engine:**
   - Connect to intent classifier
   - Add to main event loop
   - Test end-to-end conversation flow

4. **Optional enhancements:**
   - Enable GPT-powered conversation
   - Customize personality responses
   - Add more jokes/facts/quotes
   - Implement multi-language support

---

## 📝 Summary

**Phase 7 Status:** ✅ **COMPLETE**

**Files Created:**
- `src/skills/small_talk_skill.py` - Main implementation
- `tests/test_small_talk_skill.py` - Full test suite
- `test_small_talk_basic.py` - Quick verification
- `demo_small_talk.py` - Interactive chat demo
- `demo_showcase.py` - Automated showcase

**Quick Test Command:**
```bash
python3 demo_showcase.py
```

**Ready for:** Integration with ZERO main engine (Phase 8)

---

*For questions or issues, refer to the ROADMAP.md and CLAUDE.md documentation.*
