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


def verify_agent_registration():
    """Verify all agents are registered with the registry"""
    print("\n=== Verifying Agent Registration ===")
    registry_url = f"http://localhost:{REGISTRY_PORT}/registry/agents"
    
    try:
        response = requests.get(registry_url, timeout=5)
        response.raise_for_status()
        agents = response.json()
        
        print(f"Registry contains {len(agents)} agents:")
        for agent in agents:
            print(f"  - {agent['name']}: {agent['url']}")
            # Verify each agent is responding
            try:
                agent_response = requests.get(f"{agent['url']}", timeout=3)
                print(f"    ✓ Agent responding (HTTP {agent_response.status_code})")
            except Exception as e:
                print(f"    ✗ Agent not responding: {e}")
        
        expected_agents = ["Math Agent", "Quote Agent", "Search Agent"]
        registered_names = [agent['name'] for agent in agents]
        
        for expected in expected_agents:
            if expected in registered_names:
                print(f"  ✓ {expected} is registered")
            else:
                print(f"  ✗ {expected} is NOT registered")
                
        return len(agents) >= 3 and all(name in registered_names for name in expected_agents)
        
    except Exception as e:
        print(f"Failed to verify registration: {e}")
        return False


def verify_mcp_servers():
    """Verify all MCP servers are responding"""
    print("\n=== Verifying MCP Servers ===")
    mcp_endpoints = [
        ("Math Agent MCP", f"http://localhost:{MATH_MCP}/mcp/"),
        ("Quote Agent MCP", f"http://localhost:{QUOTE_MCP}/mcp/"),
        ("Search Agent MCP", f"http://localhost:{SEARCH_MCP}/mcp/"),
    ]
    
    all_healthy = True
    for name, url in mcp_endpoints:
        try:
            response = requests.get(url, timeout=3)
            print(f"  ✓ {name}: HTTP {response.status_code}")
        except Exception as e:
            print(f"  ✗ {name}: {e}")
            all_healthy = False
    
    return all_healthy


def test_individual_agents():
    """Test each agent individually to verify functionality"""
    print("\n=== Testing Individual Agents ===")
    
    # Test Math Agent
    print("\n--- Testing Math Agent ---")
    math_client = A2AClient(f"http://localhost:{MATH_PORT}")
    math_msg = Message(content=TextContent(text="calc 5*7"), role=MessageRole.USER)
    math_response = math_client.send_message(math_msg)
    print(f"Math Agent Input: '5*7'")
    print(f"Math Agent Output: '{math_response.content.text}'")
    assert math_response.content.text.strip() == "35", f"Expected 35, got {math_response.content.text}"
    print("  ✓ Math Agent working correctly")
    
    # Test Quote Agent  
    print("\n--- Testing Quote Agent ---")
    quote_client = A2AClient(f"http://localhost:{QUOTE_PORT}")
    quote_msg = Message(content=TextContent(text="quote inspiration"), role=MessageRole.USER)
    quote_response = quote_client.send_message(quote_msg)
    print(f"Quote Agent Input: 'inspiration'")
    print(f"Quote Agent Output: '{quote_response.content.text}'")
    assert len(quote_response.content.text) > 0, "Quote agent should return a quote"
    print("  ✓ Quote Agent working correctly")
    
    # Test Search Agent
    print("\n--- Testing Search Agent ---")
    search_client = A2AClient(f"http://localhost:{SEARCH_PORT}")
    search_msg = Message(content=TextContent(text="test"), role=MessageRole.USER)
    search_response = search_client.send_message(search_msg)
    print(f"Search Agent Input: 'test'")
    print(f"Search Agent Output: '{search_response.content.text}'")
    assert "Quote:" in search_response.content.text and "Product:" in search_response.content.text
    print("  ✓ Search Agent working correctly")


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
        print("\n" + "="*80)
        print("MULTIAGENT E2E TEST - DETAILED VERIFICATION")
        print("="*80)
        
        print("\n=== Starting Registry ===")
        procs.append(start(["registry.py", str(REGISTRY_PORT)]))
        wait(f"http://localhost:{REGISTRY_PORT}/registry/agents")
        print(f"✓ Registry started on port {REGISTRY_PORT}")
        
        print("\n=== Starting Math Agent ===")
        procs.append(start(["agents/math_agent.py", f"http://localhost:{REGISTRY_PORT}", str(MATH_PORT), str(MATH_MCP)]))
        wait(f"http://localhost:{MATH_PORT}/a2a")
        print(f"✓ Math Agent started on port {MATH_PORT}, MCP on port {MATH_MCP}")
        
        print("\n=== Starting Quote Agent ===")
        procs.append(start(["agents/quote_agent.py", f"http://localhost:{REGISTRY_PORT}", str(QUOTE_PORT), str(QUOTE_MCP)]))
        wait(f"http://localhost:{QUOTE_PORT}/a2a")
        print(f"✓ Quote Agent started on port {QUOTE_PORT}, MCP on port {QUOTE_MCP}")
        
        print("\n=== Starting Search Agent ===")
        procs.append(start(["agents/search_agent.py", f"http://localhost:{REGISTRY_PORT}", str(SEARCH_PORT), str(SEARCH_MCP)]))
        wait(f"http://localhost:{SEARCH_PORT}/a2a")
        print(f"✓ Search Agent started on port {SEARCH_PORT}, MCP on port {SEARCH_MCP}")

        # Wait a moment for all agents to register
        time.sleep(3)
        
        # Verify agent registration
        registration_success = verify_agent_registration()
        assert registration_success, "Agent registration verification failed"
        
        # Verify MCP servers
        mcp_success = verify_mcp_servers() 
        assert mcp_success, "MCP server verification failed"
        
        # Test individual agents
        test_individual_agents()

        print("\n" + "="*80)
        print("COMPREHENSIVE WORKFLOW TEST")
        print("="*80)
        print("\n=== Sending comprehensive message to Search Agent ===")
        client = A2AClient(f"http://localhost:{SEARCH_PORT}")
        message = Message(content=TextContent(text="death"), role=MessageRole.USER)
        print(f"Message: '{message.content.text}'")
        response = client.send_message(message)
        print(f"Response received: {response.content.text}")
        
        # Verify response format
        assert "Quote:" in response.content.text, "Response should contain a quote"
        assert "Product:" in response.content.text, "Response should contain a product calculation"
        
        print("\n" + "="*80)
        print("✓ ALL TESTS PASSED - MULTIAGENT SYSTEM FULLY FUNCTIONAL")
        print("="*80)
        
        # Summary of what was verified:
        print("\nVERIFICATION SUMMARY:")
        print("✓ Registry service operational")
        print("✓ All 3 agents registered with registry") 
        print("✓ All A2A endpoints responding")
        print("✓ All MCP servers operational")
        print("✓ Math Agent calculations working")
        print("✓ Quote Agent quotes working") 
        print("✓ Search Agent orchestration working")
        print("✓ Inter-agent communication working")
        print("✓ End-to-end workflow successful")
        
    finally:
        print(f"\n=== Cleaning up {len(procs)} processes ===")
        for i, p in enumerate(procs):
            print(f"Terminating process {i+1}...")
            p.terminate()
        print("Cleanup complete.")
