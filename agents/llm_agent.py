from __future__ import annotations
import os
import anyio
import logging
from agents.base import ToolAgent
from python_a2a.client import A2AClient
try:
    from langchain_openai import ChatOpenAI
    from langchain.agents import AgentExecutor
    from langgraph.prebuilt import create_react_agent
except Exception:  # pragma: no cover - optional dependency
    ChatOpenAI = None
    AgentExecutor = None
    create_react_agent = None
from python_a2a.models import Message, TextContent, MessageRole

logger = logging.getLogger("llm_agent")

class LangGraphToolAgent(ToolAgent):
    """ToolAgent that uses a LangGraph ReAct agent backed by an LLM."""

    def __init__(self, a2a_port: int, mcp_port: int, registry_url: str):
        super().__init__("LLM Agent", "LLM powered agent", a2a_port, mcp_port, registry_url)
        self.start_mcp()

    def _make_llm(self):
        if ChatOpenAI is None or not os.environ.get("OPENAI_API_KEY"):
            raise RuntimeError("OpenAI support not available")
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
        try:
            llm = self._make_llm()
        except Exception as e:
            logger.warning(f"LLM unavailable, falling back to simple mode: {e}")
            self.simple_mode = True
            return
        tools = self._gather_local_tools()
        if self.remote_client:
            tools += anyio.run(self._gather_remote_tools())
        react_agent = create_react_agent(llm=llm, tools=tools)
        self.executor = AgentExecutor(agent=react_agent, tools=tools, verbose=True, max_iterations=6)
        self.simple_mode = False

    def start_mcp(self):
        super().start_mcp()
        self._init_agent()

    def handle_message(self, message: Message) -> Message:
        if not hasattr(self, "simple_mode"):
            self._init_agent()
        if getattr(self, "simple_mode", False):
            agents = {a.name: a for a in self.discovery_client.discover()}
            quote_client = A2AClient(agents["Quote Agent"].url)
            math_client = A2AClient(agents["Math Agent"].url)
            topic = message.content.text.strip()
            qresp = quote_client.send_message(Message(content=TextContent(text=f"quote {topic}"), role=MessageRole.USER))
            results = [f"{topic} result {i}" for i in range(3)]
            expr = f"{len(qresp.content.text)}*{len(results)}"
            mresp = math_client.send_message(Message(content=TextContent(text=f"calc {expr}"), role=MessageRole.USER))
            try:
                self.store_memory("llm_agent_history", f"{topic}:{mresp.content.text}")
            except Exception as e:
                logger.warning(f"Failed to record llm result in memory server: {e}")
            text = f"Quote: {qresp.content.text}\nProduct: {mresp.content.text}"
        else:
            if not hasattr(self, "executor"):
                self._init_agent()
            result = anyio.run(lambda: self.executor.invoke({"input": message.content.text}))
            text = result["output"]
        return Message(
            role=MessageRole.AGENT,
            content=TextContent(text=text),
            parent_message_id=message.message_id,
            conversation_id=message.conversation_id,
        )


def main():
    import sys
    registry = sys.argv[1]
    port = int(sys.argv[2])
    mcp_port = int(sys.argv[3])
    agent = LangGraphToolAgent(port, mcp_port, registry)
    agent.start_a2a(port=port)


if __name__ == "__main__":
    main()
