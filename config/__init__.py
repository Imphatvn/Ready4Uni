"""
Configuration module for Ready4Uni.

This module provides centralized configuration management including:
- Application settings (models, API keys, paths)
- Prompt templates and system instructions
- Tool definitions and schemas

All configurable values should be imported from this module to ensure
consistency across the application.
"""

"""
Configuration module for Ready4Uni.
"""

from .settings import (
    # Paths
    BASE_DIR,
    DATA_DIR,
    ASSETS_DIR,
    
    # API Keys 
    GOOGLE_API_KEY,
    
    # LLM Settings
    GEMINI_MODEL,
    TEMPERATURE,
    MAX_TOKENS,
    TOP_P,
    TOP_K,
    MAX_RETRIES,
    RETRY_DELAY,
    TIMEOUT,
    
    # Langfuse Settings
    LANGFUSE_PUBLIC_KEY,
    LANGFUSE_SECRET_KEY,
    LANGFUSE_HOST,
    LANGFUSE_ENABLED,
    
    # Application Settings
    DEFAULT_MIN_GRADE,
    PASSING_GRADE,
    MAX_UPLOAD_SIZE_MB,
    SUPPORTED_PDF_EXTENSIONS,
    
    # Data Loaders
    load_majors,
    get_major_by_id,
    get_major_by_name,
    
    # Validation Helpers
    validate_grade,
    validate_transcript_structure,
    
    # Crisis/Safety Detection
    CRISIS_KEYWORDS,
    CRISIS_RESPONSE,
)

from .prompts import (
    # System Prompts
    SYSTEM_PROMPT,
    ROUTER_PROMPT,
    GAP_ANALYSIS_PROMPT,
    RESOURCE_GENERATION_PROMPT,
    
    # Tool Definitions
    TOOL_DEFINITIONS,
    
    # Output Schemas
    MAJOR_INFO_SCHEMA,
    GAP_ANALYSIS_SCHEMA,
    RESOURCE_SCHEMA,
    TRANSCRIPT_SCHEMA,
    
    # Utilities
    format_prompt,
)

__all__ = [
    # Settings
    "BASE_DIR",
    "DATA_DIR",
    "ASSETS_DIR",
    "GOOGLE_API_KEY",  
    "GEMINI_MODEL",
    "TEMPERATURE",
    "MAX_TOKENS",
    "TOP_P",           
    "TOP_K",           
    "MAX_RETRIES",
    "RETRY_DELAY",     
    "TIMEOUT",
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY",
    "LANGFUSE_HOST",
    "LANGFUSE_ENABLED",
    "DEFAULT_MIN_GRADE",
    "PASSING_GRADE",
    "MAX_UPLOAD_SIZE_MB",
    "SUPPORTED_PDF_EXTENSIONS",
    "load_majors",
    "get_major_by_id",
    "get_major_by_name",
    "validate_grade",
    "validate_transcript_structure",
    "CRISIS_KEYWORDS",
    "CRISIS_RESPONSE",
    
    # Prompts
    "SYSTEM_PROMPT",
    "ROUTER_PROMPT",
    "GAP_ANALYSIS_PROMPT",
    "RESOURCE_GENERATION_PROMPT",
    "TOOL_DEFINITIONS",
    "MAJOR_INFO_SCHEMA",
    "GAP_ANALYSIS_SCHEMA",
    "RESOURCE_SCHEMA",
    "TRANSCRIPT_SCHEMA",
    "format_prompt",
]
