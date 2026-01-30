"""
Major Discovery Tools

Function calling tools for major information retrieval and matching.
Implements hybrid approach: curated data + web search fallback.
"""

import logging
from typing import Dict, List, Any, Optional

from services.major_service import (
    match_interests_to_majors,
    get_major_details,
    search_majors as search_majors_service,
    MajorMatch,
)
from config import load_majors, get_major_by_name
from tools.transcript_tools import retry_on_failure

logger = logging.getLogger(__name__)


# ============================================================================
# MAJOR TOOLS
# ============================================================================

@retry_on_failure(max_retries=2)
def get_major_info(
    major_name: str,
    include_similar: bool = False,
) -> Dict[str, Any]:
    """
    Get comprehensive information about a specific university major.
    
    Hybrid approach:
    1. First checks curated database (data/majors.json)
    2. Falls back to web search if not found (future enhancement)
    
    Args:
        major_name: Name of the major (e.g., "Computer Science", "Engineering")
        include_similar: Whether to include similar majors
        
    Returns:
        Dictionary with:
            - success (bool): Whether major was found
            - major (dict): Complete major information
            - source (str): "curated_data" or "web_search"
            - similar_majors (list): If include_similar=True
            
    Example:
        >>> result = get_major_info("Computer Science")
        >>> print(result["major"]["requirements"])
        {"Math": 16, "Physics": 14, "Portuguese": 12}
    """
    logger.info(f"🔍 Getting info for major: {major_name}")
    
    try:
        # Step 1: Check curated database
        major = get_major_details(major_name)
        
        if major:
            result = {
                "success": True,
                "major": major,
                "source": "curated_data",
            }
            
            # Add similar majors if requested
            if include_similar:
                from services.major_service import MajorService
                similar = MajorService.get_similar_majors(major_name, top_n=3)
                result["similar_majors"] = [
                    {"name": m["name"], "id": m["id"]} 
                    for m in similar
                ]
            
            logger.info(f"✅ Found {major_name} in curated database")
            return result
        
        # Step 2: Web search fallback (placeholder for future)
        # TODO: Implement web search for uncommon majors
        logger.warning(f"⚠️  Major '{major_name}' not found in curated database")
        
        return {
            "success": False,
            "error": f"Major '{major_name}' not found. Try: Computer Science, Engineering, Medicine, Business, or similar common majors.",
            "suggestion": "Use get_major_suggestions to find majors based on your interests",
        }
        
    except Exception as e:
        logger.error(f"❌ get_major_info failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }


@retry_on_failure(max_retries=2)
def get_major_suggestions(
    interests: Optional[List[str]] = None,
    favorite_subjects: Optional[List[str]] = None,
    career_goals: Optional[str] = None,
    top_n: int = 5,
) -> Dict[str, Any]:
    """
    Suggest university majors based on student interests and preferences.
    
    Uses semantic matching to find best-fit majors from the curated database.
    
    Args:
        interests: List of interests/hobbies (e.g., ["programming", "math", "problem solving"])
        favorite_subjects: List of favorite school subjects (e.g., ["Math", "Physics"])
        career_goals: Career aspirations (e.g., "software engineer", "researcher")
        top_n: Number of suggestions to return (default 5)
        
    Returns:
        Dictionary with:
            - success (bool): Whether suggestions were generated
            - suggestions (list): Top matching majors with scores and reasons
            - total_matches (int): Total number of majors that matched
            
    Example:
        >>> result = get_major_suggestions(
        ...     interests=["programming", "algorithms"],
        ...     favorite_subjects=["Math", "Physics"]
        ... )
        >>> for suggestion in result["suggestions"]:
        ...     print(f"{suggestion['name']}: {suggestion['score']:.2f}")
    """
    logger.info(f"💡 Generating major suggestions for {len(interests or [])} interests")
    
    try:
        # Use major service to match interests
        matches: List[MajorMatch] = match_interests_to_majors(
            interests=interests,
            favorite_subjects=favorite_subjects,
            career_goals=career_goals,
            top_n=top_n,
        )
        
        if not matches:
            return {
                "success": False,
                "error": "No matching majors found. Try broader or different interests.",
                "suggestions": [],
            }
        
        # Format suggestions for output
        suggestions = []
        for match in matches:
            suggestions.append({
                "name": match.major["name"],
                "id": match.major["id"],
                "score": round(match.score, 2),
                "description": match.major["description"],
                "reasons": match.reasons,
                "career_paths": match.major.get("career_paths", []),
                "requirements": match.major.get("requirements", {}),
                "keywords": list(match.matching_keywords),
            })
        
        logger.info(f"✅ Generated {len(suggestions)} major suggestions")
        
        return {
            "success": True,
            "suggestions": suggestions,
            "total_matches": len(matches),
        }
        
    except Exception as e:
        logger.error(f"❌ get_major_suggestions failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "suggestions": [],
        }


@retry_on_failure(max_retries=1)
def search_major_database(query: str, max_results: int = 10) -> Dict[str, Any]:
    """
    Search the major database by name, keywords, or description.
    
    Useful when the user mentions a major but you're not sure of the exact name.
    
    Args:
        query: Search query (e.g., "computer", "engineering", "medical")
        max_results: Maximum number of results to return
        
    Returns:
        Dictionary with:
            - success (bool): Whether search completed
            - results (list): Matching majors
            - count (int): Number of results found
            
    Example:
        >>> result = search_major_database("computer")
        >>> print([m["name"] for m in result["results"]])
        ["Computer Science", "Computer Engineering"]
    """
    logger.info(f"🔎 Searching majors for: {query}")
    
    try:
        results = search_majors_service(query)
        
        # Limit results
        results = results[:max_results]
        
        # Format for output
        formatted_results = [
            {
                "name": major["name"],
                "id": major["id"],
                "description": major["description"][:150] + "...",  # Truncate
                "keywords": major.get("keywords", [])[:5],  # First 5 keywords
            }
            for major in results
        ]
        
        logger.info(f"✅ Found {len(formatted_results)} results for '{query}'")
        
        return {
            "success": True,
            "results": formatted_results,
            "count": len(formatted_results),
            "query": query,
        }
        
    except Exception as e:
        logger.error(f"❌ search_major_database failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "results": [],
        }
