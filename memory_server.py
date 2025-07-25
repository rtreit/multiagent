from fastmcp.server.server import FastMCP
from fastmcp.tools.tool import FunctionTool
import sys

class MemoryServer(FastMCP):
    def __init__(self):
        super().__init__(name="memory")
        self._data = {}

        async def add_observations(observations: list[dict]):
            for obs in observations:
                name = obs.get("entityName")
                self._data.setdefault(name, []).extend(obs.get("contents", []))
            return True

        async def get_observations(entityName: str):
            return self._data.get(entityName, [])

        self.add_tool(FunctionTool.from_function(add_observations, name="add_observations"))
        self.add_tool(FunctionTool.from_function(get_observations, name="get_observations"))


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9030
    server = MemoryServer()
    server.run(host="127.0.0.1", port=port, transport="http")

if __name__ == "__main__":
    main()
