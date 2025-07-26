#!/usr/bin/env python3
"""
Quick Start Example for Multiagent System

This script provides simple examples of how to interact with the system.
For a full demonstration, run: pytest tests/test_e2e.py -v -s
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def run_comprehensive_test():
    """Run the comprehensive test suite which demonstrates all functionality"""
    print("🚀 Multiagent System - Comprehensive Demo")
    print("=" * 50)
    print()
    print("This will run the full test suite which demonstrates:")
    print("  ✅ Agent registration and discovery")
    print("  ✅ MCP server functionality")
    print("  ✅ Inter-agent communication")
    print("  ✅ End-to-end workflow execution")
    print("  ✅ Memory integration (when available)")
    print("  ✅ Error handling and graceful fallbacks")
    print()
    
    import subprocess
    try:
        # Run the comprehensive test
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "tests/test_e2e.py::test_workflow", 
            "-v", "-s", "--tb=short"
        ], cwd=project_root)
        
        if result.returncode == 0:
            print("\n✨ All tests passed! The multiagent system is working correctly.")
        else:
            print("\n❌ Some tests failed. Check the output above for details.")
            
    except Exception as e:
        print(f"\n❌ Error running tests: {e}")

def show_manual_setup():
    """Show how to manually start the system"""
    print("\n📖 Manual Setup Instructions")
    print("-" * 30)
    print()
    print("To manually start the system:")
    print()
    print("1. Start the registry:")
    print("   python registry.py")
    print()
    print("2. Start agents (in separate terminals):")
    print("   python -m agents.math_agent http://localhost:9010 9011 8021")
    print("   python -m agents.quote_agent http://localhost:9010 9012 8022")
    print("   python -m agents.search_agent http://localhost:9010 9013 8023")
    print()
    print("3. Use the web interface:")
    print("   python gui.py")
    print("   # Open http://localhost:8000")
    print()
    print("4. Or interact via Python:")
    print("   from python_a2a.client import A2AClient")
    print("   from python_a2a.models import Message, TextContent, MessageRole")
    print("   ")
    print("   client = A2AClient('http://localhost:9011')  # Math Agent")
    print("   msg = Message(content=TextContent(text='5*7'), role=MessageRole.USER)")
    print("   response = client.send_message(msg)")
    print("   print(response.content.text)  # '35'")

def show_architecture():
    """Show the system architecture"""
    print("\n🏗️  System Architecture")
    print("-" * 22)
    print()
    print("multiagent/")
    print("├── agents/              # Agent implementations")
    print("│   ├── base.py         # Core ToolAgent with MCP integration")
    print("│   ├── mcp_adapters.py # Generic MCP server adapters")
    print("│   ├── math_agent.py   # Mathematical calculations")
    print("│   ├── quote_agent.py  # Quote generation")
    print("│   ├── search_agent.py # LangGraph orchestration")
    print("│   └── llm_agent.py    # OpenAI-powered reasoning")
    print("├── tests/")
    print("│   └── test_e2e.py     # Comprehensive system tests")
    print("├── registry.py         # Service discovery")
    print("├── gui.py             # Web interface")
    print("└── README.md          # Full documentation")
    print()
    print("Key Features:")
    print("  🔧 FastMCP tool servers with auto-discovery")
    print("  🌐 A2A protocol for agent communication")
    print("  🧠 Optional MCP memory server integration")
    print("  🎯 LangGraph workflows for orchestration")
    print("  🔌 Generic adapter pattern for MCP servers")
    print("  ✅ Comprehensive error handling and fallbacks")

def main():
    """Main entry point"""
    print("Welcome to the Multiagent Reference Implementation!")
    print()
    
    while True:
        print("\nChoose an option:")
        print("1. Run comprehensive demo (recommended)")
        print("2. Show manual setup instructions")
        print("3. Show system architecture")
        print("4. Exit")
        print()
        
        try:
            choice = input("Enter your choice (1-4): ").strip()
            
            if choice == "1":
                run_comprehensive_test()
            elif choice == "2":
                show_manual_setup()
            elif choice == "3":
                show_architecture()
            elif choice == "4":
                print("\n👋 Thank you for exploring the multiagent system!")
                break
            else:
                print("❌ Invalid choice. Please enter 1, 2, 3, or 4.")
                
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
