"""
Intent Classification Router

Analyzes user messages to determine their intent and route to the
appropriate service. Uses LLM-based classification for flexibility
while maintaining structured outputs.

Intent types:
- major_discovery: Find majors that match interests
- transcript_analysis: Parse and evaluate uploaded transcripts
- gap_analysis: Compare grades to major requirements
- resource_request: Find study materials
- general_question: Answer questions about universities/majors
- greeting_or_chitchat: Social interaction
"""

import logging
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass

from ai import call_llm, generate_structured_output
from config import ROUTER_PROMPT, SYSTEM_PROMPT, CRISIS_KEYWORDS

logger = logging.getLogger(__name__)


# ============================================================================
# INTENT TYPES
# ============================================================================

class IntentType(Enum):
    """Enumeration of possible user intents."""
    
    CRISIS_SAFETY = "crisis_safety"  # Highest priority - self-harm detection
    MAJOR_DISCOVERY = "major_discovery"
    TRANSCRIPT_ANALYSIS = "transcript_analysis"
    GAP_ANALYSIS = "gap_analysis"
    RESOURCE_REQUEST = "resource_request"
    GENERAL_QUESTION = "general_question"
    GREETING_OR_CHITCHAT = "greeting_or_chitchat"
    UNKNOWN = "unknown"


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class IntentResult:
    """
    Result of intent classification.
    
    Attributes:
        intent: The classified intent type
        confidence: Confidence score (0.0 - 1.0) if available
        reasoning: LLM's reasoning for the classification
        context: Additional context extracted from the message
        requires_transcript: Whether this intent needs transcript data
        requires_major: Whether this intent needs a specific major
    """
    intent: IntentType
    confidence: float = 1.0
    reasoning: Optional[str] = None
    context: Dict[str, Any] = None
    requires_transcript: bool = False
    requires_major: bool = False
    
    def __post_init__(self):
        if self.context is None:
            self.context = {}


# ============================================================================
# INTENT CLASSIFICATION SCHEMA
# ============================================================================

INTENT_SCHEMA = {
    "type": "object",
    "properties": {
        "intent": {
            "type": "string",
            "enum": [
                "major_discovery",
                "transcript_analysis",
                "gap_analysis",
                "resource_request",
                "general_question",
                "greeting_or_chitchat"
            ],
            "description": "The primary intent of the user's message"
        },
        "confidence": {
            "type": "number",
            "description": "Confidence in the classification (0.0 - 1.0)"
        },
        "reasoning": {
            "type": "string",
            "description": "Brief explanation of why this intent was chosen"
        },
        "extracted_entities": {
            "type": "object",
            "properties": {
                "major_mentioned": {
                    "type": "string",
                    "description": "Name of major if explicitly mentioned"
                },
                "subjects_mentioned": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "School subjects mentioned"
                },
                "interests": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Interests or hobbies mentioned"
                },
                "has_transcript_reference": {
                    "type": "boolean",
                    "description": "Whether user references their transcript/grades"
                }
            }
        }
    },
    "required": ["intent", "confidence", "reasoning"]
}


# ============================================================================
# ROUTING LOGIC
# ============================================================================

def classify_intent(
    user_message: str,
    conversation_history: Optional[list] = None,
    uploaded_files: Optional[list] = None,
) -> IntentResult:
    """
    Classify the user's intent using LLM with structured output.
    
    Args:
        user_message: The user's current message
        conversation_history: Previous messages for context (optional)
        uploaded_files: List of uploaded files (for context awareness)
        
    Returns:
        IntentResult with classified intent and metadata
        
    Example:
        >>> result = classify_intent("I love math and physics, what should I study?")
        >>> print(result.intent)
        IntentType.MAJOR_DISCOVERY
    """
    # Build context-aware prompt
    
    # SAFETY CHECK FIRST - before any LLM call
    if _detect_crisis_keywords(user_message):
        logger.warning("🚨 Crisis keywords detected - returning safety response")
        return IntentResult(
            intent=IntentType.CRISIS_SAFETY,
            confidence=1.0,
            reasoning="Crisis/safety keywords detected in user message",
        )
    
    context_parts = []
    
    if conversation_history and len(conversation_history) > 0:
        # Include last 3 messages for context
        recent_history = conversation_history[-3:]
        history_text = "\n".join([
            f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
            for msg in recent_history
        ])
        context_parts.append(f"**Recent conversation:**\n{history_text}")
    
    if uploaded_files and len(uploaded_files) > 0:
        file_list = ", ".join([f"{f.get('name', 'unnamed')} (at {f.get('path', 'unknown')})" for f in uploaded_files])
        context_parts.append(f"**Uploaded files:** {file_list}")
    
    context_str = "\n\n".join(context_parts) if context_parts else "No previous context."
    
    # Build full classification prompt
    full_prompt = f"""{ROUTER_PROMPT}

{context_str}

**Current user message:**
"{user_message}"

Classify the intent and extract any relevant entities."""
    
    try:
        # Call LLM with structured output
        result = generate_structured_output(
            prompt=full_prompt,
            schema=INTENT_SCHEMA,
            temperature=0.2,  # Low temperature for consistent classification
        )
        
        # Parse result
        intent_str = result.get("intent", "unknown")
        try:
            intent = IntentType(intent_str)
        except ValueError:
            logger.warning(f"Unknown intent returned: {intent_str}")
            intent = IntentType.UNKNOWN
        
        # Extract entities
        entities = result.get("extracted_entities", {})
        
        # Determine requirements and actual status
        has_actual_transcript = uploaded_files is not None and len(uploaded_files) > 0
        
        requires_transcript = (
            intent in [IntentType.TRANSCRIPT_ANALYSIS, IntentType.GAP_ANALYSIS]
            or entities.get("has_transcript_reference", False)
        )
        
        requires_major = (
            intent == IntentType.GAP_ANALYSIS
            and entities.get("major_mentioned") is not None
        )
        
        intent_result = IntentResult(
            intent=intent,
            confidence=result.get("confidence", 0.9),
            reasoning=result.get("reasoning", ""),
            context={
                "major": entities.get("major_mentioned"),
                "subjects": entities.get("subjects_mentioned", []),
                "interests": entities.get("interests", []),
                "has_transcript": has_actual_transcript,
            },
            requires_transcript=requires_transcript,
            requires_major=requires_major,
        )
        
        logger.info(
            f"🧭 Intent classified: {intent.value} "
            f"(confidence: {intent_result.confidence:.2f})"
        )
        
        return intent_result
        
    except Exception as e:
        logger.error(f"❌ Intent classification failed: {e}")
        
        # Fallback: keyword-based classification
        return _fallback_classification(user_message, uploaded_files)


def _fallback_classification(
    user_message: str,
    uploaded_files: Optional[list] = None
) -> IntentResult:
    """
    Simple keyword-based fallback if LLM classification fails.
    
    Args:
        user_message: The user's message
        uploaded_files: Uploaded files for context
        
    Returns:
        IntentResult with best-guess classification
    """
    message_lower = user_message.lower()
    
    # Check for transcript reference
    has_transcript = (
        uploaded_files and len(uploaded_files) > 0
        or any(kw in message_lower for kw in ["transcript", "grades", "report card", "my scores"])
    )
    
    # Keyword matching
    if any(kw in message_lower for kw in ["hello", "hi", "hey", "thanks", "thank you"]):
        intent = IntentType.GREETING_OR_CHITCHAT
    
    elif any(kw in message_lower for kw in ["what major", "which major", "suggest major", "recommend major", "i like", "i love", "interested in"]):
        intent = IntentType.MAJOR_DISCOVERY
    
    elif any(kw in message_lower for kw in ["am i ready", "do i qualify", "meet requirements", "good enough"]) and has_transcript:
        intent = IntentType.GAP_ANALYSIS
    
    elif has_transcript:
        intent = IntentType.TRANSCRIPT_ANALYSIS
    
    elif any(kw in message_lower for kw in ["study", "learn", "improve", "course", "resource", "how can i"]):
        intent = IntentType.RESOURCE_REQUEST
    
    else:
        intent = IntentType.GENERAL_QUESTION
    
    logger.warning(f"⚠️  Using fallback classification: {intent.value}")
    
    actual_has_transcript = uploaded_files is not None and len(uploaded_files) > 0
    
    return IntentResult(
        intent=intent,
        confidence=0.6,  # Lower confidence for fallback
        reasoning="Classified using keyword fallback due to LLM error",
        context={"has_transcript": actual_has_transcript},
        requires_transcript=has_transcript,
    )


def _detect_crisis_keywords(message: str) -> bool:
    """
    Check for self-harm/crisis related keywords.
    
    This check runs BEFORE any LLM call to ensure fast, reliable
    detection of crisis situations.
    
    Args:
        message: User's message to check
        
    Returns:
        True if crisis keywords detected, False otherwise
    """
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in CRISIS_KEYWORDS)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_intent_description(intent: IntentType) -> str:
    """
    Get a human-readable description of an intent type.
    
    Args:
        intent: The intent type
        
    Returns:
        Description string
    """
    descriptions = {
        IntentType.MAJOR_DISCOVERY: "Exploring which university majors match your interests",
        IntentType.TRANSCRIPT_ANALYSIS: "Analyzing your academic transcript",
        IntentType.GAP_ANALYSIS: "Checking if your grades meet requirements for a specific major",
        IntentType.RESOURCE_REQUEST: "Finding study resources to improve your skills",
        IntentType.GENERAL_QUESTION: "Answering questions about universities and majors",
        IntentType.GREETING_OR_CHITCHAT: "Having a casual conversation",
        IntentType.UNKNOWN: "Understanding your request",
    }
    return descriptions.get(intent, "Processing your message")


def requires_clarification(intent_result: IntentResult) -> Optional[str]:
    """
    Check if the intent requires clarification from the user.
    
    Args:
        intent_result: The classified intent
        
    Returns:
        Clarification question if needed, None otherwise
    """
    # Low confidence classification
    if intent_result.confidence < 0.5:
        return "I'm not quite sure what you're looking for. Could you rephrase that?"
    
    # Gap analysis without major
    if intent_result.intent == IntentType.GAP_ANALYSIS and not intent_result.context.get("major"):
        return "Which major would you like me to check your readiness for?"
    
    # Gap analysis without transcript
    if intent_result.requires_transcript and not intent_result.context.get("has_transcript"):
        return "I'll need to see your transcript to help with that. Could you upload your grades PDF?"
    
    return None
