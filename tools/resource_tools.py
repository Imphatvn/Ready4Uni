"""
Study Resource Tools

Function calling tools for generating personalized study resource
recommendations and study plans.
"""

import logging
from typing import Dict, List, Any, Optional

from services.resource_service import (
    recommend_study_resources,
    create_study_plan,
    StudyResource,
    StudyPlan,
)
from tools.transcript_tools import retry_on_failure

logger = logging.getLogger(__name__)


# ============================================================================
# RESOURCE TOOLS
# ============================================================================

@retry_on_failure(max_retries=2)
def find_study_resources(
    subject: str,
    topic: Optional[str] = None,
    level: str = "high_school",
    goal: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Find personalized study resources for a specific subject or topic.
    
    Uses LLM to generate recommendations based on:
    - Subject and topic
    - Student level
    - Specific learning goals
    
    Args:
        subject: Subject area (e.g., "Math", "Physics", "Portuguese")
        topic: Specific topic (e.g., "Calculus", "Mechanics") - optional
        level: Student level - "high_school", "university_prep", "beginner", "intermediate"
        goal: Specific goal (e.g., "improve from 13 to 16", "prepare for exam")
        
    Returns:
        Dictionary with:
            - success (bool): Whether resources were generated
            - resources (list): List of recommended resources
            - count (int): Number of resources
            - subject (str): Subject for which resources were found
            
    Example:
        >>> result = find_study_resources(
        ...     subject="Math",
        ...     topic="Calculus",
        ...     goal="improve from 13/20 to 16/20"
        ... )
        >>> for resource in result["resources"]:
        ...     print(f"{resource['name']} ({resource['provider']})")
    """
    logger.info(f"📚 Finding resources for {subject}" + (f" - {topic}" if topic else ""))
    
    try:
        # Use resource service to generate recommendations
        resources: List[StudyResource] = recommend_study_resources(
            subject=subject,
            topic=topic,
            level=level,
            goal=goal,
        )
        
        if not resources:
            return {
                "success": False,
                "error": "Could not generate resource recommendations",
                "resources": [],
            }
        
        # Format resources for output
        formatted_resources = []
        for resource in resources:
            formatted_resources.append({
                "name": resource.name,
                "provider": resource.provider,
                "type": resource.type,
                "language": resource.language,
                "free": resource.free,
                "description": resource.description,
                "search_hint": resource.search_hint,
            })
        
        logger.info(f"✅ Found {len(formatted_resources)} resources for {subject}")
        
        return {
            "success": True,
            "resources": formatted_resources,
            "count": len(formatted_resources),
            "subject": subject,
            "topic": topic,
        }
        
    except Exception as e:
        logger.error(f"❌ find_study_resources failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "resources": [],
        }


@retry_on_failure(max_retries=2)
def create_personalized_study_plan(
    subject: str,
    topic: Optional[str] = None,
    current_grade: Optional[float] = None,
    target_grade: Optional[float] = None,
    available_time_per_week: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Create a comprehensive study plan with resources and timeline.
    
    Generates a personalized plan that includes:
    - Curated study resources
    - Step-by-step study approach
    - Realistic timeline
    - Priority ordering
    
    Args:
        subject: Subject to study (e.g., "Math")
        topic: Specific topic (e.g., "Calculus") - optional
        current_grade: Student's current grade (0-20 scale)
        target_grade: Desired grade (0-20 scale)
        available_time_per_week: Hours available per week for study
        
    Returns:
        Dictionary with:
            - success (bool): Whether plan was created
            - plan (str): Study plan narrative
            - resources (list): Recommended resources in priority order
            - estimated_time (str): Time estimate to achieve goal
            - priority_order (list): Subjects/topics in order of importance
            
    Example:
        >>> result = create_personalized_study_plan(
        ...     subject="Math",
        ...     current_grade=13,
        ...     target_grade=16,
        ...     available_time_per_week=5
        ... )
        >>> print(result["plan"])
        >>> print(result["estimated_time"])
    """
    logger.info(f"📅 Creating study plan for {subject}")
    
    try:
        # Use resource service to create plan
        study_plan: StudyPlan = create_study_plan(
            subject=subject,
            topic=topic,
            current_grade=current_grade,
            target_grade=target_grade,
            available_time_per_week=available_time_per_week,
        )
        
        # Format resources
        formatted_resources = [
            {
                "name": res.name,
                "provider": res.provider,
                "type": res.type,
                "language": res.language,
                "free": res.free,
                "description": res.description,
                "search_hint": res.search_hint,
            }
            for res in study_plan.resources
        ]
        
        logger.info(f"✅ Created study plan for {subject}")
        
        return {
            "success": True,
            "plan": study_plan.plan,
            "resources": formatted_resources,
            "estimated_time": study_plan.estimated_time,
            "priority_order": study_plan.priority_order,
            "subject": subject,
            "topic": topic,
        }
        
    except Exception as e:
        logger.error(f"❌ create_personalized_study_plan failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }
