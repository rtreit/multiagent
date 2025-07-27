#!/usr/bin/env python3
"""
Test script to demonstrate periodic agent discovery.
Starts agents sequentially and shows how they discover each other.
"""

import subprocess
import time
import os
import requests
import json

def test_periodic_discovery():
    """Test periodic discovery by starting agents at different times."""
    print("🧪 Testing Periodic Agent Discovery...")
    print("=" * 60)
    
    # Change to project directory
    os.chdir(r'c:\Users\randy\Git\multiagent')
    
    processes = []
    
    try:
        # Start registry
        print("1. Starting Registry...")
        registry_proc = subprocess.Popen(['uv', 'run', 'python', 'registry.py'], 
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        processes.append(('Registry', registry_proc))
        time.sleep(3)
        
        # Start Math Agent
        print("2. Starting Math Agent...")
        math_proc = subprocess.Popen(['uv', 'run', 'python', '-m', 'agents.math_agent', 
                                    'http://localhost:9010', '9011', '8021'],
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        processes.append(('Math Agent', math_proc))
        time.sleep(5)
        
        # Start LLM Agent - should discover Math Agent
        print("3. Starting LLM Agent (should discover Math Agent)...")
        llm_proc = subprocess.Popen(['uv', 'run', 'python', '-m', 'agents.llm_agent',
                                   'http://localhost:9010', '9014', '8024'],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        processes.append(('LLM Agent', llm_proc))
        time.sleep(8)  # Give LLM Agent time to complete startup discovery
        
        # Test LLM Agent discovery
        print("4. Testing LLM Agent discovery...")
        try:
            response = requests.post(
                "http://localhost:10014/v1/chat/completions",
                headers={"Content-Type": "application/json"},
                json={
                    "messages": [{"role": "user", "content": "What agents can you interact with?"}],
                    "model": "llm-agent"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                print("📝 LLM Agent Response (should show Math Agent):")
                print(content)
                print()
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Test request failed: {e}")
        
        # Wait a moment, then start Quote Agent
        print("5. Starting Quote Agent (LLM Agent should discover it via periodic discovery)...")
        quote_proc = subprocess.Popen(['uv', 'run', 'python', '-m', 'agents.quote_agent',
                                     'http://localhost:9010', '9012', '8022'],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        processes.append(('Quote Agent', quote_proc))
        time.sleep(5)
        
        print("6. Waiting for periodic discovery (up to 60 seconds)...")
        print("   The LLM Agent should automatically discover the new Quote Agent")
        
        # Wait for periodic discovery to kick in (agents check every 60 seconds)
        print("   Waiting 65 seconds for automatic discovery...")
        for i in range(65, 0, -5):
            print(f"   {i}s remaining...", end='\r')
            time.sleep(5)
        print()
        
        # Test again - should now show both agents
        print("7. Testing LLM Agent discovery again (should now show both agents)...")
        try:
            response = requests.post(
                "http://localhost:10014/v1/chat/completions",
                headers={"Content-Type": "application/json"},
                json={
                    "messages": [{"role": "user", "content": "What agents can you interact with now?"}],
                    "model": "llm-agent"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                print("📝 LLM Agent Response (should show Math + Quote Agents):")
                print(content)
                print()
                
                if "Math Agent" in content and "Quote Agent" in content:
                    print("✅ SUCCESS: Periodic discovery is working!")
                    print("   The LLM Agent automatically discovered the new Quote Agent.")
                else:
                    print("⚠️  PARTIAL: Some agents not discovered via periodic discovery")
                    
            else:
                print(f"❌ HTTP Error: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Test request failed: {e}")
        
        # Test manual refresh
        print("\n8. Testing manual discovery refresh...")
        try:
            response = requests.post(
                "http://localhost:10014/v1/chat/completions", 
                headers={"Content-Type": "application/json"},
                json={
                    "messages": [{"role": "user", "content": "refresh discovery"}],
                    "model": "llm-agent"
                },
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                print("📝 Manual Refresh Response:")
                print(content)
                
                if "just refreshed" in content:
                    print("✅ Manual refresh is working!")
                    
        except Exception as e:
            print(f"❌ Manual refresh test failed: {e}")
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
        
    finally:
        print("\n🛑 Stopping all agents...")
        for name, proc in processes:
            if proc.poll() is None:  # Still running
                proc.terminate()
                print(f"   Stopped {name}")
        
        # Wait for clean shutdown
        time.sleep(2)
        for name, proc in processes:
            if proc.poll() is None:
                proc.kill()
                
        print("✅ All agents stopped")
        print("\n💡 Periodic Discovery Features:")
        print("   - Agents check for new peers every 60 seconds")
        print("   - Manual refresh with 'refresh discovery' command")  
        print("   - Automatic detection of new/removed agents")
        print("   - Background thread for non-blocking discovery")

if __name__ == "__main__":
    test_periodic_discovery()
