# Testing Phase 4: Weather Skill

This guide shows you how to test the Weather Skill implementation.

---

## Quick Start

### Option 1: Run the Interactive Demo (Recommended)

```bash
# Run the demo script
uv run python test_weather_demo.py
```

This will:
- Check your API key configuration
- Test various weather queries
- Demonstrate the caching system
- Show J.A.R.V.I.S.-style responses

---

## Setup Instructions

### 1. Get an OpenWeatherMap API Key (Free)

1. Visit: https://openweathermap.org/api
2. Sign up for a free account
3. Get your API key from the dashboard

### 2. Configure the API Key

Create or edit `.env` file in the project root:

```bash
# Copy the example file
cp .env.example .env

# Edit .env and add your API key
OPENWEATHERMAP_API_KEY=your_actual_api_key_here
```

### 3. Verify Dependencies

```bash
# Sync dependencies with uv
uv sync

# Verify pyowm is installed
uv run python -c "import pyowm; print('pyowm version:', pyowm.__version__)"
```

---

## Testing Methods

### Method 1: Interactive Demo Script ⭐ (Best for Quick Testing)

```bash
uv run python test_weather_demo.py
```

**Expected Output:**
```
======================================================================
              ZERO WEATHER SKILL DEMO (PHASE 4)
======================================================================

1. Checking Configuration
-------------------------
✓ API Key configured: 1234567890...

2. Initializing Components
---------------------------
✓ Weather Skill initialized
✓ Intent Classifier initialized
✓ Entity Extractor initialized

3. Testing Weather Queries
---------------------------

Query 1: "What's the weather?"
----------------------------------------------------------------------
  Intent: weather.query (confidence: 0.92)
  Entities: {}

  ZERO:
  The current weather in London is partly cloudy, sir. Temperature
  is 20.5°C, though it feels like 18.0°C. Humidity is at 65%, with
  wind speeds of 5.2 m/s.
```

### Method 2: Run Unit Tests

```bash
# Run all weather skill tests
uv run pytest tests/test_weather_skill.py -v

# Run with more detail
uv run pytest tests/test_weather_skill.py -v -s

# Run specific test
uv run pytest tests/test_weather_skill.py::TestCurrentWeather::test_get_current_weather_success -v
```

**Expected Output:**
```
tests/test_weather_skill.py::TestWeatherSkillInitialization::test_skill_initialization_with_api_key PASSED
tests/test_weather_skill.py::TestWeatherSkillIntentHandling::test_can_handle_weather_query PASSED
tests/test_weather_skill.py::TestCurrentWeather::test_get_current_weather_success PASSED
...
============================== 30+ tests passing ==============================
```

### Method 3: Python REPL (Manual Testing)

```python
# Start Python with uv
uv run python

# Then in Python:
import os
from dotenv import load_dotenv
load_dotenv()

from src.skills.weather_skill import WeatherSkill

# Initialize weather skill
weather = WeatherSkill(
    api_key=os.getenv('OPENWEATHERMAP_API_KEY'),
    units='metric'
)

# Test a query
response = weather.execute(
    intent='weather.query',
    entities={'location': 'Tokyo'},
    context={}
)

print(response.message)
# Output: The current weather in Tokyo is clear sky, sir. Temperature is...
```

### Method 4: Test Integration with Full NLU Pipeline

```python
uv run python

# Then:
from src.brain.intent import IntentClassifier
from src.brain.entities import EntityExtractor
from src.skills.weather_skill import WeatherSkill
import os
from dotenv import load_dotenv

load_dotenv()

# Initialize components
classifier = IntentClassifier(use_spacy=False)
extractor = EntityExtractor(use_spacy=False)
weather = WeatherSkill(api_key=os.getenv('OPENWEATHERMAP_API_KEY'))

# Test query
query = "What's the weather in Paris?"

# Classify intent
intent_result = classifier.classify(query)
print(f"Intent: {intent_result.intent.value}")

# Extract entities
entities_result = extractor.extract(query)
entities = {e.entity_type: e.value for e in entities_result.entities}
print(f"Entities: {entities}")

# Execute skill
if weather.can_handle(intent_result.intent.value):
    response = weather.execute(intent_result.intent.value, entities, {})
    print(f"\nZERO: {response.message}")
```

---

## Test Scenarios

### Basic Weather Queries

```bash
# Test different query formats
uv run python test_weather_demo.py
```

Test queries included:
- "What's the weather?" (default location)
- "What's the weather in New York?" (specific location)
- "How's the weather in Tokyo?" (alternate phrasing)
- "Will it rain tomorrow in Paris?" (forecast)

### Testing Without API Key (Mock Mode)

If you don't have an API key yet, the demo will run in mock mode:

```bash
# Run without API key
uv run python test_weather_demo.py
```

Expected output:
```
✗ OpenWeatherMap API key not configured!
ℹ Please set OPENWEATHERMAP_API_KEY in your .env file
ℹ Get a free API key at: https://openweathermap.org/api

Running in MOCK MODE (no actual API calls)...
```

### Testing Cache Performance

The demo automatically tests caching:

```python
# The demo script will show:
Testing Cache Performance
-------------------------

Testing cache with repeated queries for London:
  First query (API call): 1250.45ms
  Second query (cached):  2.15ms

  Cache speedup: 581.6x faster!
```

### Testing Error Handling

Test various error scenarios manually:

```python
uv run python

from src.skills.weather_skill import WeatherSkill

weather = WeatherSkill(api_key='your_key_here')

# Test invalid location
response = weather.execute(
    intent='weather.query',
    entities={'location': 'InvalidCity12345'},
    context={}
)
print(response.message)
# Expected: "I apologize, sir, but I could not find weather information..."

# Test with bad API key
weather_bad = WeatherSkill(api_key='invalid_key')
response = weather_bad.execute(
    intent='weather.query',
    entities={},
    context={}
)
print(response.message)
# Expected: Authentication error message
```

---

## Verifying J.A.R.V.I.S. Personality

The weather skill should always respond with J.A.R.V.I.S.-style language:

### Expected Personality Traits:
- ✅ Uses "sir" when addressing the user
- ✅ Calm and intelligent tone
- ✅ Provides contextual advice (coat for cold, umbrella for rain)
- ✅ Professional and composed

### Test Different Weather Conditions:

```python
# Cold weather test (should suggest coat)
response = weather.execute(
    intent='weather.query',
    entities={'location': 'Reykjavik'},  # Often cold
    context={}
)
# Look for: "I would suggest wearing a coat"

# Hot weather test (should suggest hydration)
response = weather.execute(
    intent='weather.query',
    entities={'location': 'Dubai'},  # Often hot
    context={}
)
# Look for: "Staying hydrated would be advisable"

# Rainy weather test (should suggest umbrella)
response = weather.execute(
    intent='weather.query',
    entities={'location': 'Seattle'},  # Often rainy
    context={}
)
# Look for: "You might want to bring an umbrella"
```

---

## Performance Benchmarks

### Expected Performance:

- **First query (API call)**: 500-2000ms
- **Cached query**: 1-5ms
- **Cache speedup**: 100-1000x faster
- **Cache TTL**: 5 minutes (300 seconds)

### Testing Performance:

```bash
# The demo script includes automatic performance testing
uv run python test_weather_demo.py
```

---

## Running All Phase Tests

### Test All Previous Phases + Phase 4:

```bash
# Test Phase 3 (Skills Framework)
uv run pytest tests/test_skills.py -v

# Test Phase 2 (NLU/Brain)
uv run pytest tests/test_brain.py -v

# Test Phase 4 (Weather Skill)
uv run pytest tests/test_weather_skill.py -v

# Run all together
uv run pytest tests/test_skills.py tests/test_brain.py tests/test_weather_skill.py -v
```

**Expected:**
```
117+ tests passing ✅
2-3 minor failures (pattern edge cases) ⚠️
6-7 tests skipped (require API keys) ⏭️
```

---

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'pyowm'"

**Solution:**
```bash
uv sync
# or
uv add pyowm==3.3.0
```

### Issue: "Weather service is currently unavailable"

**Possible causes:**
1. API key not set in `.env`
2. Invalid API key
3. API key not activated yet (takes ~10 minutes after signup)

**Solution:**
```bash
# Check if API key is set
cat .env | grep OPENWEATHERMAP

# Test API key manually
curl "http://api.openweathermap.org/data/2.5/weather?q=London&appid=YOUR_API_KEY"
```

### Issue: "Authentication issue with the weather service"

**Solution:**
- Wait 10-15 minutes after signing up for API activation
- Verify API key is correct in `.env`
- Check OpenWeatherMap dashboard for API key status

### Issue: Tests failing with import errors

**Solution:**
```bash
# Make sure you're using uv run
uv run pytest tests/test_weather_skill.py -v

# Not just:
pytest tests/test_weather_skill.py -v  # ❌ Wrong
```

---

## Example Complete Test Session

```bash
# 1. Set up API key
echo "OPENWEATHERMAP_API_KEY=your_key_here" >> .env

# 2. Sync dependencies
uv sync

# 3. Run demo
uv run python test_weather_demo.py

# 4. Run unit tests
uv run pytest tests/test_weather_skill.py -v

# 5. Test in Python REPL
uv run python
>>> from src.skills.weather_skill import WeatherSkill
>>> # ... interactive testing
```

---

## Next Steps

Once you've verified Phase 4 is working:

1. ✅ Weather Skill is operational
2. ⏭️ Move to Phase 5: Timer Skill
3. 📝 Keep the API key in `.env` for future use
4. 🎯 Consider adding more weather features (alerts, extended forecast)

---

## Quick Reference

### Most Common Commands:

```bash
# Quick demo
uv run python test_weather_demo.py

# Run tests
uv run pytest tests/test_weather_skill.py -v

# Interactive testing
uv run python
```

### Files Related to Phase 4:

- `src/skills/weather_skill.py` - Main implementation
- `tests/test_weather_skill.py` - Test suite
- `test_weather_demo.py` - Interactive demo
- `config/config.yaml` - Weather configuration
- `.env` - API key storage

---

**Happy Testing! 🌤️**
