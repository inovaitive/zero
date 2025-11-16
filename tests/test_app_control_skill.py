"""
Tests for App Control Skill.

Tests:
- App control skill initialization
- Opening applications
- Closing applications
- Listing running applications
- Switching to applications
- App name resolution and aliases
- Platform-specific implementations
- Error handling
- J.A.R.V.I.S. personality responses
"""

import pytest
import sys
from unittest.mock import Mock, patch, MagicMock, call
from typing import Dict, Any, List

from src.skills.app_control_skill import AppControlSkill
from src.skills.base_skill import SkillResponse


@pytest.fixture
def app_control_skill():
    """Create an app control skill instance."""
    config = {
        "app_aliases": {
            "browser": "Chrome",
            "editor": "VSCode",
        }
    }
    return AppControlSkill(config=config)


@pytest.fixture
def mock_subprocess():
    """Mock subprocess.run."""
    with patch('subprocess.run') as mock:
        yield mock


@pytest.fixture
def mock_psutil():
    """Mock psutil."""
    with patch('psutil.process_iter') as mock:
        yield mock


class TestAppControlSkillInitialization:
    """Test app control skill initialization."""

    def test_skill_initialization(self):
        """Test successful initialization."""
        skill = AppControlSkill()

        assert skill.name == "app_control"
        assert skill.description == "Control applications (open, close, switch, list)"
        assert skill.version == "1.0.0"
        assert skill.enabled is True

    def test_skill_initialization_with_config(self):
        """Test initialization with custom config."""
        config = {
            "app_aliases": {
                "custom_app": "Custom Application"
            }
        }
        skill = AppControlSkill(config=config)

        assert "custom_app" in skill.app_aliases
        assert skill.app_aliases["custom_app"] == "Custom Application"

    def test_default_aliases_exist(self):
        """Test that default aliases are loaded."""
        skill = AppControlSkill()

        # Should have some default aliases
        assert len(skill.app_aliases) > 0

        # Test platform-specific aliases
        if sys.platform == "darwin":
            assert "chrome" in skill.app_aliases
            assert "safari" in skill.app_aliases
        elif sys.platform == "win32":
            assert "chrome" in skill.app_aliases
            assert "notepad" in skill.app_aliases


class TestCanHandle:
    """Test intent handling."""

    def test_can_handle_app_open(self, app_control_skill):
        """Test handling app.open intent."""
        assert app_control_skill.can_handle("app.open") is True

    def test_can_handle_app_close(self, app_control_skill):
        """Test handling app.close intent."""
        assert app_control_skill.can_handle("app.close") is True

    def test_can_handle_app_list(self, app_control_skill):
        """Test handling app.list intent."""
        assert app_control_skill.can_handle("app.list") is True

    def test_can_handle_app_switch(self, app_control_skill):
        """Test handling app.switch intent."""
        assert app_control_skill.can_handle("app.switch") is True

    def test_cannot_handle_other_intents(self, app_control_skill):
        """Test that other intents are not handled."""
        assert app_control_skill.can_handle("weather.query") is False
        assert app_control_skill.can_handle("timer.set") is False
        assert app_control_skill.can_handle("unknown") is False

    def test_get_supported_intents(self, app_control_skill):
        """Test getting supported intents."""
        intents = app_control_skill.get_supported_intents()

        assert "app.open" in intents
        assert "app.close" in intents
        assert "app.list" in intents
        assert "app.switch" in intents
        assert len(intents) == 4


class TestAppNameResolution:
    """Test app name resolution and aliases."""

    def test_resolve_known_alias(self, app_control_skill):
        """Test resolving a known alias."""
        if sys.platform == "darwin":
            resolved = app_control_skill._resolve_app_name("chrome")
            assert resolved == "Google Chrome"
        elif sys.platform == "win32":
            resolved = app_control_skill._resolve_app_name("chrome")
            assert resolved == "chrome.exe"

    def test_resolve_custom_alias(self):
        """Test resolving a custom alias from config."""
        config = {
            "app_aliases": {
                "myapp": "My Application"
            }
        }
        skill = AppControlSkill(config=config)

        resolved = skill._resolve_app_name("myapp")
        assert resolved == "My Application"

    def test_resolve_unknown_app_name(self, app_control_skill):
        """Test resolving an unknown app name."""
        resolved = app_control_skill._resolve_app_name("unknownapp")
        # Should return title-cased version
        assert resolved == "Unknownapp"

    def test_resolve_capitalized_app_name(self, app_control_skill):
        """Test resolving a capitalized app name."""
        resolved = app_control_skill._resolve_app_name("Slack")
        # Should return as-is (title case)
        assert "Slack" in resolved or "slack" in resolved.lower()


class TestOpenApp:
    """Test opening applications."""

    @pytest.mark.skipif(sys.platform not in ["darwin", "win32"],
                       reason="Platform-specific test")
    def test_open_app_success(self, app_control_skill, mock_subprocess):
        """Test successfully opening an app."""
        mock_subprocess.return_value = Mock(returncode=0)

        entities = {"app_name": "Chrome"}
        context = {}

        response = app_control_skill._open_app(entities, context)

        assert response.success is True
        assert "Opening Chrome" in response.message
        assert "sir" in response.message
        assert response.data["app_name"] == "Chrome"
        assert response.context_update["last_app"] == "Chrome"

    @pytest.mark.skipif(sys.platform not in ["darwin", "win32"],
                       reason="Platform-specific test")
    def test_open_app_failure(self, app_control_skill, mock_subprocess):
        """Test failure when opening an app."""
        mock_subprocess.return_value = Mock(returncode=1)

        entities = {"app_name": "NonExistentApp"}
        context = {}

        response = app_control_skill._open_app(entities, context)

        assert response.success is False
        assert "unable to open" in response.message.lower()
        assert "NonExistentApp" in response.message

    def test_open_app_missing_name(self, app_control_skill):
        """Test opening app without app name."""
        entities = {}
        context = {}

        response = app_control_skill._open_app(entities, context)

        assert response.success is False
        assert "need to know which application" in response.message.lower()

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS-specific test")
    def test_open_app_macos(self, app_control_skill, mock_subprocess):
        """Test opening app on macOS."""
        mock_subprocess.return_value = Mock(returncode=0)

        result = app_control_skill._open_app_macos("Safari")

        assert result is True
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        assert "open" in call_args
        assert "-a" in call_args
        assert "Safari" in call_args

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
    def test_open_app_windows(self, app_control_skill, mock_subprocess):
        """Test opening app on Windows."""
        mock_subprocess.return_value = Mock(returncode=0)

        result = app_control_skill._open_app_windows("notepad.exe")

        assert result is True
        mock_subprocess.assert_called_once()


class TestCloseApp:
    """Test closing applications."""

    @pytest.mark.skipif(sys.platform not in ["darwin", "win32"],
                       reason="Platform-specific test")
    def test_close_app_success(self, app_control_skill, mock_subprocess):
        """Test successfully closing an app."""
        mock_subprocess.return_value = Mock(returncode=0)

        entities = {"app_name": "Chrome"}
        context = {}

        response = app_control_skill._close_app(entities, context)

        assert response.success is True
        assert "Closing Chrome" in response.message
        assert "sir" in response.message

    @pytest.mark.skipif(sys.platform not in ["darwin", "win32"],
                       reason="Platform-specific test")
    def test_close_app_failure(self, app_control_skill, mock_subprocess):
        """Test failure when closing an app."""
        mock_subprocess.return_value = Mock(returncode=1)

        entities = {"app_name": "NonRunningApp"}
        context = {}

        response = app_control_skill._close_app(entities, context)

        assert response.success is False
        assert "unable to close" in response.message.lower()

    def test_close_app_from_context(self, app_control_skill, mock_subprocess):
        """Test closing app using context when app name not provided."""
        mock_subprocess.return_value = Mock(returncode=0)

        entities = {}
        context = {"last_app": "Slack"}

        response = app_control_skill._close_app(entities, context)

        if sys.platform in ["darwin", "win32"]:
            assert response.success is True
            assert "Slack" in response.message

    def test_close_app_missing_name_no_context(self, app_control_skill):
        """Test closing app without app name or context."""
        entities = {}
        context = {}

        response = app_control_skill._close_app(entities, context)

        assert response.success is False
        assert "need to know which application" in response.message.lower()

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS-specific test")
    def test_close_app_macos(self, app_control_skill, mock_subprocess):
        """Test closing app on macOS."""
        mock_subprocess.return_value = Mock(returncode=0)

        result = app_control_skill._close_app_macos("Safari")

        assert result is True
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]
        assert "osascript" in call_args


class TestListApps:
    """Test listing running applications."""

    def test_list_apps_with_results(self, app_control_skill, mock_psutil):
        """Test listing apps when apps are running."""
        # Mock process list
        mock_processes = []
        for name in ["Chrome", "Safari", "Terminal", "Slack", "VSCode"]:
            mock_proc = Mock()
            if sys.platform == "darwin":
                mock_proc.info = {"name": name}
            else:
                mock_proc.info = {"name": f"{name}.exe", "exe": f"C:\\Program Files\\{name}.exe"}
            mock_processes.append(mock_proc)

        mock_psutil.return_value = mock_processes

        entities = {}
        context = {}

        response = app_control_skill._list_apps(entities, context)

        assert response.success is True
        assert "running" in response.message.lower()
        assert "sir" in response.message
        assert len(response.data["apps"]) > 0
        assert response.data["count"] > 0

    def test_list_apps_empty(self, app_control_skill, mock_psutil):
        """Test listing apps when no apps are running."""
        mock_psutil.return_value = []

        entities = {}
        context = {}

        response = app_control_skill._list_apps(entities, context)

        assert response.success is True
        assert "don't detect any applications" in response.message.lower()
        assert len(response.data["apps"]) == 0

    def test_list_apps_message_format_one_app(self, app_control_skill, mock_psutil):
        """Test message format with one app."""
        mock_proc = Mock()
        mock_proc.info = {"name": "Chrome"}
        mock_psutil.return_value = [mock_proc]

        entities = {}
        context = {}

        response = app_control_skill._list_apps(entities, context)

        assert response.success is True
        # Should mention the single app
        assert "Chrome" in response.message or "chrome" in response.message.lower()

    def test_list_apps_message_format_multiple_apps(self, app_control_skill, mock_psutil):
        """Test message format with multiple apps."""
        mock_processes = []
        for name in ["Chrome", "Safari", "Terminal"]:
            mock_proc = Mock()
            mock_proc.info = {"name": name}
            mock_processes.append(mock_proc)

        mock_psutil.return_value = mock_processes

        entities = {}
        context = {}

        response = app_control_skill._list_apps(entities, context)

        assert response.success is True
        assert "running" in response.message.lower()


class TestSwitchApp:
    """Test switching to applications."""

    @pytest.mark.skipif(sys.platform not in ["darwin", "win32"],
                       reason="Platform-specific test")
    def test_switch_app_success(self, app_control_skill, mock_subprocess):
        """Test successfully switching to an app."""
        mock_subprocess.return_value = Mock(returncode=0)

        entities = {"app_name": "Chrome"}
        context = {}

        response = app_control_skill._switch_app(entities, context)

        assert response.success is True
        assert "Switching to Chrome" in response.message
        assert "sir" in response.message
        assert response.context_update["last_app"] == "Chrome"

    @pytest.mark.skipif(sys.platform not in ["darwin", "win32"],
                       reason="Platform-specific test")
    def test_switch_app_failure(self, app_control_skill, mock_subprocess):
        """Test failure when switching to an app."""
        mock_subprocess.return_value = Mock(returncode=1)

        entities = {"app_name": "NonRunningApp"}
        context = {}

        response = app_control_skill._switch_app(entities, context)

        assert response.success is False
        assert "unable to switch" in response.message.lower()

    def test_switch_app_missing_name(self, app_control_skill):
        """Test switching without app name."""
        entities = {}
        context = {}

        response = app_control_skill._switch_app(entities, context)

        assert response.success is False
        assert "need to know which application" in response.message.lower()


class TestExecute:
    """Test main execute method."""

    def test_execute_app_open(self, app_control_skill, mock_subprocess):
        """Test executing app.open intent."""
        mock_subprocess.return_value = Mock(returncode=0)

        entities = {"app_name": "Chrome"}
        context = {}

        response = app_control_skill.execute("app.open", entities, context)

        if sys.platform in ["darwin", "win32"]:
            assert response.success is True
            assert "Opening" in response.message

    def test_execute_app_close(self, app_control_skill, mock_subprocess):
        """Test executing app.close intent."""
        mock_subprocess.return_value = Mock(returncode=0)

        entities = {"app_name": "Chrome"}
        context = {}

        response = app_control_skill.execute("app.close", entities, context)

        if sys.platform in ["darwin", "win32"]:
            assert response.success is True
            assert "Closing" in response.message

    def test_execute_app_list(self, app_control_skill, mock_psutil):
        """Test executing app.list intent."""
        mock_psutil.return_value = []

        entities = {}
        context = {}

        response = app_control_skill.execute("app.list", entities, context)

        assert response.success is True
        assert isinstance(response.data["apps"], list)

    def test_execute_app_switch(self, app_control_skill, mock_subprocess):
        """Test executing app.switch intent."""
        mock_subprocess.return_value = Mock(returncode=0)

        entities = {"app_name": "Chrome"}
        context = {}

        response = app_control_skill.execute("app.switch", entities, context)

        if sys.platform in ["darwin", "win32"]:
            assert response.success is True
            assert "Switching" in response.message

    def test_execute_unknown_intent(self, app_control_skill):
        """Test executing unknown intent."""
        entities = {}
        context = {}

        response = app_control_skill.execute("unknown.intent", entities, context)

        assert response.success is False
        assert "not sure how to handle" in response.message.lower()

    def test_execute_with_exception(self, app_control_skill, mock_subprocess):
        """Test execute with exception."""
        mock_subprocess.side_effect = Exception("Test error")

        entities = {"app_name": "Chrome"}
        context = {}

        response = app_control_skill.execute("app.open", entities, context)

        assert response.success is False
        assert "encountered an issue" in response.message.lower()


class TestJarvisPersonality:
    """Test J.A.R.V.I.S. personality in responses."""

    def test_responses_include_sir(self, app_control_skill, mock_subprocess):
        """Test that responses include 'sir' (J.A.R.V.I.S. style)."""
        mock_subprocess.return_value = Mock(returncode=0)

        entities = {"app_name": "Chrome"}
        context = {}

        # Test open
        response = app_control_skill._open_app(entities, context)
        if sys.platform in ["darwin", "win32"]:
            assert "sir" in response.message.lower()

        # Test close
        response = app_control_skill._close_app(entities, context)
        if sys.platform in ["darwin", "win32"]:
            assert "sir" in response.message.lower()

    def test_error_responses_polite(self, app_control_skill):
        """Test that error responses are polite."""
        entities = {}
        context = {}

        response = app_control_skill._open_app(entities, context)

        assert response.success is False
        assert "sir" in response.message.lower()
        # Should be polite and explanatory
        assert len(response.message) > 10


class TestHelp:
    """Test help functionality."""

    def test_get_help(self, app_control_skill):
        """Test getting help text."""
        help_text = app_control_skill.get_help()

        assert isinstance(help_text, str)
        assert len(help_text) > 0
        assert "app" in help_text.lower() or "application" in help_text.lower()
        assert "open" in help_text.lower()
        assert "close" in help_text.lower()


class TestValidateEntities:
    """Test entity validation."""

    def test_validate_entities_always_true(self, app_control_skill):
        """Test that entity validation passes (handled in execute methods)."""
        # Entity validation is handled in execute methods, so this returns True
        is_valid, error = app_control_skill.validate_entities({"app_name": "Chrome"})

        assert is_valid is True
        assert error is None

        # Even with empty entities
        is_valid, error = app_control_skill.validate_entities({})

        assert is_valid is True
        assert error is None


class TestPlatformSpecific:
    """Test platform-specific functionality."""

    @pytest.mark.skipif(sys.platform != "darwin", reason="macOS-specific test")
    def test_macos_specific_aliases(self):
        """Test macOS-specific app aliases."""
        skill = AppControlSkill()

        assert "safari" in skill.app_aliases
        assert "finder" in skill.app_aliases
        assert "terminal" in skill.app_aliases

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows-specific test")
    def test_windows_specific_aliases(self):
        """Test Windows-specific app aliases."""
        skill = AppControlSkill()

        assert "notepad" in skill.app_aliases
        assert "cmd" in skill.app_aliases
        assert "powershell" in skill.app_aliases


# Integration tests (require actual system capabilities)

@pytest.mark.integration
class TestIntegration:
    """Integration tests requiring actual system access."""

    @pytest.mark.skipif(sys.platform not in ["darwin", "win32"],
                       reason="Requires macOS or Windows")
    def test_list_actual_apps(self, app_control_skill):
        """Test listing actual running apps (integration test)."""
        entities = {}
        context = {}

        response = app_control_skill._list_apps(entities, context)

        # Should succeed even if no apps running
        assert response.success is True
        assert "apps" in response.data
        assert isinstance(response.data["apps"], list)
