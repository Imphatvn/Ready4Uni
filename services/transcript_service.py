"""
Transcript Service - Academic Analysis Logic

Handles all transcript-related business logic:
- Parsing and validation of transcript data
- Grade comparison against major requirements
- Gap identification and prioritization
- Academic strength/weakness analysis
"""

import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from config import (
    load_majors,
    get_major_by_name,
    DEFAULT_MIN_GRADE,
    PASSING_GRADE,
    validate_grade,
)

logger = logging.getLogger(__name__)


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class GradeGap:
    """
    Represents a gap between student grade and requirement.
    
    Attributes:
        subject: Subject name
        student_grade: Student's actual grade
        required_grade: Required grade for the major
        gap: Difference (required - student)
        severity: "meets", "close", or "significant"
        priority: Priority level (1=highest)
    """
    subject: str
    student_grade: float
    required_grade: float
    gap: float
    severity: str
    priority: int = 2
    
    @property
    def is_gap(self) -> bool:
        """Check if this is actually a gap (student below requirement)."""
        return self.gap > 0


@dataclass
class TranscriptAnalysis:
    """
    Complete analysis of a student's transcript.
    
    Attributes:
        grades: Dictionary of subject → grade
        gpa: Overall GPA (if calculated)
        strengths: List of strongest subjects
        weaknesses: List of weakest subjects
        passing_all: Whether all subjects are passing
        overall_quality: "excellent", "good", "adequate", "needs_improvement"
    """
    grades: Dict[str, float]
    gpa: Optional[float] = None
    strengths: List[str] = None
    weaknesses: List[str] = None
    passing_all: bool = True
    overall_quality: str = "adequate"
    
    def __post_init__(self):
        if self.strengths is None:
            self.strengths = []
        if self.weaknesses is None:
            self.weaknesses = []


# ============================================================================
# TRANSCRIPT SERVICE
# ============================================================================

class TranscriptService:
    """Service for transcript analysis operations."""
    
    @staticmethod
    def analyze_transcript(grades: Dict[str, float]) -> TranscriptAnalysis:
        """
        Perform comprehensive analysis of a transcript.
        
        Args:
            grades: Dictionary mapping subject names to grades (0-20 scale)
            
        Returns:
            TranscriptAnalysis with insights
        """
        if not grades:
            raise ValueError("No grades provided for analysis")
        
        # Defensive: Filter out None values (safety net)
        grades = {k: v for k, v in grades.items() if v is not None}
        
        if not grades:
            raise ValueError("All grades are None - no valid data")
        
        # Validate all grades
        for subject, grade in grades.items():
            if not validate_grade(grade):
                raise ValueError(f"Invalid grade for {subject}: {grade} (must be 0-20)")
        
        # Calculate GPA
        gpa = sum(grades.values()) / len(grades)
        
        # Identify strengths (top 3 subjects)
        sorted_subjects = sorted(grades.items(), key=lambda x: x[1], reverse=True)
        strengths = [subj for subj, grade in sorted_subjects[:3] if grade >= 14]
        
        # Identify weaknesses (bottom 3 subjects)
        weaknesses = [subj for subj, grade in sorted_subjects[-3:] if grade < 14]
        
        # Check if all passing
        passing_all = all(grade >= PASSING_GRADE for grade in grades.values())
        
        # Determine overall quality
        if gpa >= 17:
            overall_quality = "excellent"
        elif gpa >= 15:
            overall_quality = "good"
        elif gpa >= 12:
            overall_quality = "adequate"
        else:
            overall_quality = "needs_improvement"
        
        logger.info(f"📊 Transcript analysis: GPA {gpa:.1f}, {overall_quality}")
        
        return TranscriptAnalysis(
            grades=grades,
            gpa=gpa,
            strengths=strengths,
            weaknesses=weaknesses,
            passing_all=passing_all,
            overall_quality=overall_quality,
        )
    
    @staticmethod
    def compare_grades_to_requirements(
        student_grades: Dict[str, float],
        major_name: str,
    ) -> Tuple[List[GradeGap], str]:
        """
        Compare student grades against major requirements.
        
        Args:
            student_grades: Student's grades
            major_name: Name of the target major
            
        Returns:
            Tuple of (list of GradeGaps, readiness_status)
            
        Raises:
            ValueError: If major not found
        """
        # Get major data
        major = get_major_by_name(major_name, fuzzy=True)
        if not major:
            raise ValueError(f"Major '{major_name}' not found in database")
        
        requirements = major.get("requirements", {})
        if not requirements:
            raise ValueError(f"No requirements data for major '{major_name}'")
        
        # Compare each required subject
        gaps = []
        
        # Import the smart matching helper
        from utils.subject_mapper import find_matching_grade
        
        for subject, required_grade in requirements.items():
            # Use normalized matching to find the grade (handles Portuguese→English)
            student_grade = find_matching_grade(student_grades, subject)
            
            if student_grade is None:
                logger.warning(f"⚠️  Subject '{subject}' required but not in transcript")
                # Assume lowest passing grade if missing
                student_grade = PASSING_GRADE
            
            gap_value = required_grade - student_grade
            
            # Determine severity
            if gap_value <= 0:
                severity = "meets"
            elif gap_value <= 2:
                severity = "close"
            else:
                severity = "significant"
            
            # Determine priority (larger gaps = higher priority)
            if gap_value > 4:
                priority = 1  # Critical
            elif gap_value > 2:
                priority = 2  # High
            elif gap_value > 0:
                priority = 3  # Medium
            else:
                priority = 4  # Low (already meets)
            
            gaps.append(GradeGap(
                subject=subject,
                student_grade=student_grade,
                required_grade=required_grade,
                gap=gap_value,
                severity=severity,
                priority=priority,
            ))
        
        # Determine overall readiness
        actual_gaps = [g for g in gaps if g.is_gap]
        
        if not actual_gaps:
            readiness = "ready"
        elif all(g.severity == "close" for g in actual_gaps):
            readiness = "mostly_ready"
        elif any(g.severity == "significant" for g in actual_gaps):
            if len([g for g in actual_gaps if g.severity == "significant"]) >= 2:
                readiness = "significant_gaps"
            else:
                readiness = "needs_improvement"
        else:
            readiness = "needs_improvement"
        
        logger.info(f"🎯 Gap analysis for {major_name}: {readiness}, {len(actual_gaps)} gaps")
        
        return gaps, readiness
    
    @staticmethod
    def identify_grade_gaps(
        student_grades: Dict[str, float],
        major_name: str,
    ) -> Dict[str, any]:
        """
        Identify and prioritize grade gaps (convenience wrapper).
        
        Args:
            student_grades: Student's grades
            major_name: Target major name
            
        Returns:
            Dictionary with gap analysis results
        """
        gaps, readiness = TranscriptService.compare_grades_to_requirements(
            student_grades, major_name
        )
        
        # Filter only actual gaps
        actual_gaps = [g for g in gaps if g.is_gap]
        
        # Sort by priority
        actual_gaps.sort(key=lambda g: g.priority)
        
        # Get subjects meeting requirements
        meeting = [g for g in gaps if not g.is_gap]
        
        return {
            "readiness": readiness,
            "total_gaps": len(actual_gaps),
            "gaps": [
                {
                    "subject": g.subject,
                    "current": g.student_grade,
                    "required": g.required_grade,
                    "gap": g.gap,
                    "severity": g.severity,
                }
                for g in actual_gaps
            ],
            "strengths": [
                {
                    "subject": g.subject,
                    "grade": g.student_grade,
                    "required": g.required_grade,
                    "excess": -g.gap,  # Negative gap = exceeding requirement
                }
                for g in meeting
            ],
            "priority_subjects": [g.subject for g in actual_gaps[:3]],  # Top 3
        }


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def analyze_transcript(grades: Dict[str, float]) -> TranscriptAnalysis:
    """Convenience wrapper for transcript analysis."""
    return TranscriptService.analyze_transcript(grades)


def compare_grades_to_requirements(
    student_grades: Dict[str, float],
    major_name: str,
) -> Tuple[List[GradeGap], str]:
    """Convenience wrapper for grade comparison."""
    return TranscriptService.compare_grades_to_requirements(student_grades, major_name)


def identify_grade_gaps(
    student_grades: Dict[str, float],
    major_name: str,
) -> Dict[str, any]:
    """Convenience wrapper for gap identification."""
    return TranscriptService.identify_grade_gaps(student_grades, major_name)
