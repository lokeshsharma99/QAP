"""Data Agent Entry Point."""
import asyncio

from agents.data_agent.agent import data_agent

if __name__ == "__main__":
    asyncio.run(data_agent.aprint())
