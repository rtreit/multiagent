# multiagent

This project demonstrates a minimal multi-agent system using **FastMCP** for tool servers,
**python-a2a** for agent communication, and **langgraph** for orchestration.  Real MCP servers
are accessed through `MultiServerMCPClient` from `langchain-mcp-adapters`.  Example connections
include the community memory server, the Brave Search MCP server (requiring the
`BRAVE_API_KEY` environment variable) and additional public servers for searching everything
and manipulating Excel files.

Each agent can also use an OpenAI powered A2A client for reasoning.  The default model is
`gpt-4o` and the API key is read from the `OPENAI_API_KEY` environment variable.  The model
can be changed when launching an agent by passing `--model` to the `python_a2a` CLI or when
calling `AgentManager.create_openai_agent()`.

For example to run an agent with a different model:

```bash
python -m python_a2a.cli openai --api-key $OPENAI_API_KEY --model gpt-3.5-turbo
```

Three agents are provided:

- **Math Agent** – exposes a calculator via an MCP server.
- **Quote Agent** – fetches random quotes.
- **Search Agent** – searches the internet and coordinates the other agents using LangGraph.
- **LangGraph LLM Agent** – example agent that wires an OpenAI LLM into the ToolAgent
  using LangGraph's `create_react_agent`. It can call both local MCP tools and
  any remote tools discovered via `MultiServerMCPClient`.

Agents register with a discovery registry and communicate via the A2A protocol.
Tests launch all agents and verify an end‑to‑end workflow where the Search Agent
uses the other agents to answer a task.

## Architecture

`agents/base.py` defines a `ToolAgent` class that starts both an A2A server and a
FastMCP tool server.  Each subclass registers with `registry.py` so that other
agents can discover it.  Local tools are added to the agent's MCP server using
`self.add_tool()`, while remote tools are reached through `MultiServerMCPClient`.
The `DISABLE_REMOTE_MCP` environment variable prevents connecting to external
servers during testing.

`agents/search_agent.py` demonstrates a small LangGraph workflow.  It requests a
quote from the Quote Agent, performs a Brave search (falling back to a local
search tool if the remote call fails) and finally asks the Math Agent to multiply
the length of the quote by the number of search results.  The combined response
is returned to the user.

## Web interface

A small Flask app (`gui.py`) provides a simple chat UI. Run it alongside the agents
and open `http://localhost:8000` to send messages to any agent. Responses stream
live so you can watch each agent think and interact with MCP tools.
