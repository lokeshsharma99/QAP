"""
CI Log Analyzer Agent - Main Entry Point
=========================================

Run the CI Log Analyzer agent standalone for testing.
"""

from agents.ci_log_analyzer.agent import ci_log_analyzer

if __name__ == "__main__":
    print("CI Log Analyzer Agent")
    print("=" * 50)
    print("\nThis agent analyzes Azure DevOps CI pipeline logs, performs RCA,")
    print("and creates work items after HITL approval.\n")
    print("Example usage:")
    print('  ci_log_analyzer.run("Analyze pipeline run 12345 for project MyProject")')
    print("\nAgent is configured with:")
    print("  - Azure DevOps API access")
    print("  - RCA knowledge base")
    print("  - Learning and memory enabled")
    print("  - HITL approval for work item creation")
