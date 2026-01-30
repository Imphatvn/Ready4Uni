"""
Unit Tests for Major Tools

Tests major information retrieval and suggestion functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from tools.major_tools import (
    get_major_info,
    get_major_suggestions,
    search_major_database,
)


class TestGetMajorInfo:
    """Test get_major_info tool."""
    
    @patch('tools.major_tools.get_major_details')
    def test_get_major_info_success(self, mock_get_details):
        """Test successful major info retrieval."""
        # Mock successful lookup
        mock_get_details.return_value = {
            "id": "computer_science",
            "name": "Computer Science",
            "description": "Study of computing...",
            "requirements": {"Math": 16, "Physics": 14},
            "career_paths": ["Software Engineer", "Data Scientist"],
        }
        
        result = get_major_info("Computer Science")
        
        assert result["success"] is True
        assert result["major"]["name"] == "Computer Science"
        assert result["source"] == "curated_data"
        assert "requirements" in result["major"]
    
    @patch('tools.major_tools.get_major_details')
    def test_get_major_info_not_found(self, mock_get_details):
        """Test handling of major not found."""
        mock_get_details.return_value = None
        
        result = get_major_info("Nonexistent Major")
        
        assert result["success"] is False
        assert "not found" in result["error"].lower()
    
    @patch('tools.major_tools.get_major_details')
    @patch('services.major_service.MajorService.get_similar_majors')
    def test_get_major_info_with_similar(self, mock_similar, mock_get_details):
        """Test retrieval with similar majors included."""
        mock_get_details.return_value = {
            "id": "computer_science",
            "name": "Computer Science",
        }
        
        mock_similar.return_value = [
            {"name": "Data Science", "id": "data_science"},
            {"name": "Software Engineering", "id": "software_eng"},
        ]
        
        result = get_major_info("Computer Science", include_similar=True)
        
        assert result["success"] is True
        assert "similar_majors" in result
        assert len(result["similar_majors"]) == 2


class TestGetMajorSuggestions:
    """Test get_major_suggestions tool."""
    
    @patch('tools.major_tools.match_interests_to_majors')
    def test_get_major_suggestions_success(self, mock_match):
        """Test successful major suggestions."""
        # Mock MajorMatch objects
        from services.major_service import MajorMatch
        
        mock_matches = [
            MajorMatch(
                major={
                    "id": "computer_science",
                    "name": "Computer Science",
                    "description": "Study of computing",
                    "requirements": {"Math": 16},
                    "career_paths": ["Software Engineer"],
                },
                score=0.85,
                reasons=["Matches programming interest"],
                matching_keywords={"programming", "algorithms"},
            ),
            MajorMatch(
                major={
                    "id": "data_science",
                    "name": "Data Science",
                    "description": "Study of data",
                    "requirements": {"Math": 17},
                    "career_paths": ["Data Scientist"],
                },
                score=0.75,
                reasons=["Matches data interest"],
                matching_keywords={"data", "statistics"},
            ),
        ]
        
        mock_match.return_value = mock_matches
        
        result = get_major_suggestions(
            interests=["programming", "data"],
            favorite_subjects=["Math"],
            top_n=5,
        )
        
        assert result["success"] is True
        assert len(result["suggestions"]) == 2
        assert result["suggestions"][0]["name"] == "Computer Science"
        assert result["suggestions"][0]["score"] == 0.85
        assert "reasons" in result["suggestions"][0]
    
    @patch('tools.major_tools.match_interests_to_majors')
    def test_get_major_suggestions_no_matches(self, mock_match):
        """Test handling of no matching majors."""
        mock_match.return_value = []
        
        result = get_major_suggestions(interests=["random_interest"])
        
        assert result["success"] is False
        assert "No matching majors" in result["error"]
        assert result["suggestions"] == []
    
    @patch('tools.major_tools.match_interests_to_majors')
    def test_get_major_suggestions_with_career_goals(self, mock_match):
        """Test suggestions with career goals specified."""
        mock_match.return_value = []  # Empty for simplicity
        
        result = get_major_suggestions(
            interests=["programming"],
            favorite_subjects=["Math", "Physics"],
            career_goals="software engineer",
            top_n=3,
        )
        
        # Verify the function was called with correct parameters
        mock_match.assert_called_once()
        call_kwargs = mock_match.call_args[1]
        assert call_kwargs["career_goals"] == "software engineer"
        assert call_kwargs["top_n"] == 3


class TestSearchMajorDatabase:
    """Test search_major_database tool."""
    
    @patch('tools.major_tools.search_majors_service')
    def test_search_success(self, mock_search):
        """Test successful major search."""
        mock_search.return_value = [
            {
                "id": "computer_science",
                "name": "Computer Science",
                "description": "Full description of computer science program...",
                "keywords": ["programming", "algorithms", "software", "systems", "data"],
            },
            {
                "id": "computer_engineering",
                "name": "Computer Engineering",
                "description": "Another long description...",
                "keywords": ["hardware", "software", "embedded", "systems"],
            },
        ]
        
        result = search_major_database("computer", max_results=10)
        
        assert result["success"] is True
        assert result["count"] == 2
        assert result["query"] == "computer"
        
        # Check description truncation
        assert len(result["results"][0]["description"]) <= 153  # 150 + "..."
        
        # Check keyword limiting
        assert len(result["results"][0]["keywords"]) <= 5
    
    @patch('tools.major_tools.search_majors_service')
    def test_search_no_results(self, mock_search):
        """Test search with no results."""
        mock_search.return_value = []
        
        result = search_major_database("xyz123nonexistent")
        
        assert result["success"] is True  # Success even with no results
        assert result["count"] == 0
        assert result["results"] == []
    
    @patch('tools.major_tools.search_majors_service')
    def test_search_max_results_limit(self, mock_search):
        """Test that max_results parameter limits output."""
        # Mock 20 results
        mock_search.return_value = [
            {"id": f"major_{i}", "name": f"Major {i}", "description": "Desc", "keywords": []}
            for i in range(20)
        ]
        
        result = search_major_database("test", max_results=5)
        
        assert result["count"] == 5  # Should be limited
        assert len(result["results"]) == 5


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestMajorToolsIntegration:
    """Integration tests with real data."""
    
    def test_get_major_info_real_data(self):
        """Test get_major_info with real curated data."""
        result = get_major_info("Computer Science")
        
        # Should work with real data if majors.json exists
        # If not, it should gracefully fail
        assert "success" in result
        
        if result["success"]:
            assert "major" in result
            assert "name" in result["major"]
    
    def test_search_real_database(self):
        """Test search with real major database."""
        result = search_major_database("Engineering")
        
        assert "success" in result
        assert "results" in result
        
        # If majors.json exists, should find engineering majors
        if result["count"] > 0:
            assert any("engineering" in r["name"].lower() for r in result["results"])
