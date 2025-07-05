from agents.base import ToolAgent
from python_a2a.models import Message, TextContent, MessageRole

class MathAgent(ToolAgent):
    def __init__(self, a2a_port: int, mcp_port: int, registry_url: str):
        super().__init__("Math Agent", "Performs math operations", a2a_port, mcp_port, registry_url)
        async def calculate(expression: str) -> str:
            return str(eval(expression, {"__builtins__": {}}))
        self.add_tool(calculate, "calculate")
        self.start_mcp()

    def handle_message(self, message: Message) -> Message:
        expr = message.content.text.strip().split(" ", 1)[-1]
        result = self.call_tool("calculate", {"expression": expr})
        return Message(content=TextContent(text=result), role=MessageRole.AGENT,
                       parent_message_id=message.message_id, conversation_id=message.conversation_id)

def main():
    import sys
    registry = sys.argv[1]
    port = int(sys.argv[2])
    mcp_port = int(sys.argv[3])
    agent = MathAgent(port, mcp_port, registry)
    agent.start_a2a(port=port)

if __name__ == "__main__":
    main()
