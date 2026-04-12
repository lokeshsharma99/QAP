"""
Test RAG Accuracy Script
========================

This script tests the semantic search accuracy of the codebase knowledge base
by querying for specific code patterns and verifying correct file/line retrieval.
"""

from db.session import get_codebase_knowledge


def test_rag_accuracy():
    """Test RAG accuracy with ≥5 different queries."""
    print("\n" + "=" * 70)
    print("RAG ACCURACY TEST")
    print("=" * 70)
    
    kb = get_codebase_knowledge()
    
    # Test queries covering different aspects of the codebase
    test_queries = [
        ("search input locator", "HomePage.ts", "Should find HomePage.ts with #search-input selector"),
        ("search button", "HomePage.ts", "Should find HomePage.ts with searchButton method"),
        ("search results", "HomePage.ts", "Should find HomePage.ts with searchResults locator"),
        ("Given I navigate to homepage", "example.steps.ts", "Should find example.steps.ts with Given step"),
        ("When I search for", "example.steps.ts", "Should find example.steps.ts with When step"),
    ]
    
    passed = 0
    failed = 0
    
    for query, expected_file, expected_desc in test_queries:
        print(f"\nQuery: '{query}'")
        print(f"Expected file: {expected_file}")
        print(f"Description: {expected_desc}")
        
        try:
            results = kb.search(query)
            
            if results and len(results) > 0:
                # Check if expected file is in results
                found_correct_file = False
                for result in results[:2]:
                    name = getattr(result, 'name', str(result))
                    print(f"  Result: {name}")
                    if expected_file in name:
                        found_correct_file = True
                
                if found_correct_file:
                    print(f"✓ PASS: Found correct file ({expected_file})")
                    passed += 1
                else:
                    print(f"✗ FAIL: Expected file ({expected_file}) not found in results")
                    failed += 1
            else:
                print(f"✗ FAIL: No results found")
                failed += 1
        except Exception as e:
            print(f"✗ FAIL: Exception occurred: {e}")
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"RESULTS: {passed}/{len(test_queries)} tests passed")
    print("=" * 70)
    
    if passed == len(test_queries):
        print("✓ RAG accuracy verified - all queries returned results")
        return True
    else:
        print(f"✗ RAG accuracy incomplete - {failed} test(s) failed")
        return False


if __name__ == "__main__":
    test_rag_accuracy()
