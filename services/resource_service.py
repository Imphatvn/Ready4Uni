"""
Resource Service - Study Resource Recommendation Logic

Handles resource recommendation and study planning:
- Generate resource recommendations via LLM
- Create structured study plans
- Prioritize resources by effectiveness
"""

import logging
from typing import Dict, List, Optional
from dataclasses import dataclass

from ai import generate_structured_output, call_llm
from config import RESOURCE_GENERATION_PROMPT, RESOURCE_SCHEMA, format_prompt

logger = logging.getLogger(__name__)


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class StudyResource:
    """
    A single study resource recommendation.
    
    Attributes:
        name: Resource name
        provider: Platform/provider (e.g., "Khan Academy")
        type: Resource type (video_course, online_course, etc.)
        language: Language (PT, EN, etc.)
        free: Whether the resource is free
        description: Why this resource is recommended
        search_hint: How to find it (instead of direct URL)
    """
    name: str
    provider: str
    type: str
    language: str
    free: bool
    description: str
    search_hint: str


@dataclass
class StudyPlan:
    """
    A complete study plan with resources and timeline.
    
    Attributes:
        subject: Subject being studied
        topic: Specific topic (if applicable)
        resources: List of recommended resources
        plan: Study plan description
        estimated_time: Estimated time commitment
        priority_order: Ordered list of resource names
    """
    subject: str
    topic: Optional[str]
    resources: List[StudyResource]
    plan: str
    estimated_time: str
    priority_order: List[str]


# ============================================================================
# RESOURCE SERVICE
# ============================================================================

class ResourceService:
    """Service for study resource recommendations."""
    
    @staticmethod
    def recommend_study_resources(
        subject: str,
        topic: Optional[str] = None,
        level: str = "high_school",
        goal: Optional[str] = None,
    ) -> List[StudyResource]:
        """
        Generate personalized study resource recommendations.
        
        Uses LLM to recommend resources based on subject, topic, level, and goal.
        
        Args:
            subject: Subject area (e.g., "Math", "Physics")
            topic: Specific topic (e.g., "Calculus") - optional
            level: Student level (high_school, university_prep, etc.)
            goal: Specific goal (e.g., "improve from 13 to 16")
            
        Returns:
            List of StudyResource objects
        """
        logger.info(f"📚 Generating resources for {subject}" + (f" - {topic}" if topic else ""))
        
        try:
            # Format the prompt
            prompt = format_prompt(
                RESOURCE_GENERATION_PROMPT,
                subject=subject,
                topic=topic or "general",
                level=level,
                goal=goal or "improve understanding and grades",
            )
            
            # Generate structured output
            result = generate_structured_output(
                prompt=prompt,
                schema=RESOURCE_SCHEMA,
                temperature=0.7,  # Balance creativity and consistency
            )
            
            # Parse resources
            resources = []
            for res_data in result.get("resources", []):
                # Ensure mandatory fields are present to avoid KeyError
                if not all(k in res_data for k in ["name", "provider", "type", "language", "description", "search_hint"]):
                    logger.warning(f"⚠️  Skipping incomplete resource: {res_data.get('name', 'Unknown')}")
                    continue
                    
                resources.append(StudyResource(
                    name=res_data["name"],
                    provider=res_data["provider"],
                    type=res_data["type"],
                    language=res_data["language"],
                    free=res_data.get("free", True),
                    description=res_data["description"],
                    search_hint=res_data["search_hint"],
                ))
            
            logger.info(f"✅ Generated {len(resources)} resource recommendations")
            
            return resources
            
        except Exception as e:
            logger.error(f"❌ Resource generation failed: {e}")
            # Return fallback recommendations
            return ResourceService._get_fallback_resources(subject)
    
    @staticmethod
    def create_study_plan(
        subject: str,
        topic: Optional[str] = None,
        current_grade: Optional[float] = None,
        target_grade: Optional[float] = None,
        available_time_per_week: Optional[int] = None,
    ) -> StudyPlan:
        """
        Create a comprehensive study plan with resources and timeline.
        
        Args:
            subject: Subject to study
            topic: Specific topic (optional)
            current_grade: Student's current grade (0-20)
            target_grade: Target grade (0-20)
            available_time_per_week: Hours available per week
            
        Returns:
            StudyPlan object with structured recommendations
        """
        logger.info(f"📅 Creating study plan for {subject}")
        
        # Determine level and goal
        if current_grade and target_grade:
            gap = target_grade - current_grade
            if gap <= 1:
                level = "university_prep"
                goal = f"maintain and refine knowledge (currently {current_grade}/20)"
            elif gap <= 3:
                level = "high_school"
                goal = f"improve from {current_grade}/20 to {target_grade}/20"
            else:
                level = "beginner"
                goal = f"build foundations to improve from {current_grade}/20 to {target_grade}/20"
        else:
            level = "high_school"
            goal = "improve understanding and grades"
        
        # Get resources
        resources = ResourceService.recommend_study_resources(
            subject=subject,
            topic=topic,
            level=level,
            goal=goal,
        )
        
        # Generate study plan narrative
        time_str = f"{available_time_per_week} hours/week" if available_time_per_week else "flexible schedule"
        plan_prompt = f"""Create a brief study plan for a student who wants to {goal} in {subject}{f' (specifically {topic})' if topic else ''}.

Available time: {time_str}
Resources available: {len(resources)} curated resources

Provide a 3-4 sentence study plan covering:
1. Where to start (foundational concepts)
2. How to progress (sequence of topics)
3. How to practice (exercises, problems)
4. Realistic timeline

Keep it encouraging and actionable."""
        
        try:
            plan_text = call_llm(
                prompt=plan_prompt,
                temperature=0.7,
            )
        except Exception as e:
            logger.error(f"Plan generation failed: {e}")
            plan_text = f"Start with foundational {topic or subject} concepts, practice regularly with exercises, and gradually work through more advanced material. Consistency is key!"
        
        # Estimate time
        if current_grade and target_grade:
            gap = target_grade - current_grade
            if gap <= 1:
                estimated_time = "2-4 weeks with regular practice"
            elif gap <= 3:
                estimated_time = "2-3 months with 1 hour/day"
            else:
                estimated_time = "4-6 months with consistent effort"
        else:
            estimated_time = "2-3 months with regular practice"
        
        # Priority order: free first, then by type
        priority = []
        for res in sorted(resources, key=lambda r: (not r.free, r.type)):
            priority.append(res.name)
        
        return StudyPlan(
            subject=subject,
            topic=topic,
            resources=resources,
            plan=plan_text,
            estimated_time=estimated_time,
            priority_order=priority,
        )
    
    @staticmethod
    def _get_fallback_resources(subject: str) -> List[StudyResource]:
        """
        Provide fallback resources if LLM generation fails.
        
        Args:
            subject: Subject name
            
        Returns:
            List of generic but reliable resources
        """
        logger.warning(f"⚠️  Using fallback resources for {subject}")
        
        return [
            StudyResource(
                name=f"Khan Academy: {subject}",
                provider="Khan Academy",
                type="video_course",
                language="PT/EN",
                free=True,
                description="Comprehensive video lessons with practice exercises",
                search_hint=f"Visit pt.khanacademy.org and search for {subject}",
            ),
            StudyResource(
                name=f"{subject} - YouTube Educational Channels",
                provider="YouTube",
                type="video_course",
                language="PT",
                free=True,
                description="Various educational channels covering the topic",
                search_hint=f"Search YouTube for '{subject} aulas' or '{subject} explicação'",
            ),
        ]


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def recommend_study_resources(
    subject: str,
    topic: Optional[str] = None,
    level: str = "high_school",
    goal: Optional[str] = None,
) -> List[StudyResource]:
    """Convenience wrapper for resource recommendations."""
    return ResourceService.recommend_study_resources(subject, topic, level, goal)


def create_study_plan(
    subject: str,
    topic: Optional[str] = None,
    current_grade: Optional[float] = None,
    target_grade: Optional[float] = None,
    available_time_per_week: Optional[int] = None,
) -> StudyPlan:
    """Convenience wrapper for study plan creation."""
    return ResourceService.create_study_plan(
        subject, topic, current_grade, target_grade, available_time_per_week
    )
