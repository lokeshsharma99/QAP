"""
AgentOSClient Integration Example
==================================

This example demonstrates how to use the AgentOSClient to interact with
Quality Autopilot remotely via REST API.

Prerequisites:
1. Start AgentOS server: python -m app.main
2. Ensure server is running on http://localhost:8000

Usage:
    python examples/agentos_client_example.py
"""

import asyncio
from agno.client import AgentOSClient


async def main():
    # Initialize AgentOSClient
    client = AgentOSClient(base_url="http://localhost:8000")

    print("=" * 60)
    print("AgentOSClient Example")
    print("=" * 60)

    # Get AgentOS configuration
    print("\n1. Getting AgentOS configuration...")
    config = await client.aget_config()
    print(f"   Available agents: {[a.id for a in config.agents]}")
    print(f"   Available teams: {[t.id for t in config.teams]}")
    print(f"   Available workflows: {[w.id for w in config.workflows]}")

    # Example: Run an agent
    print("\n2. Running Architect agent...")
    try:
        result = await client.run_agent(
            agent_id="architect",
            message="Analyze this requirement: User login page should validate credentials",
        )
        print(f"   Response: {result[:200]}...")
    except Exception as e:
        print(f"   Error: {e}")

    # Example: List sessions (requires user_id)
    print("\n3. Listing sessions for user...")
    try:
        user_id = "example_user"
        sessions = await client.get_sessions(user_id=user_id)
        print(f"   Found {len(sessions.data)} sessions")
    except Exception as e:
        print(f"   Error: {e}")

    # Example: Create a session
    print("\n4. Creating a new session...")
    try:
        session = await client.create_session(
            agent_id="architect",
            user_id="example_user",
            session_name="My Test Session",
        )
        print(f"   Session ID: {session.session_id}")
        print(f"   Session Name: {session.session_name}")
    except Exception as e:
        print(f"   Error: {e}")

    # Example: Get session runs
    print("\n5. Getting session runs...")
    try:
        runs = await client.get_session_runs(session_id=session.session_id)
        print(f"   Found {len(runs)} runs in session")
    except Exception as e:
        print(f"   Error: {e}")

    print("\n" + "=" * 60)
    print("Example Complete")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
