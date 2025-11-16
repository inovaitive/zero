"""
Tests for Small Talk Skill.

This module tests the small talk skill functionality:
- Greetings
- Gratitude responses
- Farewells
- Status queries
- Identity questions
- Help requests
- Jokes, facts, quotes
- General conversation
- LLM integration
- Conversation history
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.skills.small_talk_skill import SmallTalkSkill
from src.skills.base_skill import SkillResponse


@pytest.fixture
def small_talk_config():
    """Create test configuration."""
    return {
        'skills': {
            'small_talk': {
                'enable_llm': False,  # Disable LLM for most tests
                'enable_jokes': True,
            }
        }
    }


@pytest.fixture
def small_talk_skill(small_talk_config):
    """Create SmallTalkSkill instance for testing."""
    skill = SmallTalkSkill(config=small_talk_config)
    yield skill


@pytest.fixture
def small_talk_skill_with_llm():
    """Create SmallTalkSkill with mocked LLM."""
    config = {
        'skills': {
            'small_talk': {
                'enable_llm': True,
                'enable_jokes': True,
            }
        },
        'nlu': {
            'cloud': {
                'api_key': 'test_api_key',
                'model': 'gpt-4',
            }
        }
    }

    with patch('src.skills.small_talk_skill.LLM_AVAILABLE', True):
        with patch('src.skills.small_talk_skill.LLMClient') as mock_llm_class:
            # Create mock LLM instance
            mock_llm = MagicMock()
            mock_llm.is_available.return_value = True
            mock_llm.chat.return_value = MagicMock(
                content="That's a fascinating question, sir. Let me provide you with a thoughtful response."
            )
            mock_llm_class.return_value = mock_llm

            skill = SmallTalkSkill(config=config)
            skill.llm_client = mock_llm
            yield skill, mock_llm


class TestSmallTalkSkillBasics:
    """Test basic small talk skill functionality."""

    def test_skill_initialization(self, small_talk_skill):
        """Test that small talk skill initializes correctly."""
        assert small_talk_skill.name == "small_talk"
        assert small_talk_skill.enabled is True
        assert small_talk_skill.version == "1.0.0"
        assert isinstance(small_talk_skill.conversation_history, list)
        assert len(small_talk_skill.conversation_history) == 0

    def test_can_handle_small_talk_intents(self, small_talk_skill):
        """Test that skill can handle small talk intents."""
        # Test all supported intents
        assert small_talk_skill.can_handle("smalltalk.greeting") is True
        assert small_talk_skill.can_handle("smalltalk.thanks") is True
        assert small_talk_skill.can_handle("smalltalk.farewell") is True
        assert small_talk_skill.can_handle("smalltalk.status") is True
        assert small_talk_skill.can_handle("smalltalk.identity") is True
        assert small_talk_skill.can_handle("smalltalk.help") is True
        assert small_talk_skill.can_handle("smalltalk.joke") is True
        assert small_talk_skill.can_handle("smalltalk.fact") is True
        assert small_talk_skill.can_handle("smalltalk.quote") is True
        assert small_talk_skill.can_handle("smalltalk.question") is True
        assert small_talk_skill.can_handle("smalltalk.general") is True

        # Test enum-style values
        assert small_talk_skill.can_handle("SMALLTALK_GREETING") is True
        assert small_talk_skill.can_handle("SMALLTALK_THANKS") is True

        # Should not handle other intents
        assert small_talk_skill.can_handle("weather.query") is False
        assert small_talk_skill.can_handle("timer.set") is False

    def test_get_supported_intents(self, small_talk_skill):
        """Test getting supported intents."""
        intents = small_talk_skill.get_supported_intents()
        assert "smalltalk.greeting" in intents
        assert "smalltalk.thanks" in intents
        assert "smalltalk.farewell" in intents
        assert "smalltalk.status" in intents
        assert "smalltalk.identity" in intents
        assert "smalltalk.help" in intents
        assert "smalltalk.joke" in intents
        assert "smalltalk.fact" in intents
        assert "smalltalk.quote" in intents
        assert len(intents) >= 9

    def test_get_help(self, small_talk_skill):
        """Test getting help text."""
        help_text = small_talk_skill.get_help()
        assert "Small Talk Skill" in help_text
        assert "J.A.R.V.I.S." in help_text
        assert "conversation" in help_text.lower()


class TestGreetings:
    """Test greeting functionality."""

    def test_greeting_response(self, small_talk_skill):
        """Test greeting intent."""
        response = small_talk_skill.execute(
            intent="smalltalk.greeting",
            entities={"user_input": "Hello"},
            context={}
        )

        assert response.success is True
        assert isinstance(response.message, str)
        assert len(response.message) > 0
        # Should contain greeting-related words
        assert any(word in response.message.lower() for word in ["hello", "good", "greetings", "assist"])

    def test_greeting_time_of_day(self, small_talk_skill):
        """Test greeting includes time of day."""
        with patch('src.skills.small_talk_skill.datetime') as mock_datetime:
            # Mock morning time (8 AM)
            mock_datetime.now.return_value = datetime(2024, 1, 1, 8, 0)
            mock_datetime.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)

            response = small_talk_skill.execute(
                intent="smalltalk.greeting",
                entities={"user_input": "Hello"},
                context={}
            )

            # May contain "morning" (but not guaranteed due to random choice)
            assert response.success is True

    def test_greeting_adds_to_history(self, small_talk_skill):
        """Test that greeting is added to conversation history."""
        response = small_talk_skill.execute(
            intent="smalltalk.greeting",
            entities={"user_input": "Hello Zero"},
            context={}
        )

        assert response.success is True
        assert len(small_talk_skill.conversation_history) == 2  # User + Assistant
        assert small_talk_skill.conversation_history[0]["role"] == "user"
        assert small_talk_skill.conversation_history[1]["role"] == "assistant"


class TestGratitude:
    """Test gratitude responses."""

    def test_thanks_response(self, small_talk_skill):
        """Test gratitude intent."""
        response = small_talk_skill.execute(
            intent="smalltalk.thanks",
            entities={"user_input": "Thank you"},
            context={}
        )

        assert response.success is True
        assert isinstance(response.message, str)
        # Should contain gratitude-related words
        assert any(word in response.message.lower() for word in ["welcome", "pleasure", "glad", "happy", "service"])

    def test_multiple_thanks_vary(self, small_talk_skill):
        """Test that multiple thanks get varied responses."""
        responses = set()
        for _ in range(10):
            response = small_talk_skill.execute(
                intent="smalltalk.thanks",
                entities={"user_input": "Thanks"},
                context={}
            )
            responses.add(response.message)

        # Should have some variety (at least 2 different responses)
        assert len(responses) >= 2


class TestFarewells:
    """Test farewell functionality."""

    def test_farewell_response(self, small_talk_skill):
        """Test farewell intent."""
        response = small_talk_skill.execute(
            intent="smalltalk.farewell",
            entities={"user_input": "Goodbye"},
            context={}
        )

        assert response.success is True
        assert isinstance(response.message, str)
        # Should contain farewell-related words
        assert any(word in response.message.lower() for word in ["goodbye", "farewell", "until", "take care"])


class TestStatus:
    """Test status query functionality."""

    def test_status_response(self, small_talk_skill):
        """Test status query intent."""
        response = small_talk_skill.execute(
            intent="smalltalk.status",
            entities={"user_input": "How are you?"},
            context={}
        )

        assert response.success is True
        assert isinstance(response.message, str)
        # Should indicate operational status
        assert any(word in response.message.lower() for word in [
            "function", "operational", "well", "peak", "running", "systems"
        ])


class TestIdentity:
    """Test identity question functionality."""

    def test_identity_response(self, small_talk_skill):
        """Test identity question intent."""
        response = small_talk_skill.execute(
            intent="smalltalk.identity",
            entities={"user_input": "Who are you?"},
            context={}
        )

        assert response.success is True
        assert isinstance(response.message, str)
        # Should mention ZERO
        assert "ZERO" in response.message
        # Should mention being an assistant
        assert "assistant" in response.message.lower()

    def test_identity_mentions_capabilities(self, small_talk_skill):
        """Test that identity response mentions some capabilities."""
        response = small_talk_skill.execute(
            intent="smalltalk.identity",
            entities={"user_input": "What's your name?"},
            context={}
        )

        assert response.success is True
        # Should mention at least one capability
        assert any(word in response.message.lower() for word in [
            "weather", "timer", "application", "assist", "help", "task"
        ])


class TestHelp:
    """Test help functionality."""

    def test_help_response(self, small_talk_skill):
        """Test help request intent."""
        response = small_talk_skill.execute(
            intent="smalltalk.help",
            entities={"user_input": "What can you do?"},
            context={}
        )

        assert response.success is True
        assert isinstance(response.message, str)
        # Should mention capabilities
        assert any(word in response.message.lower() for word in [
            "weather", "timer", "application", "assist", "help", "task"
        ])

    def test_help_detailed(self, small_talk_skill):
        """Test detailed help request."""
        response = small_talk_skill.execute(
            intent="smalltalk.help",
            entities={"user_input": "Tell me everything you can do"},
            context={}
        )

        assert response.success is True
        # Detailed help should be longer
        assert len(response.message) > 50


class TestJokes:
    """Test joke functionality."""

    def test_joke_response(self, small_talk_skill):
        """Test joke request intent."""
        response = small_talk_skill.execute(
            intent="smalltalk.joke",
            entities={"user_input": "Tell me a joke"},
            context={}
        )

        assert response.success is True
        assert isinstance(response.message, str)
        assert len(response.message) > 20  # Jokes should be substantial

    def test_jokes_disabled(self):
        """Test that jokes can be disabled."""
        config = {
            'skills': {
                'small_talk': {
                    'enable_llm': False,
                    'enable_jokes': False,
                }
            }
        }
        skill = SmallTalkSkill(config=config)

        response = skill.execute(
            intent="smalltalk.joke",
            entities={"user_input": "Tell me a joke"},
            context={}
        )

        assert response.success is True
        assert "not currently enabled" in response.message.lower()


class TestFacts:
    """Test fact functionality."""

    def test_fact_response(self, small_talk_skill):
        """Test fact request intent."""
        response = small_talk_skill.execute(
            intent="smalltalk.fact",
            entities={"user_input": "Tell me a fact"},
            context={}
        )

        assert response.success is True
        assert isinstance(response.message, str)
        assert len(response.message) > 30  # Facts should be informative

    def test_multiple_facts_vary(self, small_talk_skill):
        """Test that multiple fact requests return different facts."""
        facts = set()
        for _ in range(10):
            response = small_talk_skill.execute(
                intent="smalltalk.fact",
                entities={"user_input": "Tell me a fact"},
                context={}
            )
            facts.add(response.message)

        # Should have variety
        assert len(facts) >= 2


class TestQuotes:
    """Test quote functionality."""

    def test_quote_response(self, small_talk_skill):
        """Test quote request intent."""
        response = small_talk_skill.execute(
            intent="smalltalk.quote",
            entities={"user_input": "Give me a quote"},
            context={}
        )

        assert response.success is True
        assert isinstance(response.message, str)
        assert len(response.message) > 20


class TestGeneralConversation:
    """Test general conversation functionality."""

    def test_general_conversation_without_llm(self, small_talk_skill):
        """Test general conversation fallback without LLM."""
        response = small_talk_skill.execute(
            intent="smalltalk.question",
            entities={"user_input": "What do you think about AI?"},
            context={}
        )

        assert response.success is True
        assert isinstance(response.message, str)
        # Should provide a fallback response
        assert len(response.message) > 20

    def test_general_conversation_with_llm(self, small_talk_skill_with_llm):
        """Test general conversation with LLM."""
        skill, mock_llm = small_talk_skill_with_llm

        response = skill.execute(
            intent="smalltalk.general",
            entities={"user_input": "What do you think about technology?"},
            context={}
        )

        assert response.success is True
        assert isinstance(response.message, str)
        # Should have called LLM
        mock_llm.chat.assert_called_once()


class TestConversationHistory:
    """Test conversation history management."""

    def test_conversation_history_tracking(self, small_talk_skill):
        """Test that conversation history is tracked."""
        # First exchange
        response1 = small_talk_skill.execute(
            intent="smalltalk.greeting",
            entities={"user_input": "Hello"},
            context={}
        )

        assert len(small_talk_skill.conversation_history) == 2

        # Second exchange
        response2 = small_talk_skill.execute(
            intent="smalltalk.status",
            entities={"user_input": "How are you?"},
            context={}
        )

        assert len(small_talk_skill.conversation_history) == 4

    def test_conversation_history_limit(self, small_talk_skill):
        """Test that conversation history is limited."""
        # Add many exchanges (more than max_history * 2)
        for i in range(15):
            small_talk_skill.execute(
                intent="smalltalk.greeting",
                entities={"user_input": f"Hello {i}"},
                context={}
            )

        # Should be limited to max_history * 2
        assert len(small_talk_skill.conversation_history) <= small_talk_skill.max_history * 2

    def test_get_conversation_history(self, small_talk_skill):
        """Test getting conversation history."""
        small_talk_skill.execute(
            intent="smalltalk.greeting",
            entities={"user_input": "Hello"},
            context={}
        )

        history = small_talk_skill.get_conversation_history()
        assert isinstance(history, list)
        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[1]["role"] == "assistant"

    def test_clear_conversation_history(self, small_talk_skill):
        """Test clearing conversation history."""
        small_talk_skill.execute(
            intent="smalltalk.greeting",
            entities={"user_input": "Hello"},
            context={}
        )

        assert len(small_talk_skill.conversation_history) > 0

        small_talk_skill.clear_conversation_history()
        assert len(small_talk_skill.conversation_history) == 0


class TestTimeOfDay:
    """Test time of day functionality."""

    def test_get_time_of_day_morning(self, small_talk_skill):
        """Test morning time detection."""
        with patch('src.skills.small_talk_skill.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1, 8, 0)
            time_of_day = small_talk_skill._get_time_of_day()
            assert time_of_day == "morning"

    def test_get_time_of_day_afternoon(self, small_talk_skill):
        """Test afternoon time detection."""
        with patch('src.skills.small_talk_skill.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1, 14, 0)
            time_of_day = small_talk_skill._get_time_of_day()
            assert time_of_day == "afternoon"

    def test_get_time_of_day_evening(self, small_talk_skill):
        """Test evening time detection."""
        with patch('src.skills.small_talk_skill.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1, 19, 0)
            time_of_day = small_talk_skill._get_time_of_day()
            assert time_of_day == "evening"

    def test_get_time_of_day_night(self, small_talk_skill):
        """Test night time detection."""
        with patch('src.skills.small_talk_skill.datetime') as mock_datetime:
            mock_datetime.now.return_value = datetime(2024, 1, 1, 23, 0)
            time_of_day = small_talk_skill._get_time_of_day()
            assert time_of_day == "evening"  # Night uses evening


class TestErrorHandling:
    """Test error handling."""

    def test_unknown_intent_fallback(self, small_talk_skill):
        """Test handling of unknown intent (should fallback to general)."""
        response = small_talk_skill.execute(
            intent="smalltalk.unknown",
            entities={"user_input": "Something random"},
            context={}
        )

        # Should still return a response
        assert response.success is True
        assert isinstance(response.message, str)

    def test_empty_entities(self, small_talk_skill):
        """Test handling of empty entities."""
        response = small_talk_skill.execute(
            intent="smalltalk.greeting",
            entities={},
            context={}
        )

        assert response.success is True

    def test_missing_user_input(self, small_talk_skill):
        """Test handling when user_input is missing."""
        response = small_talk_skill.execute(
            intent="smalltalk.general",
            entities={},  # No user_input
            context={}
        )

        # Should still handle gracefully
        assert response.success is True


class TestContextUpdates:
    """Test context updates."""

    def test_context_update_timestamp(self, small_talk_skill):
        """Test that context is updated with timestamp."""
        response = small_talk_skill.execute(
            intent="smalltalk.greeting",
            entities={"user_input": "Hello"},
            context={}
        )

        assert response.success is True
        assert "last_small_talk" in response.context_update
        # Should be a valid ISO format timestamp
        assert isinstance(response.context_update["last_small_talk"], str)


class TestSkillConfiguration:
    """Test skill configuration options."""

    def test_create_with_api_key(self):
        """Test creating skill with API key."""
        skill = SmallTalkSkill(api_key="test_key_123")
        assert skill.api_key == "test_key_123"

    def test_create_with_llm_disabled(self):
        """Test creating skill with LLM disabled."""
        config = {
            'skills': {
                'small_talk': {
                    'enable_llm': False,
                }
            }
        }
        skill = SmallTalkSkill(config=config)
        assert skill.enable_llm is False

    def test_create_with_jokes_disabled(self):
        """Test creating skill with jokes disabled."""
        config = {
            'skills': {
                'small_talk': {
                    'enable_jokes': False,
                }
            }
        }
        skill = SmallTalkSkill(config=config)
        assert skill.enable_jokes is False


class TestJARVISPersonality:
    """Test J.A.R.V.I.S. personality traits in responses."""

    def test_responses_contain_sir(self, small_talk_skill):
        """Test that responses often contain 'sir' (J.A.R.V.I.S. style)."""
        # Test multiple intents
        intents_to_test = [
            "smalltalk.greeting",
            "smalltalk.status",
            "smalltalk.identity",
            "smalltalk.help"
        ]

        sir_count = 0
        for intent in intents_to_test:
            response = small_talk_skill.execute(
                intent=intent,
                entities={"user_input": "Test"},
                context={}
            )
            if "sir" in response.message.lower():
                sir_count += 1

        # At least some responses should contain "sir"
        assert sir_count > 0

    def test_responses_are_professional(self, small_talk_skill):
        """Test that responses maintain professional tone."""
        response = small_talk_skill.execute(
            intent="smalltalk.greeting",
            entities={"user_input": "Hello"},
            context={}
        )

        # Should not contain overly casual language
        casual_words = ["hey", "yeah", "nah", "cool", "awesome", "!!!"]
        message_lower = response.message.lower()

        # Professional responses shouldn't have multiple casual markers
        casual_count = sum(1 for word in casual_words if word in message_lower)
        assert casual_count == 0  # Should be formal
