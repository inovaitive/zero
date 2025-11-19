#!/usr/bin/env python3
"""
Performance Testing Script for ZERO Assistant.

Tests and measures latency improvements from optimizations.
"""

import sys
import time
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.config import get_config
from src.core.logger import setup_logger
from src.core.profiler import get_profiler, PipelineTimer
from src.core.engine import create_engine
from src.core.state import get_state_manager


# Test queries covering different intents
TEST_QUERIES = [
    # Weather (should trigger entity extraction)
    "What's the weather in New York?",
    "Will it rain tomorrow?",

    # Timer (should be fast - simple pattern match)
    "Set a timer for 5 minutes",
    "Cancel all timers",

    # Small talk (should hit cache after first run)
    "Hello",
    "Thank you",
    "Who are you?",

    # App control
    "Open Chrome",
    "Close Spotify",

    # Search
    "Search for Python tutorials",

    # Ambiguous (might trigger cloud if enabled)
    "I'm bored",
    "What should I do today?",
]


def run_performance_test(cli_only: bool = True):
    """
    Run comprehensive performance tests.

    Args:
        cli_only: Run in CLI mode (no voice)
    """
    print("=" * 70)
    print("ZERO ASSISTANT - PERFORMANCE TEST")
    print("=" * 70)
    print()

    # Load configuration
    config = get_config()

    # Setup logger
    logger = setup_logger(name="perf_test", log_level="INFO", console_output=True)

    logger.info("Initializing ZERO engine for performance testing...")

    # Initialize state manager
    state_manager = get_state_manager()

    # Create engine
    engine = create_engine(config=config, state_manager=state_manager)

    # Initialize components
    logger.info("Initializing components...")
    engine.initialize_components()

    # Get profiler
    profiler = get_profiler()
    profiler.enable()
    profiler.reset()

    logger.info(f"Testing {len(TEST_QUERIES)} queries...")
    print()

    # Test each query
    results = []
    for i, query in enumerate(TEST_QUERIES, 1):
        print(f"[{i}/{len(TEST_QUERIES)}] Testing: '{query}'")

        # Create pipeline timer
        timer = PipelineTimer(f"query_{i}")

        # Process query
        start_time = time.perf_counter()
        result = engine.process_text_command(query)
        end_time = time.perf_counter()

        latency_ms = (end_time - start_time) * 1000

        # Record result
        results.append({
            'query': query,
            'latency_ms': latency_ms,
            'success': result.success,
            'intent': result.intent if result.intent else "unknown",
            'method': result.skill_response.data.get('method', 'N/A') if result.skill_response else 'N/A'
        })

        # Print result
        status = "✓" if result.success else "✗"
        color = "\033[92m" if latency_ms < 1000 else "\033[93m" if latency_ms < 3000 else "\033[91m"
        print(f"  {status} Latency: {color}{latency_ms:.0f}ms\033[0m | Intent: {result.intent}")

        # Warn if over target
        if latency_ms > 3000:
            print(f"  ⚠️  OVER TARGET (3000ms)")

        print()

        # Small delay between queries
        time.sleep(0.1)

    # Print summary
    print("=" * 70)
    print("PERFORMANCE SUMMARY")
    print("=" * 70)
    print()

    # Calculate statistics
    latencies = [r['latency_ms'] for r in results]
    avg_latency = sum(latencies) / len(latencies)
    min_latency = min(latencies)
    max_latency = max(latencies)
    median_latency = sorted(latencies)[len(latencies) // 2]

    under_1s = sum(1 for l in latencies if l < 1000)
    under_3s = sum(1 for l in latencies if l < 3000)
    over_3s = sum(1 for l in latencies if l >= 3000)

    print(f"Total Queries:     {len(results)}")
    print(f"Average Latency:   {avg_latency:.0f}ms")
    print(f"Median Latency:    {median_latency:.0f}ms")
    print(f"Min Latency:       {min_latency:.0f}ms")
    print(f"Max Latency:       {max_latency:.0f}ms")
    print()
    print(f"Under 1s:          {under_1s}/{len(results)} ({under_1s/len(results)*100:.0f}%)")
    print(f"Under 3s (target): {under_3s}/{len(results)} ({under_3s/len(results)*100:.0f}%)")
    print(f"Over 3s:           {over_3s}/{len(results)} ({over_3s/len(results)*100:.0f}%)")
    print()

    # Performance grade
    if over_3s == 0:
        grade = "A+ (Excellent)"
        grade_color = "\033[92m"
    elif over_3s <= 2:
        grade = "A (Good)"
        grade_color = "\033[92m"
    elif under_3s >= len(results) * 0.8:
        grade = "B (Acceptable)"
        grade_color = "\033[93m"
    else:
        grade = "C (Needs Improvement)"
        grade_color = "\033[91m"

    print(f"Performance Grade: {grade_color}{grade}\033[0m")
    print()

    # Component breakdown from profiler
    print("=" * 70)
    print("COMPONENT BREAKDOWN")
    print("=" * 70)
    print()
    print(profiler.get_report())
    print()

    # Cache statistics
    if engine.skill_manager:
        print("=" * 70)
        print("CACHE STATISTICS")
        print("=" * 70)
        print()

        # Response cache stats (if available)
        try:
            from src.core.response_cache import get_response_cache
            cache = get_response_cache()
            stats = cache.get_stats()
            print("Response Cache:")
            print(f"  Hits:     {stats['hits']}")
            print(f"  Misses:   {stats['misses']}")
            print(f"  Hit Rate: {stats['hit_rate']*100:.1f}%")
            print(f"  Entries:  {stats['total_entries']}/{stats['max_entries']}")
            print()
        except Exception:
            pass

    # Recommendations
    print("=" * 70)
    print("RECOMMENDATIONS")
    print("=" * 70)
    print()

    if over_3s > 0:
        print("⚠️  Some queries are over the 3-second target:")
        for r in results:
            if r['latency_ms'] >= 3000:
                print(f"  - '{r['query']}': {r['latency_ms']:.0f}ms")
        print()
        print("Suggestions:")
        print("  1. Check if cloud fallback is enabled and causing delays")
        print("  2. Verify API response times (Deepgram, OpenAI, Weather)")
        print("  3. Enable async mode for cloud classification")
        print("  4. Use faster TTS model (VITS instead of Tacotron2)")
        print("  5. Enable response caching for common queries")
        print()
    else:
        print("✓ All queries meet the 3-second target!")
        print()

    if avg_latency > 1500:
        print("💡 To further improve performance:")
        print("  - Pre-cache common TTS phrases")
        print("  - Lower confidence threshold to reduce cloud calls")
        print("  - Use gpt-3.5-turbo instead of gpt-4")
        print("  - Enable GPU acceleration for TTS if available")
        print()

    print("=" * 70)


def run_quick_test():
    """Run a quick sanity test with 3 queries."""
    print("Running quick performance test (3 queries)...")
    print()

    config = get_config()
    state_manager = get_state_manager()
    engine = create_engine(config=config, state_manager=state_manager)
    engine.initialize_components()

    test_queries = [
        "Hello",
        "What's the weather in San Francisco?",
        "Set a timer for 10 seconds"
    ]

    latencies = []
    for query in test_queries:
        start = time.perf_counter()
        result = engine.process_text_command(query)
        latency = (time.perf_counter() - start) * 1000
        latencies.append(latency)

        status = "✓" if result.success else "✗"
        print(f"{status} '{query}': {latency:.0f}ms")

    avg = sum(latencies) / len(latencies)
    print()
    print(f"Average latency: {avg:.0f}ms")
    print()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="ZERO Performance Testing")
    parser.add_argument("--quick", action="store_true", help="Run quick test (3 queries)")
    args = parser.parse_args()

    try:
        if args.quick:
            run_quick_test()
        else:
            run_performance_test()
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"\nError during testing: {e}")
        import traceback
        traceback.print_exc()
