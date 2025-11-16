"""
App Control Skill for ZERO Assistant.

This skill provides application control capabilities:
- Open/launch applications
- Close/quit applications
- List running applications
- Switch/focus applications

Supports both macOS and Windows platforms with platform-specific implementations.
"""

import os
import sys
import subprocess
import logging
from typing import Dict, Any, Optional, List
import psutil

from src.skills.base_skill import BaseSkill, SkillResponse

logger = logging.getLogger(__name__)

# Platform-specific imports
PLATFORM = sys.platform
IS_MACOS = PLATFORM == "darwin"
IS_WINDOWS = PLATFORM == "win32"

# Try to import platform-specific modules
if IS_MACOS:
    try:
        from AppKit import NSWorkspace, NSRunningApplication
        APPKIT_AVAILABLE = True
    except ImportError:
        APPKIT_AVAILABLE = False
        logger.warning("AppKit not available - macOS app control will use subprocess fallback")

if IS_WINDOWS:
    try:
        import win32gui
        import win32con
        import win32process
        WIN32_AVAILABLE = True
    except ImportError:
        WIN32_AVAILABLE = False
        logger.warning("pywin32 not available - Windows app control will use subprocess fallback")


class AppControlSkill(BaseSkill):
    """
    Application control skill for opening, closing, and managing applications.

    Handles queries like:
    - "Open Safari"
    - "Launch Google Chrome"
    - "Close Slack"
    - "What apps are running?"
    - "Switch to Terminal"
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize app control skill.

        Args:
            config: Configuration dictionary with app aliases and preferences
        """
        super().__init__(
            name="app_control",
            description="Control applications (open, close, switch, list)",
            version="1.0.0",
        )

        self.config = config or {}

        # App name aliases (common names → actual app names)
        self.app_aliases = self._get_default_aliases()
        if config and "app_aliases" in config:
            self.app_aliases.update(config["app_aliases"])

        # Platform check
        if not (IS_MACOS or IS_WINDOWS):
            logger.warning(f"Platform '{PLATFORM}' not fully supported for app control")

        logger.info(f"App control skill initialized for {PLATFORM}")

    def _get_default_aliases(self) -> Dict[str, str]:
        """Get default app name aliases for the current platform."""
        if IS_MACOS:
            return {
                # Browsers
                "chrome": "Google Chrome",
                "firefox": "Firefox",
                "safari": "Safari",
                "edge": "Microsoft Edge",
                "brave": "Brave Browser",

                # Communication
                "slack": "Slack",
                "teams": "Microsoft Teams",
                "zoom": "zoom.us",
                "discord": "Discord",

                # Productivity
                "notes": "Notes",
                "mail": "Mail",
                "calendar": "Calendar",
                "terminal": "Terminal",
                "iterm": "iTerm",
                "finder": "Finder",
                "code": "Visual Studio Code",
                "vscode": "Visual Studio Code",
                "atom": "Atom",
                "sublime": "Sublime Text",

                # Media
                "spotify": "Spotify",
                "music": "Music",
                "itunes": "Music",
                "vlc": "VLC",

                # Office
                "word": "Microsoft Word",
                "excel": "Microsoft Excel",
                "powerpoint": "Microsoft PowerPoint",
                "pages": "Pages",
                "numbers": "Numbers",
                "keynote": "Keynote",
            }
        elif IS_WINDOWS:
            return {
                # Browsers
                "chrome": "chrome.exe",
                "firefox": "firefox.exe",
                "edge": "msedge.exe",
                "brave": "brave.exe",

                # Communication
                "slack": "slack.exe",
                "teams": "Teams.exe",
                "zoom": "Zoom.exe",
                "discord": "Discord.exe",

                # Productivity
                "notepad": "notepad.exe",
                "terminal": "WindowsTerminal.exe",
                "cmd": "cmd.exe",
                "powershell": "powershell.exe",
                "code": "Code.exe",
                "vscode": "Code.exe",
                "atom": "atom.exe",
                "sublime": "sublime_text.exe",

                # Media
                "spotify": "Spotify.exe",
                "vlc": "vlc.exe",

                # Office
                "word": "WINWORD.EXE",
                "excel": "EXCEL.EXE",
                "powerpoint": "POWERPNT.EXE",
            }
        else:
            return {}

    def can_handle(self, intent: str) -> bool:
        """Check if this skill can handle the intent."""
        return intent in [
            "app.open",
            "app.close",
            "app.list",
            "app.switch",
        ]

    def get_supported_intents(self) -> List[str]:
        """Get list of supported intents."""
        return ["app.open", "app.close", "app.list", "app.switch"]

    def execute(
        self,
        intent: str,
        entities: Dict[str, Any],
        context: Dict[str, Any]
    ) -> SkillResponse:
        """
        Execute app control action.

        Args:
            intent: The intent to handle
            entities: Extracted entities (app_name, etc.)
            context: Conversation context

        Returns:
            SkillResponse with result
        """
        try:
            if intent == "app.open":
                return self._open_app(entities, context)
            elif intent == "app.close":
                return self._close_app(entities, context)
            elif intent == "app.list":
                return self._list_apps(entities, context)
            elif intent == "app.switch":
                return self._switch_app(entities, context)
            else:
                return self._create_error_response(
                    "I'm not sure how to handle that app control request, sir."
                )

        except Exception as e:
            logger.error(f"App control error: {e}", exc_info=True)
            return self._create_error_response(
                "I encountered an issue while controlling the application, sir."
            )

    def _open_app(self, entities: Dict[str, Any], context: Dict[str, Any]) -> SkillResponse:
        """Open/launch an application."""
        app_name = entities.get("app_name")

        if not app_name:
            return self._create_error_response(
                "I need to know which application to open, sir."
            )

        # Resolve app name through aliases
        resolved_name = self._resolve_app_name(app_name)

        try:
            if IS_MACOS:
                success = self._open_app_macos(resolved_name)
            elif IS_WINDOWS:
                success = self._open_app_windows(resolved_name)
            else:
                return self._create_error_response(
                    f"App control is not supported on {PLATFORM}, sir."
                )

            if success:
                return self._create_success_response(
                    f"Opening {app_name}, sir.",
                    data={"app_name": app_name, "resolved_name": resolved_name},
                    context_update={"last_app": app_name}
                )
            else:
                return self._create_error_response(
                    f"I was unable to open {app_name}, sir. The application may not be installed."
                )

        except Exception as e:
            logger.error(f"Error opening app '{app_name}': {e}")
            return self._create_error_response(
                f"I encountered an error while opening {app_name}, sir."
            )

    def _close_app(self, entities: Dict[str, Any], context: Dict[str, Any]) -> SkillResponse:
        """Close/quit an application."""
        app_name = entities.get("app_name")

        if not app_name:
            # Check if we can use context
            app_name = context.get("last_app")
            if not app_name:
                return self._create_error_response(
                    "I need to know which application to close, sir."
                )

        # Resolve app name through aliases
        resolved_name = self._resolve_app_name(app_name)

        try:
            if IS_MACOS:
                success = self._close_app_macos(resolved_name)
            elif IS_WINDOWS:
                success = self._close_app_windows(resolved_name)
            else:
                return self._create_error_response(
                    f"App control is not supported on {PLATFORM}, sir."
                )

            if success:
                return self._create_success_response(
                    f"Closing {app_name}, sir.",
                    data={"app_name": app_name, "resolved_name": resolved_name}
                )
            else:
                return self._create_error_response(
                    f"I was unable to close {app_name}, sir. The application may not be running."
                )

        except Exception as e:
            logger.error(f"Error closing app '{app_name}': {e}")
            return self._create_error_response(
                f"I encountered an error while closing {app_name}, sir."
            )

    def _list_apps(self, entities: Dict[str, Any], context: Dict[str, Any]) -> SkillResponse:
        """List running applications."""
        try:
            if IS_MACOS:
                apps = self._list_apps_macos()
            elif IS_WINDOWS:
                apps = self._list_apps_windows()
            else:
                apps = self._list_apps_generic()

            if not apps:
                return self._create_success_response(
                    "I don't detect any applications running, sir.",
                    data={"apps": []}
                )

            # Format response
            if len(apps) == 1:
                message = f"You have {apps[0]} running, sir."
            elif len(apps) <= 5:
                apps_list = ", ".join(apps[:-1]) + f", and {apps[-1]}"
                message = f"You have {apps_list} running, sir."
            else:
                apps_list = ", ".join(apps[:5])
                message = f"You have {len(apps)} applications running, including {apps_list}, and others, sir."

            return self._create_success_response(
                message,
                data={"apps": apps, "count": len(apps)}
            )

        except Exception as e:
            logger.error(f"Error listing apps: {e}")
            return self._create_error_response(
                "I encountered an error while listing applications, sir."
            )

    def _switch_app(self, entities: Dict[str, Any], context: Dict[str, Any]) -> SkillResponse:
        """Switch to/focus an application."""
        app_name = entities.get("app_name")

        if not app_name:
            return self._create_error_response(
                "I need to know which application to switch to, sir."
            )

        # Resolve app name through aliases
        resolved_name = self._resolve_app_name(app_name)

        try:
            if IS_MACOS:
                success = self._switch_app_macos(resolved_name)
            elif IS_WINDOWS:
                success = self._switch_app_windows(resolved_name)
            else:
                return self._create_error_response(
                    f"App switching is not supported on {PLATFORM}, sir."
                )

            if success:
                return self._create_success_response(
                    f"Switching to {app_name}, sir.",
                    data={"app_name": app_name, "resolved_name": resolved_name},
                    context_update={"last_app": app_name}
                )
            else:
                return self._create_error_response(
                    f"I was unable to switch to {app_name}, sir. The application may not be running."
                )

        except Exception as e:
            logger.error(f"Error switching to app '{app_name}': {e}")
            return self._create_error_response(
                f"I encountered an error while switching to {app_name}, sir."
            )

    def _resolve_app_name(self, app_name: str) -> str:
        """Resolve app name through aliases."""
        app_lower = app_name.lower().strip()

        # Check if it's an alias
        if app_lower in self.app_aliases:
            return self.app_aliases[app_lower]

        # Return original name (capitalized)
        return app_name.title()

    # ========== macOS Implementation ==========

    def _open_app_macos(self, app_name: str) -> bool:
        """Open app on macOS."""
        try:
            # Try using 'open' command (most reliable)
            result = subprocess.run(
                ["open", "-a", app_name],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.error(f"Error opening app on macOS: {e}")
            return False

    def _close_app_macos(self, app_name: str) -> bool:
        """Close app on macOS using AppleScript."""
        try:
            # Use osascript to quit the app gracefully
            script = f'tell application "{app_name}" to quit'
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.error(f"Error closing app on macOS: {e}")
            # Try force quit as fallback
            try:
                subprocess.run(
                    ["pkill", "-x", app_name],
                    capture_output=True,
                    timeout=3
                )
                return True
            except:
                return False

    def _list_apps_macos(self) -> List[str]:
        """List running apps on macOS."""
        apps = []

        if APPKIT_AVAILABLE:
            try:
                workspace = NSWorkspace.sharedWorkspace()
                running_apps = workspace.runningApplications()

                for app in running_apps:
                    name = app.localizedName()
                    # Filter out system processes
                    if name and not name.startswith("com.apple"):
                        apps.append(name)

                return sorted(set(apps))
            except Exception as e:
                logger.error(f"Error using AppKit: {e}")

        # Fallback: use ps command
        try:
            result = subprocess.run(
                ["ps", "-eo", "comm"],
                capture_output=True,
                text=True,
                timeout=3
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                for line in lines:
                    if line and '.app/' in line:
                        # Extract app name from path
                        app_name = line.split('.app/')[0].split('/')[-1]
                        if app_name:
                            apps.append(app_name)

                return sorted(set(apps))
        except Exception as e:
            logger.error(f"Error listing apps with ps: {e}")

        return []

    def _switch_app_macos(self, app_name: str) -> bool:
        """Switch to app on macOS."""
        try:
            # Use AppleScript to activate the app
            script = f'tell application "{app_name}" to activate'
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.error(f"Error switching to app on macOS: {e}")
            return False

    # ========== Windows Implementation ==========

    def _open_app_windows(self, app_name: str) -> bool:
        """Open app on Windows."""
        try:
            # Try using 'start' command
            result = subprocess.run(
                ["start", "", app_name],
                shell=True,
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.error(f"Error opening app on Windows: {e}")
            return False

    def _close_app_windows(self, app_name: str) -> bool:
        """Close app on Windows."""
        try:
            # Use taskkill command
            # First try graceful close
            result = subprocess.run(
                ["taskkill", "/IM", app_name, "/T"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return True

            # If graceful close failed, try force kill
            result = subprocess.run(
                ["taskkill", "/IM", app_name, "/F", "/T"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0

        except (subprocess.TimeoutExpired, FileNotFoundError) as e:
            logger.error(f"Error closing app on Windows: {e}")
            return False

    def _list_apps_windows(self) -> List[str]:
        """List running apps on Windows."""
        apps = []

        try:
            # Use psutil to get running processes
            for proc in psutil.process_iter(['name', 'exe']):
                try:
                    name = proc.info['name']
                    exe = proc.info['exe']

                    # Filter for GUI applications (rough heuristic)
                    if name and exe and name.endswith('.exe'):
                        # Remove .exe extension
                        app_name = name[:-4]
                        # Filter out common system processes
                        if not any(sys_proc in app_name.lower() for sys_proc in
                                  ['svchost', 'system', 'runtime', 'service', 'csrss', 'lsass', 'winlogon']):
                            apps.append(app_name)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            return sorted(set(apps))
        except Exception as e:
            logger.error(f"Error listing apps on Windows: {e}")
            return []

    def _switch_app_windows(self, app_name: str) -> bool:
        """Switch to app on Windows."""
        if not WIN32_AVAILABLE:
            logger.warning("pywin32 not available - cannot switch apps on Windows")
            return False

        try:
            # Find window by title containing app name
            def callback(hwnd, app_windows):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if title and app_name.lower() in title.lower():
                        app_windows.append(hwnd)
                return True

            windows = []
            win32gui.EnumWindows(callback, windows)

            if windows:
                # Bring first matching window to front
                hwnd = windows[0]
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                win32gui.SetForegroundWindow(hwnd)
                return True

            return False

        except Exception as e:
            logger.error(f"Error switching to app on Windows: {e}")
            return False

    # ========== Generic/Cross-platform Implementation ==========

    def _list_apps_generic(self) -> List[str]:
        """List running apps using psutil (cross-platform fallback)."""
        apps = []

        try:
            for proc in psutil.process_iter(['name']):
                try:
                    name = proc.info['name']
                    if name:
                        apps.append(name)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            return sorted(set(apps))
        except Exception as e:
            logger.error(f"Error listing apps generically: {e}")
            return []

    def validate_entities(self, entities: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate entities for app control."""
        # App name is usually required, but not for 'list' intent
        # This is handled in the execute methods
        return True, None

    def get_help(self) -> str:
        """Get help text for app control skill."""
        return """App Control Skill

I can help you control applications on your computer:
- Open applications: "Open Safari", "Launch Chrome"
- Close applications: "Close Slack", "Quit Terminal"
- List running apps: "What apps are running?"
- Switch to apps: "Switch to Firefox", "Go to Terminal"

Supported platforms: macOS, Windows"""
