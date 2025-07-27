from agents.base import ToolAgent
from python_a2a.models import Message, TextContent, MessageRole
import logging

logger = logging.getLogger("math_agent")

class MathAgent(ToolAgent):
    def __init__(self, a2a_port: int, mcp_port: int, registry_url: str):
        super().__init__("Math Agent", "Performs math operations", a2a_port, mcp_port, registry_url)
        async def calculate(expression: str) -> str:
            """Evaluates mathematical expressions and returns the result."""
            return str(eval(expression, {"__builtins__": {}}))
        self.add_tool(calculate, "calculate")

    def handle_message(self, message_input) -> str:
        """Handle message for OpenAI API (string input) or A2A Message object."""
        import time
        start_time = time.time()
        
        # Handle both string input (for OpenAI API) and Message object (for A2A)
        if isinstance(message_input, str):
            # OpenAI API path
            text = message_input
            print(f"[MATH] Received OpenAI message: '{text}'")
        else:
            # A2A path (Message object)
            text = message_input.content.text
            print(f"[MATH] Received A2A message: '{text}'")
        
        # Check if the message contains mathematical content
        math_indicators = ['calculate', 'math', 'compute', 'solve', '+', '-', '*', '/', '=', '(', ')', 
                          'sum', 'product', 'divide', 'multiply', 'square', 'root', 'power', '^']
        
        # Also check if the content contains numbers
        has_numbers = any(char.isdigit() for char in text)
        has_math_keywords = any(indicator in text.lower() for indicator in math_indicators)
        
        if has_numbers and (has_math_keywords or any(op in text for op in ['+', '-', '*', '/', '=', '^', '(', ')'])):
            # This looks like a math request, use the calculate tool
            # Extract math expression
            expr = text.strip().split(" ", 1)[-1] if " " in text else text.strip()
            
            try:
                tool_call_start = time.time()
                result = self.call_tool("calculate", {"expression": expr})
                tool_call_time = time.time() - tool_call_start
                print(f"[MATH] Tool call took {tool_call_time:.2f}s")
                
                # Store result using generic storage (works with any compatible MCP server)
                storage_start = time.time()
                self.store_data("memory", "math_agent_history", f"{expr}={result}")
                storage_time = time.time() - storage_start
                print(f"[MATH] Storage took {storage_time:.2f}s")
                
                # For compatibility with tests expecting a plain numeric result
                response_text = str(result)
            except Exception as e:
                response_text = f"I couldn't calculate that expression. Error: {str(e)}. Please provide a valid mathematical expression."
        else:
            # This is not a math request, provide a helpful response
            response_text = ("Hello! I'm the Math Agent. I can help you with mathematical calculations and expressions. "
                           "Try asking me things like:\n"
                           "- Calculate 2 + 2\n"
                           "- What is 15 * 7?\n" 
                           "- Solve 3^2 + 4^2\n"
                           "- Compute the square root of 144\n"
                           "Just include numbers and mathematical operations in your message!")
        
        total_time = time.time() - start_time
        print(f"[MATH] Total handle_message took {total_time:.2f}s")
        
        # Return appropriate response type
        if isinstance(message_input, str):
            # OpenAI API: return string
            return response_text
        else:
            # A2A: return Message object
            message_create_start = time.time()
            response_msg = Message(content=TextContent(text=response_text), role=MessageRole.AGENT,
                           parent_message_id=message_input.message_id, conversation_id=message_input.conversation_id)
            message_create_time = time.time() - message_create_start
            return response_msg

def main():
    import sys
    registry = sys.argv[1]
    port = int(sys.argv[2])
    mcp_port = int(sys.argv[3])
    agent = MathAgent(port, mcp_port, registry)
    
    # Start all services (A2A, MCP, and OpenAI API)
    threads = agent.start_services()
    
    # Keep the main thread alive
    try:
        for thread in threads:
            thread.join()
    except KeyboardInterrupt:
        print("Shutting down Math Agent...")
        return

if __name__ == "__main__":
    main()
