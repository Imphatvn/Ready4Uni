"""
Chat Service - Main Coordinator

Orchestrates the entire user interaction flow:
1. Receives user message and context
2. Routes to agent orchestrator
3. Coordinates with other services as needed
4. Manages conversation state
5. Returns formatted response

This is the main entry point for the Streamlit UI.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import uuid

from core import run_agent_loop, AgentState
from config import SYSTEM_PROMPT

logger = logging.getLogger(__name__)


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class ChatResponse:
    """
    Response from the chat service.
    
    Attributes:
        message: The response text to display to the user
        success: Whether the request was handled successfully
        metadata: Additional metadata about the response
        suggestions: Follow-up suggestions for the user
        agent_state: Full agent execution state (for debugging)
    """
    message: str
    success: bool
    metadata: Dict[str, Any]
    suggestions: Optional[List[str]] = None
    agent_state: Optional[AgentState] = None


# ============================================================================
# CHAT SERVICE
# ============================================================================

class ChatService:
    """
    Main chat service coordinator.
    
    Manages conversation flow, session state, and coordinates between
    the agent and domain-specific services.
    """
    
    def __init__(self):
        """Initialize the chat service."""
        from tools import get_tool_registry
        self.tool_registry = get_tool_registry()
        logger.info("✅ ChatService initialized")
    
    def process_message(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict]] = None,
        uploaded_files: Optional[List[Dict]] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> ChatResponse:
        """
        Process a user message and generate a response.
        
        Args:
            user_message: The user's input text
            conversation_history: Previous conversation turns
            uploaded_files: Files uploaded by the user
            session_id: Session identifier
            user_id: User identifier
            context: Additional context (e.g., selected major, parsed transcript)
            
        Returns:
            ChatResponse with the agent's reply and metadata
        """
        # Generate session ID if not provided
        if not session_id:
            session_id = str(uuid.uuid4())
        
        logger.info(f"💬 Processing message (session: {session_id}): {user_message[:50]}...")
        
        try:
            # SAFETY CHECK FIRST - before any agent processing
            from core.router import classify_intent, IntentType
            from config import CRISIS_RESPONSE
            
            quick_intent = classify_intent(user_message)
            if quick_intent.intent == IntentType.CRISIS_SAFETY:
                logger.warning("🚨 Crisis detected - returning safety response")
                return ChatResponse(
                    message=CRISIS_RESPONSE,
                    success=True,
                    metadata={"intent": "crisis_safety", "session_id": session_id},
                    suggestions=None,  # No suggestions for crisis situations
                )
            
            # Run the agent loop
            agent_state = run_agent_loop(
                user_message=user_message,
                tool_registry=self.tool_registry,
                conversation_history=conversation_history or [],
                uploaded_files=uploaded_files or [],
                session_id=session_id,
                user_id=user_id,
            )
            
            # Check if agent completed successfully
            if agent_state.status.value == "completed" and agent_state.final_response:
                # Generate follow-up suggestions
                suggestions = self._generate_suggestions(agent_state, context)
                
                return ChatResponse(
                    message=agent_state.final_response,
                    success=True,
                    metadata={
                        "intent": agent_state.intent.intent.value if agent_state.intent else "unknown",
                        "tools_used": [tr.tool_name for tr in agent_state.tool_results],
                        "execution_time": agent_state.total_execution_time,
                        "session_id": session_id,
                    },
                    suggestions=suggestions,
                    agent_state=agent_state,
                )
            
            # Handle errors
            elif agent_state.status.value == "error":
                logger.error(f"❌ Agent error: {agent_state.error_message}")
                return ChatResponse(
                    message=agent_state.final_response or self._get_error_message(),
                    success=False,
                    metadata={
                        "error": agent_state.error_message,
                        "session_id": session_id,
                    },
                    agent_state=agent_state,
                )
            
            # Unexpected state
            else:
                logger.warning(f"⚠️  Unexpected agent state: {agent_state.status.value}")
                return ChatResponse(
                    message="I had trouble processing that. Could you try rephrasing?",
                    success=False,
                    metadata={"status": agent_state.status.value, "session_id": session_id},
                    agent_state=agent_state,
                )
        
        except Exception as e:
            logger.error(f"❌ ChatService error: {e}", exc_info=True)
            return ChatResponse(
                message=self._get_error_message(),
                success=False,
                metadata={"error": str(e), "session_id": session_id},
            )
    
    def _generate_suggestions(
        self,
        agent_state: AgentState,
        context: Optional[Dict] = None
    ) -> List[str]:
        """
        Generate contextual follow-up suggestions based on the conversation.
        
        Args:
            agent_state: The completed agent state
            context: Additional context
            
        Returns:
            List of suggestion strings
        """
        suggestions = []
        
        if not agent_state.intent:
            return suggestions
        
        intent = agent_state.intent.intent.value
        
        # Suggestions based on intent
        if intent == "major_discovery":
            suggestions = [
                "Tell me more about one of these majors",
                "Check if my grades meet the requirements",
                "What careers can I pursue with this major?",
            ]
        
        elif intent == "transcript_analysis":
            suggestions = [
                "Which major should I consider based on my grades?",
                "How can I improve my weakest subject?",
                "Am I ready for Computer Science?",
            ]
        
        elif intent == "gap_analysis":
            # Check if gaps were identified
            has_gaps = any(
                "gap" in str(tr.result).lower() or "improve" in str(tr.result).lower()
                for tr in agent_state.tool_results if tr.success
            )
            
            if has_gaps:
                suggestions = [
                    "Show me resources to improve my weak subjects",
                    "What's a realistic timeline to close these gaps?",
                    "Are there alternative majors that fit my current grades?",
                ]
            else:
                suggestions = [
                    "What universities offer this major?",
                    "What should I focus on to maintain my readiness?",
                    "Tell me about career prospects in this field",
                ]
        
        elif intent == "resource_request":
            suggestions = [
                "Create a study schedule for me",
                "Are there any free courses available?",
                "What's the most important topic to focus on first?",
            ]
        
        elif intent == "general_question":
            suggestions = [
                "Help me find majors that match my interests",
                "Analyze my transcript",
                "What are the most popular majors?",
            ]
        
        return suggestions[:3]  # Limit to 3 suggestions
    
    def _get_error_message(self) -> str:
        """Get a friendly error message."""
        return (
            "I'm having trouble processing your request right now. "
            "This could be a temporary issue. Please try:\n"
            "- Rephrasing your question\n"
            "- Being more specific about what you need\n"
            "- Checking if any files uploaded correctly\n\n"
            "If the problem persists, feel free to start a new conversation."
        )


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================

def process_user_message(
    user_message: str,
    conversation_history: Optional[List[Dict]] = None,
    uploaded_files: Optional[List[Dict]] = None,
    session_id: Optional[str] = None,
    **kwargs
) -> ChatResponse:
    """
    Convenience function to process a user message.
    
    Args:
        user_message: The user's message
        conversation_history: Previous conversation
        uploaded_files: Uploaded files
        session_id: Session ID
        **kwargs: Additional arguments
        
    Returns:
        ChatResponse
    """
    service = ChatService()
    return service.process_message(
        user_message=user_message,
        conversation_history=conversation_history,
        uploaded_files=uploaded_files,
        session_id=session_id,
        **kwargs
    )
