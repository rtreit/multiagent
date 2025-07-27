# Multiagent Reference Implementation

A clean, production-ready reference implementation of a multi-agent system using **FastMCP** for tool servers, **python-a2a** for agent communication, and **OpenAI-compatible APIs** for high-performance interactions. This project demonstrates best practices for building scalable, MCP-compatible agent architectures with industry-standard interfaces.

## 🚀 Performance Highlights

- **< 1 second response times** with OpenAI-compatible API endpoints
- **12+ second improvement** over legacy A2A protocol for GUI interactions
- **Industry-standard interfaces** compatible with any OpenAI client
- **Dual-protocol support** for both A2A and OpenAI APIs

## Key Features

🏗️ **Clean Architecture**
- Generic MCP adapter pattern supporting any compatible MCP server
- Auto-detection of server capabilities with graceful fallbacks
- Clean separation between agent logic and MCP integration

🔧 **Dual API Support**
- **OpenAI-compatible endpoints** (`/v1/chat/completions`, `/v1/models`, `/health`)
- **A2A protocol** for inter-agent communication and orchestration
- **High-performance GUI** using standard HTTP requests
- **Legacy GUI support** for A2A testing scenarios

🤖 **Multiple Agent Types**
- **Math Agent**: Performs mathematical calculations with OpenAI API
- **Quote Agent**: Generates inspirational quotes
- **Search Agent**: Orchestrates complex workflows using LangGraph
- **LLM Agent**: OpenAI-powered reasoning with tool access

🌐 **Network Communication**
- OpenAI-compatible REST APIs for external clients
- A2A (Agent-to-Agent) protocol for internal communication
- Service registry for automatic agent discovery
- HTTP-based endpoints with JSON messaging

🧠 **Memory & State**
- Optional MCP memory server integration for persistent storage
- Knowledge graph pattern support with automatic entity management
- Graceful degradation when memory services are unavailable

## Architecture Overview

### Core Components

**Base Agent (`agents/base.py`)**
- `ToolAgent` class providing MCP server, A2A, and OpenAI API endpoints
- Generic `store_data()` and `retrieve_data()` methods for any MCP server
- OpenAI-compatible `/v1/chat/completions` endpoint implementation
- Automatic tool registration and discovery capabilities
- Thread-safe async operation handling

**OpenAI API Integration**
- Standard chat completions format: `{"model": "Agent Name", "messages": [...]}`
- Health check endpoints for monitoring: `/health`
- Model listing endpoint: `/v1/models`
- Streaming support for real-time responses
- Compatible with any OpenAI client library

**High-Performance GUI (`gui.py`)**
- Uses standard HTTP requests instead of A2A protocol overhead
- Real-time agent health monitoring
- <1 second response times vs 12+ seconds with legacy GUI
- Clean, responsive web interface with timing displays

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
[OpenAI Client] → [Agent OpenAI API] → [Agent Logic] → [MCP Tools]
                                                     → [A2A Protocol] → [Other Agents]
                                                     → [Memory/External Services]
```

**Dual Protocol Architecture:**
- **External Clients**: Use OpenAI-compatible APIs for high performance
- **Internal Communication**: Use A2A protocol for agent coordination
- **Best of Both**: Standard interfaces + specialized agent communication

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

**Quick Start (Recommended):**
```bash
# Start all services with high-performance GUI
.\start_system.ps1

# Access high-performance GUI at http://localhost:8080
# Individual OpenAI APIs available at http://localhost:10011-10014
```

**Legacy Mode (for A2A testing):**
```bash
# Start with legacy A2A GUI (slower)
.\start_system.ps1 -UseOldGUI

# Access legacy GUI at http://localhost:8000
```

**Test Individual Agents:**
```bash
# Test with comprehensive test suite
pytest tests/test_e2e.py -v

# Or start individual services manually
python registry.py
python -m agents.math_agent http://localhost:9010 9011 8021
```

**OpenAI API Examples:**
```bash
# Test math calculation via OpenAI API
curl -X POST http://localhost:10011/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"Math Agent","messages":[{"role":"user","content":"Calculate 15 * 7"}]}'

# Response: {"choices":[{"message":{"content":"The result of 15 * 7 is 105"}}]}
```

## Service Endpoints

### OpenAI-Compatible APIs (High Performance)
- **Math Agent**: http://localhost:10011/v1/chat/completions
- **Quote Agent**: http://localhost:10012/v1/chat/completions  
- **Search Agent**: http://localhost:10013/v1/chat/completions
- **LLM Agent**: http://localhost:10014/v1/chat/completions

### A2A Protocol Endpoints (Internal Communication)
- **Registry**: http://localhost:9010
- **Math Agent**: http://localhost:9011/a2a
- **Quote Agent**: http://localhost:9012/a2a
- **Search Agent**: http://localhost:9013/a2a
- **LLM Agent**: http://localhost:9014/a2a

### User Interfaces
- **High-Performance GUI**: http://localhost:8080 (<1s response times)
- **Legacy GUI**: http://localhost:8000 (12+s response times, use `-UseOldGUI` flag)

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
