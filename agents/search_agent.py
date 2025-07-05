from agents.base import ToolAgent
from python_a2a.models import Message, TextContent, MessageRole
from python_a2a.client import A2AClient
# dummy search
from typing import TypedDict
import logging

from langgraph.graph import StateGraph, START, END

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("search_agent")

class WorkflowState(TypedDict):
    topic: str
    quote: str | None
    result_count: int | None
    product: str | None

class SearchAgent(ToolAgent):
    def __init__(self, a2a_port: int, mcp_port: int, registry_url: str):
        super().__init__("Search Agent", "Searches the web and coordinates others", a2a_port, mcp_port, registry_url)
        async def search(query: str) -> list:
            return [f"{query} result {i}" for i in range(3)]
        self.add_tool(search, "search")
        self.start_mcp()

    def handle_message(self, message: Message) -> Message:
        topic = message.content.text.strip()
        logger.info(f"Received message: '{topic}'")
        
        logger.info("Discovering available agents...")
        agents = {a.name: a for a in self.discovery_client.discover()}
        logger.info(f"Found agents: {', '.join(agents.keys())}")
        
        quote_client = A2AClient(agents["Quote Agent"].url)
        math_client = A2AClient(agents["Math Agent"].url)

        def fetch_quote(state: WorkflowState):
            logger.info(f"Fetching quote for topic: {state['topic']}")
            resp = quote_client.send_message(Message(content=TextContent(text=f"quote {state['topic']}"), role=MessageRole.USER))
            logger.info(f"Received quote: {resp.content.text}")
            return {"quote": resp.content.text}

        def search_web(state: WorkflowState):
            logger.info(f"Searching web for: {state['topic']}")
            try:
                result = self.call_remote_tool(
                    "brave-search",
                    "brave_web_search",
                    {"query": state["topic"], "count": 3},
                )
                result_count = result.count("Title:") if isinstance(result, str) else 0
            except Exception as e:
                logger.warning(f"Remote search failed: {e}, falling back to local search")
                results = self.call_tool("search", {"query": state["topic"]})
                result_count = len(results) if results else 0
            logger.info(f"Found {result_count} results")
            return {"result_count": result_count}

        def multiply(state: WorkflowState):
            expr = f"{len(state['quote'])}*{state['result_count']}"
            logger.info(f"Calculating: {expr}")
            resp = math_client.send_message(Message(content=TextContent(text=f"calc {expr}"), role=MessageRole.USER))
            logger.info(f"Result: {resp.content.text}")
            product = resp.content.text
            try:
                self.call_remote_tool(
                    "memory",
                    "add_observations",
                    {
                        "observations": [
                            {"entityName": "search_agent_history", "contents": [f"{topic}:{product}"]}
                        ]
                    },
                )
            except Exception as e:
                logger.warning(f"Failed to record search result in memory server: {e}")
            return {"product": product}

        graph = StateGraph(WorkflowState)
        graph.add_node("quote", fetch_quote)
        graph.add_node("search", search_web)
        graph.add_node("math", multiply)
        graph.add_edge(START, "quote")
        graph.add_edge("quote", "search")
        graph.add_edge("search", "math")
        graph.add_edge("math", END)
        app = graph.compile()
        final = app.invoke({"topic": topic})
        text = f"Quote: {final['quote']}\nProduct: {final['product']}"
        return Message(content=TextContent(text=text), role=MessageRole.AGENT,
                       parent_message_id=message.message_id, conversation_id=message.conversation_id)

def main():
    import sys
    registry = sys.argv[1]
    port = int(sys.argv[2])
    mcp_port = int(sys.argv[3])
    logger.info(f"Starting Search Agent with registry: {registry}, port: {port}, mcp_port: {mcp_port}")
    agent = SearchAgent(port, mcp_port, registry)
    logger.info(f"Starting A2A server on port {port}")
    agent.start_a2a(port=port)

if __name__ == "__main__":
    main()
