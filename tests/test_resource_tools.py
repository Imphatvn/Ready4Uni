"""
Unit Tests for Resource Tools

Tests study resource recommendation functionality.
"""

import pytest
from unittest.mock import Mock, patch

from tools.resource_tools import (
    find_study_resources,
    create_personalized_study_plan,
)


class TestFindStudyResources:
    """Test find_study_resources tool."""
    
    @patch('tools.resource_tools.recommend_study_resources')
    def test_find_resources_success(self, mock_recommend):
        """Test successful resource finding."""
        from services.resource_service import StudyResource
        
        # Mock resource recommendations
        mock_recommend.return_value = [
            StudyResource(
                name="Khan Academy: Calculus",
                provider="Khan Academy",
                type="video_course",
                language="PT",
                free=True,
                description="Comprehensive calculus course",
                search_hint="Visit pt.khanacademy.org",
            ),
            StudyResource(
                name="YouTube: Math Basics",
                provider="YouTube",
                type="video",
                language="PT",
                free=True,
                description="Basic math concepts",
                search_hint="Search 'matematica basica'",
            ),
        ]
        
        result = find_study_resources(
            subject="Math",
            topic="Calculus",
            level="high_school",
            goal="improve from 13 to 16",
        )
        
        assert result["success"] is True
        assert result["count"] == 2
        assert result["subject"] == "Math"
        assert result["topic"] == "Calculus"
        
        # Check resource format
        assert result["resources"][0]["name"] == "Khan Academy: Calculus"
        assert result["resources"][0]["free"] is True
        assert "search_hint" in result["resources"][0]
    
    @patch('tools.resource_tools.recommend_study_resources')
    def test_find_resources_no_results(self, mock_recommend):
        """Test handling when no resources are found."""
        mock_recommend.return_value = []
        
        result = find_study_resources(subject="Math")
        
        assert result["success"] is False
        assert "Could not generate" in result["error"]
        assert result["resources"] == []
    
    @patch('tools.resource_tools.recommend_study_resources')
    def test_find_resources_with_goal(self, mock_recommend):
        """Test resource finding with specific goal."""
        mock_recommend.return_value = []  # Empty for simplicity
        
        result = find_study_resources(
            subject="Physics",
            topic="Mechanics",
            level="university_prep",
            goal="prepare for entrance exam",
        )
        
        # Verify function was called with correct parameters
        mock_recommend.assert_called_once()
        call_kwargs = mock_recommend.call_args[1]
        assert call_kwargs["subject"] == "Physics"
        assert call_kwargs["topic"] == "Mechanics"
        assert call_kwargs["goal"] == "prepare for entrance exam"


class TestCreatePersonalizedStudyPlan:
    """Test create_personalized_study_plan tool."""
    
    @patch('tools.resource_tools.create_study_plan')
    def test_create_study_plan_success(self, mock_create):
        """Test successful study plan creation."""
        from services.resource_service import StudyPlan, StudyResource
        
        # Mock study plan
        mock_create.return_value = StudyPlan(
            subject="Math",
            topic="Calculus",
            resources=[
                StudyResource(
                    name="Resource 1",
                    provider="Provider",
                    type="course",
                    language="PT",
                    free=True,
                    description="Description",
                    search_hint="Hint",
                ),
            ],
            plan="Start with basics, then practice problems, review weekly",
            estimated_time="2-3 months with regular practice",
            priority_order=["Resource 1"],
        )
        
        result = create_personalized_study_plan(
            subject="Math",
            topic="Calculus",
            current_grade=13,
            target_grade=16,
            available_time_per_week=5,
        )
        
        assert result["success"] is True
        assert result["subject"] == "Math"
        assert result["topic"] == "Calculus"
        assert "plan" in result
        assert "estimated_time" in result
        assert len(result["resources"]) == 1
        assert len(result["priority_order"]) == 1
    
    @patch('tools.resource_tools.create_study_plan')
    def test_create_study_plan_with_grades(self, mock_create):
        """Test study plan creation with grade information."""
        from services.resource_service import StudyPlan
        
        mock_create.return_value = StudyPlan(
            subject="Physics",
            topic=None,
            resources=[],
            plan="Focus on fundamentals",
            estimated_time="4-6 months",
            priority_order=[],
        )
        
        result = create_personalized_study_plan(
            subject="Physics",
            current_grade=11,
            target_grade=15,
        )
        
        # Verify function was called with grade parameters
        mock_create.assert_called_once()
        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["current_grade"] == 11
        assert call_kwargs["target_grade"] == 15
    
    @patch('tools.resource_tools.create_study_plan')
    def test_create_study_plan_minimal_params(self, mock_create):
        """Test study plan creation with minimal parameters."""
        from services.resource_service import StudyPlan
        
        mock_create.return_value = StudyPlan(
            subject="Portuguese",
            topic=None,
            resources=[],
            plan="General study plan",
            estimated_time="2-3 months",
            priority_order=[],
        )
        
        result = create_personalized_study_plan(subject="Portuguese")
        
        assert result["success"] is True
        assert result["subject"] == "Portuguese"
        assert result["topic"] is None


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestResourceToolsIntegration:
    """Integration tests with real LLM calls (if API key available)."""
    
    @pytest.mark.integration
    def test_find_resources_real_llm(self):
        """Test resource finding with real LLM call."""
        result = find_study_resources(
            subject="Math",
            topic="Algebra",
            level="high_school",
        )
        
        # Should get real recommendations
        assert result["success"] is True
        assert result["count"] > 0
        assert all("name" in r for r in result["resources"])
    
    @pytest.mark.integration
    def test_create_plan_real_llm(self):
        """Test study plan creation with real LLM call."""
        result = create_personalized_study_plan(
            subject="Physics",
            current_grade=13,
            target_grade=16,
            available_time_per_week=3,
        )
        
        assert result["success"] is True
        assert len(result["plan"]) > 50  # Should be substantial
        assert result["estimated_time"]  # Should have timeline

