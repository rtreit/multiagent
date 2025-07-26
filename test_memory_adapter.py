#!/usr/bin/env python3
"""
Test the memory adapter system to ensure it's working with the new generic architecture.
"""

import os
import asyncio
import subprocess
import time
import sys
import signal
import atexit
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from agents.math_agent import MathAgent
from agents.quote_agent import QuoteAgent

# Global process tracking
processes = []

def cleanup_processes():
    """Clean up all spawned processes"""
    print(f"\n=== Cleaning up {len(processes)} processes ===")
    for i, proc in enumerate(processes, 1):
        try:
            print(f"Terminating process {i}...")
            if hasattr(proc, 'terminate'):
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
        except Exception as e:
            print(f"Error terminating process {i}: {e}")
    processes.clear()
    print("Cleanup complete.")

# Register cleanup
atexit.register(cleanup_processes)

def signal_handler(signum, frame):
    print(f"\nReceived signal {signum}, cleaning up...")
    cleanup_processes()
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

async def start_memory_server():
    """Start the Node.js memory server"""
    print("=== Starting Memory Server ===")
    
    # Find a free port for memory server
    import socket
    sock = socket.socket()
    sock.bind(('', 0))
    memory_port = sock.getsockname()[1]
    sock.close()
    
    # Start memory server using node directly
    memory_proc = subprocess.Popen([
        'node', 
        'C:/Users/randy/AppData/Roaming/npm/node_modules/@modelcontextprotocol/server-memory/dist/index.js',
        'http', f'127.0.0.1:{memory_port}'
    ], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    processes.append(memory_proc)
    
    # Wait for server to start
    await asyncio.sleep(3)
    print(f"✓ Memory server started on port {memory_port}")
    
    return memory_port

async def test_math_agent_memory(memory_port):
    """Test Math Agent with memory storage"""
    print("\n=== Testing Math Agent Memory ===")
    
    # Set memory server environment variable
    os.environ['MEMORY_SERVER_URL'] = f'http://127.0.0.1:{memory_port}'
    
    # Create Math Agent with correct parameters
    agent = MathAgent(
        a2a_port=9099,  # Use a different port for testing
        mcp_port=8099,
        registry_url=""  # Empty string instead of None
    )
    
    try:
        # Test storing and retrieving data
        print("Testing memory storage...")
        
        # Store some calculation data
        result = agent.store_data("memory", "last_calculation", {
            "expression": "2+2", 
            "result": 4,
            "timestamp": "2025-01-25T19:00:00Z"
        })
        print(f"Storage result: {result}")
        
        # Store another calculation
        result2 = agent.store_data("memory", "calculation_history", {
            "expression": "5*7",
            "result": 35,
            "timestamp": "2025-01-25T19:01:00Z"
        })
        print(f"Storage result 2: {result2}")
        
        # Try to retrieve data
        retrieved = agent.retrieve_data("memory", "last_calculation")
        print(f"Retrieved data: {retrieved}")
        
        print("✓ Math Agent memory test successful")
        return True
        
    except Exception as e:
        print(f"❌ Math Agent memory test failed: {e}")
        return False

async def test_quote_agent_memory(memory_port):
    """Test Quote Agent with memory storage"""
    print("\n=== Testing Quote Agent Memory ===")
    
    # Set memory server environment variable
    os.environ['MEMORY_SERVER_URL'] = f'http://127.0.0.1:{memory_port}'
    
    # Create Quote Agent with correct parameters
    agent = QuoteAgent(
        a2a_port=9098,  # Use a different port for testing
        mcp_port=8098,
        registry_url=""  # Empty string instead of None
    )
    
    try:
        # Test storing quote data
        print("Testing quote memory storage...")
        
        # Store a quote request
        result = agent.store_data("memory", "recent_quote_request", {
            "topic": "inspiration",
            "quote": "Life is what happens when you're busy making other plans.",
            "timestamp": "2025-01-25T19:00:00Z"
        })
        print(f"Quote storage result: {result}")
        
        # Store quote preferences
        result2 = agent.store_data("memory", "user_preferences", {
            "favorite_topics": ["inspiration", "wisdom", "humor"],
            "quote_style": "philosophical"
        })
        print(f"Preferences storage result: {result2}")
        
        # Retrieve the data
        retrieved = agent.retrieve_data("memory", "recent_quote_request")
        print(f"Retrieved quote data: {retrieved}")
        
        print("✓ Quote Agent memory test successful")
        return True
        
    except Exception as e:
        print(f"❌ Quote Agent memory test failed: {e}")
        return False

async def main():
    """Main test function"""
    print("=" * 80)
    print("MEMORY ADAPTER SYSTEM TEST")
    print("=" * 80)
    
    try:
        # Start memory server
        memory_port = await start_memory_server()
        
        # Test both agents
        math_success = await test_math_agent_memory(memory_port)
        quote_success = await test_quote_agent_memory(memory_port)
        
        # Summary
        print("\n" + "=" * 80)
        print("MEMORY TEST SUMMARY")
        print("=" * 80)
        print(f"Math Agent Memory: {'✓ PASS' if math_success else '❌ FAIL'}")
        print(f"Quote Agent Memory: {'✓ PASS' if quote_success else '❌ FAIL'}")
        
        if math_success and quote_success:
            print("\n✓ ALL MEMORY TESTS PASSED - ADAPTER SYSTEM WORKING")
        else:
            print("\n❌ SOME MEMORY TESTS FAILED")
            
    except KeyboardInterrupt:
        print("\nTest interrupted by user")
    except Exception as e:
        print(f"\nTest failed with error: {e}")
    finally:
        cleanup_processes()

if __name__ == "__main__":
    asyncio.run(main())
