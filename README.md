# multiagent

This project demonstrates a minimal multi-agent system using `fastmcp` for tool servers,
`python_a2a` for agent communication, and `langgraph` for orchestration.

Three agents are provided:

- **Math Agent** – exposes a calculator via an MCP server.
- **Quote Agent** – fetches random quotes.
- **Search Agent** – searches the internet and coordinates the other agents using LangGraph.

Agents register with a discovery registry and communicate via the A2A protocol.
Tests launch all agents and verify an end‑to‑end workflow where the Search Agent
uses the other agents to answer a task.
