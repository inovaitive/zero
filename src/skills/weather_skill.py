"""
Weather Skill for ZERO Assistant.

This skill provides weather information using the OpenWeatherMap API:
- Current weather by location
- 5-day forecast
- Hourly forecast
- Weather alerts
"""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import requests

from src.skills.base_skill import BaseSkill, SkillResponse

logger = logging.getLogger(__name__)

# Try to import pyowm
try:
    import pyowm
    from pyowm.commons.exceptions import (
        APIRequestError,
        APIResponseError,
        NotFoundError,
        UnauthorizedError
    )
    PYOWM_AVAILABLE = True
except ImportError:
    PYOWM_AVAILABLE = False
    logger.warning("pyowm not available - weather skill will be disabled")


@dataclass
class WeatherData:
    """Weather information container."""

    location: str
    temperature: float
    feels_like: float
    conditions: str
    humidity: int
    wind_speed: float
    timestamp: datetime
    forecast: Optional[List[Dict[str, Any]]] = None
    units: str = "metric"

    def get_temperature_string(self) -> str:
        """Get formatted temperature string."""
        unit = "°C" if self.units == "metric" else "°F"
        return f"{self.temperature:.1f}{unit}"

    def get_wind_speed_string(self) -> str:
        """Get formatted wind speed string."""
        unit = "m/s" if self.units == "metric" else "mph"
        return f"{self.wind_speed:.1f} {unit}"


class WeatherSkill(BaseSkill):
    """
    Weather skill using OpenWeatherMap API.

    Handles queries like:
    - "What's the weather?"
    - "What's the weather in New York?"
    - "Will it rain tomorrow?"
    - "What's the forecast for this week?"
    - "How cold is it in Tokyo?"
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        default_location: str = "auto",
        units: str = "metric",
        cache_ttl: int = 300,
        config: Dict[str, Any] = None,
    ):
        """
        Initialize weather skill.

        Args:
            api_key: OpenWeatherMap API key
            default_location: Default location for weather queries
            units: Temperature units ('metric' or 'imperial')
            cache_ttl: Cache time-to-live in seconds
            config: Full configuration dictionary
        """
        super().__init__(
            name="weather",
            description="Get weather information and forecasts",
            version="1.0.0",
        )

        # Get API key from parameter or environment
        self.api_key = api_key or os.getenv("OPENWEATHERMAP_API_KEY")
        self.default_location = default_location
        self.units = units
        self.cache_ttl = cache_ttl

        # Weather cache: {location: (data, timestamp)}
        self._cache: Dict[str, tuple[WeatherData, datetime]] = {}

        # OpenWeatherMap client
        self.owm = None

        # Check if pyowm is available
        if not PYOWM_AVAILABLE:
            self.logger.error("pyowm not installed - weather skill cannot function")
            self.enabled = False
            return

        # Initialize OpenWeatherMap client
        if not self.api_key or self.api_key == "your_openweathermap_api_key_here":
            self.logger.warning("OpenWeatherMap API key not configured - weather skill disabled")
            self.enabled = False
        else:
            try:
                self.owm = pyowm.OWM(self.api_key)
                self.mgr = self.owm.weather_manager()
                self.logger.info("OpenWeatherMap client initialized")
            except Exception as e:
                self.logger.error(f"Failed to initialize OpenWeatherMap: {e}")
                self.enabled = False

    def can_handle(self, intent: str) -> bool:
        """Check if this skill can handle the intent."""
        return intent in [
            "weather.query",
            "WEATHER_QUERY"  # Also accept enum value
        ]

    def get_supported_intents(self) -> List[str]:
        """Get list of supported intents."""
        return ["weather.query"]

    def execute(
        self,
        intent: str,
        entities: Dict[str, Any],
        context: Dict[str, Any]
    ) -> SkillResponse:
        """
        Execute weather query.

        Args:
            intent: Intent type
            entities: Extracted entities (location, time, etc.)
            context: Conversation context

        Returns:
            SkillResponse with weather information
        """
        if not self.enabled or not self.owm:
            return self._create_error_response(
                "I apologize, sir, but the weather service is currently unavailable. "
                "It appears the API key has not been configured."
            )

        try:
            # Extract location from entities
            location = self._extract_location(entities, context)

            # Extract time context (current, tomorrow, etc.)
            time_context = self._extract_time_context(entities)

            # Get weather data
            if time_context == "current":
                weather_data = self._get_current_weather(location)
                message = self._format_current_weather(weather_data)
            elif time_context in ["tomorrow", "future"]:
                forecast_data = self._get_forecast(location)
                message = self._format_forecast(forecast_data, time_context)
            else:
                # Default to current weather
                weather_data = self._get_current_weather(location)
                message = self._format_current_weather(weather_data)

            # Prepare response data
            response_data = {
                "location": location,
                "time_context": time_context,
            }

            # Update context
            context_update = {
                "last_weather_location": location,
                "last_weather_query": datetime.now().isoformat(),
            }

            return self._create_success_response(
                message=message,
                data=response_data,
                context_update=context_update,
            )

        except NotFoundError:
            return self._create_error_response(
                f"I apologize, sir, but I could not find weather information for '{location}'. "
                "Perhaps you could specify a different location?"
            )
        except UnauthorizedError:
            return self._create_error_response(
                "I apologize, sir, but there seems to be an authentication issue with the weather service. "
                "Please verify the API key configuration."
            )
        except (APIRequestError, APIResponseError) as e:
            self.logger.error(f"Weather API error: {e}")
            return self._create_error_response(
                "I apologize, sir, but I'm experiencing difficulties accessing the weather service at the moment. "
                "Please try again shortly."
            )
        except Exception as e:
            self.logger.exception(f"Unexpected error in weather skill: {e}")
            return self._create_error_response(
                "I apologize, sir, but I encountered an unexpected error while retrieving the weather information."
            )

    def _extract_location(self, entities: Dict[str, Any], context: Dict[str, Any]) -> str:
        """
        Extract location from entities or context.

        Args:
            entities: Extracted entities
            context: Conversation context

        Returns:
            Location string
        """
        # Check entities for location
        if "location" in entities:
            location = entities["location"]
            if isinstance(location, dict):
                location = location.get("value", self.default_location)
            return str(location)

        # Check context for last location
        if "last_weather_location" in context:
            return context["last_weather_location"]

        # Use default location
        if self.default_location and self.default_location != "auto":
            return self.default_location

        # Fallback to a default city
        return "London"

    def _extract_time_context(self, entities: Dict[str, Any]) -> str:
        """
        Extract time context from entities.

        Args:
            entities: Extracted entities

        Returns:
            Time context string ('current', 'tomorrow', 'future')
        """
        # Check for time-related entities
        if "time" in entities or "date" in entities:
            time_entity = entities.get("time") or entities.get("date")

            if isinstance(time_entity, dict):
                text = time_entity.get("text", "").lower()
            else:
                text = str(time_entity).lower()

            if "tomorrow" in text or "next day" in text:
                return "tomorrow"
            elif any(word in text for word in ["week", "days", "forecast"]):
                return "future"

        return "current"

    def _get_current_weather(self, location: str) -> WeatherData:
        """
        Get current weather for a location.

        Args:
            location: Location name

        Returns:
            WeatherData object
        """
        # Check cache first
        cached = self._get_from_cache(location)
        if cached:
            self.logger.debug(f"Using cached weather for {location}")
            return cached

        # Fetch from API
        self.logger.info(f"Fetching current weather for {location}")
        observation = self.mgr.weather_at_place(location)
        weather = observation.weather

        # Extract weather data
        temp_dict = weather.temperature(unit=self.units)
        wind_dict = weather.wind(unit='meters_sec' if self.units == 'metric' else 'miles_hour')

        weather_data = WeatherData(
            location=location,
            temperature=temp_dict.get('temp', 0),
            feels_like=temp_dict.get('feels_like', 0),
            conditions=weather.detailed_status,
            humidity=weather.humidity,
            wind_speed=wind_dict.get('speed', 0),
            timestamp=datetime.now(),
            units=self.units,
        )

        # Cache the result
        self._add_to_cache(location, weather_data)

        return weather_data

    def _get_forecast(self, location: str) -> List[Dict[str, Any]]:
        """
        Get weather forecast for a location.

        Args:
            location: Location name

        Returns:
            List of forecast data
        """
        self.logger.info(f"Fetching forecast for {location}")

        # Get 5-day forecast
        forecaster = self.mgr.forecast_at_place(location, '3h')
        forecast = forecaster.forecast

        # Extract forecast data
        forecast_data = []
        for weather in forecast.weathers[:8]:  # Next 24 hours (8 * 3h intervals)
            temp_dict = weather.temperature(unit=self.units)
            forecast_data.append({
                'time': weather.reference_time('date'),
                'temperature': temp_dict.get('temp', 0),
                'conditions': weather.detailed_status,
                'rain_probability': weather.rain.get('3h', 0) if weather.rain else 0,
            })

        return forecast_data

    def _format_current_weather(self, weather_data: WeatherData) -> str:
        """
        Format current weather into a J.A.R.V.I.S.-style message.

        Args:
            weather_data: Weather data to format

        Returns:
            Formatted message string
        """
        temp_str = weather_data.get_temperature_string()
        feels_str = f"{weather_data.feels_like:.1f}°{'C' if weather_data.units == 'metric' else 'F'}"
        wind_str = weather_data.get_wind_speed_string()

        message = (
            f"The current weather in {weather_data.location} is {weather_data.conditions}, sir. "
            f"Temperature is {temp_str}, though it feels like {feels_str}. "
            f"Humidity is at {weather_data.humidity}%, with wind speeds of {wind_str}."
        )

        # Add contextual advice
        if weather_data.temperature < 10 and weather_data.units == "metric":
            message += " I would suggest wearing a coat if you're going out."
        elif weather_data.temperature > 30 and weather_data.units == "metric":
            message += " It's quite warm, sir. Staying hydrated would be advisable."

        if "rain" in weather_data.conditions.lower():
            message += " You might want to bring an umbrella."

        return message

    def _format_forecast(self, forecast_data: List[Dict[str, Any]], time_context: str) -> str:
        """
        Format forecast data into a message.

        Args:
            forecast_data: List of forecast data
            time_context: Time context ('tomorrow', 'future')

        Returns:
            Formatted message string
        """
        if not forecast_data:
            return "I apologize, sir, but I couldn't retrieve the forecast data."

        # Get tomorrow's forecast (items 8-16, which is 24-48 hours from now)
        if time_context == "tomorrow":
            if len(forecast_data) >= 1:
                tomorrow = forecast_data[0]
                temp = tomorrow['temperature']
                unit = "°C" if self.units == "metric" else "°F"
                conditions = tomorrow['conditions']

                message = (
                    f"Tomorrow's forecast shows {conditions}, sir, "
                    f"with temperatures around {temp:.1f}{unit}."
                )

                if tomorrow.get('rain_probability', 0) > 0:
                    message += f" There's a possibility of rain."

                return message

        # General forecast
        avg_temp = sum(f['temperature'] for f in forecast_data) / len(forecast_data)
        unit = "°C" if self.units == "metric" else "°F"
        conditions = [f['conditions'] for f in forecast_data]
        most_common = max(set(conditions), key=conditions.count)

        message = (
            f"The forecast shows {most_common} conditions, sir, "
            f"with average temperatures around {avg_temp:.1f}{unit}."
        )

        return message

    def _get_from_cache(self, location: str) -> Optional[WeatherData]:
        """Get weather data from cache if not expired."""
        if location not in self._cache:
            return None

        weather_data, timestamp = self._cache[location]
        age = (datetime.now() - timestamp).total_seconds()

        if age < self.cache_ttl:
            return weather_data

        # Cache expired
        del self._cache[location]
        return None

    def _add_to_cache(self, location: str, weather_data: WeatherData):
        """Add weather data to cache."""
        self._cache[location] = (weather_data, datetime.now())
        self.logger.debug(f"Cached weather for {location}")

    def get_help(self) -> str:
        """Get help text for weather skill."""
        return """
Weather Skill - Get weather information and forecasts

Examples:
- "What's the weather?"
- "What's the weather in New York?"
- "Will it rain tomorrow?"
- "What's the forecast for this week?"
- "How cold is it in Tokyo?"

Features:
- Current weather conditions
- Temperature and feels-like temperature
- Humidity and wind information
- Weather forecasts
- Contextual advice (coat recommendations, rain alerts)

Supported locations: Any city or location worldwide
        """.strip()


# Convenience function for skill creation
def create_weather_skill(config: Dict[str, Any] = None) -> WeatherSkill:
    """
    Create a weather skill from configuration.

    Args:
        config: Configuration dictionary

    Returns:
        Configured WeatherSkill instance
    """
    if config is None:
        config = {}

    weather_config = config.get('skills', {}).get('weather', {})

    return WeatherSkill(
        api_key=weather_config.get('api_key'),
        default_location=weather_config.get('default_location', 'auto'),
        units=weather_config.get('units', 'metric'),
        cache_ttl=weather_config.get('cache_ttl', 300),
        config=config,
    )
