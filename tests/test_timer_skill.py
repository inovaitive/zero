"""
Tests for Timer Skill.

This module tests the timer skill functionality:
- Setting timers
- Cancelling timers
- Listing timers
- Timer status queries
- Pause/resume
- Background execution
- Persistence
"""

import pytest
import time
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from src.skills.timer_skill import TimerSkill, Timer
from src.skills.base_skill import SkillResponse


@pytest.fixture
def timer_config():
    """Create test configuration."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config = {
            'persistence': {
                'enabled': True,
                'path': str(Path(tmpdir) / 'timers.json'),
            },
            'alerts': {
                'sound': False,  # Disable for testing
                'notification': False,  # Disable for testing
                'tts': True,
            },
        }
        yield config


@pytest.fixture
def timer_skill(timer_config):
    """Create TimerSkill instance for testing."""
    skill = TimerSkill(config=timer_config)
    skill.initialize()
    yield skill
    skill.cleanup()


class TestTimerSkillBasics:
    """Test basic timer skill functionality."""

    def test_skill_initialization(self, timer_skill):
        """Test that timer skill initializes correctly."""
        assert timer_skill.name == "timer"
        assert timer_skill.enabled is True
        assert timer_skill.version == "1.0.0"
        assert isinstance(timer_skill.timers, dict)
        assert len(timer_skill.timers) == 0

    def test_can_handle_timer_intents(self, timer_skill):
        """Test that skill can handle timer intents."""
        assert timer_skill.can_handle("timer.set") is True
        assert timer_skill.can_handle("timer.cancel") is True
        assert timer_skill.can_handle("timer.list") is True
        assert timer_skill.can_handle("timer.status") is True
        assert timer_skill.can_handle("timer.pause") is True
        assert timer_skill.can_handle("timer.resume") is True

        # Should not handle other intents
        assert timer_skill.can_handle("weather.query") is False
        assert timer_skill.can_handle("app.open") is False

    def test_get_supported_intents(self, timer_skill):
        """Test getting supported intents."""
        intents = timer_skill.get_supported_intents()
        assert "timer.set" in intents
        assert "timer.cancel" in intents
        assert "timer.list" in intents
        assert "timer.status" in intents

    def test_get_help(self, timer_skill):
        """Test getting help text."""
        help_text = timer_skill.get_help()
        assert "Timer Skill" in help_text
        assert "Set a timer" in help_text


class TestTimerClass:
    """Test Timer dataclass."""

    def test_timer_creation(self):
        """Test creating a timer."""
        from datetime import datetime
        timer = Timer(
            name="test_timer",
            duration=300,  # 5 minutes
            remaining=300,
            start_time=datetime.now(),
        )
        assert timer.name == "test_timer"
        assert timer.duration == 300
        assert timer.paused is False
        assert timer.completed is False

    def test_timer_time_formatting(self):
        """Test time formatting."""
        from datetime import datetime
        timer = Timer(
            name="test",
            duration=3665,  # 1 hour, 1 minute, 5 seconds
            remaining=3665,
            start_time=datetime.now(),
        )
        formatted = timer.format_time(3665)
        assert "1 hour" in formatted
        assert "1 minute" in formatted
        assert "5 seconds" in formatted

    def test_timer_serialization(self):
        """Test timer to/from dict conversion."""
        from datetime import datetime
        timer = Timer(
            name="test",
            duration=300,
            remaining=300,
            start_time=datetime.now(),
        )

        # Convert to dict
        timer_dict = timer.to_dict()
        assert timer_dict['name'] == "test"
        assert timer_dict['duration'] == 300

        # Convert back from dict
        restored_timer = Timer.from_dict(timer_dict)
        assert restored_timer.name == timer.name
        assert restored_timer.duration == timer.duration


class TestSetTimer:
    """Test setting timers."""

    def test_set_simple_timer(self, timer_skill):
        """Test setting a simple timer."""
        entities = {'duration': 300}  # 5 minutes
        context = {}

        response = timer_skill.execute("timer.set", entities, context)

        assert isinstance(response, SkillResponse)
        assert response.success is True
        assert "Timer set for 5 minutes" in response.message
        assert len(timer_skill.timers) == 1

    def test_set_named_timer(self, timer_skill):
        """Test setting a named timer."""
        entities = {
            'duration': 1200,  # 20 minutes
            'timer_name': 'pizza',
        }
        context = {}

        response = timer_skill.execute("timer.set", entities, context)

        assert response.success is True
        assert "pizza" in response.message.lower()
        assert "pizza" in timer_skill.timers
        assert timer_skill.timers['pizza'].duration == 1200

    def test_set_timer_without_duration(self, timer_skill):
        """Test setting timer without duration (should fail)."""
        entities = {}
        context = {}

        response = timer_skill.execute("timer.set", entities, context)

        assert response.success is False
        assert "duration" in response.message.lower()

    def test_set_multiple_timers(self, timer_skill):
        """Test setting multiple timers."""
        # First timer
        response1 = timer_skill.execute(
            "timer.set",
            {'duration': 300, 'timer_name': 'timer1'},
            {}
        )
        assert response1.success is True

        # Second timer
        response2 = timer_skill.execute(
            "timer.set",
            {'duration': 600, 'timer_name': 'timer2'},
            {}
        )
        assert response2.success is True

        assert len(timer_skill.timers) == 2

    def test_set_duplicate_timer_name(self, timer_skill):
        """Test setting timer with duplicate name."""
        entities = {'duration': 300, 'timer_name': 'test'}

        # First timer
        response1 = timer_skill.execute("timer.set", entities, {})
        assert response1.success is True

        # Duplicate timer
        response2 = timer_skill.execute("timer.set", entities, {})
        assert response2.success is False
        assert "already exists" in response2.message


class TestCancelTimer:
    """Test cancelling timers."""

    def test_cancel_timer_by_name(self, timer_skill):
        """Test cancelling a timer by name."""
        # Set timer
        timer_skill.execute("timer.set", {'duration': 300, 'timer_name': 'test'}, {})

        # Cancel timer
        response = timer_skill.execute(
            "timer.cancel",
            {'timer_name': 'test'},
            {}
        )

        assert response.success is True
        assert "cancelled" in response.message.lower()
        assert 'test' not in timer_skill.timers

    def test_cancel_timer_from_context(self, timer_skill):
        """Test cancelling timer using context."""
        # Set timer
        timer_skill.execute("timer.set", {'duration': 300, 'timer_name': 'test'}, {})

        # Cancel using context
        response = timer_skill.execute(
            "timer.cancel",
            {},
            {'last_timer': 'test'}
        )

        assert response.success is True
        assert 'test' not in timer_skill.timers

    def test_cancel_only_timer(self, timer_skill):
        """Test cancelling the only active timer."""
        # Set one timer
        timer_skill.execute("timer.set", {'duration': 300, 'timer_name': 'test'}, {})

        # Cancel without specifying name
        response = timer_skill.execute("timer.cancel", {}, {})

        assert response.success is True
        assert len(timer_skill.timers) == 0

    def test_cancel_nonexistent_timer(self, timer_skill):
        """Test cancelling a timer that doesn't exist."""
        response = timer_skill.execute(
            "timer.cancel",
            {'timer_name': 'nonexistent'},
            {}
        )

        assert response.success is False
        assert "couldn't find" in response.message.lower()

    def test_cancel_with_multiple_timers_no_name(self, timer_skill):
        """Test cancelling when multiple timers exist but no name given."""
        # Set multiple timers
        timer_skill.execute("timer.set", {'duration': 300, 'timer_name': 'timer1'}, {})
        timer_skill.execute("timer.set", {'duration': 600, 'timer_name': 'timer2'}, {})

        # Try to cancel without name
        response = timer_skill.execute("timer.cancel", {}, {})

        assert response.success is False
        assert "multiple timers" in response.message.lower()


class TestListTimers:
    """Test listing timers."""

    def test_list_no_timers(self, timer_skill):
        """Test listing when no timers exist."""
        response = timer_skill.execute("timer.list", {}, {})

        assert response.success is True
        assert "no active timers" in response.message.lower()
        assert response.data['timer_count'] == 0

    def test_list_single_timer(self, timer_skill):
        """Test listing a single timer."""
        timer_skill.execute("timer.set", {'duration': 300, 'timer_name': 'test'}, {})

        response = timer_skill.execute("timer.list", {}, {})

        assert response.success is True
        assert "one" in response.message.lower()
        assert response.data['timer_count'] == 1

    def test_list_multiple_timers(self, timer_skill):
        """Test listing multiple timers."""
        timer_skill.execute("timer.set", {'duration': 300, 'timer_name': 'timer1'}, {})
        timer_skill.execute("timer.set", {'duration': 600, 'timer_name': 'timer2'}, {})
        timer_skill.execute("timer.set", {'duration': 900, 'timer_name': 'timer3'}, {})

        response = timer_skill.execute("timer.list", {}, {})

        assert response.success is True
        assert response.data['timer_count'] == 3
        assert "3 active timers" in response.message


class TestTimerStatus:
    """Test timer status queries."""

    def test_get_timer_status(self, timer_skill):
        """Test getting timer status."""
        timer_skill.execute("timer.set", {'duration': 300, 'timer_name': 'test'}, {})

        response = timer_skill.execute(
            "timer.status",
            {'timer_name': 'test'},
            {}
        )

        assert response.success is True
        assert "remaining" in response.message.lower()
        assert response.data['timer_name'] == 'test'

    def test_get_status_nonexistent_timer(self, timer_skill):
        """Test getting status of nonexistent timer."""
        response = timer_skill.execute(
            "timer.status",
            {'timer_name': 'nonexistent'},
            {}
        )

        assert response.success is False


class TestPauseResume:
    """Test pause and resume functionality."""

    def test_pause_timer(self, timer_skill):
        """Test pausing a timer."""
        timer_skill.execute("timer.set", {'duration': 300, 'timer_name': 'test'}, {})

        response = timer_skill.execute(
            "timer.pause",
            {'timer_name': 'test'},
            {}
        )

        assert response.success is True
        assert timer_skill.timers['test'].paused is True

    def test_resume_timer(self, timer_skill):
        """Test resuming a paused timer."""
        timer_skill.execute("timer.set", {'duration': 300, 'timer_name': 'test'}, {})
        timer_skill.execute("timer.pause", {'timer_name': 'test'}, {})

        response = timer_skill.execute(
            "timer.resume",
            {'timer_name': 'test'},
            {}
        )

        assert response.success is True
        assert timer_skill.timers['test'].paused is False

    def test_pause_already_paused(self, timer_skill):
        """Test pausing an already paused timer."""
        timer_skill.execute("timer.set", {'duration': 300, 'timer_name': 'test'}, {})
        timer_skill.execute("timer.pause", {'timer_name': 'test'}, {})

        response = timer_skill.execute(
            "timer.pause",
            {'timer_name': 'test'},
            {}
        )

        assert response.success is True
        assert "already paused" in response.message.lower()


class TestTimerCompletion:
    """Test timer completion and alerts."""

    def test_timer_completes(self, timer_skill):
        """Test that a timer completes after duration."""
        # Set a 2-second timer
        timer_skill.execute("timer.set", {'duration': 2, 'timer_name': 'test'}, {})

        # Wait for completion
        time.sleep(3)

        # Check timer is completed
        assert timer_skill.timers['test'].completed is True

    def test_timer_callback_on_completion(self, timer_skill):
        """Test that callback is called when timer completes."""
        callback_called = []

        def mock_callback(message):
            callback_called.append(message)

        timer_skill.set_alert_callback(mock_callback)

        # Set a 2-second timer
        timer_skill.execute("timer.set", {'duration': 2, 'timer_name': 'test'}, {})

        # Wait for completion
        time.sleep(3)

        # Check callback was called
        assert len(callback_called) > 0
        assert "complete" in callback_called[0].lower()


class TestTimerPersistence:
    """Test timer persistence."""

    def test_save_timers(self, timer_skill, timer_config):
        """Test saving timers to file."""
        # Set timers
        timer_skill.execute("timer.set", {'duration': 300, 'timer_name': 'test1'}, {})
        timer_skill.execute("timer.set", {'duration': 600, 'timer_name': 'test2'}, {})

        # Save
        timer_skill._save_timers()

        # Check file exists
        persistence_path = Path(timer_config['persistence']['path'])
        assert persistence_path.exists()

        # Check content
        with open(persistence_path, 'r') as f:
            data = json.load(f)
        assert 'test1' in data
        assert 'test2' in data

    def test_restore_timers(self, timer_config):
        """Test restoring timers from file."""
        # Create first skill and set timers
        skill1 = TimerSkill(config=timer_config)
        skill1.initialize()
        skill1.execute("timer.set", {'duration': 300, 'timer_name': 'test'}, {})
        skill1._save_timers()
        skill1.cleanup()

        # Create new skill and restore
        skill2 = TimerSkill(config=timer_config)
        skill2.initialize()

        # Check timer was restored
        assert 'test' in skill2.timers
        assert skill2.timers['test'].duration == 300

        skill2.cleanup()

    def test_restore_completed_timers_skipped(self, timer_config):
        """Test that completed timers are not restored."""
        # Create and complete a timer
        skill1 = TimerSkill(config=timer_config)
        skill1.initialize()
        skill1.execute("timer.set", {'duration': 1, 'timer_name': 'test'}, {})
        time.sleep(2)  # Wait for completion
        skill1._save_timers()
        skill1.cleanup()

        # Restore
        skill2 = TimerSkill(config=timer_config)
        skill2.initialize()

        # Completed timer should not be restored
        assert 'test' not in skill2.timers or skill2.timers['test'].completed

        skill2.cleanup()


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_very_short_timer(self, timer_skill):
        """Test setting a very short timer (1 second)."""
        response = timer_skill.execute("timer.set", {'duration': 1}, {})
        assert response.success is True

        time.sleep(2)
        # Timer should be completed
        timer_name = response.data['timer_name']
        assert timer_skill.timers[timer_name].completed is True

    def test_invalid_intent(self, timer_skill):
        """Test executing an invalid intent."""
        response = timer_skill.execute("timer.invalid", {}, {})
        assert response.success is False

    def test_concurrent_timer_operations(self, timer_skill):
        """Test that concurrent operations are thread-safe."""
        import threading

        def set_timer(name):
            timer_skill.execute(
                "timer.set",
                {'duration': 10, 'timer_name': name},
                {}
            )

        # Set multiple timers concurrently
        threads = []
        for i in range(5):
            t = threading.Thread(target=set_timer, args=(f'timer_{i}',))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All timers should be created
        assert len(timer_skill.timers) == 5


class TestIntegration:
    """Integration tests for timer skill."""

    def test_full_timer_lifecycle(self, timer_skill):
        """Test complete timer lifecycle."""
        # Set timer
        set_response = timer_skill.execute(
            "timer.set",
            {'duration': 5, 'timer_name': 'lifecycle_test'},
            {}
        )
        assert set_response.success is True

        # Check status
        status_response = timer_skill.execute(
            "timer.status",
            {'timer_name': 'lifecycle_test'},
            {}
        )
        assert status_response.success is True

        # Pause
        pause_response = timer_skill.execute(
            "timer.pause",
            {'timer_name': 'lifecycle_test'},
            {}
        )
        assert pause_response.success is True

        # Resume
        resume_response = timer_skill.execute(
            "timer.resume",
            {'timer_name': 'lifecycle_test'},
            {}
        )
        assert resume_response.success is True

        # List
        list_response = timer_skill.execute("timer.list", {}, {})
        assert list_response.success is True
        assert list_response.data['timer_count'] == 1

        # Cancel
        cancel_response = timer_skill.execute(
            "timer.cancel",
            {'timer_name': 'lifecycle_test'},
            {}
        )
        assert cancel_response.success is True
        assert 'lifecycle_test' not in timer_skill.timers

    def test_context_tracking(self, timer_skill):
        """Test that context is properly updated."""
        context = {}

        # Set timer
        response = timer_skill.execute(
            "timer.set",
            {'duration': 300, 'timer_name': 'context_test'},
            context
        )

        # Check context was updated
        assert 'last_timer' in response.context_update
        assert response.context_update['last_timer'] == 'context_test'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
