#!/usr/bin/env python3
"""
Simple example demonstrating how to use the multiagent system.

This script shows how to:
1. Start agents programmatically
2. Send messages between agents
3. Use the system for real tasks

Run this script to see the system in action!
"""

import os
import sys
import time
import asyncio
import subprocess
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from python_a2a.client import A2AClient
from python_a2a.models import Message, TextContent, MessageRole

# Disable remote MCP for this simple example
os.environ['DISABLE_REMOTE_MCP'] = 'true'

def start_agent(script_name, *args):
    """Start an agent process"""
    env = dict(**os.environ, PYTHONPATH=".")
    python_executable = sys.executable
    
    proc = subprocess.Popen(
        [python_executable, script_name, *map(str, args)],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    return proc

def wait_for_agent(url, max_attempts=30):
    """Wait for an agent to be ready"""
    import requests
    for i in range(max_attempts):
        try:
            response = requests.get(url, timeout=1)
            if response.status_code == 200:
                return True
        except Exception:
            time.sleep(0.5)
    return False

async def main():
    """Main demonstration"""
    print("🚀 Multiagent System Example")
    print("=" * 50)
    
    processes = []
    
    try:
        # Start the registry
        print("\n📋 Starting registry...")
        registry_proc = start_agent("registry.py", "9010")
        processes.append(registry_proc)
        
        if wait_for_agent("http://localhost:9010/registry/agents"):
            print("✅ Registry ready")
        else:
            print("❌ Registry failed to start")
            return
        
        # Start the Math Agent
        print("\n🧮 Starting Math Agent...")
        math_proc = start_agent("agents/math_agent.py", "http://localhost:9010", "9011", "8021")
        processes.append(math_proc)
        
        if wait_for_agent("http://localhost:9011/a2a"):
            print("✅ Math Agent ready")
        else:
            print("❌ Math Agent failed to start")
            return
        
        # Start the Quote Agent
        print("\n💬 Starting Quote Agent...")
        quote_proc = start_agent("agents/quote_agent.py", "http://localhost:9010", "9012", "8022")
        processes.append(quote_proc)
        
        if wait_for_agent("http://localhost:9012/a2a"):
            print("✅ Quote Agent ready")
        else:
            print("❌ Quote Agent failed to start")
            return
        
        # Start the Search Agent
        print("\n🔍 Starting Search Agent...")
        search_proc = start_agent("agents/search_agent.py", "http://localhost:9010", "9013", "8023")
        processes.append(search_proc)
        
        if wait_for_agent("http://localhost:9013/a2a"):
            print("✅ Search Agent ready")
        else:
            print("❌ Search Agent failed to start")
            return
        
        # Give agents time to register
        print("\n⏳ Waiting for agent registration...")
        time.sleep(10)  # Increased wait time
        
        # Verify agents are registered
        import requests
        try:
            registry_response = requests.get("http://localhost:9010/registry/agents", timeout=5)
            agents = registry_response.json()
            print(f"   📋 Found {len(agents)} registered agents")
            for agent_name, agent_url in agents.items():
                print(f"      • {agent_name}: {agent_url}")
        except Exception as e:
            print(f"   ⚠️  Could not verify agent registration: {e}")
        
        # Demonstrate the system
        print("\n🎯 Demonstrating System Capabilities")
        print("-" * 40)
        
        # Test Math Agent
        print("\n🧮 Testing Math Agent:")
        try:
            # First verify the agent is responding
            response = requests.get("http://localhost:9011/a2a", timeout=5)
            if response.status_code != 200:
                print(f"   ❌ Math Agent not responding (HTTP {response.status_code})")
            else:
                math_client = A2AClient("http://localhost:9011")
                math_msg = Message(content=TextContent(text="15 * 8"), role=MessageRole.USER)
                response = math_client.send_message(math_msg)
                print(f"   Input: 15 * 8")
                print(f"   Output: {response.content.text}")
        except Exception as e:
            print(f"   ❌ Math Agent test failed: {e}")
        
        # Test Quote Agent
        print("\n💬 Testing Quote Agent:")
        try:
            response = requests.get("http://localhost:9012/a2a", timeout=5)
            if response.status_code != 200:
                print(f"   ❌ Quote Agent not responding (HTTP {response.status_code})")
            else:
                quote_client = A2AClient("http://localhost:9012")
                quote_msg = Message(content=TextContent(text="motivation"), role=MessageRole.USER)
                response = quote_client.send_message(quote_msg)
                print(f"   Input: motivation")
                print(f"   Output: {response.content.text}")
        except Exception as e:
            print(f"   ❌ Quote Agent test failed: {e}")
        
        # Test Search Agent (orchestration)
        print("\n🔍 Testing Search Agent (Orchestration):")
        try:
            response = requests.get("http://localhost:9013/a2a", timeout=5)
            if response.status_code != 200:
                print(f"   ❌ Search Agent not responding (HTTP {response.status_code})")
            else:
                search_client = A2AClient("http://localhost:9013")
                search_msg = Message(content=TextContent(text="wisdom"), role=MessageRole.USER)
                response = search_client.send_message(search_msg)
                print(f"   Input: wisdom")
                print(f"   Output: {response.content.text}")
        except Exception as e:
            print(f"   ❌ Search Agent test failed: {e}")
        
        print("\n✨ System demonstration complete!")
        print("\n💡 Next steps:")
        print("   • Explore the web UI: python gui.py")
        print("   • Run comprehensive tests: pytest tests/ -v")
        print("   • Add OpenAI integration: export OPENAI_API_KEY=your-key")
        print("   • Add memory server: npm install -g @modelcontextprotocol/server-memory")
        
    except KeyboardInterrupt:
        print("\n⏸️  Demonstration interrupted by user")
    except Exception as e:
        print(f"\n❌ Error during demonstration: {e}")
    finally:
        print(f"\n🧹 Cleaning up {len(processes)} processes...")
        for i, proc in enumerate(processes, 1):
            try:
                proc.terminate()
                proc.wait(timeout=5)
                print(f"   ✅ Process {i} terminated")
            except subprocess.TimeoutExpired:
                proc.kill()
                print(f"   ⚠️  Process {i} killed (timeout)")
            except Exception as e:
                print(f"   ❌ Error terminating process {i}: {e}")
        print("🏁 Cleanup complete!")

if __name__ == "__main__":
    asyncio.run(main())
