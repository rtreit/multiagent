# Issue: Agent Discovery Broken

Agents were unable to discover peers because `DiscoveryClient` was initialized with the registry URL instead of an `AgentCard`. This left the client's `registry_urls` empty, causing `discover()` to return no agents.

## Fix

Create `DiscoveryClient` with the agent's own card and explicitly call `add_registry()` with the registry URL before calling `discover()`.
