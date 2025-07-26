#!/usr/bin/env python3
"""
Simple test to debug the memory MCP server connection issue
"""
import asyncio
import os
import anyio
from langchain_mcp_adapters.client import MultiServerMCPClient

async def test_memory_server():
    print("Testing memory MCP server connection...")
    
    # Configure the memory server exactly as in base.py
    config = {
        "memory": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-memory"],
            "transport": "stdio",
        }
    }
    
    try:
        print("Creating MultiServerMCPClient...")
        client = MultiServerMCPClient(config)
        
        print("Getting tools from memory server...")
        tools = await client.get_tools(server_name="memory")
        print(f"Available tools: {[tool.name for tool in tools]}")
        
        tool_map = {t.name: t for t in tools}
        
        # First create an entity before adding observations
        print("Creating entity...")
        create_result = await tool_map["create_entities"].ainvoke({
            "entities": [
                {"name": "test_entity", "entityType": "agent", "observations": []}
            ]
        })
        print(f"Create entity result: {create_result}")
        
        print("Adding observations to entity...")
        obs_result = await tool_map["add_observations"].ainvoke({
            "observations": [
                {"entityName": "test_entity", "contents": ["test content"]}
            ]
        })
        print(f"add_observations result: {obs_result}")
        
        print("Reading the graph...")
        graph_result = await tool_map["read_graph"].ainvoke({})
        print(f"Graph contents: {graph_result}")
            
    except Exception as e:
        print(f"Error occurred: {e}")
        import traceback
        traceback.print_exc()

def sync_test():
    """Test the proper workflow for agents"""
    print("Testing proper agent workflow...")
    
    config = {
        "memory": {
            "command": "npx",
            "args": ["-y", "@modelcontextprotocol/server-memory"],
            "transport": "stdio",
        }
    }
    
    try:
        client = MultiServerMCPClient(config)
        
        async def _call():
            tools = await client.get_tools(server_name="memory")
            tool_map = {t.name: t for t in tools}
            
            # Try creating an entity first - this might be the issue
            try:
                entity_result = await tool_map["create_entities"].ainvoke({
                    "entities": [
                        {"name": "math_agent_history", "entityType": "agent", "observations": []}
                    ]
                })
                print(f"Entity creation: {entity_result}")
            except Exception as e:
                print(f"Entity creation failed (might already exist): {e}")
            
            # Now add observations
            result = await tool_map["add_observations"].ainvoke({
                "observations": [
                    {"entityName": "math_agent_history", "contents": ["5*7=35"]}
                ]
            })
            return result
        
        result = anyio.run(_call)
        print(f"Success! Result: {result}")
        
    except Exception as e:
        print(f"Error with anyio.run: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_memory_server())
    print("\n" + "="*50 + "\n")
    sync_test()
