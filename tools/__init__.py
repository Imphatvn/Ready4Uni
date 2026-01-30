"""
Function Calling Tools Module

This module contains all tools (functions) that the LLM agent can invoke
through function calling. These are the "hands" of the agent - the actions
it can take to accomplish user goals.

Each tool is designed to:
- Have a clear, single purpose
- Accept structured parameters from the LLM
- Return structured results
- Include error handling with retry logic
- Be independently testable

Tools are registered in the tool_registry for the agent to use.
"""

from .transcript_tools import (
    parse_transcript,
    analyze_grades,
)

from .major_tools import (
    get_major_info,
    get_major_suggestions,
    search_major_database,
)

from .resource_tools import (
    find_study_resources,
    create_personalized_study_plan,
)

# Tool registry for agent orchestrator
def get_tool_registry():
    """
    Get the complete registry of available tools.
    
    Returns:
        Dictionary mapping tool names to callable functions
    """
    return {
        # Transcript tools
        "parse_transcript": parse_transcript,
        "analyze_grades": analyze_grades,
        
        # Major tools
        "get_major_info": get_major_info,
        "get_major_suggestions": get_major_suggestions,
        "search_major_database": search_major_database,
        
        # Resource tools
        "find_study_resources": find_study_resources,
        "create_personalized_study_plan": create_personalized_study_plan,
    }


__all__ = [
    # Transcript tools
    "parse_transcript",
    "analyze_grades",
    
    # Major tools
    "get_major_info",
    "get_major_suggestions",
    "search_major_database",
    
    # Resource tools
    "find_study_resources",
    "create_personalized_study_plan",
    
    # Registry
    "get_tool_registry",
]
