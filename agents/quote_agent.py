from agents.base import ToolAgent
from python_a2a.models import Message, TextContent, MessageRole

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

    def handle_message(self, message: Message) -> Message:
        topic = message.content.text.strip().split(" ", 1)[-1]
        quote = self.call_tool("random_quote", {"topic": topic})
        return Message(content=TextContent(text=quote), role=MessageRole.AGENT,
                       parent_message_id=message.message_id, conversation_id=message.conversation_id)

def main():
    import sys
    registry = sys.argv[1]
    port = int(sys.argv[2])
    mcp_port = int(sys.argv[3])
    agent = QuoteAgent(port, mcp_port, registry)
    agent.start_a2a(port=port)

if __name__ == "__main__":
    main()
