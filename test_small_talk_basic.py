#!/usr/bin/env python3
"""
Basic verification test for Small Talk Skill.
This runs without heavy dependencies to verify core functionality.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_small_talk_skill_import():
    """Test that small talk skill can be imported."""
    try:
        from skills.small_talk_skill import SmallTalkSkill
        print("✓ SmallTalkSkill imported successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to import SmallTalkSkill: {e}")
        return False


def test_small_talk_skill_creation():
    """Test creating a small talk skill instance."""
    try:
        from skills.small_talk_skill import SmallTalkSkill

        # Create skill without LLM
        config = {
            'skills': {
                'small_talk': {
                    'enable_llm': False,
                    'enable_jokes': True,
                }
            }
        }
        skill = SmallTalkSkill(config=config)

        assert skill.name == "small_talk"
        assert skill.enabled is True
        assert skill.version == "1.0.0"
        print("✓ SmallTalkSkill instance created successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to create SmallTalkSkill: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_can_handle_intents():
    """Test intent handling."""
    try:
        from skills.small_talk_skill import SmallTalkSkill

        config = {'skills': {'small_talk': {'enable_llm': False}}}
        skill = SmallTalkSkill(config=config)

        # Test supported intents
        assert skill.can_handle("smalltalk.greeting") is True
        assert skill.can_handle("smalltalk.thanks") is True
        assert skill.can_handle("smalltalk.farewell") is True
        assert skill.can_handle("smalltalk.status") is True
        assert skill.can_handle("smalltalk.identity") is True
        assert skill.can_handle("smalltalk.help") is True
        assert skill.can_handle("smalltalk.joke") is True

        # Test unsupported intents
        assert skill.can_handle("weather.query") is False
        assert skill.can_handle("timer.set") is False

        print("✓ Intent handling works correctly")
        return True
    except Exception as e:
        print(f"✗ Intent handling failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_greeting_execution():
    """Test greeting execution."""
    try:
        from skills.small_talk_skill import SmallTalkSkill

        config = {'skills': {'small_talk': {'enable_llm': False}}}
        skill = SmallTalkSkill(config=config)

        response = skill.execute(
            intent="smalltalk.greeting",
            entities={"user_input": "Hello"},
            context={}
        )

        assert response.success is True
        assert isinstance(response.message, str)
        assert len(response.message) > 0
        print(f"✓ Greeting execution successful: '{response.message[:50]}...'")
        return True
    except Exception as e:
        print(f"✗ Greeting execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multiple_intents():
    """Test multiple intent executions."""
    try:
        from skills.small_talk_skill import SmallTalkSkill

        config = {'skills': {'small_talk': {'enable_llm': False}}}
        skill = SmallTalkSkill(config=config)

        test_cases = [
            ("smalltalk.greeting", "Hello", "greeting"),
            ("smalltalk.thanks", "Thank you", "gratitude"),
            ("smalltalk.farewell", "Goodbye", "farewell"),
            ("smalltalk.status", "How are you?", "status"),
            ("smalltalk.identity", "Who are you?", "identity"),
            ("smalltalk.joke", "Tell me a joke", "joke"),
            ("smalltalk.fact", "Tell me a fact", "fact"),
        ]

        passed = 0
        for intent, user_input, label in test_cases:
            response = skill.execute(
                intent=intent,
                entities={"user_input": user_input},
                context={}
            )
            if response.success and len(response.message) > 0:
                passed += 1
                print(f"  ✓ {label}: '{response.message[:40]}...'")
            else:
                print(f"  ✗ {label} failed")

        print(f"✓ Multiple intent test: {passed}/{len(test_cases)} passed")
        return passed == len(test_cases)
    except Exception as e:
        print(f"✗ Multiple intent test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_conversation_history():
    """Test conversation history tracking."""
    try:
        from skills.small_talk_skill import SmallTalkSkill

        config = {'skills': {'small_talk': {'enable_llm': False}}}
        skill = SmallTalkSkill(config=config)

        # First exchange
        skill.execute(
            intent="smalltalk.greeting",
            entities={"user_input": "Hello"},
            context={}
        )

        assert len(skill.conversation_history) == 2  # user + assistant

        # Second exchange
        skill.execute(
            intent="smalltalk.thanks",
            entities={"user_input": "Thank you"},
            context={}
        )

        assert len(skill.conversation_history) == 4  # 2 exchanges

        # Test history retrieval
        history = skill.get_conversation_history()
        assert len(history) == 4

        # Test history clearing
        skill.clear_conversation_history()
        assert len(skill.conversation_history) == 0

        print("✓ Conversation history tracking works correctly")
        return True
    except Exception as e:
        print(f"✗ Conversation history test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests."""
    print("=" * 60)
    print("ZERO Small Talk Skill - Basic Verification Tests")
    print("=" * 60)
    print()

    tests = [
        test_small_talk_skill_import,
        test_small_talk_skill_creation,
        test_can_handle_intents,
        test_greeting_execution,
        test_multiple_intents,
        test_conversation_history,
    ]

    passed = 0
    failed = 0

    for test in tests:
        print(f"\n Running: {test.__name__}")
        print("-" * 60)
        if test():
            passed += 1
        else:
            failed += 1

    print()
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
