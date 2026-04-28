"""
Test SPA Crawling with Discovery Agent
======================================

Tests the Discovery Agent's ability to crawl a Single-Page Application (SPA)
using Playwright MCP tools for JavaScript rendering.
"""

import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from agents.discovery.agent import discovery
from app.settings import AUT_BASE_URL

# ---------------------------------------------------------------------------
# Test Configuration
# ---------------------------------------------------------------------------
AUT_URL = "https://gds-demo-app.vercel.app/"

def test_spa_crawling():
    """Test Discovery Agent crawling the GDS demo SPA."""
    print("\n" + "=" * 70)
    print("TEST: SPA Crawling with Discovery Agent")
    print("=" * 70)
    print(f"AUT: {AUT_URL}")
    print()
    
    try:
        # Ask the Discovery Agent to crawl the SPA
        print("Step 1: Asking Discovery Agent to crawl the SPA...")
        print("  The agent should detect it's an SPA and use Playwright MCP tools")
        print()
        
        response = discovery.run(
            f"Crawl the application at {AUT_URL} and generate a Site Manifesto. "
            f"This is a React/Next.js Single-Page Application, so use Playwright MCP tools "
            f"to navigate, wait for JavaScript rendering, and extract components."
        )
        
        print("Step 2: Agent response received")
        print()
        print(response)
        print()
        
        # Try to parse the response as JSON to check if it's a valid Site Manifesto
        try:
            # The response might contain JSON in markdown code blocks
            if "```json" in response:
                json_start = response.find("```json") + 7
                json_end = response.find("```", json_start)
                json_str = response[json_start:json_end].strip()
                manifesto = json.loads(json_str)
            else:
                # Try to find JSON in the response
                manifesto = json.loads(response)
            
            print("Step 3: Valid Site Manifesto detected")
            print(f"  Total pages: {manifesto.get('total_pages', 0)}")
            print(f"  Total components: {manifesto.get('total_components', 0)}")
            
            if manifesto.get('total_pages', 0) >= 3:
                print("✓ PASS: Successfully crawled ≥3 pages")
                return True
            else:
                print(f"✗ FAIL: Only {manifesto.get('total_pages', 0)} pages discovered (need ≥3)")
                return False
                
        except json.JSONDecodeError:
            print("⚠ WARNING: Could not parse response as JSON")
            print("  The agent may need to be prompted to return JSON format")
            return False
            
    except Exception as e:
        print(f"✗ FAIL: Exception occurred: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_spa_crawling()
    sys.exit(0 if success else 1)
