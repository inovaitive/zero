"""
Base Skill Framework for ZERO Assistant.

This module provides the foundation for creating extensible skills:
- BaseSkill: Abstract base class for all skills
- SkillResponse: Standardized response format
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


@dataclass
class SkillResponse:
    """
    Standardized response from skill execution.

    This format ensures consistent communication between skills and the engine.
    """

    success: bool
    message: str  # Text to be spoken by TTS
    data: Dict[str, Any] = field(default_factory=dict)  # Structured data for UI/logging
    should_continue_listening: bool = False  # Whether to keep listening after response
    context_update: Dict[str, Any] = field(default_factory=dict)  # Updates to conversation context
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional metadata

    def __post_init__(self):
        """Validate response after initialization."""
        if not self.message:
            logger.warning("SkillResponse created with empty message")

    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary."""
        return {
            'success': self.success,
            'message': self.message,
            'data': self.data,
            'should_continue_listening': self.should_continue_listening,
            'context_update': self.context_update,
            'metadata': self.metadata,
        }


class BaseSkill(ABC):
    """
    Abstract base class for all ZERO skills.

    All skills must inherit from this class and implement the required methods:
    - can_handle(): Determines if the skill can handle a given intent
    - execute(): Performs the skill's action

    Optional methods to override:
    - validate_entities(): Validates required entities are present
    - get_help(): Returns help text for the skill
    - initialize(): Custom initialization logic
    - cleanup(): Cleanup when skill is unloaded
    """

    def __init__(
        self,
        name: str,
        description: str = "",
        version: str = "1.0.0",
        enabled: bool = True,
    ):
        """
        Initialize base skill.

        Args:
            name: Unique skill name (e.g., 'weather', 'timer')
            description: Human-readable description
            version: Skill version
            enabled: Whether skill is enabled
        """
        self.name = name
        self.description = description or f"{name.capitalize()} skill"
        self.version = version
        self.enabled = enabled
        self.logger = logging.getLogger(f"skill.{name}")

        self.logger.info(f"Skill '{name}' initialized (v{version})")

    @abstractmethod
    def can_handle(self, intent: str) -> bool:
        """
        Determine if this skill can handle the given intent.

        Args:
            intent: Intent type (e.g., 'weather.query', 'timer.set')

        Returns:
            True if skill can handle this intent
        """
        pass

    @abstractmethod
    def execute(
        self,
        intent: str,
        entities: Dict[str, Any],
        context: Dict[str, Any]
    ) -> SkillResponse:
        """
        Execute the skill's main functionality.

        Args:
            intent: The intent to handle
            entities: Extracted entities from user input
            context: Conversation context

        Returns:
            SkillResponse with result
        """
        pass

    def validate_entities(self, entities: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """
        Validate that required entities are present.

        Args:
            entities: Extracted entities dictionary

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Default implementation accepts any entities
        return True, None

    def get_help(self) -> str:
        """
        Get help text for this skill.

        Returns:
            Help text describing skill capabilities
        """
        return f"{self.description}\n\nNo detailed help available."

    def get_supported_intents(self) -> List[str]:
        """
        Get list of intents this skill supports.

        Returns:
            List of intent names
        """
        # Default implementation - skills can override
        return []

    def initialize(self) -> bool:
        """
        Initialize skill resources (API clients, models, etc.).

        Returns:
            True if initialization successful
        """
        # Default implementation does nothing
        return True

    def cleanup(self):
        """
        Cleanup skill resources when unloaded.

        This is called when the skill is disabled or the system shuts down.
        """
        # Default implementation does nothing
        pass

    def enable(self):
        """Enable the skill."""
        self.enabled = True
        self.logger.info(f"Skill '{self.name}' enabled")

    def disable(self):
        """Disable the skill."""
        self.enabled = False
        self.logger.info(f"Skill '{self.name}' disabled")

    def is_enabled(self) -> bool:
        """Check if skill is enabled."""
        return self.enabled

    def get_info(self) -> Dict[str, Any]:
        """
        Get skill information.

        Returns:
            Dictionary with skill metadata
        """
        return {
            'name': self.name,
            'description': self.description,
            'version': self.version,
            'enabled': self.enabled,
            'supported_intents': self.get_supported_intents(),
        }

    def _create_error_response(
        self,
        error_message: str,
        data: Dict[str, Any] = None
    ) -> SkillResponse:
        """
        Helper to create error responses.

        Args:
            error_message: Error message to speak
            data: Optional error data

        Returns:
            SkillResponse indicating failure
        """
        self.logger.error(f"Skill error: {error_message}")

        return SkillResponse(
            success=False,
            message=error_message,
            data=data or {},
            metadata={'error': True}
        )

    def _create_success_response(
        self,
        message: str,
        data: Dict[str, Any] = None,
        context_update: Dict[str, Any] = None,
        should_continue_listening: bool = False,
    ) -> SkillResponse:
        """
        Helper to create success responses.

        Args:
            message: Success message to speak
            data: Optional result data
            context_update: Optional context updates
            should_continue_listening: Whether to continue listening

        Returns:
            SkillResponse indicating success
        """
        self.logger.debug(f"Skill success: {message[:50]}...")

        return SkillResponse(
            success=True,
            message=message,
            data=data or {},
            context_update=context_update or {},
            should_continue_listening=should_continue_listening,
        )

    def __repr__(self) -> str:
        """String representation."""
        status = "enabled" if self.enabled else "disabled"
        return f"<{self.__class__.__name__}(name={self.name}, {status})>"


class SkillError(Exception):
    """Base exception for skill-related errors."""
    pass


class SkillNotFoundError(SkillError):
    """Raised when a requested skill is not found."""
    pass


class SkillExecutionError(SkillError):
    """Raised when skill execution fails."""
    pass


class SkillValidationError(SkillError):
    """Raised when skill entity validation fails."""
    pass
