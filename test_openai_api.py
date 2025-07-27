#!/usr/bin/env python3
"""
Test script for OpenAI-compatible API endpoints.
"""

import requests
import json
import time

def test_math_agent_openai_api():
    """Test the Math Agent's OpenAI-compatible API."""
    
    # Math Agent will be on port 5001 + 1000 = 6001
    base_url = "http://127.0.0.1:6001"
    
    print("Testing Math Agent OpenAI API...")
    
    # Test health check
    print("1. Testing health check...")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        print(f"Health check status: {response.status_code}")
        print(f"Health check response: {response.json()}")
    except Exception as e:
        print(f"Health check failed: {e}")
        return False
    
    # Test models endpoint
    print("\n2. Testing models endpoint...")
    try:
        response = requests.get(f"{base_url}/v1/models", timeout=5)
        print(f"Models status: {response.status_code}")
        print(f"Models response: {response.json()}")
    except Exception as e:
        print(f"Models endpoint failed: {e}")
        return False
    
    # Test chat completion
    print("\n3. Testing chat completion...")
    try:
        chat_request = {
            "model": "Math Agent",
            "messages": [
                {"role": "user", "content": "Calculate 15 * 7"}
            ]
        }
        
        start_time = time.time()
        response = requests.post(
            f"{base_url}/v1/chat/completions",
            json=chat_request,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        elapsed = time.time() - start_time
        
        print(f"Chat completion status: {response.status_code}")
        print(f"Response time: {elapsed:.2f}s")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Chat response: {json.dumps(result, indent=2)}")
            
            # Extract the answer
            if 'choices' in result and len(result['choices']) > 0:
                answer = result['choices'][0]['message']['content']
                print(f"Math result: {answer}")
                return True
        else:
            print(f"Error response: {response.text}")
            return False
            
    except Exception as e:
        print(f"Chat completion failed: {e}")
        return False

def test_all_agents():
    """Test all agent APIs if they're running."""
    
    # Test math agent first
    if test_math_agent_openai_api():
        print("\n✅ Math Agent OpenAI API test passed!")
    else:
        print("\n❌ Math Agent OpenAI API test failed!")
    
    # Add tests for other agents here when they're updated
    print("\nNote: Only Math Agent has been updated with OpenAI API support so far.")

if __name__ == "__main__":
    print("Testing OpenAI-compatible API endpoints...")
    print("Make sure the agents are running first with start_system.ps1")
    print("-" * 60)
    
    test_all_agents()
