from __future__ import annotations
import os
import anyio
import logging
from agents.base import ToolAgent
from python_a2a.client import A2AClient

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except (ImportError, Exception):
    # dotenv not available or error loading, skip
    pass
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
        
        # Add core LLM reasoning tool
        async def reason(query: str) -> str:
            """Provides intelligent reasoning and analysis using OpenAI GPT models for complex questions and tasks."""
            return self.handle_message(query)
        
        self.add_tool(reason, "reason")

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

    def handle_message(self, message_input) -> str:
        """Handle message for OpenAI API (string input) or A2A Message object."""
        
        # Handle both string input (for OpenAI API) and Message object (for A2A)
        if isinstance(message_input, str):
            # OpenAI API path
            text_input = message_input
            logger.info(f"[LLM] Received OpenAI message: '{text_input}'")
        else:
            # A2A path (Message object)
            text_input = message_input.content.text
            logger.info(f"[LLM] Received A2A message: '{text_input}'")
        
        # Check if this is a query about local agents/system capabilities
        agent_discovery_keywords = ['agents', 'skills', 'capabilities', 'interact with', 'other agents', 
                                   'available agents', 'what can you do', 'system agents', 'refresh discovery']
        
        if any(keyword in text_input.lower() for keyword in agent_discovery_keywords):
            # This is asking about local agents - use cached startup discovery
            logger.info(f"[LLM] Detected agent discovery query, using cached agent discovery")
            
            # Check if this is a refresh request
            if 'refresh' in text_input.lower():
                logger.info(f"[LLM] Refresh requested, updating discovery cache")
                self.refresh_agent_discovery()
            
            try:
                # Use cached discovered agents from startup
                discovered_agents = self.get_discovered_agents()
                
                agent_info = []
                for agent_data in discovered_agents.values():
                    agent_name = agent_data['name']
                    agent_desc = agent_data['description']
                    skills = agent_data['skills']
                    
                    if skills:
                        skill_list = [f"'{skill['name']}' - {skill['description']}" for skill in skills]
                        agent_info.append(f"**{agent_name}**: {agent_desc}\n  Skills: {', '.join(skill_list)}")
                    else:
                        agent_info.append(f"**{agent_name}**: {agent_desc}\n  Skills: None discovered")
                
                if agent_info:
                    refresh_note = " (just refreshed)" if 'refresh' in text_input.lower() else ""
                    text = f"I can interact with the following agents in this multi-agent system{refresh_note}:\n\n" + "\n\n".join(agent_info)
                    text += f"\n\nThese {len(discovered_agents)} agents work together through the A2A (Agent-to-Agent) protocol to coordinate complex tasks and share capabilities."
                    text += f"\n\nDiscovery status: {'✓ Completed at startup' if self.is_discovery_completed() else '⚠ In progress'}"
                    text += f"\n\n💡 Note: I automatically check for new agents every minute. Say 'refresh discovery' to check immediately."
                else:
                    discovery_status = "completed" if self.is_discovery_completed() else "still in progress"
                    refresh_note = " (just refreshed)" if 'refresh' in text_input.lower() else ""
                    text = f"I don't currently see any other agents registered in the system{refresh_note} (discovery {discovery_status}). No other agents appear to be running at the moment."
                    text += f"\n\n💡 Note: I automatically check for new agents every minute. Say 'refresh discovery' to check immediately."
                    
            except Exception as e:
                logger.warning(f"[LLM] Cached agent discovery failed ({e}), falling back to OpenAI API")
                # Fall back to OpenAI if discovery fails
                text = None
        else:
            # Not an agent discovery query, try OpenAI API first
            text = None
        
        # If we haven't handled the query yet, try OpenAI API
        if text is None:
            try:
                # Check if we have OpenAI API key
                api_key = os.environ.get("OPENAI_API_KEY")
                if api_key:
                    import openai
                    
                    # Set up OpenAI client
                    client = openai.OpenAI(api_key=api_key)
                    
                    # Make API call to OpenAI
                    response = client.chat.completions.create(
                        model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
                        messages=[
                            {"role": "system", "content": "You are a helpful AI assistant. Provide accurate, concise answers to questions."},
                            {"role": "user", "content": text_input}
                        ],
                        temperature=0.7,
                        max_tokens=500
                    )
                    
                    text = response.choices[0].message.content
                    logger.info(f"[LLM] Used OpenAI API for response")
                    
                else:
                    logger.info(f"[LLM] No OpenAI API key found in environment")
                    raise Exception("No OpenAI API key available")
                    
            except Exception as e:
                logger.warning(f"[LLM] OpenAI API failed ({e}), using fallback response")
                text = None
            
            # Check if this is a general conversation or a specific tool request
            if any(keyword in text_input.lower() for keyword in ['quote', 'search', 'calculate', 'math']):
                # This looks like a tool request, use the complex agent logic
                if not hasattr(self, "simple_mode"):
                    self._init_agent()
                if getattr(self, "simple_mode", False):
                    agents = {a.name: a for a in self.discovery_client.discover()}
                    quote_client = A2AClient(agents["Quote Agent"].url)
                    math_client = A2AClient(agents["Math Agent"].url)
                    topic = text_input.strip()
                    qresp = quote_client.send_message(Message(content=TextContent(text=f"quote {topic}"), role=MessageRole.USER))
                    results = [f"{topic} result {i}" for i in range(3)]
                    expr = f"{len(qresp.content.text)}*{len(results)}"
                    mresp = math_client.send_message(Message(content=TextContent(text=f"calc {expr}"), role=MessageRole.USER))
                    # Store interaction in memory using generic storage
                    self.store_data("memory", "llm_agent_history", f"{topic}:{mresp.content.text}")
                    text = f"Quote: {qresp.content.text}\nProduct: {mresp.content.text}"
                else:
                    if not hasattr(self, "executor"):
                        self._init_agent()
                    result = anyio.run(lambda: self.executor.invoke({"input": text_input}))
                    text = result["output"]
            else:
                # This is a general conversation, provide a helpful fallback response
                if text is None:
                    # Provide a more informative fallback when OpenAI API isn't available
                    text = f"I'm the LLM Agent, but I don't have access to OpenAI API to answer general questions like '{text_input}'."
                    text += "\n\nI can help with specific tasks using other agents:"
                    text += "\n- Ask about 'agents' or 'capabilities' to see available agents"
                    text += "\n- Use keywords like 'quote', 'calculate', 'math', or 'search' for specific tasks"
                    text += "\n- Coordinate multi-agent workflows"
                    
                    # Show discovered agents if available
                    discovered_agents = self.get_discovered_agents()
                    if discovered_agents:
                        text += f"\n\nI can coordinate with {len(discovered_agents)} other agents:"
                        for agent_name in discovered_agents.keys():
                            text += f" {agent_name},"
                        text = text.rstrip(",")
                    
                    text += "\n\nFor general questions, please provide an OpenAI API key in the environment."
        
        # Return appropriate response type
        if isinstance(message_input, str):
            # OpenAI API: return string
            return text
        else:
            # A2A: return Message object
            return Message(
                role=MessageRole.AGENT,
                content=TextContent(text=text),
                parent_message_id=message_input.message_id,
                conversation_id=message_input.conversation_id,
            )


def main():
    import sys
    registry = sys.argv[1]
    port = int(sys.argv[2])
    mcp_port = int(sys.argv[3])
    agent = LangGraphToolAgent(port, mcp_port, registry)
    
    # Start all services (A2A, MCP, and OpenAI API)
    threads = agent.start_services()
    
    # Keep the main thread alive
    try:
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        logger.info("Shutting down LLM Agent...")
        return


if __name__ == "__main__":
    main()
