"""
Search Skill for ZERO Assistant.

This skill handles web search requests by opening the default browser
with a search query on the configured search engine.
"""

import webbrowser
import urllib.parse
from typing import Dict, Any, List
import logging

from src.skills.base_skill import BaseSkill, SkillResponse

logger = logging.getLogger(__name__)


class SearchSkill(BaseSkill):
    """
    Search skill that opens web searches in the default browser.

    Features:
    - Extracts search query from user input
    - Opens default browser with search URL
    - Supports multiple search engines (Google, DuckDuckGo, Bing)
    - J.A.R.V.I.S. personality responses
    """

    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize search skill.

        Args:
            config: Configuration dictionary
        """
        super().__init__(
            name="search",
            description="Web search functionality - opens browser with search results",
            version="1.0.0",
        )

        self.config = config or {}
        search_config = self.config.get("skills", {}).get("search", {})
        self.default_engine = search_config.get("default_engine", "google")
        
        # Check if skill is enabled in config
        if not search_config.get("enabled", True):
            self.enabled = False

        # Search engine URLs
        self.search_engines = {
            "google": "https://www.google.com/search?q={}",
            "duckduckgo": "https://duckduckgo.com/?q={}",
            "bing": "https://www.bing.com/search?q={}",
        }

        logger.info(f"Search skill initialized with engine: {self.default_engine}")

    def can_handle(self, intent: str) -> bool:
        """
        Check if this skill can handle the given intent.

        Args:
            intent: Intent type

        Returns:
            True if skill can handle this intent
        """
        return intent == "search.web"

    def get_supported_intents(self) -> List[str]:
        """Get list of intents this skill supports."""
        return ["search.web"]

    def validate_entities(self, entities: Dict[str, Any]) -> tuple[bool, str | None]:
        """
        Validate that required entities are present.

        Args:
            entities: Extracted entities dictionary

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if we have a search query
        search_query = entities.get("search_query") or entities.get("query")
        user_input = entities.get("user_input", "")

        if not search_query and not user_input:
            return False, "I need to know what you'd like me to search for, sir."

        return True, None

    def execute(
        self, intent: str, entities: Dict[str, Any], context: Dict[str, Any]
    ) -> SkillResponse:
        """
        Execute search by opening browser with search query.

        Args:
            intent: Intent type (should be "search.web")
            entities: Extracted entities (should contain "search_query" or "query")
            context: Conversation context

        Returns:
            SkillResponse with result
        """
        try:
            # Extract search query from entities or user input
            search_query = entities.get("search_query") or entities.get("query")
            user_input = entities.get("user_input", "")

            # If no explicit query, try to extract from user input
            if not search_query and user_input:
                search_query = self._extract_search_query(user_input)

            if not search_query:
                return self._create_error_response(
                    "I need to know what you'd like me to search for, sir."
                )

            # Get search engine from config or use default
            engine = entities.get("search_engine") or self.default_engine
            if engine not in self.search_engines:
                engine = self.default_engine
                logger.warning(f"Unknown search engine, using default: {self.default_engine}")

            # Build search URL
            search_url = self._build_search_url(search_query, engine)

            # Open browser
            logger.info(f"Opening search: {search_query} on {engine}")
            try:
                webbrowser.open(search_url)
                logger.info(f"Browser opened with search URL: {search_url}")

                # Create success response
                message = f"I've opened a search for '{search_query}' in your browser, sir."
                return self._create_success_response(
                    message=message,
                    data={
                        "search_query": search_query,
                        "search_engine": engine,
                        "search_url": search_url,
                    },
                )
            except Exception as e:
                logger.error(f"Failed to open browser: {e}")
                return self._create_error_response(
                    "I apologize, but I encountered an error opening your browser, sir."
                )

        except Exception as e:
            logger.error(f"Search skill execution error: {e}", exc_info=True)
            return self._create_error_response(
                "I encountered an error processing your search request, sir."
            )

    def _extract_search_query(self, user_input: str) -> str:
        """
        Extract search query from user input.

        Args:
            user_input: User's input text

        Returns:
            Extracted search query
        """
        # Remove common search phrases
        query = user_input.lower()

        # Remove "search for", "search", "google", "look up", "find"
        patterns_to_remove = [
            r"^search\s+(for\s+)?",
            r"^google\s+",
            r"^look\s+up\s+",
            r"^find\s+(me\s+)?(information\s+)?(about\s+)?",
            r"^search\s+",
        ]

        import re

        for pattern in patterns_to_remove:
            query = re.sub(pattern, "", query, flags=re.IGNORECASE)

        # Clean up and return
        query = query.strip()
        return query if query else user_input

    def _build_search_url(self, query: str, engine: str) -> str:
        """
        Build search URL for the given query and engine.

        Args:
            query: Search query
            engine: Search engine name

        Returns:
            Complete search URL
        """
        # URL encode the query
        encoded_query = urllib.parse.quote_plus(query)

        # Get base URL for engine
        base_url = self.search_engines.get(engine, self.search_engines["google"])

        # Format URL with encoded query
        search_url = base_url.format(encoded_query)

        return search_url

    def get_help(self) -> str:
        """Get help text for this skill."""
        return """Search Skill - Web Search Functionality

I can search the web for you by opening your default browser with search results.

Examples:
- "Search for Python tutorials"
- "Google machine learning"
- "Look up the weather in Paris"
- "Find information about quantum computing"

Supported search engines: Google, DuckDuckGo, Bing
Configure your preferred engine in config.yaml"""

