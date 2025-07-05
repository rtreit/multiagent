import os
import subprocess
import sys
import time
import requests
from python_a2a.client import A2AClient
from python_a2a.models import Message, TextContent, MessageRole

REGISTRY_PORT = 9010
MATH_PORT = 9011
MATH_MCP = 8021
QUOTE_PORT = 9012
QUOTE_MCP = 8022
SEARCH_PORT = 9013
SEARCH_MCP = 8023


def wait(url: str, attempts: int = 30):
    for _ in range(attempts):
        try:
            requests.get(url, timeout=1)
            return
        except Exception:
            time.sleep(0.5)
    raise RuntimeError(f"server {url} not up")


def start(cmd):
    env = dict(**os.environ, PYTHONPATH=".", DISABLE_REMOTE_MCP="1")
    # Use the same Python interpreter that's running the tests
    python_executable = sys.executable
    # Capture stdout and stderr but don't redirect to PIPE to avoid blocking
    return subprocess.Popen(
        [python_executable, *cmd], 
        env=env,
        stdout=None,  # Use None to show output in console
        stderr=None,  # Use None to show output in console
    )


def test_workflow():
    procs = []
    try:
        print("\n=== Starting Registry ===")
        procs.append(start(["registry.py", str(REGISTRY_PORT)]))
        wait(f"http://localhost:{REGISTRY_PORT}/registry/agents")
        print(f"Registry started on port {REGISTRY_PORT}")
        
        print("\n=== Starting Math Agent ===")
        procs.append(start(["agents/math_agent.py", f"http://localhost:{REGISTRY_PORT}", str(MATH_PORT), str(MATH_MCP)]))
        wait(f"http://localhost:{MATH_PORT}/a2a")
        print(f"Math Agent started on port {MATH_PORT}, MCP on port {MATH_MCP}")
        
        print("\n=== Starting Quote Agent ===")
        procs.append(start(["agents/quote_agent.py", f"http://localhost:{REGISTRY_PORT}", str(QUOTE_PORT), str(QUOTE_MCP)]))
        wait(f"http://localhost:{QUOTE_PORT}/a2a")
        print(f"Quote Agent started on port {QUOTE_PORT}, MCP on port {QUOTE_MCP}")
        
        print("\n=== Starting Search Agent ===")
        procs.append(start(["agents/search_agent.py", f"http://localhost:{REGISTRY_PORT}", str(SEARCH_PORT), str(SEARCH_MCP)]))
        wait(f"http://localhost:{SEARCH_PORT}/a2a")
        print(f"Search Agent started on port {SEARCH_PORT}, MCP on port {SEARCH_MCP}")

        print("\n=== Sending message to Search Agent ===")
        client = A2AClient(f"http://localhost:{SEARCH_PORT}")
        message = Message(content=TextContent(text="life"), role=MessageRole.USER)
        print(f"Message: '{message.content.text}'")
        response = client.send_message(message)
        print(f"Response received: {response.content.text}")
        assert "Quote:" in response.content.text
        assert "Product:" in response.content.text
    finally:
        for p in procs:
            p.terminate()
