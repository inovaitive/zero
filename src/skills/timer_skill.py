"""
Timer Skill for ZERO Assistant.

This skill provides timer/alarm functionality with background execution:
- Set timers with duration (seconds, minutes, hours)
- Multiple concurrent timers
- Named timers ("pizza timer", "meeting timer")
- Cancel, pause, resume timers
- List active timers
- Persistence (survive restarts)
- Audio and visual alerts
"""

import threading
import time
import json
import os
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List
from pathlib import Path
import logging

from src.skills.base_skill import BaseSkill, SkillResponse

logger = logging.getLogger(__name__)

# Try to import audio libraries
try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    logger.warning("pygame not available - timer alerts will be silent")

try:
    from plyer import notification
    PLYER_AVAILABLE = True
except (ImportError, ModuleNotFoundError) as e:
    # On macOS, plyer might fail if pyobjus is not installed
    # This is non-critical - we can continue without notifications
    PLYER_AVAILABLE = False
    logger.warning(f"plyer not available - no system notifications: {e}")


@dataclass
class Timer:
    """Represents a single timer."""

    name: str  # Timer name or auto-generated ID
    duration: int  # Total duration in seconds
    remaining: int  # Remaining seconds
    start_time: datetime  # When timer was started
    paused: bool = False
    completed: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            'name': self.name,
            'duration': self.duration,
            'remaining': self.remaining,
            'start_time': self.start_time.isoformat(),
            'paused': self.paused,
            'completed': self.completed,
            'metadata': self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Timer':
        """Create Timer from dictionary."""
        data['start_time'] = datetime.fromisoformat(data['start_time'])
        return cls(**data)

    def get_elapsed_time(self) -> int:
        """Get elapsed time in seconds."""
        if self.completed:
            return self.duration
        if self.paused:
            return self.duration - self.remaining
        elapsed = int((datetime.now() - self.start_time).total_seconds())
        return min(elapsed, self.duration)

    def get_remaining_time(self) -> int:
        """Get remaining time in seconds."""
        if self.completed:
            return 0
        elapsed = self.get_elapsed_time()
        return max(0, self.duration - elapsed)

    def format_time(self, seconds: int) -> str:
        """Format seconds into human-readable string."""
        if seconds <= 0:
            return "0 seconds"

        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        parts = []
        if hours > 0:
            parts.append(f"{hours} hour{'s' if hours != 1 else ''}")
        if minutes > 0:
            parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
        if secs > 0 or not parts:
            parts.append(f"{secs} second{'s' if secs != 1 else ''}")

        return " and ".join(parts)


class TimerSkill(BaseSkill):
    """
    Timer skill with background execution and persistence.

    Features:
    - Multiple concurrent timers
    - Named timers
    - Background execution (non-blocking)
    - Pause/resume functionality
    - Persistence across restarts
    - Audio and visual alerts
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize timer skill.

        Args:
            config: Configuration dictionary
        """
        super().__init__(
            name="timer",
            description="Manage timers and alarms with background execution",
            version="1.0.0",
        )

        self.config = config or {}
        self.timers: Dict[str, Timer] = {}  # name -> Timer
        self.timer_threads: Dict[str, threading.Thread] = {}  # name -> Thread
        self.lock = threading.Lock()  # Thread safety
        self.timer_counter = 0  # For auto-generated timer names

        # Persistence settings
        self.persistence_enabled = self.config.get('persistence', {}).get('enabled', True)
        self.persistence_path = self.config.get('persistence', {}).get(
            'path', 'data/timers.json'
        )

        # Alert settings
        self.alert_sound_enabled = self.config.get('alerts', {}).get('sound', True)
        self.alert_notification_enabled = self.config.get('alerts', {}).get('notification', True)
        self.alert_tts_enabled = self.config.get('alerts', {}).get('tts', True)

        # Callbacks
        self.on_timer_complete = None  # Callback for TTS alerts

        # Initialize pygame for audio (if available)
        if PYGAME_AVAILABLE and self.alert_sound_enabled:
            try:
                pygame.mixer.init()
                logger.info("Pygame mixer initialized for timer alerts")
            except Exception as e:
                logger.warning(f"Failed to initialize pygame mixer: {e}")

        logger.info("Timer skill initialized")

    def initialize(self) -> bool:
        """Initialize skill resources and restore saved timers."""
        try:
            # Restore timers from persistence
            if self.persistence_enabled:
                self._restore_timers()

            return True
        except Exception as e:
            logger.error(f"Timer skill initialization failed: {e}")
            return False

    def cleanup(self):
        """Cleanup resources and save timers."""
        # Save timers before shutdown
        if self.persistence_enabled:
            self._save_timers()

        # Stop all running timers
        with self.lock:
            for name in list(self.timers.keys()):
                self._stop_timer_thread(name)

        logger.info("Timer skill cleanup complete")

    def can_handle(self, intent: str) -> bool:
        """Check if this skill can handle the intent."""
        timer_intents = [
            'timer.set',
            'timer.cancel',
            'timer.list',
            'timer.status',
            'timer.pause',
            'timer.resume',
        ]
        return intent in timer_intents

    def get_supported_intents(self) -> List[str]:
        """Get list of supported intents."""
        return [
            'timer.set',
            'timer.cancel',
            'timer.list',
            'timer.status',
            'timer.pause',
            'timer.resume',
        ]

    def execute(
        self,
        intent: str,
        entities: Dict[str, Any],
        context: Dict[str, Any]
    ) -> SkillResponse:
        """
        Execute timer skill action.

        Args:
            intent: Intent type (timer.set, timer.cancel, etc.)
            entities: Extracted entities (duration, timer name, etc.)
            context: Conversation context

        Returns:
            SkillResponse with result
        """
        try:
            if intent == 'timer.set':
                return self._set_timer(entities, context)
            elif intent == 'timer.cancel':
                return self._cancel_timer(entities, context)
            elif intent == 'timer.list':
                return self._list_timers(entities, context)
            elif intent == 'timer.status':
                return self._get_timer_status(entities, context)
            elif intent == 'timer.pause':
                return self._pause_timer(entities, context)
            elif intent == 'timer.resume':
                return self._resume_timer(entities, context)
            else:
                return self._create_error_response(
                    "I'm not sure how to handle that timer command, sir."
                )

        except Exception as e:
            logger.error(f"Timer skill execution error: {e}", exc_info=True)
            return self._create_error_response(
                "I encountered an error managing the timer, sir. Please try again."
            )

    def _set_timer(self, entities: Dict[str, Any], context: Dict[str, Any]) -> SkillResponse:
        """Set a new timer."""
        # Extract duration
        duration = entities.get('duration')
        if not duration:
            return self._create_error_response(
                "I need to know the timer duration, sir. For example, 'set a timer for 5 minutes'."
            )

        # Extract timer name (optional)
        timer_name = entities.get('timer_name')
        if not timer_name:
            # Auto-generate timer name
            with self.lock:
                self.timer_counter += 1
                timer_name = f"timer_{self.timer_counter}"

        # Check if timer already exists
        with self.lock:
            if timer_name in self.timers:
                return self._create_error_response(
                    f"A timer named '{timer_name}' already exists, sir. "
                    "Please cancel it first or use a different name."
                )

        # Create timer
        timer = Timer(
            name=timer_name,
            duration=duration,
            remaining=duration,
            start_time=datetime.now(),
        )

        # Start timer thread
        with self.lock:
            self.timers[timer_name] = timer
            thread = threading.Thread(
                target=self._timer_thread,
                args=(timer_name,),
                daemon=True,
            )
            self.timer_threads[timer_name] = thread
            thread.start()

        # Save timers
        if self.persistence_enabled:
            self._save_timers()

        # Format response
        duration_str = timer.format_time(duration)
        message = f"Timer set for {duration_str}, sir."
        if timer_name.startswith('timer_'):
            message = f"Timer set for {duration_str}, sir."
        else:
            message = f"{timer_name.capitalize()} timer set for {duration_str}, sir."

        return self._create_success_response(
            message=message,
            data={'timer_name': timer_name, 'duration': duration},
            context_update={'last_timer': timer_name},
        )

    def _cancel_timer(self, entities: Dict[str, Any], context: Dict[str, Any]) -> SkillResponse:
        """Cancel a timer."""
        timer_name = entities.get('timer_name')

        # If no name specified, try to cancel last timer from context
        if not timer_name:
            timer_name = context.get('last_timer')

        # If still no name, try to cancel the only timer if there's just one
        if not timer_name:
            with self.lock:
                active_timers = [t for t in self.timers.values() if not t.completed]
                if len(active_timers) == 1:
                    timer_name = active_timers[0].name
                elif len(active_timers) > 1:
                    return self._create_error_response(
                        "You have multiple timers running, sir. "
                        "Please specify which timer to cancel."
                    )
                else:
                    return self._create_error_response(
                        "There are no active timers to cancel, sir."
                    )

        # Check if timer exists
        with self.lock:
            if timer_name not in self.timers:
                return self._create_error_response(
                    f"I couldn't find a timer named '{timer_name}', sir."
                )

            # Stop the timer
            self._stop_timer_thread(timer_name)
            del self.timers[timer_name]

        # Save timers
        if self.persistence_enabled:
            self._save_timers()

        message = f"Timer cancelled, sir."
        if not timer_name.startswith('timer_'):
            message = f"{timer_name.capitalize()} timer cancelled, sir."

        return self._create_success_response(
            message=message,
            data={'timer_name': timer_name},
        )

    def _list_timers(self, entities: Dict[str, Any], context: Dict[str, Any]) -> SkillResponse:
        """List all active timers."""
        with self.lock:
            active_timers = [t for t in self.timers.values() if not t.completed]

        if not active_timers:
            return self._create_success_response(
                message="You have no active timers, sir.",
                data={'timer_count': 0, 'timers': []},
            )

        # Format timer list
        timer_info = []
        for timer in active_timers:
            remaining = timer.get_remaining_time()
            timer_info.append({
                'name': timer.name,
                'remaining': remaining,
                'duration': timer.duration,
                'paused': timer.paused,
            })

        if len(active_timers) == 1:
            timer = active_timers[0]
            remaining = timer.get_remaining_time()
            remaining_str = timer.format_time(remaining)
            name_str = timer.name if not timer.name.startswith('timer_') else "timer"
            message = f"You have one {name_str} with {remaining_str} remaining, sir."
        else:
            timer_count = len(active_timers)
            message = f"You have {timer_count} active timers, sir. "
            timer_descriptions = []
            for timer in active_timers[:3]:  # List up to 3 timers
                remaining = timer.get_remaining_time()
                remaining_str = timer.format_time(remaining)
                name_str = timer.name if not timer.name.startswith('timer_') else "a timer"
                timer_descriptions.append(f"{name_str} with {remaining_str}")

            message += ", ".join(timer_descriptions)
            if len(active_timers) > 3:
                message += f", and {len(active_timers) - 3} more"
            message += "."

        return self._create_success_response(
            message=message,
            data={'timer_count': len(active_timers), 'timers': timer_info},
        )

    def _get_timer_status(self, entities: Dict[str, Any], context: Dict[str, Any]) -> SkillResponse:
        """Get status of a specific timer."""
        timer_name = entities.get('timer_name')

        # If no name, get last timer from context
        if not timer_name:
            timer_name = context.get('last_timer')

        # If still no name, try single timer
        if not timer_name:
            with self.lock:
                active_timers = [t for t in self.timers.values() if not t.completed]
                if len(active_timers) == 1:
                    timer_name = active_timers[0].name
                elif len(active_timers) > 1:
                    return self._create_error_response(
                        "You have multiple timers, sir. Please specify which one."
                    )
                else:
                    return self._create_error_response(
                        "There are no active timers, sir."
                    )

        # Get timer
        with self.lock:
            timer = self.timers.get(timer_name)
            if not timer or timer.completed:
                return self._create_error_response(
                    f"Timer '{timer_name}' is not active, sir."
                )

        remaining = timer.get_remaining_time()
        remaining_str = timer.format_time(remaining)
        name_str = timer.name if not timer.name.startswith('timer_') else "The timer"

        if timer.paused:
            message = f"{name_str} is paused with {remaining_str} remaining, sir."
        else:
            message = f"{name_str} has {remaining_str} remaining, sir."

        return self._create_success_response(
            message=message,
            data={
                'timer_name': timer_name,
                'remaining': remaining,
                'duration': timer.duration,
                'paused': timer.paused,
            },
        )

    def _pause_timer(self, entities: Dict[str, Any], context: Dict[str, Any]) -> SkillResponse:
        """Pause a timer."""
        timer_name = entities.get('timer_name') or context.get('last_timer')

        with self.lock:
            if timer_name not in self.timers:
                return self._create_error_response("No timer found to pause, sir.")

            timer = self.timers[timer_name]
            if timer.paused:
                return self._create_success_response(
                    message="That timer is already paused, sir.",
                    data={'timer_name': timer_name},
                )

            timer.paused = True
            timer.remaining = timer.get_remaining_time()

        if self.persistence_enabled:
            self._save_timers()

        return self._create_success_response(
            message="Timer paused, sir.",
            data={'timer_name': timer_name},
        )

    def _resume_timer(self, entities: Dict[str, Any], context: Dict[str, Any]) -> SkillResponse:
        """Resume a paused timer."""
        timer_name = entities.get('timer_name') or context.get('last_timer')

        with self.lock:
            if timer_name not in self.timers:
                return self._create_error_response("No timer found to resume, sir.")

            timer = self.timers[timer_name]
            if not timer.paused:
                return self._create_success_response(
                    message="That timer is already running, sir.",
                    data={'timer_name': timer_name},
                )

            timer.paused = False
            timer.start_time = datetime.now()

        if self.persistence_enabled:
            self._save_timers()

        return self._create_success_response(
            message="Timer resumed, sir.",
            data={'timer_name': timer_name},
        )

    def _timer_thread(self, timer_name: str):
        """Background thread that runs the timer."""
        logger.info(f"Timer thread started: {timer_name}")

        while True:
            time.sleep(1)  # Check every second

            with self.lock:
                timer = self.timers.get(timer_name)
                if not timer:
                    # Timer was cancelled
                    logger.info(f"Timer {timer_name} was cancelled")
                    break

                if timer.paused:
                    # Timer is paused, keep looping
                    continue

                remaining = timer.get_remaining_time()

                if remaining <= 0:
                    # Timer completed!
                    timer.completed = True
                    logger.info(f"Timer {timer_name} completed!")

                    # Trigger alerts
                    self._trigger_alert(timer)

                    # Clean up thread reference
                    if timer_name in self.timer_threads:
                        del self.timer_threads[timer_name]

                    # Save state
                    if self.persistence_enabled:
                        self._save_timers()

                    break

        logger.info(f"Timer thread ended: {timer_name}")

    def _trigger_alert(self, timer: Timer):
        """Trigger alerts when timer completes."""
        name_str = timer.name if not timer.name.startswith('timer_') else "Timer"
        message = f"{name_str} complete, sir."

        # System notification
        if PLYER_AVAILABLE and self.alert_notification_enabled:
            try:
                notification.notify(
                    title="ZERO - Timer Alert",
                    message=f"{name_str} has completed!",
                    app_name="ZERO",
                    timeout=10,
                )
            except Exception as e:
                logger.warning(f"Failed to show notification: {e}")

        # Audio alert (beep sound)
        if PYGAME_AVAILABLE and self.alert_sound_enabled:
            try:
                # Generate a simple beep using pygame
                # Since we don't have a sound file, we'll skip for now
                # TODO: Add a default beep sound or generate one
                pass
            except Exception as e:
                logger.warning(f"Failed to play alert sound: {e}")

        # TTS callback
        if self.alert_tts_enabled and self.on_timer_complete:
            try:
                self.on_timer_complete(message)
            except Exception as e:
                logger.error(f"TTS callback failed: {e}")

        logger.info(f"Alert triggered for timer: {timer.name}")

    def _stop_timer_thread(self, timer_name: str):
        """Stop a timer thread."""
        if timer_name in self.timer_threads:
            thread = self.timer_threads[timer_name]
            # Thread will stop when timer is removed from dict
            del self.timer_threads[timer_name]
            logger.info(f"Timer thread stopped: {timer_name}")

    def _save_timers(self):
        """Save timers to JSON file."""
        try:
            # Ensure directory exists
            persistence_path = Path(self.persistence_path)
            persistence_path.parent.mkdir(parents=True, exist_ok=True)

            # Convert timers to dict
            timer_data = {
                name: timer.to_dict()
                for name, timer in self.timers.items()
            }

            # Save to file
            with open(persistence_path, 'w') as f:
                json.dump(timer_data, f, indent=2)

            logger.debug(f"Saved {len(timer_data)} timers to {persistence_path}")

        except Exception as e:
            logger.error(f"Failed to save timers: {e}")

    def _restore_timers(self):
        """Restore timers from JSON file."""
        try:
            persistence_path = Path(self.persistence_path)
            if not persistence_path.exists():
                logger.info("No saved timers found")
                return

            # Load from file
            with open(persistence_path, 'r') as f:
                timer_data = json.load(f)

            # Restore timers
            for name, data in timer_data.items():
                try:
                    timer = Timer.from_dict(data)

                    # Skip completed timers
                    if timer.completed:
                        continue

                    # Check if timer should have already completed
                    if timer.get_remaining_time() <= 0:
                        timer.completed = True
                        continue

                    # Restore timer
                    with self.lock:
                        self.timers[name] = timer

                        # Restart thread if not paused
                        if not timer.paused:
                            thread = threading.Thread(
                                target=self._timer_thread,
                                args=(name,),
                                daemon=True,
                            )
                            self.timer_threads[name] = thread
                            thread.start()

                    logger.info(f"Restored timer: {name}")

                except Exception as e:
                    logger.error(f"Failed to restore timer {name}: {e}")

            logger.info(f"Restored {len(self.timers)} timers")

        except Exception as e:
            logger.error(f"Failed to restore timers: {e}")

    def set_alert_callback(self, callback):
        """Set callback for TTS alerts."""
        self.on_timer_complete = callback

    def get_help(self) -> str:
        """Get help text for timer skill."""
        return """Timer Skill - Manage timers and alarms

Commands:
- "Set a timer for 5 minutes"
- "Set a pizza timer for 20 minutes"
- "How much time is left?"
- "List timers"
- "Cancel the timer"
- "Cancel all timers"
- "Pause the timer"
- "Resume the timer"

Features:
- Multiple concurrent timers
- Named timers
- Background execution
- Pause/resume support
- Persistence across restarts
- Audio and visual alerts
"""
