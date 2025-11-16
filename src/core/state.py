"""
State management for ZERO assistant.

This module defines the state machine for the voice assistant's lifecycle
and provides thread-safe state management.
"""

from enum import Enum, auto
from threading import Lock
from typing import Optional, Callable, Dict, Any
from datetime import datetime


class AssistantState(Enum):
    """
    States of the voice assistant.

    The assistant follows this state flow:
    IDLE -> LISTENING -> PROCESSING -> EXECUTING -> RESPONDING -> IDLE
           ^                                                         |
           |_________________________________________________________|

    ERROR can be entered from any state and returns to IDLE.
    """
    IDLE = auto()           # Waiting for wake word
    LISTENING = auto()      # Recording user command
    PROCESSING = auto()     # Understanding intent (STT + NLU)
    EXECUTING = auto()      # Running skill
    RESPONDING = auto()     # Speaking response (TTS)
    ERROR = auto()          # Handling error
    SHUTDOWN = auto()       # Shutting down


class StateManager:
    """
    Thread-safe state manager for the voice assistant.

    Manages state transitions, tracks state history, and provides
    callbacks for state changes.
    """

    def __init__(self):
        """Initialize state manager."""
        self._state = AssistantState.IDLE
        self._previous_state: Optional[AssistantState] = None
        self._lock = Lock()
        self._callbacks: Dict[AssistantState, list[Callable]] = {}
        self._state_history: list[tuple[AssistantState, datetime]] = []
        self._max_history = 100

        # Metadata for current state
        self._metadata: Dict[str, Any] = {}

    @property
    def state(self) -> AssistantState:
        """Get current state."""
        with self._lock:
            return self._state

    @property
    def previous_state(self) -> Optional[AssistantState]:
        """Get previous state."""
        with self._lock:
            return self._previous_state

    @property
    def metadata(self) -> Dict[str, Any]:
        """Get metadata for current state."""
        with self._lock:
            return self._metadata.copy()

    def transition_to(
        self,
        new_state: AssistantState,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Transition to a new state.

        Args:
            new_state: State to transition to
            metadata: Optional metadata for the new state

        Returns:
            True if transition was successful, False otherwise
        """
        with self._lock:
            # Validate transition
            if not self._is_valid_transition(self._state, new_state):
                return False

            # Store previous state
            self._previous_state = self._state

            # Update state
            self._state = new_state

            # Update metadata
            self._metadata = metadata or {}

            # Record in history
            self._state_history.append((new_state, datetime.now()))
            if len(self._state_history) > self._max_history:
                self._state_history.pop(0)

            # Trigger callbacks
            self._trigger_callbacks(new_state)

            return True

    def _is_valid_transition(
        self,
        from_state: AssistantState,
        to_state: AssistantState
    ) -> bool:
        """
        Check if a state transition is valid.

        Args:
            from_state: Current state
            to_state: Desired state

        Returns:
            True if transition is valid
        """
        # Can always transition to ERROR or SHUTDOWN
        if to_state in (AssistantState.ERROR, AssistantState.SHUTDOWN):
            return True

        # From ERROR, can only go to IDLE
        if from_state == AssistantState.ERROR:
            return to_state == AssistantState.IDLE

        # From SHUTDOWN, cannot transition
        if from_state == AssistantState.SHUTDOWN:
            return False

        # Normal flow: IDLE -> LISTENING -> PROCESSING -> EXECUTING -> RESPONDING -> IDLE
        valid_transitions = {
            AssistantState.IDLE: [AssistantState.LISTENING],
            AssistantState.LISTENING: [AssistantState.PROCESSING, AssistantState.IDLE],
            AssistantState.PROCESSING: [AssistantState.EXECUTING, AssistantState.IDLE],
            AssistantState.EXECUTING: [AssistantState.RESPONDING, AssistantState.IDLE],
            AssistantState.RESPONDING: [AssistantState.IDLE],
        }

        return to_state in valid_transitions.get(from_state, [])

    def register_callback(
        self,
        state: AssistantState,
        callback: Callable[[AssistantState, Dict[str, Any]], None]
    ):
        """
        Register a callback for when a specific state is entered.

        Args:
            state: State to watch
            callback: Function to call when state is entered.
                     Receives (state, metadata) as arguments.
        """
        with self._lock:
            if state not in self._callbacks:
                self._callbacks[state] = []
            self._callbacks[state].append(callback)

    def _trigger_callbacks(self, state: AssistantState):
        """
        Trigger callbacks for a state (internal method).

        Args:
            state: State that was entered
        """
        if state in self._callbacks:
            for callback in self._callbacks[state]:
                try:
                    callback(state, self._metadata)
                except Exception as e:
                    # Don't let callback errors crash the state manager
                    print(f"Error in state callback: {e}")

    def get_history(self, limit: int = 10) -> list[tuple[AssistantState, datetime]]:
        """
        Get recent state history.

        Args:
            limit: Maximum number of history items to return

        Returns:
            List of (state, timestamp) tuples, most recent first
        """
        with self._lock:
            return list(reversed(self._state_history[-limit:]))

    def is_idle(self) -> bool:
        """Check if assistant is idle."""
        return self.state == AssistantState.IDLE

    def is_listening(self) -> bool:
        """Check if assistant is listening."""
        return self.state == AssistantState.LISTENING

    def is_processing(self) -> bool:
        """Check if assistant is processing."""
        return self.state == AssistantState.PROCESSING

    def is_executing(self) -> bool:
        """Check if assistant is executing a skill."""
        return self.state == AssistantState.EXECUTING

    def is_responding(self) -> bool:
        """Check if assistant is responding."""
        return self.state == AssistantState.RESPONDING

    def is_error(self) -> bool:
        """Check if assistant is in error state."""
        return self.state == AssistantState.ERROR

    def is_active(self) -> bool:
        """Check if assistant is actively processing a command."""
        return self.state in (
            AssistantState.LISTENING,
            AssistantState.PROCESSING,
            AssistantState.EXECUTING,
            AssistantState.RESPONDING,
        )

    def reset(self):
        """Reset state to IDLE."""
        with self._lock:
            self._state = AssistantState.IDLE
            self._previous_state = None
            self._metadata = {}

    def __str__(self) -> str:
        """String representation of current state."""
        return f"StateManager(state={self._state.name})"

    def __repr__(self) -> str:
        """Detailed string representation."""
        return (
            f"StateManager(state={self._state.name}, "
            f"previous={self._previous_state.name if self._previous_state else None})"
        )


# Global state manager instance
_state_manager_instance: Optional[StateManager] = None


def get_state_manager() -> StateManager:
    """
    Get global state manager instance.

    Returns:
        Global StateManager instance
    """
    global _state_manager_instance

    if _state_manager_instance is None:
        _state_manager_instance = StateManager()

    return _state_manager_instance
