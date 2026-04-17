"""
Technical Tester Agent - Main Entry Point
==========================================

Run the Technical Tester agent standalone for testing.
"""

from agents.technical_tester.agent import technical_tester

if __name__ == "__main__":
    print("Technical Tester Agent")
    print("=" * 50)
    print("\nThis agent uses Playwright Test Agents (planner, generator, healer)")
    print("for rapid test generation, smoke tests, and exploratory testing.\n")
    print("Example usage:")
    print('  technical_tester.run("Generate smoke tests for https://example.com")')
    print("\nAgent is configured with:")
    print("  - Playwright CLI tools")
    print("  - Codebase knowledge base")
    print("  - Learning and memory enabled")
    print("  - Complementary to Engineer agent (BDD+POM)")
