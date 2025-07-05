import os
import subprocess
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
    env = dict(**os.environ, PYTHONPATH=".")
    return subprocess.Popen(["python", *cmd], env=env)


def run_workflow():
    procs = []
    try:
        procs.append(start(["registry.py", str(REGISTRY_PORT)]))
        wait(f"http://localhost:{REGISTRY_PORT}/registry/agents")
        print("Registry started")
        procs.append(start(["agents/math_agent.py", f"http://localhost:{REGISTRY_PORT}", str(MATH_PORT), str(MATH_MCP)]))
        wait(f"http://localhost:{MATH_PORT}/a2a")
        print("Math agent started")
        procs.append(start(["agents/quote_agent.py", f"http://localhost:{REGISTRY_PORT}", str(QUOTE_PORT), str(QUOTE_MCP)]))
        wait(f"http://localhost:{QUOTE_PORT}/a2a")
        print("Quote agent started")
        procs.append(start(["agents/search_agent.py", f"http://localhost:{REGISTRY_PORT}", str(SEARCH_PORT), str(SEARCH_MCP)]))
        wait(f"http://localhost:{SEARCH_PORT}/a2a")
        print("Search agent started")
        client = A2AClient(f"http://localhost:{SEARCH_PORT}")
        message = Message(content=TextContent(text="life"), role=MessageRole.USER)
        response = client.send_message(message)
        print("Response:")
        print(response.content.text)
    finally:
        for p in procs:
            p.terminate()


if __name__ == "__main__":
    run_workflow()
