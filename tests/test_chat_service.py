"""
Unit Tests for Chat Service

Tests the main chat coordinator and conversation flow.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from services.chat_service import ChatService, process_user_message


class TestChatService:
    """Test ChatService class."""
    
    @pytest.fixture
    def chat_service(self):
        """Fixture providing ChatService instance."""
        return ChatService()
    
    @patch('services.chat_service.run_agent_loop')
    def test_process_message_success(self, mock_run_agent, chat_service):
        """Test successful message processing."""
        from core.orchestrator import AgentState, AgentStatus
        from core.router import IntentResult, IntentType
        
        # Mock successful agent execution
        mock_state = AgentState(
            user_message="I want to study Computer Science",
            status=AgentStatus.COMPLETED,
            final_response="Here are some suggestions for Computer Science...",
        )
        mock_state.intent = IntentResult(intent=IntentType.MAJOR_DISCOVERY)
        mock_run_agent.return_value = mock_state
        
        response = chat_service.process_message(
            user_message="I want to study Computer Science",
            session_id="test_session_123",
        )
        
        assert response.success is True
        assert response.message == "Here are some suggestions for Computer Science..."
        assert response.metadata["session_id"] == "test_session_123"
        assert response.metadata["intent"] == "major_discovery"
    
    @patch('services.chat_service.run_agent_loop')
    def test_process_message_with_conversation_history(self, mock_run_agent, chat_service):
        """Test message processing with conversation history."""
        from core.orchestrator import AgentState, AgentStatus
        
        mock_state = AgentState(
            user_message="What about Physics?",
            status=AgentStatus.COMPLETED,
            final_response="Physics requirements are...",
        )
        mock_run_agent.return_value = mock_state
        
        history = [
            {"role": "user", "content": "Tell me about Engineering"},
            {"role": "assistant", "content": "Engineering requires..."},
        ]
        
        response = chat_service.process_message(
            user_message="What about Physics?",
            conversation_history=history,
        )
        
        # Verify conversation history was passed to agent
        mock_run_agent.assert_called_once()
        call_kwargs = mock_run_agent.call_args[1]
        assert call_kwargs["conversation_history"] == history
    
    @patch('services.chat_service.run_agent_loop')
    def test_process_message_with_uploaded_file(self, mock_run_agent, chat_service):
        """Test message processing with uploaded transcript."""
        from core.orchestrator import AgentState, AgentStatus
        
        mock_state = AgentState(
            user_message="Analyze my transcript",
            status=AgentStatus.COMPLETED,
            final_response="Your grades show...",
        )
        mock_run_agent.return_value = mock_state
        
        uploaded_files = [
            {"name": "transcript.pdf", "path": "/tmp/transcript.pdf"}
        ]
        
        response = chat_service.process_message(
            user_message="Analyze my transcript",
            uploaded_files=uploaded_files,
        )
        
        # Verify files were passed to agent
        call_kwargs = mock_run_agent.call_args[1]
        assert call_kwargs["uploaded_files"] == uploaded_files
    
    @patch('services.chat_service.run_agent_loop')
    def test_process_message_error_handling(self, mock_run_agent, chat_service):
        """Test error handling in message processing."""
        from core.orchestrator import AgentState, AgentStatus
        
        # Mock error state
        mock_state = AgentState(
            user_message="Error message",
            status=AgentStatus.ERROR,
            error_message="Something went wrong",
            final_response="I had trouble processing that.",
        )
        mock_run_agent.return_value = mock_state
        
        response = chat_service.process_message(user_message="Error message")
        
        assert response.success is False
        assert "error" in response.metadata
    
    @patch('services.chat_service.run_agent_loop')
    def test_generate_suggestions_major_discovery(self, mock_run_agent, chat_service):
        """Test suggestion generation for major discovery intent."""
        from core.orchestrator import AgentState, AgentStatus
        from core.router import IntentResult, IntentType
        
        mock_state = AgentState(
            user_message="What should I study?",
            status=AgentStatus.COMPLETED,
            final_response="Consider Computer Science...",
        )
        mock_state.intent = IntentResult(intent=IntentType.MAJOR_DISCOVERY)
        mock_run_agent.return_value = mock_state
        
        response = chat_service.process_message(user_message="What should I study?")
        
        # Should have follow-up suggestions
        assert response.suggestions is not None
        assert len(response.suggestions) > 0
        assert any("major" in s.lower() for s in response.suggestions)


class TestProcessUserMessage:
    """Test convenience function."""
    
    @patch('services.chat_service.ChatService')
    def test_process_user_message_convenience(self, mock_service_class):
        """Test the convenience function wrapper."""
        # Mock ChatService instance
        mock_service = Mock()
        mock_service.process_message.return_value = Mock(
            success=True,
            message="Response",
        )
        mock_service_class.return_value = mock_service
        
        response = process_user_message(
            user_message="Hello",
            session_id="test123",
        )
        
        # Verify service was instantiated and called
        mock_service_class.assert_called_once()
        mock_service.process_message.assert_called_once()


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestChatServiceIntegration:
    """Integration tests for complete chat flow."""
    
    @pytest.mark.integration
    def test_simple_greeting_flow(self):
        """Test simple greeting conversation flow."""
        chat_service = ChatService()
        
        response = chat_service.process_message(
            user_message="Hello",
            session_id="integration_test",
        )
        
        # Greeting should succeed
        assert response.success is True
        assert len(response.message) > 0
    
    @pytest.mark.integration
    def test_major_discovery_flow(self):
        """Test major discovery conversation flow."""
        chat_service = ChatService()
        
        response = chat_service.process_message(
            user_message="I love programming and math, what should I study?",
            session_id="integration_test",
        )
        
        assert response.success is True
        assert "Computer Science" in response.message or "Data Science" in response.message
