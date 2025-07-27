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

class AgentSkill:
    """Represents a skill/tool available to an agent for A2A discovery."""
    def __init__(self, name: str, description: str, skill_type: str = "function"):
        self.name = name
        self.description = description
        self.type = skill_type
    
    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "type": self.type
        }

class ToolAgent(A2AServer):
    def __init__(self, name: str, description: str, a2a_port: int, mcp_port: int, registry_url: str, 
                 adapter_registry: MCPAdapterRegistry = None):
        # Initialize with empty skills list - will be populated as tools are added
        card = AgentCard(name=name, description=description, url=f"http://localhost:{a2a_port}", skills=[])
        super().__init__(agent_card=card)
        self.name = name
        self.description = description
        self.a2a_port = a2a_port
        self.mcp = FastMCP(name=name)
        self.mcp_port = mcp_port
        self.client = Client(f"http://localhost:{mcp_port}/mcp/")
        self._registry_url = registry_url
        self.adapter_registry = adapter_registry or default_adapter_registry
        
        # Track tools for A2A agent card skills
        self._tools = {}
        
        # Agent discovery cache - populated at startup and updated periodically
        self._discovered_agents = {}
        self._discovery_completed = False
        self._discovery_thread = None
        self._stop_discovery = False
        
        # Create Flask app for OpenAI-compatible API
        self.flask_app = Flask(f"{name}_api")
        self._setup_cors()
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
        
        # Track tool for A2A agent card skills
        tool_info = {
            "name": name,
            "description": fn.__doc__ or f"Tool: {name}",
            "type": "function"
        }
        self._tools[name] = tool_info
        
        # Update agent card skills
        self._update_agent_card_skills()
    
    def _update_agent_card_skills(self):
        """Update the A2A agent card with current tool list."""
        skills = [
            AgentSkill(
                name=tool_info["name"],
                description=tool_info["description"],
                skill_type=tool_info["type"]
            )
            for tool_info in self._tools.values()
        ]
        
        # Update the agent card skills
        self.agent_card.skills = skills
        logger.info(f"Updated agent card skills: {[skill.name for skill in skills]}")

    def start_mcp(self):
        logger.info(f"Starting MCP server on port {self.mcp_port}")
        threading.Thread(target=self.mcp.run, kwargs={"transport": "http", "host": "127.0.0.1", "port": self.mcp_port}, daemon=True).start()

    def start_a2a(self, host: str = "127.0.0.1", port: int = 0):
        """Start the A2A server without blocking on discovery."""

        logger.info(f"Enabling discovery with registry at {self._registry_url}")
        enable_discovery(self, self._registry_url)

        # Run startup discovery in the background so the server can start quickly
        discovery_thread = threading.Thread(
            target=self._perform_startup_discovery,
            daemon=True,
            name=f"{self.name}_startup_discovery",
        )
        discovery_thread.start()

        # Start periodic discovery in background
        self._start_periodic_discovery()

        logger.info(f"Starting A2A server on {host}:{port}")
        run_server(self, host=host, port=port)

    def _perform_startup_discovery(self):
        """Discover and cache other agents at startup with retries."""
        try:
            from python_a2a.discovery.client import DiscoveryClient
            discovery_client = DiscoveryClient(self.agent_card)
            discovery_client.add_registry(self._registry_url)
            
            # Wait for registry and other agents to start with retries
            max_attempts = 8  # Increased from 5 to 8
            wait_time = 5     # Increased from 3 to 5 seconds
            
            for attempt in range(max_attempts):
                logger.info(f"[STARTUP DISCOVERY] Attempt {attempt + 1}/{max_attempts}")
                
                try:
                    agents = discovery_client.discover()
                    other_agents = [agent for agent in agents if agent.name != self.name]
                    
                    logger.info(f"[STARTUP DISCOVERY] Found {len(agents)} total agents, {len(other_agents)} peers")
                    
                    # Only proceed if we found other agents
                    if other_agents:
                        # Process discovered agents
                        for agent in other_agents:
                            # Extract skills information
                            skills = []
                            if hasattr(agent, 'skills') and agent.skills:
                                for skill in agent.skills:
                                    if hasattr(skill, 'name') and hasattr(skill, 'description'):
                                        skills.append({
                                            'name': skill.name,
                                            'description': skill.description,
                                            'type': getattr(skill, 'type', 'function')
                                        })
                                    elif isinstance(skill, dict):
                                        skills.append({
                                            'name': skill.get('name', 'unknown'),
                                            'description': skill.get('description', 'no description'),
                                            'type': skill.get('type', 'function')
                                        })
                            
                            self._discovered_agents[agent.name] = {
                                'name': agent.name,
                                'description': agent.description,
                                'url': agent.url,
                                'skills': skills
                            }
                            
                            logger.info(f"[STARTUP DISCOVERY] Cached {agent.name}: {len(skills)} skills")
                        
                        self._discovery_completed = True
                        logger.info(f"[STARTUP DISCOVERY] Completed - cached {len(self._discovered_agents)} peer agents")
                        return
                        
                    else:
                        logger.info(f"[STARTUP DISCOVERY] No peers found yet, waiting {wait_time}s before retry...")
                        import time
                        time.sleep(wait_time)
                        
                except Exception as e:
                    logger.warning(f"[STARTUP DISCOVERY] Attempt {attempt + 1} failed: {e}")
                    if attempt < max_attempts - 1:
                        import time
                        time.sleep(wait_time)
            
            # Mark as completed even if we didn't find agents
            self._discovery_completed = True
            logger.warning(f"[STARTUP DISCOVERY] Completed with retries - cached {len(self._discovered_agents)} peer agents")
            
        except Exception as e:
            logger.warning(f"[STARTUP DISCOVERY] Failed: {e}")
            self._discovery_completed = False

    def get_discovered_agents(self):
        """Get the cached discovered agents from startup."""
        return self._discovered_agents.copy()

    def is_discovery_completed(self):
        """Check if startup discovery has completed."""
        return self._discovery_completed

    def refresh_agent_discovery(self):
        """Manually refresh the agent discovery cache."""
        logger.info("Refreshing agent discovery cache...")
        self._perform_startup_discovery()

    def _start_periodic_discovery(self):
        """Start periodic discovery in a background thread."""
        if self._discovery_thread is None:
            import threading
            self._discovery_thread = threading.Thread(
                target=self._periodic_discovery_worker, 
                daemon=True, 
                name=f"{self.name}_discovery"
            )
            self._discovery_thread.start()
            logger.info(f"[PERIODIC DISCOVERY] Started background discovery thread")

    def _periodic_discovery_worker(self):
        """Background worker that periodically checks for new agents."""
        import time
        
        discovery_interval = 60  # Check every 60 seconds
        
        while not self._stop_discovery:
            try:
                time.sleep(discovery_interval)
                if self._stop_discovery:
                    break
                    
                logger.debug(f"[PERIODIC DISCOVERY] Checking for agent changes...")
                old_agent_names = set(self._discovered_agents.keys())
                
                # Perform discovery
                self._perform_discovery_update()
                
                new_agent_names = set(self._discovered_agents.keys())
                
                # Check for new agents
                added_agents = new_agent_names - old_agent_names
                removed_agents = old_agent_names - new_agent_names
                
                if added_agents:
                    logger.info(f"[PERIODIC DISCOVERY] New agents discovered: {', '.join(added_agents)}")
                    
                if removed_agents:
                    logger.info(f"[PERIODIC DISCOVERY] Agents went offline: {', '.join(removed_agents)}")
                    
                if not added_agents and not removed_agents:
                    logger.debug(f"[PERIODIC DISCOVERY] No changes detected ({len(new_agent_names)} agents)")
                    
            except Exception as e:
                logger.warning(f"[PERIODIC DISCOVERY] Error during periodic check: {e}")
                
        logger.info(f"[PERIODIC DISCOVERY] Background discovery thread stopped")

    def _perform_discovery_update(self):
        """Perform a discovery update without the startup retries."""
        try:
            from python_a2a.discovery.client import DiscoveryClient
            discovery_client = DiscoveryClient(self.agent_card)
            discovery_client.add_registry(self._registry_url)
            
            agents = discovery_client.discover()
            other_agents = [agent for agent in agents if agent.name != self.name]
            
            # Clear existing cache
            self._discovered_agents.clear()
            
            # Process discovered agents
            for agent in other_agents:
                # Extract skills information
                skills = []
                if hasattr(agent, 'skills') and agent.skills:
                    for skill in agent.skills:
                        if hasattr(skill, 'name') and hasattr(skill, 'description'):
                            skills.append({
                                'name': skill.name,
                                'description': skill.description,
                                'type': getattr(skill, 'type', 'function')
                            })
                        elif isinstance(skill, dict):
                            skills.append({
                                'name': skill.get('name', 'unknown'),
                                'description': skill.get('description', 'no description'),
                                'type': skill.get('type', 'function')
                            })
                
                self._discovered_agents[agent.name] = {
                    'name': agent.name,
                    'description': agent.description,
                    'url': agent.url,
                    'skills': skills
                }
            
            # Update discovery status
            if not self._discovery_completed:
                self._discovery_completed = True
                
        except Exception as e:
            logger.warning(f"[PERIODIC DISCOVERY] Update failed: {e}")

    def stop_discovery(self):
        """Stop the periodic discovery thread."""
        self._stop_discovery = True
        if self._discovery_thread and self._discovery_thread.is_alive():
            self._discovery_thread.join(timeout=5)
            logger.info(f"[PERIODIC DISCOVERY] Stopped")

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

    def _setup_cors(self):
        """Setup CORS headers for the Flask app."""
        @self.flask_app.after_request
        def after_request(response):
            # Allow requests from any origin for development
            # Use 'set' instead of 'add' to avoid duplicate headers
            response.headers['Access-Control-Allow-Origin'] = '*'
            response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
            response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
            return response
            
        # Handle preflight OPTIONS requests
        @self.flask_app.route('/v1/chat/completions', methods=['OPTIONS'])
        @self.flask_app.route('/v1/models', methods=['OPTIONS'])
        @self.flask_app.route('/health', methods=['OPTIONS'])
        def handle_preflight():
            response = jsonify({'status': 'ok'})
            # Headers are already set by after_request, no need to set them again
            return response

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

    def shutdown(self):
        """Clean shutdown of the agent, stopping all background threads."""
        logger.info(f"Shutting down {self.name}...")
        self.stop_discovery()
        logger.info(f"{self.name} shutdown complete")

    def handle_message(self, message: str) -> str:
        """Handle a message - to be overridden by subclasses."""
        return f"Agent {self.name} received: {message}"
