from python_a2a.discovery.server import RegistryAgent
from python_a2a.server.http import run_server
from python_a2a.models.agent import AgentCard

if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9010
    card = AgentCard(name="Registry", description="A2A discovery registry", url=f"http://localhost:{port}")
    agent = RegistryAgent(card)
    run_server(agent, host="127.0.0.1", port=port)
