from python_a2a.discovery.server import RegistryAgent
from python_a2a.server.http import run_server
from python_a2a.models.agent import AgentCard
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("registry")

# Monkey patch to add more logging
original_register = RegistryAgent.register

def register_with_logging(self, card):
    logger.info(f"Registering agent: {card.name} at {card.url}")
    return original_register(self, card)

RegistryAgent.register = register_with_logging

if __name__ == "__main__":
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 9010
    card = AgentCard(name="Registry", description="A2A discovery registry", url=f"http://localhost:{port}")
    agent = RegistryAgent(card)
    logger.info(f"Starting registry server on port {port}")
    run_server(agent, host="127.0.0.1", port=port)
