# multiagent

This project demonstrates a minimal multi-agent system using **FastMCP** for tool servers,
**python-a2a** for agent communication, and **langgraph** for orchestration. Agents rely on
OpenAI's `gpt-4o` model for reasoning. Real MCP servers are accessed through `MultiServerMCPClient`
from `langchain-mcp-adapters`. Example connections include the community memory server, the
Brave Search MCP server (requiring the `BRAVE_API_KEY` environment variable) and additional
public servers for searching everything and manipulating Excel files.

Three agents are provided:

- **Math Agent** – exposes a calculator via an MCP server.
- **Quote Agent** – fetches random quotes.
- **Search Agent** – searches the internet and coordinates the other agents using LangGraph.

Agents register with a discovery registry and communicate via the A2A protocol.
Tests launch all agents and verify an end‑to‑end workflow where the Search Agent
uses the other agents to answer a task.

## Web interface

A small Flask app (`gui.py`) provides a simple chat UI. Run it alongside the agents
and open `http://localhost:8000` to send messages to any agent. Responses stream
live so you can watch each agent think and interact with MCP tools.
