import threading
import anyio
import logging
import os
from fastmcp.server.server import FastMCP
from fastmcp.tools.tool import FunctionTool
from fastmcp.client import Client
from langchain_mcp_adapters.client import MultiServerMCPClient
from python_a2a.agent_flow.server.api import A2AServer
from python_a2a.discovery.server import enable_discovery
from python_a2a.server.http import run_server
from python_a2a.models.agent import AgentCard
from python_a2a.models import Message, TextContent, MessageRole

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("base_agent")

class ToolAgent(A2AServer):
    def __init__(self, name: str, description: str, a2a_port: int, mcp_port: int, registry_url: str):
        card = AgentCard(name=name, description=description, url=f"http://localhost:{a2a_port}")
        super().__init__(agent_card=card)
        self.mcp = FastMCP(name=name)
        self.mcp_port = mcp_port
        self.client = Client(f"http://localhost:{mcp_port}/mcp/")
        self._registry_url = registry_url
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
        logger.info(f"Calling tool: {name} with args: {args}")
        async def _call():
            async with self.client as c:
                logger.info(f"Making async call to tool: {name}")
                result = await c.call_tool(name, args)
                text = result.structured_content.get("result") if result.structured_content else None
                if text is None and result.content:
                    text = result.content[0].text
                logger.info(f"Tool {name} returned: {text}")
                return text
        return anyio.run(_call)

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
        return anyio.run(_call)
