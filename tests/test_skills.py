"""
Tests for the Skills System.

Tests:
- BaseSkill functionality
- SkillResponse data structure
- SkillManager registration and routing
- Skill lifecycle management
- Error handling
"""

import pytest
from unittest.mock import Mock, patch
from typing import Dict, Any

from src.skills.base_skill import (
    BaseSkill,
    SkillResponse,
    SkillError,
    SkillNotFoundError,
    SkillExecutionError,
    SkillValidationError,
)
from src.skills.skill_manager import SkillManager


# Mock skill implementations for testing
class MockWeatherSkill(BaseSkill):
    """Mock weather skill for testing."""

    def __init__(self):
        super().__init__(
            name="weather",
            description="Get weather information",
            version="1.0.0"
        )

    def can_handle(self, intent: str) -> bool:
        return intent.startswith("weather.")

    def execute(
        self,
        intent: str,
        entities: Dict[str, Any],
        context: Dict[str, Any]
    ) -> SkillResponse:
        location = entities.get('location', 'your area')
        return self._create_success_response(
            message=f"The weather in {location} is sunny and 72 degrees.",
            data={'temperature': 72, 'condition': 'sunny', 'location': location}
        )

    def get_supported_intents(self):
        return ['weather.query']


class MockTimerSkill(BaseSkill):
    """Mock timer skill for testing."""

    def __init__(self):
        super().__init__(
            name="timer",
            description="Manage timers",
            version="1.0.0"
        )

    def can_handle(self, intent: str) -> bool:
        return intent.startswith("timer.")

    def execute(
        self,
        intent: str,
        entities: Dict[str, Any],
        context: Dict[str, Any]
    ) -> SkillResponse:
        if intent == "timer.set":
            duration = entities.get('duration', 300)
            return self._create_success_response(
                message=f"Timer set for {duration} seconds.",
                data={'duration': duration},
                context_update={'timer_id': 'timer_1'}
            )
        elif intent == "timer.cancel":
            return self._create_success_response(
                message="Timer cancelled.",
                data={'cancelled': True}
            )
        else:
            return self._create_error_response("Unknown timer intent")

    def validate_entities(self, entities: Dict[str, Any]) -> tuple[bool, str]:
        if 'duration' not in entities:
            return False, "Please specify a duration for the timer."
        return True, None

    def get_supported_intents(self):
        return ['timer.set', 'timer.cancel', 'timer.list']


class MockFailingSkill(BaseSkill):
    """Mock skill that always fails for testing error handling."""

    def __init__(self):
        super().__init__(name="failing", description="A skill that fails")

    def can_handle(self, intent: str) -> bool:
        return intent == "failing.test"

    def execute(
        self,
        intent: str,
        entities: Dict[str, Any],
        context: Dict[str, Any]
    ) -> SkillResponse:
        raise SkillExecutionError("Intentional failure for testing")


# Tests for SkillResponse
class TestSkillResponse:
    """Test SkillResponse data structure."""

    def test_create_success_response(self):
        """Test creating a success response."""
        response = SkillResponse(
            success=True,
            message="Task completed successfully",
            data={'result': 'success'}
        )

        assert response.success is True
        assert response.message == "Task completed successfully"
        assert response.data == {'result': 'success'}
        assert response.should_continue_listening is False

    def test_create_error_response(self):
        """Test creating an error response."""
        response = SkillResponse(
            success=False,
            message="Task failed",
            data={'error': 'some_error'}
        )

        assert response.success is False
        assert response.message == "Task failed"
        assert response.data == {'error': 'some_error'}

    def test_response_with_context_update(self):
        """Test response with context updates."""
        response = SkillResponse(
            success=True,
            message="Context updated",
            context_update={'location': 'San Francisco'}
        )

        assert response.context_update == {'location': 'San Francisco'}

    def test_response_to_dict(self):
        """Test converting response to dictionary."""
        response = SkillResponse(
            success=True,
            message="Test",
            data={'key': 'value'}
        )

        result = response.to_dict()

        assert result['success'] is True
        assert result['message'] == "Test"
        assert result['data'] == {'key': 'value'}


# Tests for BaseSkill
class TestBaseSkill:
    """Test BaseSkill functionality."""

    def test_skill_initialization(self):
        """Test skill initialization."""
        skill = MockWeatherSkill()

        assert skill.name == "weather"
        assert skill.description == "Get weather information"
        assert skill.version == "1.0.0"
        assert skill.enabled is True

    def test_can_handle(self):
        """Test intent matching."""
        skill = MockWeatherSkill()

        assert skill.can_handle("weather.query") is True
        assert skill.can_handle("weather.forecast") is True
        assert skill.can_handle("timer.set") is False

    def test_execute(self):
        """Test skill execution."""
        skill = MockWeatherSkill()

        response = skill.execute(
            intent="weather.query",
            entities={'location': 'New York'},
            context={}
        )

        assert response.success is True
        assert 'New York' in response.message
        assert response.data['location'] == 'New York'

    def test_enable_disable(self):
        """Test enabling and disabling skills."""
        skill = MockWeatherSkill()

        assert skill.is_enabled() is True

        skill.disable()
        assert skill.is_enabled() is False

        skill.enable()
        assert skill.is_enabled() is True

    def test_get_info(self):
        """Test getting skill info."""
        skill = MockWeatherSkill()
        info = skill.get_info()

        assert info['name'] == 'weather'
        assert info['description'] == 'Get weather information'
        assert info['version'] == '1.0.0'
        assert info['enabled'] is True
        assert 'weather.query' in info['supported_intents']

    def test_validate_entities(self):
        """Test entity validation."""
        skill = MockTimerSkill()

        # Valid entities
        valid, error = skill.validate_entities({'duration': 60})
        assert valid is True
        assert error is None

        # Invalid entities
        valid, error = skill.validate_entities({})
        assert valid is False
        assert error is not None

    def test_helper_methods(self):
        """Test helper methods for creating responses."""
        skill = MockWeatherSkill()

        # Test success response helper
        response = skill._create_success_response(
            message="Success",
            data={'key': 'value'}
        )
        assert response.success is True
        assert response.message == "Success"

        # Test error response helper
        response = skill._create_error_response(
            error_message="Error occurred",
            data={'error': True}
        )
        assert response.success is False
        assert "Error occurred" in response.message


# Tests for SkillManager
class TestSkillManager:
    """Test SkillManager functionality."""

    @pytest.fixture
    def manager(self):
        """Create a skill manager for testing."""
        return SkillManager(auto_discover=False)

    def test_manager_initialization(self, manager):
        """Test manager initialization."""
        assert isinstance(manager, SkillManager)
        assert len(manager.skills) == 0

    def test_register_skill(self, manager):
        """Test skill registration."""
        skill = MockWeatherSkill()
        result = manager.register_skill(skill)

        assert result is True
        assert 'weather' in manager.skills
        assert manager.get_skill('weather') == skill

    def test_register_multiple_skills(self, manager):
        """Test registering multiple skills."""
        weather_skill = MockWeatherSkill()
        timer_skill = MockTimerSkill()

        manager.register_skill(weather_skill)
        manager.register_skill(timer_skill)

        assert len(manager.skills) == 2
        assert 'weather' in manager.skills
        assert 'timer' in manager.skills

    def test_unregister_skill(self, manager):
        """Test skill unregistration."""
        skill = MockWeatherSkill()
        manager.register_skill(skill)

        result = manager.unregister_skill('weather')

        assert result is True
        assert 'weather' not in manager.skills

    def test_list_skills(self, manager):
        """Test listing skills."""
        manager.register_skill(MockWeatherSkill())
        manager.register_skill(MockTimerSkill())

        skills = manager.list_skills()

        assert len(skills) == 2
        assert any(s['name'] == 'weather' for s in skills)
        assert any(s['name'] == 'timer' for s in skills)

    def test_list_enabled_skills_only(self, manager):
        """Test listing only enabled skills."""
        weather_skill = MockWeatherSkill()
        timer_skill = MockTimerSkill()

        manager.register_skill(weather_skill)
        manager.register_skill(timer_skill)

        # Disable one skill
        manager.disable_skill('timer')

        enabled_skills = manager.list_skills(enabled_only=True)

        assert len(enabled_skills) == 1
        assert enabled_skills[0]['name'] == 'weather'

    def test_enable_disable_skill(self, manager):
        """Test enabling and disabling skills."""
        skill = MockWeatherSkill()
        manager.register_skill(skill)

        # Disable
        result = manager.disable_skill('weather')
        assert result is True
        assert not manager.get_skill('weather').is_enabled()

        # Enable
        result = manager.enable_skill('weather')
        assert result is True
        assert manager.get_skill('weather').is_enabled()

    def test_route_intent(self, manager):
        """Test intent routing."""
        manager.register_skill(MockWeatherSkill())

        response = manager.route_intent(
            intent="weather.query",
            entities={'location': 'Boston'},
            context={}
        )

        assert response.success is True
        assert 'Boston' in response.message

    def test_route_to_correct_skill(self, manager):
        """Test that intents are routed to the correct skill."""
        manager.register_skill(MockWeatherSkill())
        manager.register_skill(MockTimerSkill())

        # Test weather intent
        response = manager.route_intent(
            intent="weather.query",
            entities={'location': 'Seattle'},
            context={}
        )
        assert 'Seattle' in response.message

        # Test timer intent
        response = manager.route_intent(
            intent="timer.set",
            entities={'duration': 120},
            context={}
        )
        assert '120' in response.message

    def test_route_unknown_intent(self, manager):
        """Test routing an unknown intent."""
        manager.register_skill(MockWeatherSkill())

        response = manager.route_intent(
            intent="unknown.intent",
            entities={},
            context={}
        )

        assert response.success is False
        assert 'not sure' in response.message.lower()

    def test_route_intent_with_disabled_skill(self, manager):
        """Test routing to a disabled skill."""
        manager.register_skill(MockWeatherSkill())
        manager.disable_skill('weather')

        response = manager.route_intent(
            intent="weather.query",
            entities={},
            context={}
        )

        assert response.success is False

    def test_error_handling(self, manager):
        """Test error handling in skill execution."""
        manager.register_skill(MockFailingSkill())

        response = manager.route_intent(
            intent="failing.test",
            entities={},
            context={}
        )

        assert response.success is False
        assert 'error' in response.message.lower()

    def test_entity_validation_error(self, manager):
        """Test entity validation error handling."""
        manager.register_skill(MockTimerSkill())

        # Missing required 'duration' entity
        response = manager.route_intent(
            intent="timer.set",
            entities={},
            context={}
        )

        assert response.success is False
        assert 'duration' in response.message.lower()

    def test_intent_caching(self, manager):
        """Test intent caching."""
        manager.register_skill(MockWeatherSkill())

        # First call - cache miss
        response1 = manager.route_intent(
            intent="weather.query",
            entities={},
            context={}
        )

        # Second call - cache hit
        response2 = manager.route_intent(
            intent="weather.query",
            entities={},
            context={}
        )

        assert response1.success is True
        assert response2.success is True
        assert 'weather.query' in manager._intent_cache

    def test_get_help(self, manager):
        """Test getting help text."""
        manager.register_skill(MockWeatherSkill())
        manager.register_skill(MockTimerSkill())

        help_text = manager.get_help()

        assert 'weather' in help_text
        assert 'timer' in help_text

    def test_get_stats(self, manager):
        """Test getting statistics."""
        manager.register_skill(MockWeatherSkill())
        manager.register_skill(MockTimerSkill())
        manager.disable_skill('timer')

        stats = manager.get_stats()

        assert stats['total_skills'] == 2
        assert stats['enabled_skills'] == 1
        assert stats['disabled_skills'] == 1

    def test_shutdown(self, manager):
        """Test manager shutdown."""
        skill = MockWeatherSkill()
        skill.cleanup = Mock()

        manager.register_skill(skill)
        manager.shutdown()

        skill.cleanup.assert_called_once()
        assert len(manager.skills) == 0


# Tests for exceptions
class TestSkillExceptions:
    """Test skill exception handling."""

    def test_skill_not_found_error(self):
        """Test SkillNotFoundError."""
        manager = SkillManager(auto_discover=False)

        with pytest.raises(SkillNotFoundError):
            manager.enable_skill('nonexistent')

    def test_skill_execution_error(self):
        """Test SkillExecutionError."""
        error = SkillExecutionError("Test error")
        assert str(error) == "Test error"

    def test_skill_validation_error(self):
        """Test SkillValidationError."""
        error = SkillValidationError("Validation failed")
        assert str(error) == "Validation failed"


# Integration tests
class TestSkillSystemIntegration:
    """Integration tests for the complete skill system."""

    def test_complete_workflow(self):
        """Test a complete workflow from intent to response."""
        # Create manager
        manager = SkillManager(auto_discover=False)

        # Register skills
        manager.register_skill(MockWeatherSkill())
        manager.register_skill(MockTimerSkill())

        # Route weather intent
        weather_response = manager.route_intent(
            intent="weather.query",
            entities={'location': 'London'},
            context={}
        )

        assert weather_response.success is True
        assert 'London' in weather_response.message

        # Route timer intent
        timer_response = manager.route_intent(
            intent="timer.set",
            entities={'duration': 300},
            context={}
        )

        assert timer_response.success is True
        assert timer_response.context_update.get('timer_id') is not None

    def test_skill_lifecycle(self):
        """Test complete skill lifecycle."""
        manager = SkillManager(auto_discover=False)
        skill = MockWeatherSkill()

        # Register
        assert manager.register_skill(skill) is True

        # Use
        response = manager.route_intent("weather.query", {}, {})
        assert response.success is True

        # Disable
        assert manager.disable_skill('weather') is True
        response = manager.route_intent("weather.query", {}, {})
        assert response.success is False

        # Re-enable
        assert manager.enable_skill('weather') is True
        response = manager.route_intent("weather.query", {}, {})
        assert response.success is True

        # Unregister
        assert manager.unregister_skill('weather') is True
        assert manager.get_skill('weather') is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
