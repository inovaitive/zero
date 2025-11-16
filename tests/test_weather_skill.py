"""
Tests for Weather Skill.

Tests:
- Weather skill initialization
- Current weather queries
- Forecast queries
- Entity extraction for weather
- Caching mechanism
- Error handling
- J.A.R.V.I.S. personality responses
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from typing import Dict, Any

# Skip tests if pyowm is not available
pytest.importorskip("pyowm", reason="pyowm not installed")

from src.skills.weather_skill import WeatherSkill, WeatherData, create_weather_skill
from src.skills.base_skill import SkillResponse


@pytest.fixture
def mock_owm():
    """Create a mock OWM client."""
    with patch('src.skills.weather_skill.pyowm.OWM') as mock:
        yield mock


@pytest.fixture
def weather_skill(mock_owm):
    """Create a weather skill with mock OWM."""
    mock_owm_instance = MagicMock()
    mock_owm.return_value = mock_owm_instance

    skill = WeatherSkill(
        api_key="test_api_key",
        default_location="London",
        units="metric",
        cache_ttl=300
    )

    # Set up mock manager
    mock_manager = MagicMock()
    mock_owm_instance.weather_manager.return_value = mock_manager
    skill.mgr = mock_manager

    return skill


@pytest.fixture
def mock_weather_observation():
    """Create a mock weather observation."""
    mock_weather = MagicMock()
    mock_weather.temperature.return_value = {
        'temp': 20.5,
        'feels_like': 18.0,
    }
    mock_weather.detailed_status = "partly cloudy"
    mock_weather.humidity = 65
    mock_weather.wind.return_value = {
        'speed': 5.2,
    }

    mock_observation = MagicMock()
    mock_observation.weather = mock_weather

    return mock_observation


@pytest.fixture
def mock_forecast():
    """Create a mock weather forecast."""
    mock_forecast_obj = MagicMock()

    # Create mock weather objects for forecast
    forecast_weathers = []
    for i in range(8):
        mock_weather = MagicMock()
        mock_weather.temperature.return_value = {
            'temp': 20.0 + i,
        }
        mock_weather.detailed_status = "clear sky"
        mock_weather.reference_time.return_value = datetime.now() + timedelta(hours=i*3)
        mock_weather.rain = {}
        forecast_weathers.append(mock_weather)

    mock_forecast_obj.forecast.weathers = forecast_weathers

    return mock_forecast_obj


class TestWeatherSkillInitialization:
    """Test weather skill initialization."""

    def test_skill_initialization_with_api_key(self, mock_owm):
        """Test successful initialization with API key."""
        skill = WeatherSkill(api_key="test_api_key")

        assert skill.name == "weather"
        assert skill.enabled is True
        assert skill.api_key == "test_api_key"
        assert skill.units == "metric"

    def test_skill_initialization_without_api_key(self, mock_owm):
        """Test initialization without API key."""
        skill = WeatherSkill(api_key=None)

        # Should be disabled without API key
        assert skill.enabled is False

    def test_skill_initialization_from_env(self, mock_owm):
        """Test initialization with API key from environment."""
        with patch.dict('os.environ', {'OPENWEATHERMAP_API_KEY': 'env_api_key'}):
            skill = WeatherSkill()
            assert skill.api_key == 'env_api_key'

    def test_skill_initialization_with_config(self, mock_owm):
        """Test initialization with configuration."""
        config = {
            'skills': {
                'weather': {
                    'api_key': 'config_api_key',
                    'default_location': 'Paris',
                    'units': 'imperial',
                    'cache_ttl': 600,
                }
            }
        }

        skill = create_weather_skill(config)

        assert skill.default_location == 'Paris'
        assert skill.units == 'imperial'
        assert skill.cache_ttl == 600


class TestWeatherSkillIntentHandling:
    """Test weather skill intent handling."""

    def test_can_handle_weather_query(self, weather_skill):
        """Test that skill can handle weather queries."""
        assert weather_skill.can_handle("weather.query") is True
        assert weather_skill.can_handle("WEATHER_QUERY") is True

    def test_cannot_handle_other_intents(self, weather_skill):
        """Test that skill doesn't handle non-weather intents."""
        assert weather_skill.can_handle("timer.set") is False
        assert weather_skill.can_handle("app.open") is False

    def test_get_supported_intents(self, weather_skill):
        """Test getting list of supported intents."""
        intents = weather_skill.get_supported_intents()
        assert "weather.query" in intents


class TestWeatherDataClass:
    """Test WeatherData dataclass."""

    def test_weather_data_creation(self):
        """Test creating WeatherData object."""
        data = WeatherData(
            location="London",
            temperature=20.5,
            feels_like=18.0,
            conditions="partly cloudy",
            humidity=65,
            wind_speed=5.2,
            timestamp=datetime.now(),
            units="metric"
        )

        assert data.location == "London"
        assert data.temperature == 20.5
        assert data.conditions == "partly cloudy"

    def test_temperature_string_metric(self):
        """Test temperature string formatting in metric."""
        data = WeatherData(
            location="London",
            temperature=20.5,
            feels_like=18.0,
            conditions="sunny",
            humidity=50,
            wind_speed=5.0,
            timestamp=datetime.now(),
            units="metric"
        )

        assert "°C" in data.get_temperature_string()
        assert "20.5" in data.get_temperature_string()

    def test_temperature_string_imperial(self):
        """Test temperature string formatting in imperial."""
        data = WeatherData(
            location="New York",
            temperature=68.0,
            feels_like=65.0,
            conditions="sunny",
            humidity=50,
            wind_speed=10.0,
            timestamp=datetime.now(),
            units="imperial"
        )

        assert "°F" in data.get_temperature_string()
        assert "68.0" in data.get_temperature_string()

    def test_wind_speed_string(self):
        """Test wind speed string formatting."""
        data = WeatherData(
            location="London",
            temperature=20.0,
            feels_like=18.0,
            conditions="windy",
            humidity=60,
            wind_speed=12.5,
            timestamp=datetime.now(),
            units="metric"
        )

        wind_str = data.get_wind_speed_string()
        assert "12.5" in wind_str
        assert "m/s" in wind_str


class TestCurrentWeather:
    """Test current weather queries."""

    def test_get_current_weather_success(self, weather_skill, mock_weather_observation):
        """Test successful current weather query."""
        weather_skill.mgr.weather_at_place.return_value = mock_weather_observation

        response = weather_skill.execute(
            intent="weather.query",
            entities={},
            context={}
        )

        assert response.success is True
        assert "London" in response.message  # Default location
        assert "partly cloudy" in response.message.lower()

    def test_get_current_weather_with_location(self, weather_skill, mock_weather_observation):
        """Test current weather query with specific location."""
        weather_skill.mgr.weather_at_place.return_value = mock_weather_observation

        response = weather_skill.execute(
            intent="weather.query",
            entities={'location': 'New York'},
            context={}
        )

        assert response.success is True
        assert "New York" in response.message

    def test_get_current_weather_with_context_location(self, weather_skill, mock_weather_observation):
        """Test using location from context."""
        weather_skill.mgr.weather_at_place.return_value = mock_weather_observation

        response = weather_skill.execute(
            intent="weather.query",
            entities={},
            context={'last_weather_location': 'Paris'}
        )

        assert response.success is True
        assert "Paris" in response.message

    def test_weather_response_format(self, weather_skill, mock_weather_observation):
        """Test that weather response has J.A.R.V.I.S. personality."""
        weather_skill.mgr.weather_at_place.return_value = mock_weather_observation

        response = weather_skill.execute(
            intent="weather.query",
            entities={'location': 'London'},
            context={}
        )

        assert response.success is True
        # Check for J.A.R.V.I.S. style language
        assert "sir" in response.message.lower()
        assert "temperature" in response.message.lower()
        assert "humidity" in response.message.lower()

    def test_weather_context_update(self, weather_skill, mock_weather_observation):
        """Test that weather updates context."""
        weather_skill.mgr.weather_at_place.return_value = mock_weather_observation

        response = weather_skill.execute(
            intent="weather.query",
            entities={'location': 'Tokyo'},
            context={}
        )

        assert 'last_weather_location' in response.context_update
        assert response.context_update['last_weather_location'] == 'Tokyo'


class TestWeatherCaching:
    """Test weather caching mechanism."""

    def test_cache_stores_weather_data(self, weather_skill, mock_weather_observation):
        """Test that weather data is cached."""
        weather_skill.mgr.weather_at_place.return_value = mock_weather_observation

        # First call
        response1 = weather_skill.execute(
            intent="weather.query",
            entities={'location': 'London'},
            context={}
        )

        # Check cache
        assert 'London' in weather_skill._cache

    def test_cache_reuses_data(self, weather_skill, mock_weather_observation):
        """Test that cached data is reused."""
        weather_skill.mgr.weather_at_place.return_value = mock_weather_observation

        # First call
        response1 = weather_skill.execute(
            intent="weather.query",
            entities={'location': 'London'},
            context={}
        )

        # Second call should use cache
        response2 = weather_skill.execute(
            intent="weather.query",
            entities={'location': 'London'},
            context={}
        )

        # API should only be called once
        assert weather_skill.mgr.weather_at_place.call_count == 1

    def test_cache_expiration(self, weather_skill, mock_weather_observation):
        """Test that cache expires after TTL."""
        weather_skill.cache_ttl = 0  # Immediate expiration
        weather_skill.mgr.weather_at_place.return_value = mock_weather_observation

        # First call
        response1 = weather_skill.execute(
            intent="weather.query",
            entities={'location': 'London'},
            context={}
        )

        # Second call should not use cache (expired)
        response2 = weather_skill.execute(
            intent="weather.query",
            entities={'location': 'London'},
            context={}
        )

        # API should be called twice
        assert weather_skill.mgr.weather_at_place.call_count == 2


class TestWeatherForecast:
    """Test weather forecast queries."""

    def test_get_forecast(self, weather_skill, mock_forecast):
        """Test getting weather forecast."""
        weather_skill.mgr.forecast_at_place.return_value = mock_forecast

        response = weather_skill.execute(
            intent="weather.query",
            entities={'time': {'text': 'tomorrow'}},
            context={}
        )

        assert response.success is True
        assert "forecast" in response.message.lower()


class TestWeatherErrorHandling:
    """Test error handling in weather skill."""

    def test_location_not_found(self, weather_skill):
        """Test handling of location not found error."""
        from pyowm.commons.exceptions import NotFoundError

        weather_skill.mgr.weather_at_place.side_effect = NotFoundError("Not found")

        response = weather_skill.execute(
            intent="weather.query",
            entities={'location': 'InvalidCity123'},
            context={}
        )

        assert response.success is False
        assert "could not find" in response.message.lower()

    def test_api_authentication_error(self, weather_skill):
        """Test handling of authentication errors."""
        from pyowm.commons.exceptions import UnauthorizedError

        weather_skill.mgr.weather_at_place.side_effect = UnauthorizedError("Unauthorized")

        response = weather_skill.execute(
            intent="weather.query",
            entities={},
            context={}
        )

        assert response.success is False
        assert "authentication" in response.message.lower()

    def test_api_request_error(self, weather_skill):
        """Test handling of API request errors."""
        from pyowm.commons.exceptions import APIRequestError

        weather_skill.mgr.weather_at_place.side_effect = APIRequestError("Request failed")

        response = weather_skill.execute(
            intent="weather.query",
            entities={},
            context={}
        )

        assert response.success is False
        assert "difficulties" in response.message.lower()

    def test_unexpected_error(self, weather_skill):
        """Test handling of unexpected errors."""
        weather_skill.mgr.weather_at_place.side_effect = Exception("Unexpected error")

        response = weather_skill.execute(
            intent="weather.query",
            entities={},
            context={}
        )

        assert response.success is False
        assert "unexpected error" in response.message.lower()

    def test_disabled_skill(self):
        """Test execution when skill is disabled."""
        skill = WeatherSkill(api_key=None)  # No API key = disabled

        response = skill.execute(
            intent="weather.query",
            entities={},
            context={}
        )

        assert response.success is False
        assert "unavailable" in response.message.lower()


class TestWeatherMessageFormatting:
    """Test weather message formatting."""

    def test_message_includes_temperature(self, weather_skill, mock_weather_observation):
        """Test that message includes temperature."""
        weather_skill.mgr.weather_at_place.return_value = mock_weather_observation

        response = weather_skill.execute(
            intent="weather.query",
            entities={},
            context={}
        )

        assert "temperature" in response.message.lower()
        assert "°C" in response.message or "°F" in response.message

    def test_cold_weather_advice(self, weather_skill, mock_weather_observation):
        """Test advice for cold weather."""
        # Set up cold weather
        mock_weather_observation.weather.temperature.return_value = {
            'temp': 5.0,
            'feels_like': 3.0,
        }
        weather_skill.mgr.weather_at_place.return_value = mock_weather_observation

        response = weather_skill.execute(
            intent="weather.query",
            entities={},
            context={}
        )

        assert "coat" in response.message.lower()

    def test_hot_weather_advice(self, weather_skill, mock_weather_observation):
        """Test advice for hot weather."""
        # Set up hot weather
        mock_weather_observation.weather.temperature.return_value = {
            'temp': 35.0,
            'feels_like': 37.0,
        }
        weather_skill.mgr.weather_at_place.return_value = mock_weather_observation

        response = weather_skill.execute(
            intent="weather.query",
            entities={},
            context={}
        )

        assert "warm" in response.message.lower() or "hydrat" in response.message.lower()

    def test_rainy_weather_advice(self, weather_skill, mock_weather_observation):
        """Test advice for rainy weather."""
        # Set up rainy weather
        mock_weather_observation.weather.detailed_status = "light rain"
        weather_skill.mgr.weather_at_place.return_value = mock_weather_observation

        response = weather_skill.execute(
            intent="weather.query",
            entities={},
            context={}
        )

        assert "umbrella" in response.message.lower()


class TestWeatherHelp:
    """Test weather skill help text."""

    def test_get_help(self, weather_skill):
        """Test getting help text."""
        help_text = weather_skill.get_help()

        assert "weather" in help_text.lower()
        assert "examples" in help_text.lower()
        assert "forecast" in help_text.lower()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
