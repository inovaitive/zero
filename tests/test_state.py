"""
Tests for state management.
"""

import pytest
from src.core.state import AssistantState, StateManager


class TestStateManager:
    """Test state management system."""

    def test_initial_state_is_idle(self):
        """Test that initial state is IDLE."""
        manager = StateManager()
        assert manager.state == AssistantState.IDLE
        assert manager.is_idle()

    def test_valid_transition(self):
        """Test valid state transition."""
        manager = StateManager()

        # IDLE -> LISTENING is valid
        result = manager.transition_to(AssistantState.LISTENING)
        assert result is True
        assert manager.state == AssistantState.LISTENING
        assert manager.previous_state == AssistantState.IDLE

    def test_invalid_transition(self):
        """Test invalid state transition."""
        manager = StateManager()

        # IDLE -> EXECUTING is invalid (must go through LISTENING -> PROCESSING first)
        result = manager.transition_to(AssistantState.EXECUTING)
        assert result is False
        assert manager.state == AssistantState.IDLE  # State should not change

    def test_can_always_transition_to_error(self):
        """Test that ERROR state can be reached from any state."""
        manager = StateManager()

        # From IDLE
        result = manager.transition_to(AssistantState.ERROR)
        assert result is True
        assert manager.is_error()

    def test_state_history(self):
        """Test state history tracking."""
        manager = StateManager()

        manager.transition_to(AssistantState.LISTENING)
        manager.transition_to(AssistantState.PROCESSING)

        history = manager.get_history(limit=3)
        assert len(history) >= 2
        assert history[0][0] == AssistantState.PROCESSING  # Most recent first

    def test_state_callbacks(self):
        """Test state change callbacks."""
        manager = StateManager()
        callback_called = []

        def callback(state, metadata):
            callback_called.append(state)

        manager.register_callback(AssistantState.LISTENING, callback)
        manager.transition_to(AssistantState.LISTENING)

        assert AssistantState.LISTENING in callback_called

    def test_state_metadata(self):
        """Test state metadata."""
        manager = StateManager()

        metadata = {'test': 'value'}
        manager.transition_to(AssistantState.LISTENING, metadata=metadata)

        assert manager.metadata == metadata

    def test_reset_to_idle(self):
        """Test resetting state to IDLE."""
        manager = StateManager()

        manager.transition_to(AssistantState.LISTENING)
        manager.reset()

        assert manager.state == AssistantState.IDLE
        assert manager.previous_state is None

    def test_is_active(self):
        """Test is_active method."""
        manager = StateManager()

        assert not manager.is_active()  # IDLE is not active

        manager.transition_to(AssistantState.LISTENING)
        assert manager.is_active()  # LISTENING is active

        manager.transition_to(AssistantState.PROCESSING)
        assert manager.is_active()  # PROCESSING is active
