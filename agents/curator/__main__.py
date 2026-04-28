"""
Curator Agent Entry Point
=========================

Standalone entry point for running the Curator agent.
"""

if __name__ == "__main__":
    from agents.curator.agent import curator

    curator.cli()
