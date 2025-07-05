from __future__ import annotations
import os
import anyio
import logging
from agents.base import ToolAgent
from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor
from langgraph.prebuilt import create_react_agent
from python_a2a.models import Message, TextContent, MessageRole

logger = logging.getLogger("llm_agent")

class LangGraphToolAgent(ToolAgent):
    """ToolAgent that uses a LangGraph ReAct agent backed by an LLM."""

    def _make_llm(self) -> ChatOpenAI:
        model = os.environ.get("OPENAI_MODEL", "gpt-4o")
        api_key = os.environ.get("OPENAI_API_KEY")
        return ChatOpenAI(model=model, api_key=api_key, streaming=True, temperature=0.2)

    def _gather_local_tools(self):
        from langchain_mcp_adapters.tools import load_mcp_tools
        from langchain_mcp_adapters.sessions import StreamableHttpConnection
        connection: StreamableHttpConnection = {
            "transport": "streamable_http",
            "url": f"http://localhost:{self.mcp_port}/mcp",
        }
        return anyio.run(load_mcp_tools(None, connection=connection))

    async def _gather_remote_tools(self):
        if not self.remote_client:
            return []
        tools = []
        for srv in await self.remote_client.list_servers():
            srv_tools = await self.remote_client.get_tools(server_name=srv)
            tools.extend(srv_tools)
        return tools

    def _init_agent(self):
        llm = self._make_llm()
        tools = self._gather_local_tools()
        if self.remote_client:
            tools += anyio.run(self._gather_remote_tools())
        react_agent = create_react_agent(llm=llm, tools=tools)
        self.executor = AgentExecutor(agent=react_agent, tools=tools, verbose=True, max_iterations=6)

    def start_mcp(self):
        super().start_mcp()
        self._init_agent()

    def handle_message(self, message: Message) -> Message:
        if not hasattr(self, "executor"):
            self._init_agent()
        result = anyio.run(lambda: self.executor.invoke({"input": message.content.text}))
        return Message(
            role=MessageRole.AGENT,
            content=TextContent(text=result["output"]),
            parent_message_id=message.message_id,
            conversation_id=message.conversation_id,
        )
