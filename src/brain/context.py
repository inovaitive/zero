"""
Context Management for ZERO Assistant.

This module manages conversation context and session state:
- Conversation history
- User preferences
- Active references (for follow-up questions)
- Session state
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import logging

logger = logging.getLogger(__name__)


@dataclass
class Interaction:
    """Represents a single user-assistant interaction."""

    user_input: str
    intent: str
    entities: Dict[str, Any]
    response: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConversationContext:
    """Represents the current conversation context."""

    # Conversation history
    history: List[Interaction] = field(default_factory=list)

    # Current references (for follow-up questions)
    current_topic: Optional[str] = None
    current_location: Optional[str] = None
    current_app: Optional[str] = None
    active_timers: List[str] = field(default_factory=list)

    # User preferences
    preferences: Dict[str, Any] = field(default_factory=dict)

    # Session metadata
    session_start: datetime = field(default_factory=datetime.now)
    last_interaction: datetime = field(default_factory=datetime.now)

    def is_expired(self, timeout_seconds: int = 300) -> bool:
        """Check if context has expired."""
        time_since_last = datetime.now() - self.last_interaction
        return time_since_last.total_seconds() > timeout_seconds

    def get_recent_history(self, count: int = 5) -> List[Interaction]:
        """Get recent interactions."""
        return self.history[-count:] if self.history else []

    def add_interaction(self, interaction: Interaction):
        """Add an interaction to history."""
        self.history.append(interaction)
        self.last_interaction = datetime.now()

    def clear_history(self):
        """Clear conversation history."""
        self.history.clear()
        logger.info("Conversation history cleared")

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'history_count': len(self.history),
            'current_topic': self.current_topic,
            'current_location': self.current_location,
            'current_app': self.current_app,
            'active_timers': self.active_timers,
            'session_start': self.session_start.isoformat(),
            'last_interaction': self.last_interaction.isoformat(),
        }


class ContextManager:
    """
    Manages conversation context and session state.

    Features:
    - Tracks conversation history
    - Maintains current context for follow-up questions
    - Learns user preferences
    - Handles context expiration
    """

    def __init__(
        self,
        max_history: int = 5,
        timeout_seconds: int = 300,
        enable_learning: bool = True,
    ):
        """
        Initialize context manager.

        Args:
            max_history: Maximum number of interactions to keep
            timeout_seconds: Context timeout in seconds (default 5 minutes)
            enable_learning: Whether to learn user preferences
        """
        self.max_history = max_history
        self.timeout_seconds = timeout_seconds
        self.enable_learning = enable_learning

        self.context = ConversationContext()

        logger.info(
            f"Context manager initialized (max_history={max_history}, "
            f"timeout={timeout_seconds}s, learning={enable_learning})"
        )

    def update(
        self,
        user_input: str,
        intent: str,
        entities: Dict[str, Any],
        response: str,
        metadata: Dict[str, Any] = None,
    ):
        """
        Update context with a new interaction.

        Args:
            user_input: User's input text
            intent: Classified intent
            entities: Extracted entities
            response: Assistant's response
            metadata: Optional metadata
        """
        # Check if context has expired
        if self.context.is_expired(self.timeout_seconds):
            logger.info("Context expired, resetting")
            self.reset()

        # Create interaction
        interaction = Interaction(
            user_input=user_input,
            intent=intent,
            entities=entities,
            response=response,
            metadata=metadata or {},
        )

        # Add to history
        self.context.add_interaction(interaction)

        # Update current references
        self._update_references(intent, entities)

        # Learn preferences
        if self.enable_learning:
            self._learn_preferences(intent, entities)

        # Trim history if needed
        if len(self.context.history) > self.max_history:
            self.context.history = self.context.history[-self.max_history:]

        logger.debug(f"Context updated: {self.context.to_dict()}")

    def _update_references(self, intent: str, entities: Dict[str, Any]):
        """Update current context references."""
        # Update topic based on intent
        if '.' in intent:
            topic = intent.split('.')[0]
            self.context.current_topic = topic

        # Update location if mentioned
        if 'location' in entities:
            self.context.current_location = entities['location']
            logger.debug(f"Updated current location: {entities['location']}")

        # Update app if mentioned
        if 'app_name' in entities:
            self.context.current_app = entities['app_name']
            logger.debug(f"Updated current app: {entities['app_name']}")

        # Track timer operations
        if intent == 'timer.set' and 'timer_id' in entities:
            timer_id = entities['timer_id']
            if timer_id not in self.context.active_timers:
                self.context.active_timers.append(timer_id)
                logger.debug(f"Added timer to context: {timer_id}")

        elif intent == 'timer.cancel' and 'timer_id' in entities:
            timer_id = entities['timer_id']
            if timer_id in self.context.active_timers:
                self.context.active_timers.remove(timer_id)
                logger.debug(f"Removed timer from context: {timer_id}")

    def _learn_preferences(self, intent: str, entities: Dict[str, Any]):
        """Learn user preferences from interactions."""
        # Learn preferred location for weather
        if intent == 'weather.query' and 'location' in entities:
            if 'preferred_location' not in self.context.preferences:
                self.context.preferences['preferred_location'] = entities['location']
                logger.info(f"Learned preferred location: {entities['location']}")

        # Learn preferred apps
        if intent == 'app.open' and 'app_name' in entities:
            app_name = entities['app_name']
            if 'frequently_used_apps' not in self.context.preferences:
                self.context.preferences['frequently_used_apps'] = {}

            freq_apps = self.context.preferences['frequently_used_apps']
            freq_apps[app_name] = freq_apps.get(app_name, 0) + 1

        # Learn preferred units (temperature, distance, etc.)
        if 'units' in entities:
            self.context.preferences['units'] = entities['units']

    def get_context_for_query(self, user_input: str) -> Dict[str, Any]:
        """
        Get relevant context for processing a user query.

        Args:
            user_input: User's input text

        Returns:
            Dictionary with relevant context
        """
        context_data = {
            'has_history': len(self.context.history) > 0,
            'current_topic': self.context.current_topic,
            'preferences': self.context.preferences.copy(),
        }

        # Add recent history
        recent = self.context.get_recent_history(3)
        if recent:
            context_data['recent_intents'] = [i.intent for i in recent]
            context_data['recent_entities'] = [i.entities for i in recent]

        # Add current references if they might be relevant
        if self._is_follow_up_question(user_input):
            if self.context.current_location:
                context_data['implied_location'] = self.context.current_location

            if self.context.current_app:
                context_data['implied_app'] = self.context.current_app

            if self.context.current_topic:
                context_data['implied_topic'] = self.context.current_topic

        # Add active timers
        if self.context.active_timers:
            context_data['active_timers'] = self.context.active_timers.copy()

        return context_data

    def _is_follow_up_question(self, user_input: str) -> bool:
        """Detect if user input is a follow-up question."""
        follow_up_patterns = [
            'what about', 'how about', 'and', 'also',
            'tomorrow', 'next', 'cancel it', 'stop it',
            'what else', 'anything else',
        ]

        user_input_lower = user_input.lower()
        return any(pattern in user_input_lower for pattern in follow_up_patterns)

    def get_last_interaction(self) -> Optional[Interaction]:
        """Get the last interaction."""
        return self.context.history[-1] if self.context.history else None

    def get_history(self, count: int = None) -> List[Interaction]:
        """
        Get conversation history.

        Args:
            count: Number of recent interactions (None for all)

        Returns:
            List of interactions
        """
        if count is None:
            return self.context.history.copy()
        return self.context.get_recent_history(count)

    def get_preference(self, key: str, default: Any = None) -> Any:
        """Get a user preference."""
        return self.context.preferences.get(key, default)

    def set_preference(self, key: str, value: Any):
        """Set a user preference."""
        self.context.preferences[key] = value
        logger.info(f"Set preference: {key} = {value}")

    def get_active_timers(self) -> List[str]:
        """Get list of active timer IDs."""
        return self.context.active_timers.copy()

    def reset(self):
        """Reset the context."""
        self.context = ConversationContext()
        logger.info("Context reset")

    def get_status(self) -> Dict[str, Any]:
        """Get context status."""
        return {
            'context': self.context.to_dict(),
            'max_history': self.max_history,
            'timeout_seconds': self.timeout_seconds,
            'enable_learning': self.enable_learning,
            'is_expired': self.context.is_expired(self.timeout_seconds),
        }

    def get_conversation_summary(self) -> str:
        """Get a text summary of the conversation."""
        if not self.context.history:
            return "No conversation history"

        lines = [f"Conversation (started {self.context.session_start.strftime('%H:%M:%S')}):"]

        for i, interaction in enumerate(self.context.get_recent_history(5), 1):
            time_str = interaction.timestamp.strftime('%H:%M:%S')
            lines.append(f"{i}. [{time_str}] User: {interaction.user_input}")
            lines.append(f"   Intent: {interaction.intent}")
            lines.append(f"   Response: {interaction.response[:60]}...")

        if self.context.current_topic:
            lines.append(f"\nCurrent topic: {self.context.current_topic}")

        if self.context.current_location:
            lines.append(f"Current location: {self.context.current_location}")

        return '\n'.join(lines)


# Convenience function
def create_context_manager(config: Dict[str, Any] = None) -> ContextManager:
    """
    Create a context manager with configuration.

    Args:
        config: Configuration dictionary

    Returns:
        Configured ContextManager instance
    """
    if config is None:
        config = {}

    context_config = config.get('context', {})

    return ContextManager(
        max_history=context_config.get('max_history', 5),
        timeout_seconds=context_config.get('timeout', 300),
        enable_learning=context_config.get('enabled', True),
    )
