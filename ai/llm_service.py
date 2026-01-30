
"""
LLM Service - Gemini API Wrapper with Langfuse Observability

This service provides a robust interface to Google's Gemini API with:
- Automatic retry logic with exponential backoff
- Langfuse tracing for all LLM calls
- Token usage tracking
- Error handling and validation
- Support for function calling (tools)
- Structured JSON output
- Streaming support

All LLM interactions in Ready4Uni should use this service.
"""

import time
import json
import logging
from typing import Optional, Dict, List, Any, Union, Generator
from functools import wraps

import google.generativeai as genai
from google.generativeai.types import GenerationConfig, HarmCategory, HarmBlockThreshold

# Try to import Langfuse, make it optional
try:
    from langfuse import Langfuse
    from langfuse.decorators import observe, langfuse_context
    LANGFUSE_AVAILABLE = True
except (ImportError, AttributeError):
    LANGFUSE_AVAILABLE = False
    
    # Dummy decorator when Langfuse unavailable
    def observe(name=None, **kwargs):
        def decorator(func):
            return func
        if callable(name):
            return name
        return decorator
    
    class DummyContext:
        def update_current_trace(self, **kwargs):
            pass
        def update_current_observation(self, **kwargs):
            pass
    
    langfuse_context = DummyContext()
    Langfuse = None

from config import (
    GOOGLE_API_KEY,
    GEMINI_MODEL,
    TEMPERATURE,
    MAX_TOKENS,
    TOP_P,
    TOP_K,
    MAX_RETRIES,
    RETRY_DELAY,
    TIMEOUT,
    LANGFUSE_PUBLIC_KEY,
    LANGFUSE_SECRET_KEY,
    LANGFUSE_HOST,
    LANGFUSE_ENABLED,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# INITIALIZATION
# ============================================================================

# Configure Gemini API
genai.configure(api_key=GOOGLE_API_KEY)

# Initialize Langfuse client (if available and enabled)
_langfuse_client: Optional[Any] = None

if LANGFUSE_AVAILABLE and LANGFUSE_ENABLED:
    try:
        _langfuse_client = Langfuse(
            public_key=LANGFUSE_PUBLIC_KEY,
            secret_key=LANGFUSE_SECRET_KEY,
            host=LANGFUSE_HOST,
        )
        logger.info("✅ Langfuse observability initialized")
    except Exception as e:
        logger.warning(f"⚠️  Langfuse initialization failed: {e}. Continuing without tracing.")
        _langfuse_client = None
else:
    logger.info("ℹ️  Langfuse observability disabled or not available")


def get_langfuse_client() -> Optional[Any]:
    """Get the Langfuse client instance."""
    return _langfuse_client


# ============================================================================
# SAFETY SETTINGS
# ============================================================================

SAFETY_SETTINGS = {
    HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
}


# ============================================================================
# GENERATION CONFIGURATION
# ============================================================================

def get_generation_config(
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    top_p: Optional[float] = None,
    top_k: Optional[int] = None,
    response_mime_type: Optional[str] = None,
    response_schema: Optional[Dict] = None,
) -> GenerationConfig:
    """
    Create a generation configuration for Gemini API calls.
    
    Args:
        temperature: Sampling temperature (0.0 - 2.0). Defaults to config value.
        max_tokens: Maximum tokens to generate. Defaults to config value.
        top_p: Nucleus sampling parameter. Defaults to config value.
        top_k: Top-k sampling parameter. Defaults to config value.
        response_mime_type: MIME type for structured output (e.g., "application/json")
        response_schema: JSON schema for structured output validation
        
    Returns:
        GenerationConfig object
    """
    config_dict = {
        "temperature": temperature or TEMPERATURE,
        "max_output_tokens": max_tokens or MAX_TOKENS,
        "top_p": top_p or TOP_P,
        "top_k": top_k or TOP_K,
    }
    
    # Add structured output configuration if provided
    if response_mime_type:
        config_dict["response_mime_type"] = response_mime_type
    if response_schema:
        config_dict["response_schema"] = response_schema
    
    return GenerationConfig(**config_dict)


# ============================================================================
# RETRY DECORATOR
# ============================================================================

def retry_on_error(max_retries: int = MAX_RETRIES, delay: float = RETRY_DELAY):
    """
    Decorator to retry function calls on specific exceptions.
    Implements exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            current_delay = delay
            
            while retries < max_retries:
                try:
                    return func(*args, **kwargs)
                    
                except Exception as e:
                    error_type = type(e).__name__
                    error_msg = str(e)
                    
                    # Determine if error is retryable
                    retryable = any([
                        "rate limit" in error_msg.lower(),
                        "quota" in error_msg.lower(),
                        "timeout" in error_msg.lower(),
                        "503" in error_msg,
                        "429" in error_msg,
                        "500" in error_msg,
                    ])
                    
                    if not retryable or retries >= max_retries - 1:
                        logger.error(f"❌ {func.__name__} failed: {error_type}: {error_msg}")
                        raise
                    
                    retries += 1
                    logger.warning(
                        f"⚠️  {func.__name__} failed (attempt {retries}/{max_retries}): "
                        f"{error_type}. Retrying in {current_delay}s..."
                    )
                    
                    time.sleep(current_delay)
                    current_delay *= 2  # Exponential backoff
            
            raise Exception(f"Max retries ({max_retries}) exceeded")
        
        return wrapper
    return decorator


# ============================================================================
# CORE LLM FUNCTIONS
# ============================================================================

@observe(name="call_llm")
@retry_on_error()
def call_llm(
    prompt: str,
    system_instruction: Optional[str] = None,
    temperature: Optional[float] = None,
    max_tokens: Optional[int] = None,
    model_name: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Make a basic LLM call to Gemini API with Langfuse tracing.
    
    Args:
        prompt: The user prompt/query
        system_instruction: System prompt to set agent behavior
        temperature: Sampling temperature (overrides default)
        max_tokens: Max output tokens (overrides default)
        model_name: Model to use (overrides default)
        metadata: Additional metadata for Langfuse tracking
        
    Returns:
        Generated text response
        
    Raises:
        Exception: If API call fails after retries
    """
    model_name = model_name or GEMINI_MODEL
    
    # Log to Langfuse (if enabled)
    if _langfuse_client:
        langfuse_context.update_current_trace(
            name="llm_call",
            metadata={
                "model": model_name,
                "temperature": temperature or TEMPERATURE,
                **(metadata or {})
            }
        )
    
    # Create model instance
    model = genai.GenerativeModel(
        model_name=model_name,
        generation_config=get_generation_config(temperature, max_tokens),
        safety_settings=SAFETY_SETTINGS,
        system_instruction=system_instruction,
    )
    
    # Generate response
    start_time = time.time()
    response = model.generate_content(prompt)
    latency = time.time() - start_time
    
    # Extract text
    if not response.candidates:
        raise Exception("No response candidates returned from Gemini API")
    
    text = response.text
    
    # Track token usage
    if hasattr(response, 'usage_metadata'):
        usage = response.usage_metadata
        if _langfuse_client:
            langfuse_context.update_current_observation(
                usage={
                    "input": usage.prompt_token_count,
                    "output": usage.candidates_token_count,
                    "total": usage.total_token_count,
                }
            )
        
        logger.debug(
            f"📊 Tokens: {usage.prompt_token_count} in, "
            f"{usage.candidates_token_count} out, "
            f"⏱️  {latency:.2f}s"
        )
    
    return text


@observe(name="call_llm_with_tools")
@retry_on_error()
def call_llm_with_tools(
    prompt: str,
    tools: List[Dict],
    system_instruction: Optional[str] = None,
    temperature: Optional[float] = None,
    model_name: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Make an LLM call with function calling (tools) enabled.
    
    Args:
        prompt: The user prompt/query
        tools: List of tool definitions (function calling schemas)
        system_instruction: System prompt
        temperature: Sampling temperature
        model_name: Model to use
        metadata: Additional metadata for tracking
        
    Returns:
        Dict with:
            - response_text: The text response (if any)
            - tool_calls: List of tool calls requested by the LLM
            - raw_response: Full API response object
    """
    model_name = model_name or GEMINI_MODEL
    
    if _langfuse_client:
        langfuse_context.update_current_trace(
            name="llm_call_with_tools",
            metadata={
                "model": model_name,
                "num_tools": len(tools),
                **(metadata or {})
            }
        )
    
    # Create model with tools
    model = genai.GenerativeModel(
        model_name=model_name,
        generation_config=get_generation_config(temperature),
        safety_settings=SAFETY_SETTINGS,
        system_instruction=system_instruction,
        tools=tools,
    )
    
    # Generate response
    start_time = time.time()
    response = model.generate_content(prompt)
    latency = time.time() - start_time
    
    # Parse response
    result = {
        "response_text": None,
        "tool_calls": [],
        "raw_response": response,
        "latency": latency,
    }
    
    # Check for function calls
    if response.candidates:
        candidate = response.candidates[0]
        
        # Extract text (if any)
        if candidate.content.parts:
            for part in candidate.content.parts:
                if hasattr(part, 'text') and part.text:
                    result["response_text"] = part.text
                
                # Extract function calls
                if hasattr(part, 'function_call') and part.function_call:
                    func_call = part.function_call
                    result["tool_calls"].append({
                        "name": func_call.name,
                        "args": dict(func_call.args),
                    })
    
    # Track usage
    if hasattr(response, 'usage_metadata'):
        usage = response.usage_metadata
        if _langfuse_client:
            langfuse_context.update_current_observation(
                usage={
                    "input": usage.prompt_token_count,
                    "output": usage.candidates_token_count,
                    "total": usage.total_token_count,
                }
            )
        
        logger.debug(f"🔧 Tool call: {len(result['tool_calls'])} functions, ⏱️  {latency:.2f}s")
    
    return result


@observe(name="generate_structured_output")
@retry_on_error()
def generate_structured_output(
    prompt: str,
    schema: Dict,
    system_instruction: Optional[str] = None,
    temperature: Optional[float] = None,
    model_name: Optional[str] = None,
) -> Dict:
    """
    Generate structured JSON output conforming to a specific schema.
    
    Args:
        prompt: The user prompt/query
        schema: JSON schema defining the expected output structure
        system_instruction: System prompt
        temperature: Sampling temperature
        model_name: Model to use
        
    Returns:
        Parsed JSON object matching the schema
        
    Raises:
        json.JSONDecodeError: If output is not valid JSON
        ValueError: If output doesn't match schema
    """
    model_name = model_name or GEMINI_MODEL
    
    if _langfuse_client:
        langfuse_context.update_current_trace(
            name="structured_output",
            metadata={"model": model_name, "schema": schema.get("type", "unknown")}
        )
    
    # Create model with JSON output mode
    model = genai.GenerativeModel(
        model_name=model_name,
        generation_config=get_generation_config(
            temperature=temperature,
            response_mime_type="application/json",
            response_schema=schema,
        ),
        safety_settings=SAFETY_SETTINGS,
        system_instruction=system_instruction,
    )
    
    # Generate response
    start_time = time.time()
    response = model.generate_content(prompt)
    latency = time.time() - start_time
    
    # Parse JSON
    text = response.text
    
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        logger.error(f"❌ Invalid JSON from LLM: {text[:200]}...")
        raise ValueError(f"LLM did not return valid JSON: {e}")
    
    logger.debug(f"📋 Structured output generated in {latency:.2f}s")
    
    return data


def call_llm_streaming(
    prompt: str,
    system_instruction: Optional[str] = None,
    temperature: Optional[float] = None,
    model_name: Optional[str] = None,
) -> Generator[str, None, None]:
    """
    Stream LLM response token-by-token (for real-time UI updates).
    
    Args:
        prompt: The user prompt/query
        system_instruction: System prompt
        temperature: Sampling temperature
        model_name: Model to use
        
    Yields:
        Text chunks as they are generated
    """
    model_name = model_name or GEMINI_MODEL
    
    model = genai.GenerativeModel(
        model_name=model_name,
        generation_config=get_generation_config(temperature),
        safety_settings=SAFETY_SETTINGS,
        system_instruction=system_instruction,
    )
    
    response = model.generate_content(prompt, stream=True)
    
    for chunk in response:
        if chunk.text:
            yield chunk.text


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================

def count_tokens(text: str, model_name: Optional[str] = None) -> int:
    """
    Count tokens in a text string using Gemini's tokenizer.
    
    Args:
        text: Text to count tokens for
        model_name: Model to use for tokenization (affects count)
        
    Returns:
        Number of tokens
    """
    model_name = model_name or GEMINI_MODEL
    model = genai.GenerativeModel(model_name)
    
    try:
        result = model.count_tokens(text)
        return result.total_tokens
    except Exception as e:
        logger.warning(f"Token counting failed: {e}. Using rough estimate.")
        # Rough estimate: ~4 chars per token
        return len(text) // 4


def validate_model_available(model_name: str) -> bool:
    """
    Check if a specific model is available via the API.
    
    Args:
        model_name: Name of the model to check
        
    Returns:
        True if model is available, False otherwise
    """
    try:
        available_models = [m.name for m in genai.list_models()]
        full_name = f"models/{model_name}"
        return full_name in available_models
    except Exception as e:
        logger.error(f"Failed to check model availability: {e}")
        return False


def trace_llm_call(
    trace_name: str,
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    metadata: Optional[Dict] = None,
):
    """
    Decorator to add custom Langfuse tracing to any function.
    
    Usage:
        @trace_llm_call("gap_analysis", user_id="user123")
        def analyze_gaps(student_grades, major):
            ...
    """
    def decorator(func):
        if not _langfuse_client:
            return func  # No-op if Langfuse disabled
        
        @observe(name=trace_name)
        @wraps(func)
        def wrapper(*args, **kwargs):
            if _langfuse_client:
                langfuse_context.update_current_trace(
                    user_id=user_id,
                    session_id=session_id,
                    metadata=metadata or {}
                )
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


# ============================================================================
# HEALTH CHECK
# ============================================================================

def health_check() -> Dict[str, Any]:
    """
    Perform a health check on the LLM service.
    
    Returns:
        Dict with service status information
    """
    status = {
        "gemini_api": "unknown",
        "langfuse": "unknown",
        "model": GEMINI_MODEL,
        "model_available": False,
    }
    
    # Check Gemini API
    try:
        test_response = call_llm("Say 'OK' if you can read this.", temperature=0.0)
        status["gemini_api"] = "✅ healthy" if "ok" in test_response.lower() else "⚠️  degraded"
    except Exception as e:
        status["gemini_api"] = f"❌ error: {str(e)[:100]}"
    
    # Check model availability
    try:
        status["model_available"] = validate_model_available(GEMINI_MODEL)
    except:
        pass
    
    # Check Langfuse
    if _langfuse_client:
        try:
            # Attempt to flush pending traces
            _langfuse_client.flush()
            status["langfuse"] = "✅ connected"
        except Exception as e:
            status["langfuse"] = f"⚠️  {str(e)[:50]}"
    else:
        status["langfuse"] = "➖ disabled"
    
    return status


# ============================================================================
# MODULE INITIALIZATION
# ============================================================================

# Validate configuration on import
if __name__ != "__main__":
    try:
        if not validate_model_available(GEMINI_MODEL):
            logger.warning(
                f"⚠️  Model '{GEMINI_MODEL}' may not be available. "
                f"Check your API key and model name."
            )
    except Exception as e:
        logger.debug(f"Could not validate model on import: {e}")
