"""
Unit Tests for Transcript Tools

Tests transcript parsing and grade analysis functionality.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from tools.transcript_tools import (
    parse_transcript,
    analyze_grades,
)
from tests import SAMPLE_TRANSCRIPT_PATH


class TestParseTranscript:
    """Test parse_transcript tool."""
    
    @patch('tools.transcript_tools.extract_text_from_pdf')
    @patch('tools.transcript_tools.generate_structured_output')
    def test_parse_transcript_success(self, mock_generate, mock_extract):
        """Test successful transcript parsing."""
        # Mock PDF extraction
        mock_extract.return_value = """
        Student Name: João Silva
        School: Escola Secundária de Lisboa
        
        Math: 15/20
        Physics: 17/20
        Portuguese: 14/20
        """
        
        # Mock LLM parsing
        mock_generate.return_value = {
            "grades": [
                {"subject": "Math", "grade": 15},
                {"subject": "Physics", "grade": 17},
                {"subject": "Portuguese", "grade": 14},
            ],
            "student_name": "João Silva",
            "school": "Escola Secundária de Lisboa",
            "gpa": 15.3,
            "parsing_confidence": "high",
        }
        
        result = parse_transcript("/tmp/transcript.pdf")
        
        assert result["success"] is True
        assert len(result["grades"]) == 3
        assert result["grades"]["Math"] == 15
        assert result["student_info"]["name"] == "João Silva"
        assert result["confidence"] == "high"
    
    @patch('tools.transcript_tools.extract_text_from_pdf')
    def test_parse_transcript_empty_pdf(self, mock_extract):
        """Test handling of empty PDF."""
        mock_extract.return_value = "   "  # Only whitespace
        
        result = parse_transcript("/tmp/empty.pdf")
        
        assert result["success"] is False
        assert "empty or unreadable" in result["error"].lower()
    
    @patch('tools.transcript_tools.extract_text_from_pdf')
    @patch('tools.transcript_tools.generate_structured_output')
    def test_parse_transcript_no_grades_found(self, mock_generate, mock_extract):
        """Test handling when no grades are found."""
        # Text must be > 50 chars to pass the minimum length check
        mock_extract.return_value = "Some random text without any grades or academic information here in this document"
        mock_generate.return_value = {"grades": []}
        
        result = parse_transcript("/tmp/transcript.pdf")
        
        assert result["success"] is False
        assert "No grades found" in result["error"]
    
    @patch('tools.transcript_tools.extract_text_from_pdf')
    @patch('tools.transcript_tools.generate_structured_output')
    def test_parse_transcript_invalid_grades(self, mock_generate, mock_extract):
        """Test handling of invalid grade values."""
        # Return text > 50 chars to pass the minimum length check
        mock_extract.return_value = "Student Name: Test Student\nSchool: Test School\nMath: 15, Physics: 25, Portuguese: -5"
        
        # Mock LLM returning invalid grades
        mock_generate.return_value = {
            "grades": [
                {"subject": "Math", "grade": 15},      # Valid
                {"subject": "Physics", "grade": 25},   # Invalid (>20)
                {"subject": "Portuguese", "grade": -5}, # Invalid (<0)
            ],
            "parsing_confidence": "low",
        }
        
        result = parse_transcript("/tmp/transcript.pdf")
        
        assert result["success"] is True
        # Invalid grades should be removed
        assert "Physics" not in result["grades"]
        assert "Portuguese" not in result["grades"]
        assert "Math" in result["grades"]
    
    @patch('tools.transcript_tools.extract_text_from_pdf')
    def test_parse_transcript_extraction_failure(self, mock_extract):
        """Test handling of PDF extraction failure."""
        mock_extract.side_effect = Exception("PDF extraction failed")
        
        result = parse_transcript("/tmp/bad.pdf")
        
        assert result["success"] is False
        assert "Failed to parse transcript" in result["error"]


class TestAnalyzeGrades:
    """Test analyze_grades tool."""
    
    @patch('services.transcript_service.analyze_transcript')
    def test_analyze_grades_without_major(self, mock_analyze):
        """Test grade analysis without specifying a major."""
        from services.transcript_service import TranscriptAnalysis
        
        # Mock transcript analysis
        mock_analyze.return_value = TranscriptAnalysis(
            grades={"Math": 15, "Physics": 17, "Portuguese": 14},
            gpa=15.3,
            strengths=["Physics", "Math"],
            weaknesses=["Portuguese"],
            passing_all=True,
            overall_quality="good",
        )
        
        result = analyze_grades(
            student_grades={"Math": 15, "Physics": 17, "Portuguese": 14}
        )
        
        assert result["success"] is True
        assert result["analysis"]["gpa"] == 15.3
        assert result["analysis"]["overall_quality"] == "good"
        assert len(result["analysis"]["strengths"]) == 2
        assert "recommendations" in result
    
    @patch('services.transcript_service.analyze_transcript')
    @patch('services.transcript_service.compare_grades_to_requirements')
    @patch('tools.transcript_tools.generate_structured_output')
    def test_analyze_grades_with_major_ready(self, mock_generate, mock_compare, mock_analyze):
        """Test grade analysis when student meets requirements."""
        from services.transcript_service import TranscriptAnalysis, GradeGap
        
        mock_analyze.return_value = TranscriptAnalysis(
            grades={"Math": 17, "Physics": 16},
            gpa=16.5,
            strengths=["Math", "Physics"],
            weaknesses=[],
            passing_all=True,
            overall_quality="excellent",
        )
        
        # Mock no gaps (student meets all requirements)
        mock_compare.return_value = (
            [
                GradeGap("Math", 17, 16, -1, "meets", 4),
                GradeGap("Physics", 16, 14, -2, "meets", 4),
            ],
            "ready"
        )
        
        # Mock LLM summary
        mock_generate.return_value = {
            "overall_readiness": "ready",
            "analysis": [],
            "summary": "You meet all requirements for this major!",
            "strengths": ["Math", "Physics"]
        }
        
        result = analyze_grades(
            student_grades={"Math": 17, "Physics": 16},
            major_name="Computer Science",
        )
        
        assert result["success"] is True
        assert result["readiness"] == "ready"
        assert len(result["gaps"]) == 0  # No actual gaps
        assert "meet all requirements" in result["recommendations"][0]
    
    @patch('services.transcript_service.analyze_transcript')
    @patch('services.transcript_service.compare_grades_to_requirements')
    @patch('tools.transcript_tools.generate_structured_output')
    def test_analyze_grades_with_gaps(self, mock_generate, mock_compare, mock_analyze):
        """Test grade analysis when gaps exist."""
        from services.transcript_service import TranscriptAnalysis, GradeGap
        
        mock_analyze.return_value = TranscriptAnalysis(
            grades={"Math": 13, "Physics": 15},
            gpa=14.0,
            strengths=["Physics"],
            weaknesses=["Math"],
            passing_all=True,
            overall_quality="adequate",
        )
        
        # Mock gaps
        mock_compare.return_value = (
            [
                GradeGap("Math", 13, 16, 3, "significant", 1),  # Gap of 3
                GradeGap("Physics", 15, 14, -1, "meets", 4),    # No gap
            ],
            "needs_improvement"
        )
        
        # Mock LLM summary with gaps
        mock_generate.return_value = {
            "overall_readiness": "needs_improvement",
            "analysis": [
                {"subject": "Math", "recommendation": "Focus on Math"}
            ],
            "summary": "You need to improve Math.",
            "strengths": ["Physics"]
        }
        
        result = analyze_grades(
            student_grades={"Math": 13, "Physics": 15},
            major_name="Computer Science",
        )
        
        assert result["success"] is True
        assert result["readiness"] == "needs_improvement"
        assert len(result["gaps"]) == 1  # Only Math has a gap
        assert result["gaps"][0]["subject"] == "Math"
        assert result["gaps"][0]["gap"] == 3
        assert result["gaps"][0]["severity"] == "significant"
        
        # Should have recommendations
        assert len(result["recommendations"]) > 0
        assert "Math" in result["recommendations"][0]
    
    @patch('services.transcript_service.analyze_transcript')
    @patch('services.transcript_service.compare_grades_to_requirements')
    def test_analyze_grades_major_not_found(self, mock_compare, mock_analyze):
        """Test handling when major is not found."""
        from services.transcript_service import TranscriptAnalysis
        
        mock_analyze.return_value = TranscriptAnalysis(
            grades={"Math": 15},
            gpa=15.0,
            strengths=["Math"],
            weaknesses=[],
            passing_all=True,
            overall_quality="good",
        )
        
        # Mock major not found error
        mock_compare.side_effect = ValueError("Major 'Fake Major' not found")
        
        result = analyze_grades(
            student_grades={"Math": 15},
            major_name="Fake Major",
        )
        
        assert result["success"] is True
        assert result["readiness"] == "unknown"
        assert "Could not find requirement data" in result["recommendations"][0]


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestTranscriptToolsIntegration:
    """Integration tests with real components."""
    
    @pytest.mark.skipif(
        not SAMPLE_TRANSCRIPT_PATH.exists(),
        reason="Sample transcript PDF not available"
    )
    def test_parse_real_transcript(self):
        """Test parsing a real transcript PDF (if available)."""
        result = parse_transcript(str(SAMPLE_TRANSCRIPT_PATH))
        
        # Should attempt parsing
        assert "success" in result
        
        # If successful, should have grades
        if result["success"]:
            assert "grades" in result
            assert isinstance(result["grades"], dict)
    
    def test_analyze_grades_realistic_data(self):
        """Test grade analysis with realistic student data."""
        student_grades = {
            "Math": 15,
            "Physics": 14,
            "Portuguese": 13,
            "English": 16,
            "Chemistry": 14,
        }
        
        result = analyze_grades(student_grades)
        
        assert result["success"] is True
        assert "analysis" in result
        assert "gpa" in result["analysis"]
        assert 10 <= result["analysis"]["gpa"] <= 20  # Valid GPA range
