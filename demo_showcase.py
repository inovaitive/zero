#!/usr/bin/env python3
"""
Showcase demo for ZERO Small Talk Skill.
Demonstrates various capabilities automatically.
"""

import sys
import os
import time

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from skills.small_talk_skill import SmallTalkSkill


def print_interaction(user_input, response, delay=0.5):
    """Print a user-ZERO interaction."""
    print(f"\n👤 You: {user_input}")
    time.sleep(delay)
    print(f"🤖 ZERO: {response}")
    print("-" * 70)
    time.sleep(delay)


def main():
    """Run automated showcase."""
    print("\n" + "=" * 70)
    print("  ZERO Small Talk Skill - Capability Showcase")
    print("=" * 70)
    print("\n🔧 Initializing ZERO...")

    # Initialize skill
    config = {
        'skills': {
            'small_talk': {
                'enable_llm': False,
                'enable_jokes': True,
            }
        }
    }

    skill = SmallTalkSkill(config=config)
    print("✅ ZERO ready!\n")
    print("=" * 70)

    # Test cases to demonstrate
    test_cases = [
        ("smalltalk.greeting", "Hello Zero", "Greeting"),
        ("smalltalk.status", "How are you?", "Status Query"),
        ("smalltalk.identity", "Who are you?", "Identity Question"),
        ("smalltalk.help", "What can you do?", "Help Request"),
        ("smalltalk.joke", "Tell me a joke", "Joke"),
        ("smalltalk.fact", "Tell me a fact", "Interesting Fact"),
        ("smalltalk.quote", "Give me a quote", "Motivational Quote"),
        ("smalltalk.thanks", "Thank you", "Gratitude Response"),
        ("smalltalk.farewell", "Goodbye", "Farewell"),
    ]

    for intent, user_input, label in test_cases:
        print(f"\n📌 Testing: {label}")
        print("=" * 70)

        response = skill.execute(
            intent=intent,
            entities={"user_input": user_input},
            context={}
        )

        print_interaction(user_input, response.message)

    # Show conversation history
    print("\n📝 Conversation History Summary:")
    print("=" * 70)
    history = skill.get_conversation_history()
    print(f"Total exchanges: {len(history) // 2}")
    print(f"History entries: {len(history)}")

    # Show some history
    if len(history) >= 4:
        print("\nLast 2 exchanges:")
        for i in range(-4, 0, 2):
            user_msg = history[i]["content"]
            zero_msg = history[i + 1]["content"]
            print(f"\n  You: {user_msg}")
            print(f"  ZERO: {zero_msg[:60]}...")

    print("\n" + "=" * 70)
    print("✅ Showcase complete!")
    print("=" * 70)
    print("\n💡 To chat interactively, run: python3 demo_small_talk.py")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
