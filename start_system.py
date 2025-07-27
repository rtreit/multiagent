#!/usr/bin/env python3

import subprocess
import time
import sys
import os

def start_agent_system():
    """Start the agent system with proper coordination for startup discovery."""
    
    # Ensure we're in the right directory
    os.chdir(r'c:\Users\randy\Git\multiagent')
    
    python_exe = r'C:\Users\randy\Git\multiagent\.venv\Scripts\python.exe'
    
    print("Starting Multi-Agent System with Startup Discovery...")
    print("=" * 60)
    
    # Start registry first
    print("1. Starting Registry on port 9010...")
    registry_proc = subprocess.Popen([
        python_exe, 'registry.py', '9010'
    ])
    time.sleep(2)  # Give registry time to start
    
    # Start Math agent
    print("2. Starting Math Agent on ports 8010/8011...")
    math_proc = subprocess.Popen([
        python_exe, '-m', 'agents.math_agent', 
        'http://localhost:9010', '8010', '8011'
    ])
    time.sleep(3)  # Give it time to register
    
    # Start Quote agent
    print("3. Starting Quote Agent on ports 8020/8021...")
    quote_proc = subprocess.Popen([
        python_exe, '-m', 'agents.quote_agent',
        'http://localhost:9010', '8020', '8021'
    ])
    time.sleep(3)  # Give it time to register
    
    # Start LLM agent (should discover the other two)
    print("4. Starting LLM Agent on ports 8030/8032...")
    llm_proc = subprocess.Popen([
        python_exe, '-m', 'agents.llm_agent',
        'http://localhost:9010', '8030', '8032'
    ])
    time.sleep(5)  # Give it time to start and perform discovery
    
    print("\n" + "=" * 60)
    print("Agent System Started!")
    print("Registry: http://localhost:9010")
    print("Math Agent A2A: http://localhost:8010, API: http://localhost:9010 (conflict)")  
    print("Quote Agent A2A: http://localhost:8020, API: http://localhost:9020")
    print("LLM Agent A2A: http://localhost:8030, API: http://localhost:9030")
    print("\nTesting startup discovery...")
    
    # Wait a moment for everything to stabilize
    time.sleep(3)
    
    # Test discovery
    try:
        import requests
        response = requests.post(
            "http://localhost:9030/v1/chat/completions",
            headers={"Content-Type": "application/json"},
            json={
                "messages": [
                    {"role": "user", "content": "What agents are available in the system?"}
                ],
                "model": "llm-agent"
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            print("\n🤖 LLM Agent Response:")
            print("-" * 40)
            print(content)
            print("-" * 40)
            
            if "Math Agent" in content or "Quote Agent" in content:
                print("\n✅ SUCCESS: Startup discovery is working!")
                print("   LLM Agent successfully discovered peer agents at startup.")
            else:
                print("\n⚠️  PARTIAL: Discovery needs investigation")
                
        else:
            print(f"\n❌ HTTP Error {response.status_code}: {response.text}")
            
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
    
    print(f"\nProcesses running:")
    print(f"Registry PID: {registry_proc.pid}")
    print(f"Math Agent PID: {math_proc.pid}")
    print(f"Quote Agent PID: {quote_proc.pid}")
    print(f"LLM Agent PID: {llm_proc.pid}")
    print("\nPress Ctrl+C to stop all agents...")
    
    try:
        # Keep running until interrupted
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\nStopping agents...")
        for proc in [llm_proc, quote_proc, math_proc, registry_proc]:
            proc.terminate()
        time.sleep(2)
        for proc in [llm_proc, quote_proc, math_proc, registry_proc]:
            proc.kill()
        print("All agents stopped.")

if __name__ == "__main__":
    start_agent_system()
