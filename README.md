# Multiagent Reference Implementation

A clean, production-ready reference implementation of a multi-agent system using **FastMCP** for tool servers, **python-a2a** for agent communication, and **LangGraph** for orchestration workflows. This project demonstrates best practices for building scalable, MCP-compatible agent architectures.

## Key Features

🏗️ **Clean Architecture**
- Generic MCP adapter pattern supporting any compatible MCP server
- Auto-detection of server capabilities with graceful fallbacks
- Clean separation between agent logic and MCP integration

🔧 **Tool Integration**
- FastMCP servers expose agent capabilities as standardized tools
- Automatic tool discovery and registration via A2A protocol
- Support for both local tools and remote MCP server connections

🤖 **Multiple Agent Types**
- **Math Agent**: Performs mathematical calculations
- **Quote Agent**: Generates inspirational quotes
- **Search Agent**: Orchestrates complex workflows using LangGraph
- **LLM Agent**: OpenAI-powered reasoning with tool access

🌐 **Network Communication**
- A2A (Agent-to-Agent) protocol for seamless inter-agent communication
- Service registry for automatic agent discovery
- HTTP-based endpoints with JSON messaging

🧠 **Memory & State**
- Optional MCP memory server integration for persistent storage
- Knowledge graph pattern support with automatic entity management
- Graceful degradation when memory services are unavailable

## Architecture Overview

### Core Components

**Base Agent (`agents/base.py`)**
- `ToolAgent` class providing MCP server and A2A communication
- Generic `store_data()` and `retrieve_data()` methods for any MCP server
- Automatic tool registration and discovery capabilities
- Thread-safe async operation handling

**MCP Adapters (`agents/mcp_adapters.py`)**
- `KnowledgeGraphAdapter` for knowledge graph-style memory servers
- `KeyValueAdapter` for simple key-value storage servers
- `MCPAdapterRegistry` with auto-detection capabilities
- Clean abstraction layer for different server types

**Service Registry (`registry.py`)**
- Centralized agent discovery and registration
- Health monitoring with automatic heartbeat management
- RESTful API for agent lookup and status

**Search Orchestration (`agents/search_agent.py`)**
- LangGraph workflow demonstrating agent coordination
- Quote fetching → Web search → Mathematical calculation pipeline
- Fallback mechanisms for robust operation

### Agent Communication Flow

```
[Client Request] → [Target Agent] → [A2A Protocol] → [Other Agents]
                                 → [MCP Tools] → [Memory/External Services]
```

## Quick Start

### 1. Install Dependencies

```bash
pip install -e .
```

### 2. Optional: Set up External Services

```bash
# For OpenAI-powered reasoning (optional)
export OPENAI_API_KEY="your-key-here"

# For Brave Search integration (optional)  
export BRAVE_API_KEY="your-key-here"

# For memory server (optional)
npm install -g @modelcontextprotocol/server-memory
```

### 3. Run the System

**Start all agents with the test suite:**
```bash
pytest tests/test_e2e.py -v
```

**Or run individual agents:**
```bash
# Start registry
python registry.py

# Start agents (in separate terminals)
python -m agents.math_agent http://localhost:9010 9011 8021
python -m agents.quote_agent http://localhost:9010 9012 8022
python -m agents.search_agent http://localhost:9010 9013 8023
```

**Web Interface:**
```bash
python gui.py
# Open http://localhost:8000 for chat interface
```

## Testing

The comprehensive test suite (`tests/test_e2e.py`) verifies:
- ✅ Agent registration and discovery
- ✅ MCP server functionality
- ✅ Inter-agent communication
- ✅ End-to-end workflow execution
- ✅ Memory integration (when available)
- ✅ Graceful error handling

```bash
# Run all tests
pytest tests/ -v

# Run with detailed output
pytest tests/test_e2e.py -v -s
```

## Configuration

### Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `OPENAI_API_KEY` | OpenAI API access for LLM agents | None |
| `BRAVE_API_KEY` | Brave Search API access | None |
| `MEMORY_SERVER_URL` | MCP memory server endpoint | Auto-detect |
| `DISABLE_REMOTE_MCP` | Disable external MCP connections | False |

### MCP Server Integration

The system automatically detects and adapts to different MCP server types:

- **Knowledge Graph Servers**: Automatic entity creation and relationship management
- **Key-Value Stores**: Simple storage with fallback support
- **Document Stores**: Text-based storage and retrieval
- **Custom Servers**: Extensible adapter pattern for new server types

## Extending the System

### Adding New Agents

1. Inherit from `ToolAgent` in `agents/base.py`
2. Implement agent-specific tools with `self.add_tool()`
3. Override `handle_message()` for custom behavior
4. Register with the discovery registry

### Adding MCP Server Support

1. Create a new adapter class in `agents/mcp_adapters.py`
2. Implement `store_data()` and `retrieve_data()` methods
3. Add detection logic to `auto_detect_adapter()`
4. Register the adapter with `MCPAdapterRegistry`

### Custom Workflows

Use LangGraph for complex agent orchestration:

```python
from langgraph import StateGraph, END
from agents.base import ToolAgent

class CustomWorkflowAgent(ToolAgent):
    def create_workflow(self):
        workflow = StateGraph(dict)
        workflow.add_node("step1", self.step1)
        workflow.add_node("step2", self.step2)
        workflow.add_edge("step1", "step2")
        workflow.add_edge("step2", END)
        return workflow.compile()
```

## Production Considerations

- **Security**: Validate all inter-agent communications
- **Monitoring**: Use structured logging for observability
- **Scaling**: Deploy agents across multiple processes/containers
- **Error Handling**: All operations include graceful fallbacks
- **Performance**: Async operations with proper thread management

## Project Structure

```
multiagent/
├── agents/                 # Agent implementations
│   ├── base.py            # Core ToolAgent class with MCP integration
│   ├── mcp_adapters.py    # Generic MCP server adapters
│   ├── math_agent.py      # Mathematical calculation agent
│   ├── quote_agent.py     # Quote generation agent
│   ├── search_agent.py    # LangGraph orchestration agent
│   └── llm_agent.py       # OpenAI-powered reasoning agent
├── tests/                 # Comprehensive test suite
│   └── test_e2e.py        # End-to-end system verification
├── registry.py            # Service discovery and registration
├── gui.py                 # Web interface for agent interaction
├── quick_start.py         # Interactive demonstration and setup guide
└── README.md              # This file
```

## Quick Demo

```bash
# Interactive quick start guide
python quick_start.py

# Or run the comprehensive test suite directly
pytest tests/ -v
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
