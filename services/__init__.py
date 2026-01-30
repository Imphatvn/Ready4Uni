"""
Business Logic Services Module

This module contains the core business logic for Ready4Uni:
- Chat service: Main coordinator for user interactions
- Transcript service: Academic transcript analysis and gap identification
- Major service: Major discovery and matching algorithms
- Resource service: Study resource recommendation logic

Services orchestrate multiple tools and apply domain-specific business rules.
"""

from .chat_service import (
    ChatService,
    process_user_message,
)

from .transcript_service import (
    TranscriptService,
    analyze_transcript,
    compare_grades_to_requirements,
    identify_grade_gaps,
)

from .major_service import (
    MajorService,
    match_interests_to_majors,
    get_major_details,
    search_majors,
)

from .resource_service import (
    ResourceService,
    recommend_study_resources,
    create_study_plan,
)

__all__ = [
    # Chat Service
    "ChatService",
    "process_user_message",
    
    # Transcript Service
    "TranscriptService",
    "analyze_transcript",
    "compare_grades_to_requirements",
    "identify_grade_gaps",
    
    # Major Service
    "MajorService",
    "match_interests_to_majors",
    "get_major_details",
    "search_majors",
    
    # Resource Service
    "ResourceService",
    "recommend_study_resources",
    "create_study_plan",
]
