"""
AI Infrastructure Module

This module provides the core LLM infrastructure for Ready4Uni:
- Gemini API client with error handling and retry logic
- Langfuse observability integration
- Token usage tracking
- Structured output support

All LLM calls should go through this module to ensure consistent
observability, error handling, and configuration.
"""

from .llm_service import (
    # Main LLM functions
    call_llm,
    call_llm_with_tools,
    call_llm_streaming,
    
    # Structured output
    generate_structured_output,
    
    # Utility functions
    count_tokens,
    validate_model_available,
    
    # Observability
    get_langfuse_client,
    trace_llm_call,
)

__all__ = [
    "call_llm",
    "call_llm_with_tools",
    "call_llm_streaming",
    "generate_structured_output",
    "count_tokens",
    "validate_model_available",
    "get_langfuse_client",
    "trace_llm_call",
]
