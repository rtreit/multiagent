from agents.base import ToolAgent
from python_a2a.models import Message, TextContent, MessageRole
from python_a2a.client import A2AClient
# dummy search
from typing import TypedDict
import logging
import time

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
            """Performs web search and returns a list of search results for the given query."""
            return [f"{query} result {i}" for i in range(3)]
        self.add_tool(search, "search")

    def handle_message(self, message_input) -> str:
        """Handle message for OpenAI API (string input) or A2A Message object."""
        start_time = time.time()
        
        # Handle both string input (for OpenAI API) and Message object (for A2A)
        if isinstance(message_input, str):
            # OpenAI API path
            topic = message_input
            logger.info(f"[SEARCH] Received OpenAI message: '{topic}'")
        else:
            # A2A path (Message object)
            topic = message_input.content.text.strip()
            logger.info(f"[SEARCH] Received A2A message: '{topic}'")
        
        logger.info("Discovering available agents...")
        agents = {a.name: a for a in self.discovery_client.discover()}
        logger.info(f"Found agents: {', '.join(agents.keys())}")
        
        quote_client = A2AClient(agents["Quote Agent"].url)
        math_client = A2AClient(agents["Math Agent"].url)

        def fetch_quote(state: WorkflowState):
            step_start = time.time()
            logger.info(f"[SEARCH] Fetching quote for topic: {state['topic']} at {time.time():.2f}")
            resp = quote_client.send_message(Message(content=TextContent(text=f"quote {state['topic']}"), role=MessageRole.USER))
            step_time = time.time() - step_start
            logger.info(f"[SEARCH] Quote fetch took {step_time:.2f}s - Received: {resp.content.text}")
            return {"quote": resp.content.text}

        def search_web(state: WorkflowState):
            step_start = time.time()
            logger.info(f"[SEARCH] Searching web for: {state['topic']} at {time.time():.2f}")
            try:
                remote_start = time.time()
                # Reduce timeout to avoid long waits
                result = self.call_remote_tool(
                    "brave-search",
                    "brave_web_search",
                    {"query": state["topic"], "count": 3},
                )
                remote_time = time.time() - remote_start
                logger.info(f"[SEARCH] Remote search took {remote_time:.2f}s")
                result_count = result.count("Title:") if isinstance(result, str) else 0
            except Exception as e:
                fallback_start = time.time()
                logger.warning(f"Remote search failed after timeout: {e}, falling back to local search")
                results = self.call_tool("search", {"query": state["topic"]})
                fallback_time = time.time() - fallback_start
                logger.info(f"[SEARCH] Fallback search took {fallback_time:.2f}s")
                result_count = len(results) if results else 0
            
            step_time = time.time() - step_start
            logger.info(f"[SEARCH] Total search step took {step_time:.2f}s - Found {result_count} results")
            return {"result_count": result_count}

        def multiply(state: WorkflowState):
            step_start = time.time()
            expr = f"{len(state['quote'])}*{state['result_count']}"
            logger.info(f"[SEARCH] Calculating: {expr} at {time.time():.2f}")
            resp = math_client.send_message(Message(content=TextContent(text=f"calc {expr}"), role=MessageRole.USER))
            step_time = time.time() - step_start
            logger.info(f"[SEARCH] Math calculation took {step_time:.2f}s - Result: {resp.content.text}")
            product = resp.content.text
            
            # Store result using generic storage
            storage_start = time.time()
            self.store_data("memory", "search_agent_history", f"{topic}:{product}")
            storage_time = time.time() - storage_start
            logger.info(f"[SEARCH] Storage attempt took {storage_time:.2f}s")
            
            return {"product": product}

        workflow_start = time.time()
        graph = StateGraph(WorkflowState)
        graph.add_node("quote", fetch_quote)
        graph.add_node("search", search_web)
        graph.add_node("math", multiply)
        graph.add_edge(START, "quote")
        graph.add_edge("quote", "search")
        graph.add_edge("search", "math")
        graph.add_edge("math", END)
        app = graph.compile()
        
        workflow_execution_start = time.time()
        final = app.invoke({"topic": topic})
        workflow_execution_time = time.time() - workflow_execution_start
        
        total_workflow_time = time.time() - workflow_start
        total_time = time.time() - start_time
        
        logger.info(f"[SEARCH] Workflow execution took {workflow_execution_time:.2f}s")
        logger.info(f"[SEARCH] Total workflow setup+execution took {total_workflow_time:.2f}s")
        logger.info(f"[SEARCH] Total message handling took {total_time:.2f}s")
        
        text = f"Quote: {final['quote']}\nProduct: {final['product']}"
        
        # Return appropriate response type
        if isinstance(message_input, str):
            # OpenAI API: return string
            return f"Search results for '{topic}':\n{text}"
        else:
            # A2A: return Message object
            return Message(content=TextContent(text=text), role=MessageRole.AGENT,
                           parent_message_id=message_input.message_id, conversation_id=message_input.conversation_id)

def main():
    import sys
    registry = sys.argv[1]
    port = int(sys.argv[2])
    mcp_port = int(sys.argv[3])
    logger.info(f"Starting Search Agent with registry: {registry}, port: {port}, mcp_port: {mcp_port}")
    agent = SearchAgent(port, mcp_port, registry)
    
    # Start all services (A2A, MCP, and OpenAI API)
    threads = agent.start_services()
    
    # Keep the main thread alive
    try:
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        logger.info("Shutting down Search Agent...")
        return

if __name__ == "__main__":
    main()
