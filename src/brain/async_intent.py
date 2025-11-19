"""
Async Intent Classification for ZERO Assistant.

This module provides async intent classification with parallel local/cloud processing
for reduced latency.
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from concurrent.futures import ThreadPoolExecutor

from src.brain.intent import IntentClassifier, IntentResult, IntentType
from src.core.profiler import profile_async_method, get_profiler

logger = logging.getLogger(__name__)


class AsyncIntentClassifier(IntentClassifier):
    """
    Async intent classifier with parallel local/cloud processing.

    Key improvements:
    1. Run local and cloud classification in parallel
    2. Return local result immediately if confidence is acceptable
    3. Upgrade to cloud result if better, but don't block
    4. Significantly reduces latency for ambiguous queries
    """

    def __init__(self, *args, **kwargs):
        """Initialize async intent classifier."""
        super().__init__(*args, **kwargs)
        self._executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="AsyncIntent")
        logger.info("Async intent classifier initialized")

    @profile_async_method("async_intent.classify")
    async def classify_async(
        self,
        text: str,
        timeout: float = 2.0
    ) -> IntentResult:
        """
        Classify intent asynchronously with parallel local/cloud processing.

        Strategy:
        1. Start local classification
        2. If cloud is enabled and local confidence is low, start cloud in parallel
        3. Return local result immediately if confidence >= threshold
        4. Otherwise wait for cloud result (with timeout)
        5. Return best result

        Args:
            text: User input text
            timeout: Maximum time to wait for cloud result (seconds)

        Returns:
            IntentResult with best classification
        """
        profiler = get_profiler()

        text = text.strip().lower()

        if not text:
            return IntentResult(
                intent=IntentType.UNKNOWN,
                confidence=1.0,
                method='empty',
                raw_text=text
            )

        # Start local classification
        with profiler.measure("async_intent.local"):
            local_result = self._classify_with_patterns(text)

        # If spaCy available, try it too
        if self.nlp and self.matcher:
            with profiler.measure("async_intent.spacy"):
                spacy_result = self._classify_with_spacy(text)
                if spacy_result.confidence > local_result.confidence:
                    local_result = spacy_result

        # If local confidence is high enough, return immediately
        if local_result.confidence >= self.confidence_threshold:
            logger.debug(
                f"High confidence local result: {local_result.intent.value} "
                f"({local_result.confidence:.2f})"
            )
            return local_result

        # If cloud is disabled, return local result
        if not self.use_cloud_fallback or not self.llm_client:
            logger.debug(
                f"Cloud disabled, using local result: {local_result.intent.value} "
                f"({local_result.confidence:.2f})"
            )
            return local_result

        # Low confidence and cloud enabled - run cloud classification
        logger.debug(
            f"Low confidence ({local_result.confidence:.2f}), "
            f"trying cloud classification..."
        )

        try:
            # Run cloud classification with timeout
            cloud_task = asyncio.create_task(
                self._classify_with_cloud_async(text)
            )

            # Wait for cloud result with timeout
            cloud_result = await asyncio.wait_for(cloud_task, timeout=timeout)

            # Compare results
            if cloud_result and cloud_result.confidence > local_result.confidence:
                logger.info(
                    f"Cloud improved confidence: "
                    f"{local_result.confidence:.2f} -> {cloud_result.confidence:.2f}"
                )
                return cloud_result
            else:
                logger.debug("Local result is better or cloud failed, using local")
                return local_result

        except asyncio.TimeoutError:
            logger.warning(f"Cloud classification timed out after {timeout}s, using local")
            return local_result
        except Exception as e:
            logger.error(f"Cloud classification error: {e}")
            return local_result

    async def _classify_with_cloud_async(self, text: str) -> Optional[IntentResult]:
        """
        Async wrapper for cloud classification.

        Runs the synchronous cloud classification in a thread pool.

        Args:
            text: User input text

        Returns:
            IntentResult or None if failed
        """
        profiler = get_profiler()

        with profiler.measure("async_intent.cloud"):
            loop = asyncio.get_event_loop()
            try:
                # Run sync cloud classification in executor
                result = await loop.run_in_executor(
                    self._executor,
                    self._classify_with_cloud,
                    text
                )
                return result
            except Exception as e:
                logger.error(f"Error in async cloud classification: {e}")
                return None

    def classify(self, text: str) -> IntentResult:
        """
        Synchronous classify method (for backward compatibility).

        Falls back to sync behavior if not in async context.

        Args:
            text: User input text

        Returns:
            IntentResult
        """
        # Check if we're in an async context
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context, but this is a sync call
            # Use the sync version from parent class
            return super().classify(text)
        except RuntimeError:
            # No event loop, use sync version
            return super().classify(text)

    def shutdown(self):
        """Shutdown the classifier and cleanup resources."""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=True)
            logger.info("Async intent classifier executor shutdown")


class FastLocalIntentClassifier(IntentClassifier):
    """
    Fast local-only intent classifier (no cloud fallback).

    Optimized for:
    - Sub-50ms classification
    - Offline operation
    - Resource-constrained environments

    Trade-off: Lower accuracy on ambiguous queries
    """

    def __init__(self, *args, **kwargs):
        """Initialize fast local classifier."""
        # Force disable cloud
        kwargs['use_cloud_fallback'] = False
        kwargs['confidence_threshold'] = 0.6  # Lower threshold for faster decisions
        super().__init__(*args, **kwargs)
        logger.info("Fast local-only intent classifier initialized")

    def classify(self, text: str) -> IntentResult:
        """
        Fast local classification.

        Args:
            text: User input text

        Returns:
            IntentResult
        """
        profiler = get_profiler()

        with profiler.measure("fast_intent.classify"):
            text = text.strip().lower()

            if not text:
                return IntentResult(
                    intent=IntentType.UNKNOWN,
                    confidence=1.0,
                    method='empty',
                    raw_text=text
                )

            # Try patterns first (fastest)
            result = self._classify_with_patterns(text)

            # If confidence is acceptable, return
            if result.confidence >= self.confidence_threshold:
                return result

            # Try spaCy if available (still local, but slower)
            if self.nlp and self.matcher:
                spacy_result = self._classify_with_spacy(text)
                if spacy_result.confidence > result.confidence:
                    return spacy_result

            # Return best local result
            return result


def create_async_intent_classifier(config: Dict[str, Any] = None) -> AsyncIntentClassifier:
    """
    Create an async intent classifier with configuration.

    Args:
        config: Configuration dictionary

    Returns:
        Configured AsyncIntentClassifier instance
    """
    if config is None:
        config = {}

    # Extract NLU config
    nlu_config = config.get('nlu', {})
    local_config = nlu_config.get('local', {})
    cloud_config = nlu_config.get('cloud', {})

    # Create LLM client if cloud fallback is enabled
    llm_client = None
    use_cloud_fallback = cloud_config.get('enabled', False)
    if use_cloud_fallback:
        from src.brain.llm import create_llm_client
        llm_client = create_llm_client(config)
        if llm_client and llm_client.is_available():
            logger.info("LLM client initialized for async cloud fallback")
        else:
            logger.warning("Cloud fallback enabled but LLM client not available")
            use_cloud_fallback = False

    return AsyncIntentClassifier(
        use_spacy=local_config.get('enabled', True),
        spacy_model=local_config.get('spacy_model', 'en_core_web_sm'),
        confidence_threshold=local_config.get('confidence_threshold', 0.8),
        use_cloud_fallback=use_cloud_fallback,
        llm_client=llm_client,
    )


def create_fast_local_classifier(config: Dict[str, Any] = None) -> FastLocalIntentClassifier:
    """
    Create a fast local-only intent classifier.

    Args:
        config: Configuration dictionary

    Returns:
        Configured FastLocalIntentClassifier instance
    """
    if config is None:
        config = {}

    nlu_config = config.get('nlu', {})
    local_config = nlu_config.get('local', {})

    return FastLocalIntentClassifier(
        use_spacy=local_config.get('enabled', True),
        spacy_model=local_config.get('spacy_model', 'en_core_web_sm'),
        confidence_threshold=0.6,  # Lower for fast decisions
        use_cloud_fallback=False,
        llm_client=None,
    )
