"""
Skill Manager for ZERO Assistant.

This module manages the skill system:
- Skill registration and discovery
- Skill lifecycle management
- Intent routing to appropriate skills
- Skill priority and conflict resolution
"""

import importlib
import inspect
import pkgutil
from pathlib import Path
from typing import Dict, List, Optional, Type, Any
import logging

from src.skills.base_skill import (
    BaseSkill,
    SkillResponse,
    SkillError,
    SkillNotFoundError,
    SkillExecutionError,
    SkillValidationError,
)

logger = logging.getLogger(__name__)


class SkillManager:
    """
    Manages all skills in the ZERO assistant.

    Features:
    - Auto-discovery of skills in the skills directory
    - Skill registration and initialization
    - Intent-based routing to appropriate skills
    - Skill enabling/disabling
    - Hot-reloading (development mode)
    - Error handling and fallback
    """

    def __init__(
        self,
        skills_dir: Optional[Path] = None,
        config: Dict[str, Any] = None,
        auto_discover: bool = True,
    ):
        """
        Initialize skill manager.

        Args:
            skills_dir: Directory containing skill modules
            config: Configuration dictionary
            auto_discover: Whether to auto-discover skills on init
        """
        self.skills_dir = skills_dir or Path(__file__).parent
        self.config = config or {}
        self.skills: Dict[str, BaseSkill] = {}
        self._intent_cache: Dict[str, str] = {}  # intent -> skill_name mapping

        logger.info(f"Skill manager initialized (skills_dir={self.skills_dir})")

        if auto_discover:
            self.discover_skills()

    def discover_skills(self) -> int:
        """
        Auto-discover and load skills from the skills directory.

        Returns:
            Number of skills discovered
        """
        logger.info("Discovering skills...")
        discovered_count = 0

        try:
            # Import the skills package
            import src.skills

            # Find all modules in the skills directory
            for importer, modname, ispkg in pkgutil.iter_modules(src.skills.__path__):
                # Skip __init__ and base_skill
                if modname in ['__init__', 'base_skill', 'skill_manager']:
                    continue

                # Skip non-skill files
                if not modname.endswith('_skill'):
                    continue

                try:
                    # Import the module
                    module = importlib.import_module(f'src.skills.{modname}')

                    # Find skill classes in the module
                    for name, obj in inspect.getmembers(module, inspect.isclass):
                        # Check if it's a skill class (inherits from BaseSkill but not BaseSkill itself)
                        if issubclass(obj, BaseSkill) and obj is not BaseSkill:
                            # Instantiate the skill with config if it accepts it
                            try:
                                # Try to instantiate with config parameter
                                import inspect as inspect_module
                                sig = inspect_module.signature(obj.__init__)
                                if 'config' in sig.parameters:
                                    skill = obj(config=self.config)
                                else:
                                    skill = obj()
                            except Exception as e:
                                # Fallback to no-arg instantiation
                                logger.warning(f"Could not instantiate {name} with config, trying without: {e}")
                                skill = obj()
                            
                            self.register_skill(skill)
                            discovered_count += 1
                            logger.info(f"Discovered skill: {modname} ({skill.name})")

                except Exception as e:
                    logger.error(f"Failed to load skill module '{modname}': {e}")

        except Exception as e:
            logger.error(f"Failed to discover skills: {e}")

        logger.info(f"Discovery complete: {discovered_count} skills found")
        return discovered_count

    def register_skill(self, skill: BaseSkill) -> bool:
        """
        Register a skill with the manager.

        Args:
            skill: Skill instance to register

        Returns:
            True if registered successfully
        """
        if skill.name in self.skills:
            logger.warning(f"Skill '{skill.name}' already registered, replacing")

        # Check if skill is enabled in config
        skill_config = self.config.get('skills', {}).get(skill.name, {})
        if not skill_config.get('enabled', True):
            skill.disable()
            logger.info(f"Skill '{skill.name}' disabled by configuration")

        # Initialize the skill
        try:
            if skill.initialize():
                self.skills[skill.name] = skill
                self._invalidate_intent_cache()
                logger.info(f"Registered skill: {skill.name} (v{skill.version})")
                return True
            else:
                logger.error(f"Skill '{skill.name}' initialization failed")
                return False
        except Exception as e:
            logger.error(f"Failed to initialize skill '{skill.name}': {e}")
            return False

    def unregister_skill(self, skill_name: str) -> bool:
        """
        Unregister a skill.

        Args:
            skill_name: Name of skill to unregister

        Returns:
            True if unregistered successfully
        """
        if skill_name not in self.skills:
            logger.warning(f"Skill '{skill_name}' not found")
            return False

        skill = self.skills[skill_name]
        try:
            skill.cleanup()
            del self.skills[skill_name]
            self._invalidate_intent_cache()
            logger.info(f"Unregistered skill: {skill_name}")
            return True
        except Exception as e:
            logger.error(f"Error unregistering skill '{skill_name}': {e}")
            return False

    def get_skill(self, skill_name: str) -> Optional[BaseSkill]:
        """
        Get a skill by name.

        Args:
            skill_name: Name of skill

        Returns:
            Skill instance or None
        """
        return self.skills.get(skill_name)

    def list_skills(self, enabled_only: bool = False) -> List[Dict[str, Any]]:
        """
        List all registered skills.

        Args:
            enabled_only: Only return enabled skills

        Returns:
            List of skill info dictionaries
        """
        skills = self.skills.values()

        if enabled_only:
            skills = [s for s in skills if s.is_enabled()]

        return [skill.get_info() for skill in skills]

    def enable_skill(self, skill_name: str) -> bool:
        """
        Enable a skill.

        Args:
            skill_name: Name of skill to enable

        Returns:
            True if enabled successfully
        """
        skill = self.get_skill(skill_name)
        if not skill:
            raise SkillNotFoundError(f"Skill '{skill_name}' not found")

        skill.enable()
        self._invalidate_intent_cache()
        return True

    def disable_skill(self, skill_name: str) -> bool:
        """
        Disable a skill.

        Args:
            skill_name: Name of skill to disable

        Returns:
            True if disabled successfully
        """
        skill = self.get_skill(skill_name)
        if not skill:
            raise SkillNotFoundError(f"Skill '{skill_name}' not found")

        skill.disable()
        self._invalidate_intent_cache()
        return True

    def route_intent(
        self,
        intent: str,
        entities: Dict[str, Any],
        context: Dict[str, Any]
    ) -> SkillResponse:
        """
        Route an intent to the appropriate skill and execute it.

        Args:
            intent: Intent to route
            entities: Extracted entities
            context: Conversation context

        Returns:
            SkillResponse from the executed skill
        """
        logger.debug(f"Routing intent: {intent}")

        # Try to find skill from cache first
        skill_name = self._intent_cache.get(intent)
        if skill_name:
            skill = self.get_skill(skill_name)
            if skill and skill.is_enabled() and skill.can_handle(intent):
                return self._execute_skill(skill, intent, entities, context)
            else:
                # Cache is stale, invalidate
                self._invalidate_intent_cache()

        # Find skill that can handle this intent
        skill = self._find_skill_for_intent(intent)

        if not skill:
            logger.warning(f"No skill found for intent: {intent}")
            return SkillResponse(
                success=False,
                message="I'm not sure how to handle that request.",
                data={'intent': intent, 'error': 'no_skill_found'},
            )

        # Cache the mapping
        self._intent_cache[intent] = skill.name

        # Execute the skill
        return self._execute_skill(skill, intent, entities, context)

    def _find_skill_for_intent(self, intent: str) -> Optional[BaseSkill]:
        """
        Find the best skill to handle an intent.

        Args:
            intent: Intent to match

        Returns:
            Skill instance or None
        """
        # Check all enabled skills
        for skill in self.skills.values():
            if skill.is_enabled() and skill.can_handle(intent):
                logger.debug(f"Found skill '{skill.name}' for intent '{intent}'")
                return skill

        return None

    def _execute_skill(
        self,
        skill: BaseSkill,
        intent: str,
        entities: Dict[str, Any],
        context: Dict[str, Any]
    ) -> SkillResponse:
        """
        Execute a skill with error handling.

        Args:
            skill: Skill to execute
            intent: Intent to handle
            entities: Extracted entities
            context: Conversation context

        Returns:
            SkillResponse
        """
        logger.info(f"Executing skill: {skill.name} for intent: {intent}")

        try:
            # Validate entities
            is_valid, error_msg = skill.validate_entities(entities)
            if not is_valid:
                logger.warning(f"Entity validation failed for {skill.name}: {error_msg}")
                return SkillResponse(
                    success=False,
                    message=error_msg or "I don't have all the information I need for that.",
                    data={'validation_error': True},
                )

            # Execute the skill
            response = skill.execute(intent, entities, context)

            # Validate response
            if not isinstance(response, SkillResponse):
                logger.error(f"Skill '{skill.name}' returned invalid response type")
                return SkillResponse(
                    success=False,
                    message="An internal error occurred.",
                    data={'error': 'invalid_response_type'},
                )

            logger.debug(f"Skill '{skill.name}' execution complete: {response.success}")
            return response

        except SkillValidationError as e:
            logger.warning(f"Validation error in skill '{skill.name}': {e}")
            return SkillResponse(
                success=False,
                message=str(e),
                data={'validation_error': True},
            )

        except SkillExecutionError as e:
            logger.error(f"Execution error in skill '{skill.name}': {e}")
            return SkillResponse(
                success=False,
                message="I encountered an error while processing that request.",
                data={'execution_error': True, 'error_message': str(e)},
            )

        except Exception as e:
            logger.exception(f"Unexpected error in skill '{skill.name}': {e}")
            return SkillResponse(
                success=False,
                message="An unexpected error occurred.",
                data={'unexpected_error': True, 'error_message': str(e)},
            )

    def _invalidate_intent_cache(self):
        """Invalidate the intent cache."""
        self._intent_cache.clear()
        logger.debug("Intent cache invalidated")

    def reload_skill(self, skill_name: str) -> bool:
        """
        Reload a skill (development mode).

        Args:
            skill_name: Name of skill to reload

        Returns:
            True if reloaded successfully
        """
        skill = self.get_skill(skill_name)
        if not skill:
            raise SkillNotFoundError(f"Skill '{skill_name}' not found")

        # Get the module name
        module_name = skill.__class__.__module__

        try:
            # Cleanup old skill
            skill.cleanup()

            # Reload the module
            module = importlib.import_module(module_name)
            importlib.reload(module)

            # Find and instantiate new skill class
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if issubclass(obj, BaseSkill) and obj is not BaseSkill:
                    new_skill = obj()
                    self.register_skill(new_skill)
                    logger.info(f"Reloaded skill: {skill_name}")
                    return True

            logger.error(f"No skill class found in reloaded module: {module_name}")
            return False

        except Exception as e:
            logger.exception(f"Failed to reload skill '{skill_name}': {e}")
            return False

    def get_help(self, skill_name: Optional[str] = None) -> str:
        """
        Get help text for skills.

        Args:
            skill_name: Optional specific skill name

        Returns:
            Help text
        """
        if skill_name:
            skill = self.get_skill(skill_name)
            if skill:
                return skill.get_help()
            else:
                return f"Skill '{skill_name}' not found."

        # Generate help for all enabled skills
        lines = ["Available skills:"]
        for skill in sorted(self.skills.values(), key=lambda s: s.name):
            if skill.is_enabled():
                status = "✓"
                intents = ", ".join(skill.get_supported_intents()[:3])
                if len(skill.get_supported_intents()) > 3:
                    intents += ", ..."
                lines.append(f"  {status} {skill.name}: {skill.description}")
                if intents:
                    lines.append(f"      Supports: {intents}")

        return "\n".join(lines)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get skill manager statistics.

        Returns:
            Statistics dictionary
        """
        total_skills = len(self.skills)
        enabled_skills = sum(1 for s in self.skills.values() if s.is_enabled())

        return {
            'total_skills': total_skills,
            'enabled_skills': enabled_skills,
            'disabled_skills': total_skills - enabled_skills,
            'intent_cache_size': len(self._intent_cache),
            'skills': {name: skill.get_info() for name, skill in self.skills.items()},
        }

    def shutdown(self):
        """
        Shutdown all skills and cleanup resources.
        """
        logger.info("Shutting down skill manager...")

        for skill_name, skill in list(self.skills.items()):
            try:
                skill.cleanup()
                logger.debug(f"Cleaned up skill: {skill_name}")
            except Exception as e:
                logger.error(f"Error cleaning up skill '{skill_name}': {e}")

        self.skills.clear()
        self._intent_cache.clear()
        logger.info("Skill manager shutdown complete")

    def __repr__(self) -> str:
        """String representation."""
        enabled = sum(1 for s in self.skills.values() if s.is_enabled())
        return f"<SkillManager(skills={len(self.skills)}, enabled={enabled})>"


# Convenience function
def create_skill_manager(config: Dict[str, Any] = None) -> SkillManager:
    """
    Create a skill manager with configuration.

    Args:
        config: Configuration dictionary

    Returns:
        Configured SkillManager instance
    """
    return SkillManager(
        config=config,
        auto_discover=True,
    )
