"""
Comprehensive tests for NLU (brain) modules.

Tests cover:
- Intent classification
- Entity extraction
- Context management
- LLM integration
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from src.brain.intent import IntentClassifier, IntentType, IntentResult, create_intent_classifier
from src.brain.entities import EntityExtractor, Entity, create_entity_extractor
from src.brain.context import ContextManager, Interaction, create_context_manager
from src.brain.llm import LLMClient, LLMResponse, OPENAI_AVAILABLE


class TestIntentClassification:
    """Test intent classification with 50+ example queries."""

    @pytest.fixture
    def classifier(self):
        """Create intent classifier for testing."""
        return IntentClassifier(
            use_spacy=False,  # Don't require spaCy for basic tests
            confidence_threshold=0.7,
            use_cloud_fallback=False,
        )

    def test_classifier_initialization(self, classifier):
        """Test classifier can be created."""
        assert classifier is not None
        assert classifier.confidence_threshold == 0.7

    # Weather intent tests
    @pytest.mark.parametrize("query,expected_intent", [
        ("what's the weather", IntentType.WEATHER_QUERY),
        ("how's the weather in New York", IntentType.WEATHER_QUERY),
        ("weather forecast", IntentType.WEATHER_QUERY),
        ("will it rain tomorrow", IntentType.WEATHER_QUERY),
        ("how cold is it", IntentType.WEATHER_QUERY),
        ("temperature in London", IntentType.WEATHER_QUERY),
        ("what's the forecast for this week", IntentType.WEATHER_QUERY),
        ("is it going to snow", IntentType.WEATHER_QUERY),
        ("how hot will it be tomorrow", IntentType.WEATHER_QUERY),
        ("weather in Tokyo", IntentType.WEATHER_QUERY),
    ])
    def test_weather_intents(self, classifier, query, expected_intent):
        """Test weather-related queries."""
        result = classifier.classify(query)
        assert result.intent == expected_intent
        assert result.confidence > 0.0

    # Timer intent tests
    @pytest.mark.parametrize("query,expected_intent", [
        ("set a timer for 5 minutes", IntentType.TIMER_SET),
        ("timer for 10 seconds", IntentType.TIMER_SET),
        ("remind me in 1 hour", IntentType.TIMER_SET),
        ("set timer", IntentType.TIMER_SET),
        ("cancel the timer", IntentType.TIMER_CANCEL),
        ("stop timer", IntentType.TIMER_CANCEL),
        ("delete all timers", IntentType.TIMER_CANCEL),
        ("list timers", IntentType.TIMER_LIST),
        ("show my timers", IntentType.TIMER_LIST),
        ("how much time is left", IntentType.TIMER_STATUS),
    ])
    def test_timer_intents(self, classifier, query, expected_intent):
        """Test timer-related queries."""
        result = classifier.classify(query)
        assert result.intent == expected_intent

    # App control intent tests
    @pytest.mark.parametrize("query,expected_intent", [
        ("open Chrome", IntentType.APP_OPEN),
        ("launch Safari", IntentType.APP_OPEN),
        ("start Spotify", IntentType.APP_OPEN),
        ("run Terminal", IntentType.APP_OPEN),
        ("close Slack", IntentType.APP_CLOSE),
        ("quit Firefox", IntentType.APP_CLOSE),
        ("exit Discord", IntentType.APP_CLOSE),
        ("kill Zoom", IntentType.APP_CLOSE),
        ("list applications", IntentType.APP_LIST),
        ("what apps are running", IntentType.APP_LIST),
        ("switch to Code", IntentType.APP_SWITCH),
    ])
    def test_app_control_intents(self, classifier, query, expected_intent):
        """Test app control queries."""
        result = classifier.classify(query)
        assert result.intent == expected_intent

    # Search intent tests
    @pytest.mark.parametrize("query,expected_intent", [
        ("search for Python tutorials", IntentType.SEARCH_WEB),
        ("google cats", IntentType.SEARCH_WEB),
        ("look up best restaurants", IntentType.SEARCH_WEB),
        ("find information about AI", IntentType.SEARCH_WEB),
    ])
    def test_search_intents(self, classifier, query, expected_intent):
        """Test search queries."""
        result = classifier.classify(query)
        assert result.intent == expected_intent

    # Small talk intent tests
    @pytest.mark.parametrize("query,expected_intent", [
        ("hello", IntentType.SMALLTALK_GREETING),
        ("hi there", IntentType.SMALLTALK_GREETING),
        ("good morning", IntentType.SMALLTALK_GREETING),
        ("hey", IntentType.SMALLTALK_GREETING),
        ("thank you", IntentType.SMALLTALK_THANKS),
        ("thanks", IntentType.SMALLTALK_THANKS),
        ("appreciate it", IntentType.SMALLTALK_THANKS),
        ("goodbye", IntentType.SMALLTALK_FAREWELL),
        ("bye", IntentType.SMALLTALK_FAREWELL),
        ("see you later", IntentType.SMALLTALK_FAREWELL),
        ("how are you", IntentType.SMALLTALK_QUESTION),
        ("who are you", IntentType.SMALLTALK_QUESTION),
        ("what's your name", IntentType.SMALLTALK_QUESTION),
        ("help", IntentType.SMALLTALK_HELP),
        ("what can you do", IntentType.SMALLTALK_HELP),
    ])
    def test_smalltalk_intents(self, classifier, query, expected_intent):
        """Test small talk queries."""
        result = classifier.classify(query)
        assert result.intent == expected_intent

    def test_unknown_intent(self, classifier):
        """Test unknown/unclear queries."""
        result = classifier.classify("asdfghjkl")
        assert result.intent == IntentType.UNKNOWN

    def test_empty_input(self, classifier):
        """Test empty input."""
        result = classifier.classify("")
        assert result.intent == IntentType.UNKNOWN

    def test_intent_confidence(self, classifier):
        """Test confidence scoring."""
        result = classifier.classify("what's the weather")
        assert 0.0 <= result.confidence <= 1.0

    def test_get_intent_info(self, classifier):
        """Test intent information retrieval."""
        info = classifier.get_intent_info(IntentType.WEATHER_QUERY)
        assert 'name' in info
        assert 'description' in info
        assert 'category' in info

    def test_list_intents(self, classifier):
        """Test listing all intents."""
        intents = classifier.list_intents()
        assert len(intents) > 0
        assert all('name' in intent for intent in intents)

    def test_create_intent_classifier_with_config(self):
        """Test creating classifier with config."""
        config = {
            'nlu': {
                'local': {
                    'enabled': True,
                    'confidence_threshold': 0.9,
                }
            }
        }
        classifier = create_intent_classifier(config)
        assert classifier.confidence_threshold == 0.9


class TestEntityExtraction:
    """Test entity extraction."""

    @pytest.fixture
    def extractor(self):
        """Create entity extractor for testing."""
        return EntityExtractor(use_spacy=False)

    def test_extractor_initialization(self, extractor):
        """Test extractor can be created."""
        assert extractor is not None

    def test_extract_duration_minutes(self, extractor):
        """Test extracting duration in minutes."""
        result = extractor.extract("set a timer for 5 minutes")
        duration_entity = result.get_entity('duration')
        assert duration_entity is not None
        assert duration_entity.value == 300  # 5 minutes = 300 seconds

    def test_extract_duration_hours(self, extractor):
        """Test extracting duration in hours."""
        result = extractor.extract("timer for 2 hours")
        duration_entity = result.get_entity('duration')
        assert duration_entity is not None
        assert duration_entity.value == 7200  # 2 hours = 7200 seconds

    def test_extract_duration_mixed(self, extractor):
        """Test extracting mixed duration."""
        result = extractor.extract("set timer for 1 hour 30 minutes")
        duration_entity = result.get_entity('duration')
        assert duration_entity is not None
        assert duration_entity.value == 5400  # 1.5 hours = 5400 seconds

    def test_extract_app_name_known(self, extractor):
        """Test extracting known app names."""
        result = extractor.extract("open chrome")
        app_entity = result.get_entity('app_name')
        assert app_entity is not None
        assert "Chrome" in app_entity.value

    def test_extract_app_name_capitalized(self, extractor):
        """Test extracting capitalized app names."""
        result = extractor.extract("open Spotify")
        app_entity = result.get_entity('app_name')
        assert app_entity is not None

    def test_extract_numbers(self, extractor):
        """Test extracting numbers."""
        result = extractor.extract("set timer for 42 seconds")
        numbers = result.get_entities('number')
        assert len(numbers) > 0
        assert any(e.value == 42 for e in numbers)

    def test_extract_location(self, extractor):
        """Test extracting location."""
        result = extractor.extract("weather in New York")
        location = result.get_entity('location')
        # May or may not extract without spaCy
        # Just ensure no error

    def test_add_custom_app_alias(self, extractor):
        """Test adding custom app alias."""
        extractor.add_app_alias("myapp", "My Application")
        result = extractor.extract("open myapp")
        app_entity = result.get_entity('app_name')
        assert app_entity is not None
        assert app_entity.value == "My Application"

    def test_get_app_aliases(self, extractor):
        """Test getting all app aliases."""
        aliases = extractor.get_app_aliases()
        assert isinstance(aliases, dict)
        assert len(aliases) > 0

    def test_has_entity(self, extractor):
        """Test has_entity method."""
        result = extractor.extract("set timer for 5 minutes")
        assert result.has_entity('duration')
        assert not result.has_entity('location')

    def test_get_entities_multiple(self, extractor):
        """Test getting multiple entities of same type."""
        result = extractor.extract("set timer for 5 minutes and 30 seconds")
        durations = result.get_entities('duration')
        # Should find at least one duration
        assert len(durations) >= 1

    def test_create_entity_extractor_with_config(self):
        """Test creating extractor with config."""
        config = {
            'skills': {
                'app_control': {
                    'aliases': {
                        'myeditor': 'Sublime Text'
                    }
                }
            }
        }
        extractor = create_entity_extractor(config)
        aliases = extractor.get_app_aliases()
        assert 'myeditor' in aliases


class TestContextManagement:
    """Test context management."""

    @pytest.fixture
    def context_manager(self):
        """Create context manager for testing."""
        return ContextManager(max_history=5, timeout_seconds=300)

    def test_context_manager_initialization(self, context_manager):
        """Test context manager can be created."""
        assert context_manager is not None
        assert context_manager.max_history == 5
        assert context_manager.timeout_seconds == 300

    def test_update_context(self, context_manager):
        """Test updating context with interaction."""
        context_manager.update(
            user_input="what's the weather",
            intent="weather.query",
            entities={'location': 'New York'},
            response="It's sunny in New York"
        )

        last = context_manager.get_last_interaction()
        assert last is not None
        assert last.user_input == "what's the weather"
        assert last.intent == "weather.query"

    def test_conversation_history(self, context_manager):
        """Test conversation history tracking."""
        # Add multiple interactions
        for i in range(3):
            context_manager.update(
                user_input=f"query {i}",
                intent="test.intent",
                entities={},
                response=f"response {i}"
            )

        history = context_manager.get_history()
        assert len(history) == 3

    def test_max_history_limit(self, context_manager):
        """Test history is limited to max_history."""
        # Add more than max_history interactions
        for i in range(10):
            context_manager.update(
                user_input=f"query {i}",
                intent="test.intent",
                entities={},
                response=f"response {i}"
            )

        history = context_manager.get_history()
        assert len(history) == context_manager.max_history

    def test_current_location_tracking(self, context_manager):
        """Test current location is tracked."""
        context_manager.update(
            user_input="weather in Paris",
            intent="weather.query",
            entities={'location': 'Paris'},
            response="Sunny in Paris"
        )

        assert context_manager.context.current_location == 'Paris'

    def test_current_app_tracking(self, context_manager):
        """Test current app is tracked."""
        context_manager.update(
            user_input="open Chrome",
            intent="app.open",
            entities={'app_name': 'Google Chrome'},
            response="Opening Chrome"
        )

        assert context_manager.context.current_app == 'Google Chrome'

    def test_timer_tracking(self, context_manager):
        """Test timer tracking."""
        context_manager.update(
            user_input="set timer",
            intent="timer.set",
            entities={'timer_id': 'timer1'},
            response="Timer set"
        )

        assert 'timer1' in context_manager.get_active_timers()

    def test_get_context_for_query(self, context_manager):
        """Test getting context for query."""
        # Add some history
        context_manager.update(
            user_input="weather in Boston",
            intent="weather.query",
            entities={'location': 'Boston'},
            response="Sunny"
        )

        context = context_manager.get_context_for_query("what about tomorrow")
        assert context['has_history']
        assert 'implied_location' in context

    def test_preferences_learning(self, context_manager):
        """Test learning user preferences."""
        context_manager.update(
            user_input="weather in Seattle",
            intent="weather.query",
            entities={'location': 'Seattle'},
            response="Rainy"
        )

        pref_location = context_manager.get_preference('preferred_location')
        assert pref_location == 'Seattle'

    def test_set_preference(self, context_manager):
        """Test setting preference manually."""
        context_manager.set_preference('theme', 'dark')
        assert context_manager.get_preference('theme') == 'dark'

    def test_reset_context(self, context_manager):
        """Test resetting context."""
        # Add some data
        context_manager.update("test", "test.intent", {}, "response")

        # Reset
        context_manager.reset()

        # Check it's cleared
        history = context_manager.get_history()
        assert len(history) == 0

    def test_get_status(self, context_manager):
        """Test getting context status."""
        status = context_manager.get_status()
        assert 'context' in status
        assert 'max_history' in status
        assert 'is_expired' in status

    def test_conversation_summary(self, context_manager):
        """Test getting conversation summary."""
        context_manager.update("hello", "greeting", {}, "hi there")

        summary = context_manager.get_conversation_summary()
        assert isinstance(summary, str)
        assert len(summary) > 0

    def test_create_context_manager_with_config(self):
        """Test creating context manager with config."""
        config = {
            'context': {
                'max_history': 10,
                'timeout': 600,
            }
        }
        cm = create_context_manager(config)
        assert cm.max_history == 10
        assert cm.timeout_seconds == 600


@pytest.mark.skipif(not OPENAI_AVAILABLE, reason="OpenAI SDK not available")
class TestLLMIntegration:
    """Test LLM integration (mocked)."""

    def test_llm_client_initialization_without_key(self):
        """Test LLM client without API key."""
        client = LLMClient(api_key=None)
        assert not client.is_available()

    @patch('src.brain.llm.OpenAI')
    def test_llm_client_initialization_with_key(self, mock_openai):
        """Test LLM client with API key."""
        client = LLMClient(api_key="test_key", model="gpt-3.5-turbo")
        assert client.model == "gpt-3.5-turbo"

    @patch('src.brain.llm.OpenAI')
    def test_llm_chat(self, mock_openai):
        """Test LLM chat functionality."""
        # Mock response
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hello, sir."
        mock_response.choices[0].finish_reason = "stop"
        mock_response.usage.total_tokens = 50

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        client = LLMClient(api_key="test_key")
        result = client.chat("Hello")

        assert result.content == "Hello, sir."
        assert 'tokens' in result.metadata

    @patch('src.brain.llm.OpenAI')
    def test_llm_classify_intent(self, mock_openai):
        """Test LLM intent classification."""
        # Mock response with JSON
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = '{"intent": "weather.query", "confidence": 0.95}'
        mock_response.usage.total_tokens = 30

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        client = LLMClient(api_key="test_key")
        result = client.classify_intent("what's the weather")

        assert result.intent == "weather.query"
        assert result.metadata['confidence'] == 0.95

    def test_llm_usage_stats(self):
        """Test usage statistics tracking."""
        client = LLMClient(api_key="test_key")
        stats = client.get_usage_stats()

        assert 'total_requests' in stats
        assert 'total_tokens' in stats
        assert 'total_cost' in stats

    def test_create_llm_client_disabled(self):
        """Test creating LLM client when disabled."""
        config = {
            'nlu': {
                'cloud': {
                    'enabled': False
                }
            }
        }
        from src.brain.llm import create_llm_client
        client = create_llm_client(config)
        assert client is None


# Integration tests
class TestNLUIntegration:
    """Test integration between NLU components."""

    @pytest.fixture
    def nlu_components(self):
        """Create all NLU components."""
        return {
            'classifier': IntentClassifier(use_spacy=False),
            'extractor': EntityExtractor(use_spacy=False),
            'context': ContextManager(),
        }

    def test_full_nlu_pipeline(self, nlu_components):
        """Test complete NLU pipeline."""
        classifier = nlu_components['classifier']
        extractor = nlu_components['extractor']
        context = nlu_components['context']

        # Process query
        query = "set a timer for 5 minutes"

        # Classify intent
        intent_result = classifier.classify(query)
        assert intent_result.intent == IntentType.TIMER_SET

        # Extract entities
        entity_result = extractor.extract(query)
        assert entity_result.has_entity('duration')

        # Update context
        context.update(
            user_input=query,
            intent=intent_result.intent.value,
            entities={'duration': 300},
            response="Timer set for 5 minutes"
        )

        # Check context was updated
        last = context.get_last_interaction()
        assert last is not None
        assert last.intent == IntentType.TIMER_SET.value

    def test_context_aware_follow_up(self, nlu_components):
        """Test context-aware follow-up questions."""
        classifier = nlu_components['classifier']
        context = nlu_components['context']

        # First query
        context.update(
            user_input="weather in Paris",
            intent="weather.query",
            entities={'location': 'Paris'},
            response="Sunny in Paris"
        )

        # Follow-up query
        follow_up = "what about tomorrow"
        ctx = context.get_context_for_query(follow_up)

        # Should have implied location from context
        assert 'implied_location' in ctx
        assert ctx['implied_location'] == 'Paris'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
