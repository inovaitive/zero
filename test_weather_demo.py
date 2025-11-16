#!/usr/bin/env python3
"""
Demo script to test the Weather Skill (Phase 4).

This script demonstrates the weather skill functionality without requiring
the full voice pipeline (wake word, STT, TTS).
"""

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from src.skills.weather_skill import WeatherSkill
from src.brain.intent import IntentClassifier
from src.brain.entities import EntityExtractor

# ANSI color codes for nice output
GREEN = '\033[92m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
RED = '\033[91m'
RESET = '\033[0m'
BOLD = '\033[1m'


def print_header(text):
    """Print a formatted header."""
    print(f"\n{BOLD}{BLUE}{'=' * 70}{RESET}")
    print(f"{BOLD}{BLUE}{text:^70}{RESET}")
    print(f"{BOLD}{BLUE}{'=' * 70}{RESET}\n")


def print_section(text):
    """Print a section header."""
    print(f"\n{BOLD}{YELLOW}{text}{RESET}")
    print(f"{YELLOW}{'-' * len(text)}{RESET}")


def print_success(text):
    """Print success message."""
    print(f"{GREEN}✓ {text}{RESET}")


def print_error(text):
    """Print error message."""
    print(f"{RED}✗ {text}{RESET}")


def print_info(text):
    """Print info message."""
    print(f"{BLUE}ℹ {text}{RESET}")


def test_weather_skill():
    """Test the weather skill with various queries."""

    print_header("ZERO WEATHER SKILL DEMO (PHASE 4)")

    # Check API key
    print_section("1. Checking Configuration")
    api_key = os.getenv('OPENWEATHERMAP_API_KEY')

    if not api_key or api_key == 'your_openweathermap_api_key_here':
        print_error("OpenWeatherMap API key not configured!")
        print_info("Please set OPENWEATHERMAP_API_KEY in your .env file")
        print_info("Get a free API key at: https://openweathermap.org/api")
        print("\nRunning in MOCK MODE (no actual API calls)...\n")
        mock_mode = True
    else:
        print_success(f"API Key configured: {api_key[:10]}...")
        mock_mode = False

    # Initialize components
    print_section("2. Initializing Components")

    try:
        weather_skill = WeatherSkill(
            api_key=api_key,
            default_location="London",
            units="metric",
            cache_ttl=300
        )
        print_success("Weather Skill initialized")

        intent_classifier = IntentClassifier(
            use_spacy=False,  # Disable spaCy to avoid dependency issues
            confidence_threshold=0.7
        )
        print_success("Intent Classifier initialized")

        entity_extractor = EntityExtractor(use_spacy=False)
        print_success("Entity Extractor initialized")

    except Exception as e:
        print_error(f"Initialization failed: {e}")
        return

    # Test queries
    print_section("3. Testing Weather Queries")

    test_queries = [
        "What's the weather?",
        "What's the weather in New York?",
        "How's the weather in Tokyo?",
        "What's the weather in London?",
        "Will it rain tomorrow in Paris?",
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"\n{BOLD}Query {i}:{RESET} \"{query}\"")
        print("-" * 70)

        # Classify intent
        intent_result = intent_classifier.classify(query)
        print(f"  Intent: {intent_result.intent.value} (confidence: {intent_result.confidence:.2f})")

        # Extract entities
        entities_result = entity_extractor.extract(query, intent_result.intent.value)

        # Convert entities to dict
        entities_dict = {}
        for entity in entities_result.entities:
            entities_dict[entity.entity_type] = entity.value

        if entities_dict:
            print(f"  Entities: {entities_dict}")

        # Execute skill
        if weather_skill.can_handle(intent_result.intent.value):
            if not mock_mode and weather_skill.enabled:
                try:
                    response = weather_skill.execute(
                        intent=intent_result.intent.value,
                        entities=entities_dict,
                        context={}
                    )

                    if response.success:
                        print(f"\n  {GREEN}ZERO:{RESET}")
                        # Wrap text nicely
                        import textwrap
                        wrapped = textwrap.fill(response.message, width=66, initial_indent="  ", subsequent_indent="  ")
                        print(f"{GREEN}{wrapped}{RESET}")
                    else:
                        print(f"\n  {RED}Error: {response.message}{RESET}")

                except Exception as e:
                    print_error(f"Execution error: {e}")
            else:
                print_info("Mock mode - would call weather API here")
        else:
            print_error(f"Weather skill cannot handle intent: {intent_result.intent.value}")

    # Test caching
    if not mock_mode and weather_skill.enabled:
        print_section("4. Testing Cache Performance")

        test_location = "London"
        print(f"\n{BOLD}Testing cache with repeated queries for {test_location}:{RESET}")

        import time

        # First query (cache miss)
        start = time.time()
        response1 = weather_skill.execute(
            intent="weather.query",
            entities={'location': test_location},
            context={}
        )
        time1 = (time.time() - start) * 1000
        print(f"  First query (API call): {time1:.2f}ms")

        # Second query (cache hit)
        start = time.time()
        response2 = weather_skill.execute(
            intent="weather.query",
            entities={'location': test_location},
            context={}
        )
        time2 = (time.time() - start) * 1000
        print(f"  Second query (cached):  {time2:.2f}ms")

        speedup = time1 / time2 if time2 > 0 else 0
        print(f"\n  {GREEN}Cache speedup: {speedup:.1f}x faster!{RESET}")

    # Summary
    print_section("5. Test Summary")

    skill_info = weather_skill.get_info()
    print(f"  Name: {skill_info['name']}")
    print(f"  Version: {skill_info['version']}")
    print(f"  Enabled: {skill_info['enabled']}")
    print(f"  Supported Intents: {', '.join(skill_info['supported_intents'])}")

    if not mock_mode and weather_skill.enabled:
        print(f"\n  Cache entries: {len(weather_skill._cache)}")

    print_header("DEMO COMPLETE")

    if mock_mode:
        print_info("To enable real weather queries:")
        print_info("1. Get API key from https://openweathermap.org/api")
        print_info("2. Add to .env file: OPENWEATHERMAP_API_KEY=your_key_here")
        print_info("3. Run this script again")
    else:
        print_success("Weather Skill is fully operational!")

    print()


if __name__ == '__main__':
    test_weather_skill()
