"""
Agent Orchestrator - Main Agent Loop

Implements the agentic workflow:
1. Observe: Understand user intent and context
2. Plan: Decide which tools to call and in what order
3. Act: Execute tools and gather results
4. Respond: Synthesize information into a helpful response

Supports multi-step workflows, tool calling, error recovery, and
conversation memory.
"""

import logging
import time
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

from ai import call_llm, call_llm_with_tools
from config import SYSTEM_PROMPT, TOOL_DEFINITIONS
from .router import classify_intent, IntentType, IntentResult, requires_clarification

logger = logging.getLogger(__name__)


# ============================================================================
# DATA STRUCTURES
# ============================================================================

class AgentStatus(Enum):
    """Agent execution status."""
    IDLE = "idle"
    THINKING = "thinking"
    CALLING_TOOL = "calling_tool"
    SYNTHESIZING = "synthesizing"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class ToolResult:
    """
    Result from a tool execution.
    
    Attributes:
        tool_name: Name of the tool that was called
        success: Whether the tool executed successfully
        result: The actual result data
        error: Error message if unsuccessful
        execution_time: Time taken to execute (seconds)
        metadata: Additional metadata about the execution
    """
    tool_name: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentState:
    """
    Current state of the agent during execution.
    
    Tracks conversation, tools called, intermediate results, and status.
    """
    # Conversation
    user_message: str
    conversation_history: List[Dict[str, str]] = field(default_factory=list)
    uploaded_files: List[Dict] = field(default_factory=list)
    
    # Intent
    intent: Optional[IntentResult] = None
    
    # Execution tracking
    status: AgentStatus = AgentStatus.IDLE
    tool_calls: List[Dict[str, Any]] = field(default_factory=list)
    tool_results: List[ToolResult] = field(default_factory=list)
    
    # Agent thinking
    plan: Optional[str] = None
    intermediate_thoughts: List[str] = field(default_factory=list)
    
    # Results
    final_response: Optional[str] = None
    error_message: Optional[str] = None
    
    # Metadata
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    start_time: float = field(default_factory=time.time)
    total_execution_time: float = 0.0
    
    def add_tool_result(self, result: ToolResult):
        """Add a tool result to the state."""
        self.tool_results.append(result)
        self.tool_calls.append({
            "tool": result.tool_name,
            "success": result.success,
            "timestamp": time.time(),
        })
    
    def get_execution_summary(self) -> Dict[str, Any]:
        """Get a summary of the execution."""
        return {
            "intent": self.intent.intent.value if self.intent else "unknown",
            "status": self.status.value,
            "num_tool_calls": len(self.tool_calls),
            "tools_used": list(set(tc["tool"] for tc in self.tool_calls)),
            "success": self.status == AgentStatus.COMPLETED and self.final_response is not None,
            "execution_time": self.total_execution_time,
            "had_errors": any(not tr.success for tr in self.tool_results),
        }


# ============================================================================
# AGENT ORCHESTRATOR
# ============================================================================

class AgentOrchestrator:
    """
    Main agent orchestrator implementing the observe-plan-act loop.
    
    Coordinates intent classification, tool execution, and response generation
    for multi-step agentic workflows.
    """
    
    def __init__(
        self,
        tool_registry: Dict[str, Callable],
        max_iterations: int = 5,
        max_tool_calls: int = 10,
    ):
        """
        Initialize the orchestrator.
        
        Args:
            tool_registry: Dictionary mapping tool names to callable functions
            max_iterations: Maximum number of reasoning iterations
            max_tool_calls: Maximum total tool calls (safety limit)
        """
        self.tool_registry = tool_registry
        self.max_iterations = max_iterations
        self.max_tool_calls = max_tool_calls
    
    def run(
        self,
        user_message: str,
        conversation_history: Optional[List[Dict]] = None,
        uploaded_files: Optional[List[Dict]] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> AgentState:
        """
        Execute the full agent loop for a user message.
        
        Args:
            user_message: The user's input
            conversation_history: Previous conversation turns
            uploaded_files: Any files uploaded by the user
            session_id: Session identifier for tracking
            user_id: User identifier for tracking
            
        Returns:
            AgentState with execution results and final response
        """
        # Initialize state
        state = AgentState(
            user_message=user_message,
            conversation_history=conversation_history or [],
            uploaded_files=uploaded_files or [],
            session_id=session_id,
            user_id=user_id,
        )
        
        try:
            # Step 1: Observe - Classify intent
            state.status = AgentStatus.THINKING
            state.intent = classify_intent(
                user_message,
                conversation_history,
                uploaded_files
            )
            
            logger.info(f"🎯 Intent: {state.intent.intent.value}")
            
            # Check if clarification is needed before planning
            clarification_question = requires_clarification(state.intent)
            if clarification_question:
                logger.info(f"❓ Clarification needed: {clarification_question}")
                state.final_response = clarification_question
                state.status = AgentStatus.COMPLETED
                state.total_execution_time = time.time() - state.start_time
                return state
            
            # Handle simple intents without tools
            if state.intent.intent == IntentType.GREETING_OR_CHITCHAT:
                state.final_response = self._handle_greeting(user_message, state)
                state.status = AgentStatus.COMPLETED
                state.total_execution_time = time.time() - state.start_time
                return state
            
            # Step 2: Plan - Decide on tool usage
            state.status = AgentStatus.THINKING
            plan = self._create_plan(state)
            state.plan = plan
            logger.info(f"📋 Plan: {plan}")
            
            # Step 3: Act - Execute tools in loop
            iteration = 0
            while iteration < self.max_iterations:
                iteration += 1
                
                # Check if we need more tool calls
                if len(state.tool_calls) >= self.max_tool_calls:
                    logger.warning(f"⚠️  Reached max tool calls limit ({self.max_tool_calls})")
                    break
                
                state.status = AgentStatus.CALLING_TOOL
                
                # Call LLM with tools to decide next action
                tool_decision = self._decide_next_tool(state)
                
                # If no more tools needed, break
                if not tool_decision or not tool_decision.get("tool_calls"):
                    logger.info("✅ No more tools needed")
                    break
                
                # Execute tool calls
                for tool_call in tool_decision["tool_calls"]:
                    tool_name = tool_call["name"]
                    tool_args = tool_call["args"]
                    
                    logger.info(f"🔧 Calling tool: {tool_name} with args: {tool_args}")
                    
                    # Execute the tool
                    tool_result = self._execute_tool(tool_name, tool_args)
                    state.add_tool_result(tool_result)
                    
                    if not tool_result.success:
                        logger.error(f"❌ Tool {tool_name} failed: {tool_result.error}")
            
            # Step 4: Respond - Synthesize final response
            state.status = AgentStatus.SYNTHESIZING
            final_response = self._synthesize_response(state)
            state.final_response = final_response
            state.status = AgentStatus.COMPLETED
            
            logger.info(f"✅ Agent completed in {len(state.tool_calls)} tool calls")
            
        except Exception as e:
            logger.error(f"❌ Agent execution failed: {e}", exc_info=True)
            state.status = AgentStatus.ERROR
            state.error_message = str(e)
            state.final_response = (
                "I encountered an error while processing your request. "
                "Could you try rephrasing or let me know if you need help?"
            )
        
        state.total_execution_time = time.time() - state.start_time
        return state
    
    def _handle_greeting(self, message: str, state: AgentState) -> str:
        """Handle greetings and chitchat without tools."""
        prompt = f"""The user said: "{message}"

Respond warmly and professionally. If it's a greeting, introduce yourself as Ready4Uni 
and briefly mention you can help with:
- Finding university majors that match their interests
- Analyzing transcripts and checking readiness
- Recommending study resources

Keep it brief and friendly."""
        
        response = call_llm(
            prompt=prompt,
            system_instruction=SYSTEM_PROMPT,
            temperature=0.8
        )
        return response
    
    def _create_plan(self, state: AgentState) -> str:
        """
        Create a high-level plan based on the intent.
        
        Args:
            state: Current agent state
            
        Returns:
            Plan description string
        """
        intent = state.intent.intent
        
        plans = {
            IntentType.MAJOR_DISCOVERY: (
                "1. Extract user's interests and favorite subjects\n"
                "2. Call get_major_suggestions tool\n"
                "3. Present top 3-5 matching majors with explanations"
            ),
            IntentType.TRANSCRIPT_ANALYSIS: (
                "1. Call parse_transcript tool to extract grades\n"
                "2. Identify strongest and weakest subjects\n"
                "3. Provide overview of academic profile"
            ),
            IntentType.GAP_ANALYSIS: (
                "1. Parse transcript if not already done\n"
                "2. Get major requirements using get_major_info\n"
                "3. Call analyze_grade_gaps to compare\n"
                "4. If gaps exist, call find_study_resources for weak subjects"
            ),
            IntentType.RESOURCE_REQUEST: (
                "1. Identify subject and specific topic from user message\n"
                "2. Call find_study_resources tool\n"
                "3. Present curated list with study plan"
            ),
            IntentType.GENERAL_QUESTION: (
                "1. Use general knowledge to answer\n"
                "2. Call get_major_info if specific major mentioned\n"
                "3. Provide comprehensive, cited answer"
            ),
        }
        
        return plans.get(intent, "Analyze message and respond appropriately")
    
    def _decide_next_tool(self, state: AgentState) -> Optional[Dict]:
        """
        Use LLM with function calling to decide next tool(s) to call.
        
        Args:
            state: Current agent state
            
        Returns:
            Dictionary with tool_calls or None if no tools needed
        """
        # Build context from previous tool results
        context_parts = [
            f"User intent: {state.intent.intent.value}",
            f"User message: \"{state.user_message}\"",
            f"Plan: {state.plan}",
        ]
        
        if state.tool_results:
            context_parts.append("\n**Tools already called:**")
            for tr in state.tool_results:
                status = "✅" if tr.success else "❌"
                context_parts.append(
                    f"- {status} {tr.tool_name}: "
                    f"{str(tr.result)[:100] if tr.success else tr.error}"
                )
        
        # Add uploaded files context
        if state.uploaded_files:
            file_info = [f"{f['name']} (at {f['path']})" for f in state.uploaded_files]
            context_parts.append(f"\n**Uploaded files:** {', '.join(file_info)}")
        
        context = "\n".join(context_parts)
        
        prompt = f"""{context}

Based on the above context, decide what tool (if any) to call next to accomplish the goal.

**Guidelines:**
- If you have enough information to answer, return NO tool calls
- If you need to parse a transcript, call parse_transcript ONLY if a transcript was actually uploaded. Use the full path provided in the context (e.g., 'temp_uploads/filename.pdf').
- If you need major info, call get_major_info
- If comparing grades to requirements, call analyze_grades
- If finding study resources, call find_study_resources
- If suggesting majors, call get_major_suggestions

**IMPORTANT:** Never invent, hallucinate, or guess filenames like "sample_transcript.pdf". Only use files listed in the **Uploaded files** section above. If no files are listed, do NOT call parse_transcript.

What should we do next?"""
        
        result = call_llm_with_tools(
            prompt=prompt,
            tools=TOOL_DEFINITIONS,
            system_instruction=SYSTEM_PROMPT,
            temperature=0.3,  # Low temp for consistent tool selection
        )
        
        return result
    
    def _execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> ToolResult:
        """
        Execute a specific tool with given arguments.
        
        Args:
            tool_name: Name of the tool to execute
            tool_args: Arguments to pass to the tool
            
        Returns:
            ToolResult with execution outcome
        """
        start_time = time.time()
        
        # Check if tool exists
        if tool_name not in self.tool_registry:
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=f"Tool '{tool_name}' not found in registry",
                execution_time=time.time() - start_time,
            )
        
        # Get the tool function
        tool_func = self.tool_registry[tool_name]
        
        try:
            # Execute the tool
            result = tool_func(**tool_args)
            
            execution_time = time.time() - start_time
            
            return ToolResult(
                tool_name=tool_name,
                success=True,
                result=result,
                execution_time=execution_time,
                metadata={"args": tool_args},
            )
            
        except Exception as e:
            logger.error(f"Tool {tool_name} execution failed: {e}", exc_info=True)
            
            return ToolResult(
                tool_name=tool_name,
                success=False,
                error=str(e),
                execution_time=time.time() - start_time,
                metadata={"args": tool_args},
            )
    
    def _synthesize_response(self, state: AgentState) -> str:
        """
        Synthesize final response from all tool results and context.
        
        Args:
            state: Final agent state with all tool results
            
        Returns:
            Final response string for the user
        """
        # Build synthesis prompt
        context_parts = [
            f"**User's original question:** \"{state.user_message}\"",
            f"**Intent:** {state.intent.intent.value}",
        ]
        
        # Add tool results
        if state.tool_results:
            context_parts.append("\n**Information gathered from tools:**")
            for tr in state.tool_results:
                if tr.success:
                    context_parts.append(f"\n*{tr.tool_name}:*")
                    context_parts.append(f"```\n{str(tr.result)[:500]}\n```")
                else:
                    context_parts.append(f"\n*{tr.tool_name} failed:* {tr.error}")
        
        context = "\n".join(context_parts)
        
        synthesis_prompt = f"""{context}

Based on all the information gathered above, provide a comprehensive, helpful response to the user.

**Response guidelines:**
- Be encouraging and supportive
- Use specific data from tool results (mention actual grades, majors, requirements)
- If gaps were found, frame them as opportunities for improvement
- Provide actionable next steps
- Use bullet points for clarity when listing multiple items
- Keep tone conversational but professional
- If any tools failed, gracefully work around it without mentioning technical errors

Generate your final response:"""
        
        response = call_llm(
            prompt=synthesis_prompt,
            system_instruction=SYSTEM_PROMPT,
            temperature=0.7,
        )
        
        return response


# ============================================================================
# CONVENIENCE FUNCTION
# ============================================================================

def run_agent_loop(
    user_message: str,
    tool_registry: Dict[str, Callable],
    conversation_history: Optional[List[Dict]] = None,
    uploaded_files: Optional[List[Dict]] = None,
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    max_iterations: int = 5,
) -> AgentState:
    """
    Convenience function to run the agent loop.
    
    Args:
        user_message: User's input message
        tool_registry: Dictionary of available tools
        conversation_history: Previous conversation
        uploaded_files: Uploaded files
        session_id: Session ID for tracking
        user_id: User ID for tracking
        max_iterations: Max reasoning iterations
        
    Returns:
        Final AgentState with results
    """
    orchestrator = AgentOrchestrator(
        tool_registry=tool_registry,
        max_iterations=max_iterations,
    )
    
    return orchestrator.run(
        user_message=user_message,
        conversation_history=conversation_history,
        uploaded_files=uploaded_files,
        session_id=session_id,
        user_id=user_id,
    )
