#!/usr/bin/env python3

import time
import requests
import json

def test_discovery():
    """Test the startup discovery functionality."""
    
    print("Testing LLM Agent discovery via OpenAI API...")
    
    # Test the LLM agent's discovery response
    try:
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
            print("✓ LLM Agent Response:")
            print(content)
            print()
            
            # Check if it mentions discovered agents
            if "Math Agent" in content or "Quote Agent" in content:
                print("✓ SUCCESS: Agent discovery is working!")
            else:
                print("⚠ PARTIAL: LLM Agent responded but didn't mention discovered agents")
                print("This might indicate discovery timing issues or no other agents running")
                
        else:
            print(f"✗ HTTP Error {response.status_code}: {response.text}")
            
    except requests.RequestException as e:
        print(f"✗ Request failed: {e}")
        
    # Test health endpoints
    print("\nTesting agent health endpoints...")
    agents = [
        ("Math Agent", "http://localhost:9010/health"),
        ("LLM Agent", "http://localhost:9030/health"),
        ("Quote Agent", "http://localhost:9020/health")  # Assuming Quote agent port
    ]
    
    for name, url in agents:
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✓ {name}: Healthy")
            else:
                print(f"⚠ {name}: HTTP {response.status_code}")
        except requests.RequestException:
            print(f"✗ {name}: Not responding")

if __name__ == "__main__":
    test_discovery()
