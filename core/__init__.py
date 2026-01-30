"""
Core Agent Logic Module

This module contains the brain of Ready4Uni's agentic system:
- Intent classification (router): Understands what the user wants
- Agent orchestration: Plans multi-step workflows and executes tools
- Conversation state management

The agent uses an observe-plan-act loop to accomplish complex tasks
through multiple tool calls and reasoning steps.
"""

from .router import (
    classify_intent,
    IntentType,
    IntentResult,
)

from .orchestrator import (
    AgentOrchestrator,
    AgentState,
    ToolResult,
    run_agent_loop,
)

__all__ = [
    # Router
    "classify_intent",
    "IntentType",
    "IntentResult",
    
    # Orchestrator
    "AgentOrchestrator",
    "AgentState",
    "ToolResult",
    "run_agent_loop",
]
