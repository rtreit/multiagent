import threading
import anyio
from fastmcp.server.server import FastMCP
from fastmcp.tools.tool import FunctionTool
from fastmcp.client import Client
from python_a2a.agent_flow.server.api import A2AServer
from python_a2a.discovery.server import enable_discovery
from python_a2a.server.http import run_server
from python_a2a.models.agent import AgentCard
from python_a2a.models import Message, TextContent, MessageRole

class ToolAgent(A2AServer):
    def __init__(self, name: str, description: str, a2a_port: int, mcp_port: int, registry_url: str):
        card = AgentCard(name=name, description=description, url=f"http://localhost:{a2a_port}")
        super().__init__(agent_card=card)
        self.mcp = FastMCP(name=name)
        self.mcp_port = mcp_port
        self.client = Client(f"http://localhost:{mcp_port}/mcp/")
        self._registry_url = registry_url

    def add_tool(self, fn, name: str):
        self.mcp.add_tool(FunctionTool.from_function(fn, name=name))

    def start_mcp(self):
        threading.Thread(target=self.mcp.run, kwargs={"transport": "http", "host": "127.0.0.1", "port": self.mcp_port}, daemon=True).start()

    def start_a2a(self, host: str = "127.0.0.1", port: int = 0):
        enable_discovery(self, self._registry_url)
        run_server(self, host=host, port=port)

    def call_tool(self, name: str, args: dict):
        async def _call():
            async with self.client as c:
                result = await c.call_tool(name, args)
                text = result.structured_content.get("result") if result.structured_content else None
                if text is None and result.content:
                    text = result.content[0].text
                return text
        return anyio.run(_call)
