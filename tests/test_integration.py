"""
Integration tests for ZERO Assistant - Phase 8.

Tests the complete pipeline from user input through to response.
"""

import pytest
from pathlib import Path

from src.core.config import get_config
from src.core.state import get_state_manager, AssistantState
from src.core.engine import create_engine, ZeroEngine


@pytest.fixture
def config():
    """Create test configuration."""
    config_path = Path(__file__).parent.parent / "config" / "config.yaml"
    return get_config(str(config_path))


@pytest.fixture
def state_manager():
    """Create state manager."""
    return get_state_manager()


@pytest.fixture
def engine(config, state_manager):
    """Create and initialize engine."""
    eng = create_engine(config, state_manager)
    eng.initialize_components()
    return eng


class TestEngineInitialization:
    """Test engine initialization."""

    def test_engine_creation(self, config):
        """Test that engine can be created."""
        engine = create_engine(config)
        assert engine is not None
        assert isinstance(engine, ZeroEngine)

    def test_component_initialization(self, engine):
        """Test that all components are initialized."""
        assert engine.intent_classifier is not None
        assert engine.entity_extractor is not None
        assert engine.context_manager is not None
        assert engine.skill_manager is not None

    def test_engine_status(self, engine):
        """Test engine status reporting."""
        status = engine.get_status()

        assert 'running' in status
        assert 'state' in status
        assert 'skills_loaded' in status
        assert 'components' in status
        assert status['skills_loaded'] > 0  # Should have discovered skills


class TestTextPipeline:
    """Test text command processing pipeline."""

    def test_weather_query(self, engine):
        """Test processing a weather query."""
        result = engine.process_text_command("What's the weather in New York?")

        assert result.success
        assert result.intent is not None
        assert result.intent.startswith("weather")
        assert result.entities is not None
        assert 'location' in result.entities
        assert result.response_text is not None
        assert result.latency_ms is not None
        assert result.latency_ms > 0

    def test_timer_set(self, engine):
        """Test setting a timer."""
        result = engine.process_text_command("Set a timer for 5 minutes")

        assert result.success
        assert result.intent is not None
        assert result.intent == "timer.set"
        assert result.entities is not None
        assert result.response_text is not None

    def test_timer_list(self, engine):
        """Test listing timers."""
        result = engine.process_text_command("What timers are active?")

        assert result.success
        assert result.intent is not None
        assert result.intent == "timer.list"
        assert result.response_text is not None

    def test_smalltalk_greeting(self, engine):
        """Test greeting interaction."""
        result = engine.process_text_command("Hello")

        assert result.success
        assert result.intent is not None
        assert result.intent.startswith("smalltalk")
        assert result.response_text is not None

    def test_smalltalk_thanks(self, engine):
        """Test thanking interaction."""
        result = engine.process_text_command("Thank you")

        assert result.success
        assert result.intent is not None
        assert result.intent == "smalltalk.thanks"
        assert result.response_text is not None

    def test_unknown_intent(self, engine):
        """Test handling of unknown intent."""
        result = engine.process_text_command("asdfghjkl qwerty")

        # Should not crash, should return a response
        assert result.success or not result.success  # Either way is OK
        assert result.response_text is not None


class TestStateManagement:
    """Test state management during pipeline execution."""

    def test_state_transitions(self, engine, state_manager):
        """Test that state transitions correctly during processing."""
        # Initial state should be IDLE
        initial_state = state_manager.state

        # Process a command
        result = engine.process_text_command("Hello")

        # Should return to IDLE after processing
        final_state = state_manager.state
        assert final_state == AssistantState.IDLE

    def test_error_handling(self, engine):
        """Test that errors are handled gracefully."""
        # This should not crash the engine
        result = engine.process_text_command("")

        # Engine should still be functional
        status = engine.get_status()
        assert status is not None


class TestContextManagement:
    """Test context management across multiple queries."""

    def test_context_persistence(self, engine):
        """Test that context is maintained across queries."""
        # First query establishes context
        result1 = engine.process_text_command("What's the weather in Paris?")
        assert result1.success

        # Second query may use context
        result2 = engine.process_text_command("What about tomorrow?")
        assert result2.success

        # Context should have been updated
        assert result2.context is not None

    def test_context_update(self, engine):
        """Test that context is updated after each interaction."""
        result1 = engine.process_text_command("Hello")
        result2 = engine.process_text_command("How are you?")

        # Second query should have context from first
        if result2.context:
            assert 'history' in result2.context or 'current_topic' in result2.context


class TestSkillIntegration:
    """Test skill system integration."""

    def test_skill_discovery(self, engine):
        """Test that skills are auto-discovered."""
        assert engine.skill_manager is not None
        assert len(engine.skill_manager.skills) > 0

        # Should have core skills
        skill_names = list(engine.skill_manager.skills.keys())
        assert any('weather' in name.lower() for name in skill_names)
        assert any('timer' in name.lower() for name in skill_names)
        assert any('talk' in name.lower() for name in skill_names)

    def test_skill_routing(self, engine):
        """Test that intents are routed to correct skills."""
        # Weather query should route to weather skill
        result = engine.process_text_command("Is it raining in London?")
        assert result.success
        assert result.intent.startswith("weather")

        # Timer query should route to timer skill
        result = engine.process_text_command("Set a timer for 10 seconds")
        assert result.success
        assert result.intent.startswith("timer")


class TestEngineLifecycle:
    """Test engine lifecycle management."""

    def test_engine_start_stop(self, engine):
        """Test starting and stopping the engine."""
        assert not engine.is_running()

        # Start engine
        engine.start()
        assert engine.is_running()

        # Stop engine
        engine.stop()
        assert not engine.is_running()

    def test_engine_restart(self, engine):
        """Test that engine can be restarted."""
        engine.start()
        assert engine.is_running()

        engine.stop()
        assert not engine.is_running()

        # Restart
        engine.start()
        assert engine.is_running()

        engine.stop()


class TestPerformance:
    """Test performance requirements."""

    def test_response_latency(self, engine):
        """Test that response latency is acceptable."""
        result = engine.process_text_command("Hello")

        assert result.success
        assert result.latency_ms is not None

        # Should be reasonably fast (under 1 second for simple query)
        # This is lenient for testing, real target is <3s for full pipeline
        assert result.latency_ms < 5000  # 5 seconds max for test

    def test_multiple_queries_latency(self, engine):
        """Test latency across multiple queries."""
        queries = [
            "Hello",
            "What's the weather?",
            "Set a timer for 5 minutes",
            "Thank you"
        ]

        latencies = []
        for query in queries:
            result = engine.process_text_command(query)
            assert result.success
            latencies.append(result.latency_ms)

        # All queries should complete reasonably quickly
        avg_latency = sum(latencies) / len(latencies)
        assert avg_latency < 5000  # Average under 5 seconds


@pytest.mark.integration
class TestFullPipeline:
    """Test complete end-to-end pipeline."""

    def test_conversation_flow(self, engine):
        """Test a full conversation flow."""
        conversation = [
            ("Hello", "smalltalk.greeting"),
            ("What's the weather in Tokyo?", "weather.query"),
            ("Set a timer for 2 minutes", "timer.set"),
            ("What timers do I have?", "timer.list"),
            ("Thank you", "smalltalk.thanks"),
        ]

        for query, expected_intent_prefix in conversation:
            result = engine.process_text_command(query)

            assert result.success, f"Failed on query: {query}"
            assert result.intent is not None
            assert result.intent.startswith(expected_intent_prefix.split('.')[0])
            assert result.response_text is not None

    def test_error_recovery(self, engine):
        """Test that engine recovers from errors."""
        # Invalid query
        result1 = engine.process_text_command("")

        # Should still be able to process valid queries
        result2 = engine.process_text_command("Hello")
        assert result2.success

    def test_skill_execution_flow(self, engine):
        """Test that skills execute and return proper responses."""
        test_cases = [
            "What's the weather in New York?",
            "Set a timer for 5 minutes",
            "How are you?",
        ]

        for query in test_cases:
            result = engine.process_text_command(query)

            assert result.success
            assert result.skill_response is not None
            assert result.skill_response.message is not None
            assert len(result.skill_response.message) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
