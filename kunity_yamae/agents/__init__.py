"""Agent adapters package - supports multiple AI coding agent backends."""

from .base import BaseAgent
from .claude_agent import ClaudeAgent
from .codex_agent import CodexAgent
from .gemini_agent import GeminiAgent
from .glm_agent import GlmAgent
from .kimi_agent import KimiAgent
from .local_patch_agent import LocalPatchAgent
from .mimo_agent import MiMoAgent

AGENT_REGISTRY = {
    "codex": CodexAgent,
    "claude": ClaudeAgent,
    "gemini": GeminiAgent,
    "kimi": KimiAgent,
    "glm": GlmAgent,
    "mimo": MiMoAgent,
    "local-patch": LocalPatchAgent,
}


def get_agent(name: str, config: dict) -> BaseAgent:
    """Get an agent instance by name."""
    agent_cls = AGENT_REGISTRY.get(name)
    if not agent_cls:
        raise ValueError(f"Unknown agent: {name}. Available: {list(AGENT_REGISTRY.keys())}")
    agent_config = config.get("agents", {}).get("backends", {}).get(name, {})
    return agent_cls(name, config, agent_config)


def list_agents() -> list[str]:
    return list(AGENT_REGISTRY.keys())
