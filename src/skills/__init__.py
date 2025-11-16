"""
Skills Package for ZERO Assistant.

This package contains the extensible skill system that allows ZERO to perform
various tasks through modular, pluggable skills.
"""

from src.skills.base_skill import (
    BaseSkill,
    SkillResponse,
    SkillError,
    SkillNotFoundError,
    SkillExecutionError,
    SkillValidationError,
)

from src.skills.skill_manager import (
    SkillManager,
    create_skill_manager,
)

__all__ = [
    # Base classes
    'BaseSkill',
    'SkillResponse',

    # Exceptions
    'SkillError',
    'SkillNotFoundError',
    'SkillExecutionError',
    'SkillValidationError',

    # Manager
    'SkillManager',
    'create_skill_manager',
]
