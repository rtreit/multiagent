import threading
import anyio
import logging
import os
import time
import json
from fastmcp.server.server import FastMCP
from fastmcp.tools.tool import FunctionTool
from fastmcp.client import Client
from langchain_mcp_adapters.client import MultiServerMCPClient
from python_a2a.agent_flow.server.api import A2AServer
from python_a2a.discovery.server import enable_discovery
from python_a2a.server.http import run_server
from python_a2a.models.agent import AgentCard
from python_a2a.models import Message, TextContent, MessageRole
from flask import Flask, request, jsonify, Response

try:
    from .mcp_adapters import default_adapter_registry, MCPAdapterRegistry
except ImportError:
    from agents.mcp_adapters import default_adapter_registry, MCPAdapterRegistry

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("base_agent")

class ToolAgent(A2AServer):
    def __init__(self, name: str, description: str, a2a_port: int, mcp_port: int, registry_url: str, 
                 adapter_registry: MCPAdapterRegistry = None):
        card = AgentCard(name=name, description=description, url=f"http://localhost:{a2a_port}")
        super().__init__(agent_card=card)
        self.name = name
        self.description = description
        self.a2a_port = a2a_port
        self.mcp = FastMCP(name=name)
        self.mcp_port = mcp_port
        self.client = Client(f"http://localhost:{mcp_port}/mcp/")
        self._registry_url = registry_url
        self.adapter_registry = adapter_registry or default_adapter_registry
        
        # Create Flask app for OpenAI-compatible API
        self.flask_app = Flask(f"{name}_api")
        self._setup_openai_endpoints()
        
        if not os.environ.get("DISABLE_REMOTE_MCP"):
            self.remote_client = MultiServerMCPClient(
                {
                    "memory": {
                        "command": "npx",
                        "args": ["-y", "@modelcontextprotocol/server-memory"],
                        "transport": "stdio",
                    },
                    "brave-search": {
                        "command": "npx",
                        "args": ["-y", "brave-search-mcp"],
                        "env": {"BRAVE_API_KEY": os.environ.get("BRAVE_API_KEY", "")},
                        "transport": "stdio",
                    },
                    "everything-search": {
                        "url": "https://mcpservers.org/servers/mamertofabian/mcp-everything-search/mcp",
                        "transport": "streamable_http",
                    },
                    "excel": {
                        "url": "https://mcpservers.org/servers/haris-musa/excel-mcp-server/mcp",
                        "transport": "streamable_http",
                    },
                }
            )
        else:
            self.remote_client = None

    def add_tool(self, fn, name: str):
        logger.info(f"Adding tool: {name}")
        self.mcp.add_tool(FunctionTool.from_function(fn, name=name))

    def start_mcp(self):
        logger.info(f"Starting MCP server on port {self.mcp_port}")
        threading.Thread(target=self.mcp.run, kwargs={"transport": "http", "host": "127.0.0.1", "port": self.mcp_port}, daemon=True).start()

    def start_a2a(self, host: str = "127.0.0.1", port: int = 0):
        logger.info(f"Enabling discovery with registry at {self._registry_url}")
        enable_discovery(self, self._registry_url)
        logger.info(f"Starting A2A server on {host}:{port}")
        run_server(self, host=host, port=port)

    def call_tool(self, name: str, args: dict):
        import time
        start_time = time.time()
        logger.info(f"[BASE] Calling tool: {name} with args: {args}")
        
        async def _call():
            client_start = time.time()
            async with self.client as c:
                client_time = time.time() - client_start
                logger.info(f"[BASE] Client context took {client_time:.2f}s")
                
                tool_call_start = time.time()
                logger.info(f"[BASE] Making async call to tool: {name}")
                result = await c.call_tool(name, args)
                tool_call_time = time.time() - tool_call_start
                logger.info(f"[BASE] Actual tool call took {tool_call_time:.2f}s")
                
                text = result.structured_content.get("result") if result.structured_content else None
                if text is None and result.content:
                    text = result.content[0].text
                logger.info(f"[BASE] Tool {name} returned: {text}")
                return text
        
        anyio_start = time.time()
        result = anyio.run(_call)
        anyio_time = time.time() - anyio_start
        
        total_time = time.time() - start_time
        logger.info(f"[BASE] anyio.run took {anyio_time:.2f}s, total call_tool took {total_time:.2f}s")
        return result

    def call_remote_tool(self, server: str, tool: str, args: dict):
        logger.info(f"Calling remote tool {tool} on {server} with {args}")
        if self.remote_client is None:
            raise RuntimeError("Remote MCP client disabled")
        
        async def _call():
            tools = await self.remote_client.get_tools(server_name=server)
            tool_map = {t.name: t for t in tools}
            if tool not in tool_map:
                raise ValueError(f"Tool {tool} not found on server {server}")
            result = await tool_map[tool].ainvoke(args)
            return result
        
        # Handle both sync and async contexts properly
        try:
            # Try to get the current event loop
            import asyncio
            loop = asyncio.get_running_loop()
            # If we're in an async context, we need to run in a thread
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(anyio.run, _call)
                return future.result()
        except RuntimeError:
            # No running event loop, safe to use anyio.run
            return anyio.run(_call)

    def safe_remote_tool_call(self, server: str, tool: str, args: dict, fallback_result=None):
        """
        Safely call a remote tool with error handling and fallback.
        Returns the result on success, fallback_result on failure.
        This provides a clean interface for optional MCP functionality.
        """
        try:
            return self.call_remote_tool(server, tool, args)
        except Exception as e:
            logger.warning(f"Remote tool call failed ({server}.{tool}): {e}")
            return fallback_result

    def store_data(self, server: str, key: str, data: str) -> bool:
        """
        Generic data storage method that adapts to different MCP server types.
        Returns True if successful, False otherwise.
        
        This method uses the adapter pattern to work with different server implementations
        without hardcoding server-specific logic in the base agent.
        """
        import time
        start_time = time.time()
        logger.debug(f"[BASE] Starting store_data to {server}")
        
        if self.remote_client is None:
            logger.debug(f"Remote MCP client disabled, skipping storage to {server}")
            return False
            
        # Try to get a registered adapter first
        adapter = self.adapter_registry.get_adapter(server)
        logger.debug(f"Looking for adapter for {server}: {'found' if adapter else 'not found'}")
        
        # If no adapter registered, try auto-detection
        if adapter is None:
            logger.debug(f"Attempting auto-detection for {server}")
            adapter = self.adapter_registry.auto_detect_adapter(self, server)
            if adapter:
                logger.info(f"Auto-detected adapter for {server}: {type(adapter).__name__}")
                self.adapter_registry.register_adapter(server, adapter)
            else:
                logger.debug(f"Auto-detection failed for {server}")
        
        # Use adapter if available
        if adapter:
            logger.debug(f"Using adapter {type(adapter).__name__} for {server}")
            result = adapter.store_data(self, key, data)
            if result is not None:
                logger.debug(f"Successfully stored data to {server} using {type(adapter).__name__}")
                return True
            else:
                logger.warning(f"Adapter {type(adapter).__name__} failed to store data to {server}")
        
        # Fallback: try direct tool call (for simple servers)
        logger.debug(f"Trying fallback direct tool call for {server}")
        result = self.safe_remote_tool_call(server, "store", {"key": key, "value": data})
        if result is not None:
            logger.debug(f"Successfully stored data to {server} using direct call")
            total_time = time.time() - start_time
            logger.debug(f"[BASE] store_data total time: {total_time:.2f}s")
            return True
            
        total_time = time.time() - start_time
        logger.debug(f"[BASE] store_data failed after {total_time:.2f}s")
        logger.debug(f"Failed to store data to {server}")
        return False

    def retrieve_data(self, server: str, key: str):
        """
        Generic data retrieval method that adapts to different MCP server types.
        Returns the data on success, None on failure.
        """
        if self.remote_client is None:
            return None
            
        # Try to get a registered adapter first
        adapter = self.adapter_registry.get_adapter(server)
        
        # If no adapter registered, try auto-detection
        if adapter is None:
            adapter = self.adapter_registry.auto_detect_adapter(self, server)
            if adapter:
                self.adapter_registry.register_adapter(server, adapter)
        
        # Use adapter if available
        if adapter:
            return adapter.retrieve_data(self, key)
        
        # Fallback: try direct tool call
        return self.safe_remote_tool_call(server, "retrieve", {"key": key})

    def _setup_openai_endpoints(self):
        """Setup OpenAI-compatible chat completion endpoints."""
        
        @self.flask_app.route('/v1/chat/completions', methods=['POST'])
        def chat_completions():
            try:
                data = request.json
                messages = data.get('messages', [])
                model = data.get('model', self.name)
                stream = data.get('stream', False)
                
                if not messages:
                    return jsonify({'error': 'No messages provided'}), 400
                
                # Get the last user message
                user_message = None
                for msg in reversed(messages):
                    if msg.get('role') == 'user':
                        user_message = msg.get('content')
                        break
                
                if not user_message:
                    return jsonify({'error': 'No user message found'}), 400
                
                # Process the message through the agent
                response_content = self.handle_message(user_message)
                
                # Format response in OpenAI format
                response = {
                    'id': f'chatcmpl-{int(time.time())}',
                    'object': 'chat.completion',
                    'created': int(time.time()),
                    'model': model,
                    'choices': [{
                        'index': 0,
                        'message': {
                            'role': 'assistant',
                            'content': response_content
                        },
                        'finish_reason': 'stop'
                    }],
                    'usage': {
                        'prompt_tokens': len(user_message.split()),
                        'completion_tokens': len(response_content.split()),
                        'total_tokens': len(user_message.split()) + len(response_content.split())
                    }
                }
                
                if stream:
                    # For streaming, return a simple response for now
                    return Response(
                        f"data: {json.dumps(response)}\n\ndata: [DONE]\n\n",
                        mimetype='text/event-stream'
                    )
                else:
                    return jsonify(response)
                    
            except Exception as e:
                logger.error(f"Error in chat_completions: {e}")
                return jsonify({'error': str(e)}), 500
        
        @self.flask_app.route('/v1/models', methods=['GET'])
        def list_models():
            """List available models."""
            return jsonify({
                'object': 'list',
                'data': [{
                    'id': self.name,
                    'object': 'model',
                    'created': int(time.time()),
                    'owned_by': 'multiagent-system'
                }]
            })
        
        @self.flask_app.route('/health', methods=['GET'])
        def health_check():
            """Health check endpoint."""
            return jsonify({'status': 'healthy', 'agent': self.name})

    def run_openai_api(self, host='127.0.0.1', port=None):
        """Run the OpenAI-compatible API server."""
        if port is None:
            port = self.a2a_port + 1000  # Use different port for API
        
        logger.info(f"Starting OpenAI-compatible API for {self.name} on {host}:{port}")
        self.flask_app.run(host=host, port=port, debug=False, threaded=True)

    def start_services(self):
        """Start both A2A and OpenAI API services."""
        import threading
        
        # Start A2A server in a thread
        a2a_thread = threading.Thread(target=lambda: self.start_a2a(host="127.0.0.1", port=self.a2a_port), daemon=True)
        a2a_thread.start()
        
        # Start MCP server in a thread
        mcp_thread = threading.Thread(target=self.start_mcp, daemon=True)
        mcp_thread.start()
        
        # Start OpenAI API server in a thread
        api_port = self.a2a_port + 1000
        api_thread = threading.Thread(target=lambda: self.run_openai_api(port=api_port), daemon=True)
        api_thread.start()
        
        logger.info(f"Started {self.name} with A2A on port {self.a2a_port}, MCP on port {self.mcp_port}, OpenAI API on port {api_port}")
        
        return a2a_thread, mcp_thread, api_thread

    def handle_message(self, message: str) -> str:
        """Handle a message - to be overridden by subclasses."""
        return f"Agent {self.name} received: {message}"
