"""
MCP Server Adapters - Generic patterns for working with different MCP servers

This module provides adapters for common MCP server patterns, allowing agents
to work with different server implementations without hardcoding server-specific logic.
"""

import logging
from typing import Dict, Any, Optional, List, Callable
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class MCPServerAdapter(ABC):
    """Base class for MCP server adapters"""
    
    def __init__(self, server_name: str):
        self.server_name = server_name
    
    @abstractmethod
    def store_data(self, agent, key: str, data: str) -> Optional[Any]:
        """Store data using this server's pattern"""
        pass
    
    @abstractmethod
    def retrieve_data(self, agent, key: str) -> Optional[Any]:
        """Retrieve data using this server's pattern"""
        pass


class KnowledgeGraphAdapter(MCPServerAdapter):
    """Adapter for knowledge graph-style memory servers"""
    
    def store_data(self, agent, entity_name: str, content: str) -> Optional[Any]:
        """Store data in a knowledge graph, creating entities as needed"""
        
        # First try to add observations directly
        result = agent.safe_remote_tool_call(
            self.server_name,
            "add_observations",
            {
                "observations": [{"entityName": entity_name, "contents": [content]}]
            }
        )
        
        if result is not None:
            return result
            
        # If that failed, try creating the entity first
        logger.info(f"Creating entity {entity_name} for knowledge graph")
        create_result = agent.safe_remote_tool_call(
            self.server_name,
            "create_entities",
            {
                "entities": [{"name": entity_name, "entityType": "agent", "observations": []}]
            }
        )
        
        if create_result is not None:
            # Now try adding observations again
            return agent.safe_remote_tool_call(
                self.server_name,
                "add_observations",
                {
                    "observations": [{"entityName": entity_name, "contents": [content]}]
                }
            )
        
        return None
    
    def retrieve_data(self, agent, entity_name: str) -> Optional[Any]:
        """Retrieve data from knowledge graph"""
        return agent.safe_remote_tool_call(
            self.server_name,
            "search_nodes", 
            {"query": entity_name}
        )


class SimpleKeyValueAdapter(MCPServerAdapter):
    """Adapter for simple key-value storage servers"""
    
    def store_data(self, agent, key: str, data: str) -> Optional[Any]:
        """Store data in key-value format"""
        return agent.safe_remote_tool_call(
            self.server_name,
            "store",
            {"key": key, "value": data}
        )
    
    def retrieve_data(self, agent, key: str) -> Optional[Any]:
        """Retrieve data by key"""
        return agent.safe_remote_tool_call(
            self.server_name,
            "retrieve",
            {"key": key}
        )


class DocumentStoreAdapter(MCPServerAdapter):
    """Adapter for document storage servers"""
    
    def store_data(self, agent, document_id: str, content: str) -> Optional[Any]:
        """Store data as a document"""
        return agent.safe_remote_tool_call(
            self.server_name,
            "create_document",
            {"id": document_id, "content": content}
        )
    
    def retrieve_data(self, agent, document_id: str) -> Optional[Any]:
        """Retrieve document by ID"""
        return agent.safe_remote_tool_call(
            self.server_name,
            "get_document",
            {"id": document_id}
        )


class MCPAdapterRegistry:
    """Registry for MCP server adapters"""
    
    def __init__(self):
        self.adapters: Dict[str, MCPServerAdapter] = {}
        self.auto_detect_patterns: List[Callable] = []
    
    def register_adapter(self, server_name: str, adapter: MCPServerAdapter):
        """Register an adapter for a specific server"""
        self.adapters[server_name] = adapter
    
    def get_adapter(self, server_name: str) -> Optional[MCPServerAdapter]:
        """Get adapter for a server"""
        return self.adapters.get(server_name)
    
    def add_auto_detect_pattern(self, pattern_func: Callable):
        """Add a function that can auto-detect server type from available tools"""
        self.auto_detect_patterns.append(pattern_func)
    
    def auto_detect_adapter(self, agent, server_name: str) -> Optional[MCPServerAdapter]:
        """Try to auto-detect the appropriate adapter based on available tools"""
        try:
            # Get available tools from the server
            async def _get_tools():
                return await agent.remote_client.get_tools(server_name=server_name)
            
            import anyio
            tools = anyio.run(_get_tools)
            tool_names = {tool.name for tool in tools}
            
            # Check patterns
            for pattern_func in self.auto_detect_patterns:
                adapter = pattern_func(server_name, tool_names)
                if adapter:
                    return adapter
                    
        except Exception as e:
            logger.warning(f"Failed to auto-detect adapter for {server_name}: {e}")
        
        return None


# Default adapter registry with common patterns
default_adapter_registry = MCPAdapterRegistry()

# Register default adapters
default_adapter_registry.register_adapter("memory", KnowledgeGraphAdapter("memory"))

# Auto-detection patterns
def detect_knowledge_graph(server_name: str, tool_names: set) -> Optional[MCPServerAdapter]:
    """Detect knowledge graph servers by their tool signatures"""
    kg_tools = {"create_entities", "add_observations", "read_graph"}
    if kg_tools.issubset(tool_names):
        return KnowledgeGraphAdapter(server_name)
    return None

def detect_key_value(server_name: str, tool_names: set) -> Optional[MCPServerAdapter]:
    """Detect key-value servers"""
    kv_tools = {"store", "retrieve"}
    if kv_tools.issubset(tool_names):
        return SimpleKeyValueAdapter(server_name)
    return None

def detect_document_store(server_name: str, tool_names: set) -> Optional[MCPServerAdapter]:
    """Detect document storage servers"""
    doc_tools = {"create_document", "get_document"}
    if doc_tools.issubset(tool_names):
        return DocumentStoreAdapter(server_name)
    return None

# Register auto-detection patterns
default_adapter_registry.add_auto_detect_pattern(detect_knowledge_graph)
default_adapter_registry.add_auto_detect_pattern(detect_key_value)
default_adapter_registry.add_auto_detect_pattern(detect_document_store)
