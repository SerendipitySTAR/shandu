#!/usr/bin/env python3
"""
Test script to verify the improved search functionality and 429 error handling.
"""
import asyncio
import logging
from shandu.search.search import UnifiedSearcher

# Configure logging to see the improvements
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

async def test_search_improvements():
    """Test the improved search functionality."""
    print("Testing improved search functionality...")
    
    # Create searcher with conservative settings
    searcher = UnifiedSearcher(max_results=5)
    
    # Test queries
    test_queries = [
        "《西游记》三界权力体系",
        "孙悟空大闹天宫",
        "唐僧师徒关系"
    ]
    
    for i, query in enumerate(test_queries):
        print(f"\n--- Test {i+1}: {query} ---")
        
        try:
            # Test with default engines (should avoid Google)
            results = await searcher.search(query)
            print(f"✓ Found {len(results)} results using default engines")
            
            for j, result in enumerate(results[:3]):  # Show first 3 results
                print(f"  {j+1}. {result.source}: {result.title[:50]}...")
                
        except Exception as e:
            print(f"✗ Search failed: {e}")
        
        # Add delay between searches
        if i < len(test_queries) - 1:
            print("Waiting 2 seconds before next search...")
            await asyncio.sleep(2)
    
    print("\n--- Testing Google rate limiting ---")
    try:
        # Test Google specifically (should be rate limited or skipped)
        results = await searcher.search("测试查询", engines=["google"])
        print(f"Google search result: {len(results)} results")
    except Exception as e:
        print(f"Google search handled gracefully: {e}")
    
    print("\nTest completed!")

if __name__ == "__main__":
    asyncio.run(test_search_improvements())
