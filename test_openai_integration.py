#!/usr/bin/env python3
"""
Test script to verify OpenAI integration in LLM Agent
"""

import os
import sys

def test_openai_integration():
    """Test if OpenAI integration works correctly."""
    print("🧪 Testing OpenAI Integration...")
    print("=" * 50)
    
    # Test 1: Check environment variable
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("❌ OPENAI_API_KEY environment variable not set")
        return False
    
    print(f"✅ OPENAI_API_KEY found: {api_key[:10]}...")
    
    # Test 2: Check imports
    try:
        from langchain_openai import ChatOpenAI
        from langchain.agents import AgentExecutor
        from langgraph.prebuilt import create_react_agent
        print("✅ All required imports successful")
    except ImportError as e:
        print(f"❌ Import failed: {e}")
        return False
    
    # Test 3: Test OpenAI API connection
    try:
        print("🔄 Testing OpenAI API connection...")
        llm = ChatOpenAI(
            model=os.environ.get("OPENAI_MODEL", "gpt-4o"),
            api_key=api_key,
            temperature=0.7
        )
        
        response = llm.invoke("What is 2+2? Answer briefly.")
        print(f"✅ OpenAI API response: {response.content[:100]}")
        
    except Exception as e:
        print(f"❌ OpenAI API test failed: {e}")
        return False
    
    # Test 4: Test LLM Agent initialization
    try:
        print("🔄 Testing LLM Agent initialization...")
        sys.path.append('.')
        from agents.llm_agent import LangGraphToolAgent
        
        # Create agent (won't start servers)
        agent = LangGraphToolAgent(8030, 8031, "http://localhost:9010")
        print("✅ LLM Agent created successfully")
        
        # Test _make_llm method
        test_llm = agent._make_llm()
        print("✅ LLM creation successful")
        
    except Exception as e:
        print(f"❌ LLM Agent test failed: {e}")
        return False
    
    print("=" * 50)
    print("🎉 All OpenAI integration tests passed!")
    print("The LLM Agent should now work correctly with OpenAI API.")
    return True

if __name__ == "__main__":
    success = test_openai_integration()
    if not success:
        print("\n💡 Try running: uv add langchain-openai langgraph")
        sys.exit(1)
    else:
        print("\n✅ Ready to use OpenAI-powered LLM Agent!")
