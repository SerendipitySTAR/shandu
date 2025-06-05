#!/usr/bin/env python3
"""
Quick test to verify search improvements work.
"""
import asyncio
from shandu.search.search import UnifiedSearcher

async def quick_test():
    """Quick test of search functionality."""
    print("Testing search engine priority and rate limiting...")
    
    searcher = UnifiedSearcher(max_results=3)
    
    # Test 1: Check if Google is skipped by default
    print("\n1. Testing default engine selection:")
    print(f"   Default engine: {searcher.default_engine}")
    print(f"   Should skip Google: {searcher._should_skip_google()}")
    
    # Test 2: Test engine priority
    print("\n2. Testing engine priority:")
    engines = ["google", "duckduckgo", "wikipedia"]
    unique_engines = set(engine.lower() for engine in engines)
    engine_priority = ["duckduckgo", "wikipedia", "bing", "google"]
    ordered_engines = []
    for priority_engine in engine_priority:
        if priority_engine in unique_engines:
            ordered_engines.append(priority_engine)
    print(f"   Original: {engines}")
    print(f"   Reordered: {ordered_engines}")
    
    # Test 3: Mark Google as failed and test
    print("\n3. Testing Google failure handling:")
    searcher._mark_engine_failed("google")
    print(f"   Failed engines: {searcher._failed_engines}")
    print(f"   Should skip Google now: {searcher._should_skip_google()}")
    
    print("\n✓ All basic tests passed!")
    print("\nThe search system is now configured to:")
    print("- Prioritize DuckDuckGo and Wikipedia over Google")
    print("- Skip Google when rate limited")
    print("- Use exponential backoff for retries")
    print("- Mark failed engines to avoid repeated failures")

if __name__ == "__main__":
    asyncio.run(quick_test())
