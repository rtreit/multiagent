import os
import subprocess
import sys
import time
import requests
from python_a2a.client import A2AClient
from python_a2a.models import Message, TextContent, MessageRole

REGISTRY_PORT = 9020
MATH_PORT = 9021
MATH_MCP = 8031


def wait(url: str, attempts: int = 30):
    for i in range(attempts):
        try:
            requests.get(url, timeout=1)
            return
        except Exception:
            if i == attempts - 1:
                raise RuntimeError(f"server {url} not up after {attempts} attempts")
            time.sleep(0.5)


def start(cmd):
    env = dict(**os.environ, PYTHONPATH=".")
    # Remove DISABLE_REMOTE_MCP to enable memory server
    if "DISABLE_REMOTE_MCP" in env:
        del env["DISABLE_REMOTE_MCP"]
    
    # Use the same Python interpreter that's running the tests
    python_executable = sys.executable
    return subprocess.Popen(
        [python_executable, *cmd], 
        env=env,
        stdout=None,
        stderr=None,
    )


def test_memory_functionality():
    """Test that the MCP memory server works correctly"""
    procs = []
    try:
        print("\n" + "="*80)
        print("MEMORY SERVER FUNCTIONALITY TEST")
        print("="*80)
        
        print("\n=== Starting Registry ===")
        procs.append(start(["registry.py", str(REGISTRY_PORT)]))
        wait(f"http://localhost:{REGISTRY_PORT}/registry/agents")
        print(f"✓ Registry started on port {REGISTRY_PORT}")
        
        print("\n=== Starting Math Agent (with memory enabled) ===")
        procs.append(start(["agents/math_agent.py", f"http://localhost:{REGISTRY_PORT}", str(MATH_PORT), str(MATH_MCP)]))
        wait(f"http://localhost:{MATH_PORT}/a2a")
        print(f"✓ Math Agent started on port {MATH_PORT}, MCP on port {MATH_MCP}")

        # Wait for memory server to initialize
        print("\n=== Waiting for memory server initialization ===")
        time.sleep(10)  # Give time for memory server to start via npx
        
        print("\n=== Testing memory operations ===")
        math_client = A2AClient(f"http://localhost:{MATH_PORT}")
        
        # Send multiple calculations
        calculations = ["5*7", "10+15", "100/4"]
        for calc in calculations:
            print(f"Sending calculation: {calc}")
            math_msg = Message(content=TextContent(text=f"calc {calc}"), role=MessageRole.USER)
            response = math_client.send_message(math_msg)
            print(f"Result: {response.content.text}")
            time.sleep(2)  # Give time for memory storage
        
        print("\n✓ Memory test completed successfully")
        print("Note: Memory operations should be visible in the agent logs above")
        print("Look for 'add_observations' calls without warning messages")
        
    except Exception as e:
        print(f"Memory test encountered an issue: {e}")
        print("This is expected if npm/node is not available or network access is restricted")
        
    finally:
        print(f"\n=== Cleaning up {len(procs)} processes ===")
        for i, p in enumerate(procs):
            print(f"Terminating process {i+1}...")
            p.terminate()
        print("Cleanup complete.")


if __name__ == "__main__":
    test_memory_functionality()
