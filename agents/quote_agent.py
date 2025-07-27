from agents.base import ToolAgent
from python_a2a.models import Message, TextContent, MessageRole
import logging

logger = logging.getLogger("quote_agent")

class QuoteAgent(ToolAgent):
    def __init__(self, a2a_port: int, mcp_port: int, registry_url: str):
        super().__init__("Quote Agent", "Provides random quotes", a2a_port, mcp_port, registry_url)
        async def random_quote(topic: str) -> str:
            quotes = [
                "Life is what happens when you're busy making other plans.",
                "To be or not to be, that is the question.",
                "I think, therefore I am."
            ]
            return quotes[0]
        self.add_tool(random_quote, "random_quote")
        self.start_mcp()

    def handle_message(self, message_input) -> str:
        """Handle message for OpenAI API (string input) or A2A Message object."""
        
        # Handle both string input (for OpenAI API) and Message object (for A2A)
        if isinstance(message_input, str):
            # OpenAI API path
            topic = message_input.strip().split(" ", 1)[-1] if " " in message_input else message_input.strip()
            logger.info(f"[QUOTE] Received OpenAI message: '{topic}'")
        else:
            # A2A path (Message object)
            topic = message_input.content.text.strip().split(" ", 1)[-1]
            logger.info(f"[QUOTE] Received A2A message: '{topic}'")
        
        quote = self.call_tool("random_quote", {"topic": topic})
        
        # Store quote using generic storage
        self.store_data("memory", "quote_agent_history", quote)
        
        # Return appropriate response type
        if isinstance(message_input, str):
            # OpenAI API: return string
            return f"Here's a quote about {topic}: {quote}"
        else:
            # A2A: return Message object
            return Message(content=TextContent(text=quote), role=MessageRole.AGENT,
                           parent_message_id=message_input.message_id, conversation_id=message_input.conversation_id)

def main():
    import sys
    registry = sys.argv[1]
    port = int(sys.argv[2])
    mcp_port = int(sys.argv[3])
    agent = QuoteAgent(port, mcp_port, registry)
    
    # Start all services (A2A, MCP, and OpenAI API)
    threads = agent.start_services()
    
    # Keep the main thread alive
    try:
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        logger.info("Shutting down Quote Agent...")
        return

if __name__ == "__main__":
    main()
