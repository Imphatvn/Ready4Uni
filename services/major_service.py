"""
Major Service - Major Discovery and Matching Logic

Handles major-related operations:
- Interest-to-major matching algorithm
- Major search and filtering
- Major recommendations
- Similarity scoring
"""

import logging
from typing import List, Dict, Optional, Set
from dataclasses import dataclass

from config import load_majors, get_major_by_name, get_major_by_id

logger = logging.getLogger(__name__)


# ============================================================================
# DATA STRUCTURES
# ============================================================================

@dataclass
class MajorMatch:
    """
    A major match with scoring information.
    
    Attributes:
        major: The major dictionary
        score: Match score (0.0 - 1.0)
        reasons: List of reasons why this major matched
        matching_keywords: Keywords that matched
    """
    major: Dict
    score: float
    reasons: List[str]
    matching_keywords: Set[str]
    
    @property
    def name(self) -> str:
        return self.major["name"]
    
    @property
    def id(self) -> str:
        return self.major["id"]


# ============================================================================
# MAJOR SERVICE
# ============================================================================

class MajorService:
    """Service for major discovery and matching operations."""
    
    @staticmethod
    def match_interests_to_majors(
        interests: Optional[List[str]] = None,
        favorite_subjects: Optional[List[str]] = None,
        career_goals: Optional[str] = None,
        top_n: int = 5,
    ) -> List[MajorMatch]:
        """
        Match student interests to suitable majors.
        
        Uses keyword matching and semantic similarity to find best-fit majors.
        
        Args:
            interests: List of interests/hobbies (e.g., ["programming", "math"])
            favorite_subjects: List of favorite school subjects
            career_goals: Career aspirations (optional)
            top_n: Number of top matches to return
            
        Returns:
            List of MajorMatch objects, sorted by score (highest first)
        """
        # Ensure top_n is an integer (Gemini may pass it as string)
        top_n = int(top_n) if top_n else 5
        
        majors = load_majors()
        matches = []
        
        # Normalize inputs
        interests_lower = [i.lower() for i in (interests or [])]
        subjects_lower = [s.lower() for s in (favorite_subjects or [])]
        career_lower = career_goals.lower() if career_goals else ""
        
        for major in majors:
            score = 0.0
            reasons = []
            matching_kw = set()
            
            # Check keyword matches
            major_keywords = [kw.lower() for kw in major.get("keywords", [])]
            
            # Interest matching (40% weight)
            interest_matches = set(interests_lower) & set(major_keywords)
            if interest_matches:
                score += 0.4 * (len(interest_matches) / max(len(interests_lower), 1))
                reasons.append(f"Matches your interests: {', '.join(interest_matches)}")
                matching_kw.update(interest_matches)
            
            # Subject matching (30% weight)
            if favorite_subjects:
                from utils.subject_mapper import normalize_subject_name
                
                # Map favorite subjects to normalized names
                mapped_subjects = []
                for s in subjects_lower:
                    mapped_subjects.append(s)
                    normalized = normalize_subject_name(s)
                    if normalized != s:
                        mapped_subjects.append(normalized)
                
                # Check if favorite subjects align with major requirements
                requirements = major.get("requirements", {})
                req_keys_lower = [rk.lower() for rk in requirements.keys()]
                subject_matches = set(mapped_subjects) & set(req_keys_lower)
                
                if subject_matches:
                    score += 0.3 * (len(subject_matches) / len(requirements))
                    reasons.append(f"Aligns with your strong subjects: {', '.join(subject_matches)}")
                    matching_kw.update(subject_matches)
            
            # Career goal matching (30% weight)
            if career_goals:
                career_paths = [cp.lower() for cp in major.get("career_paths", [])]
                if any(career_lower in cp or cp in career_lower for cp in career_paths):
                    score += 0.3
                    reasons.append("Matches your career goals")
            
            # Bonus: Description matching (semantic)
            description = major.get("description", "").lower()
            desc_matches = sum(1 for interest in interests_lower if interest in description)
            if desc_matches > 0 and len(interests_lower) > 0:
                score += 0.1 * min(desc_matches / len(interests_lower), 1.0)
            
            # Only include majors with some match
            if score > 0:
                matches.append(MajorMatch(
                    major=major,
                    score=score,
                    reasons=reasons if reasons else ["General interest alignment"],
                    matching_keywords=matching_kw,
                ))
        
        # Sort by score
        matches.sort(key=lambda m: m.score, reverse=True)
        
        logger.info(f"🎯 Matched {len(matches)} majors, returning top {top_n}")
        
        return matches[:top_n]
    
    @staticmethod
    def get_major_details(major_name: str) -> Optional[Dict]:
        """
        Get complete details for a specific major.
        
        Args:
            major_name: Name of the major
            
        Returns:
            Major dictionary with all metadata, or None if not found
        """
        major = get_major_by_name(major_name, fuzzy=True)
        
        if major:
            logger.info(f"📖 Retrieved details for {major['name']}")
        else:
            logger.warning(f"⚠️  Major '{major_name}' not found")
        
        return major
    
    @staticmethod
    def search_majors(
        query: str,
        filters: Optional[Dict] = None,
    ) -> List[Dict]:
        """
        Search majors by name, keywords, or description.
        
        Args:
            query: Search query string
            filters: Optional filters (e.g., {"min_salary": 30000})
            
        Returns:
            List of matching majors
        """
        majors = load_majors()
        query_lower = query.lower()
        results = []
        
        for major in majors:
            # Check name match
            if query_lower in major["name"].lower():
                results.append(major)
                continue
            
            # Check keywords
            keywords = [kw.lower() for kw in major.get("keywords", [])]
            if any(query_lower in kw or kw in query_lower for kw in keywords):
                results.append(major)
                continue
            
            # Check description
            if query_lower in major.get("description", "").lower():
                results.append(major)
                continue
        
        # Apply filters (future enhancement)
        if filters:
            # Example: filter by minimum requirements, salary, etc.
            pass
        
        logger.info(f"🔍 Search '{query}' returned {len(results)} results")
        
        return results
    
    @staticmethod
    def get_similar_majors(major_name: str, top_n: int = 3) -> List[Dict]:
        """
        Find majors similar to a given major.
        
        Args:
            major_name: Name of the reference major
            top_n: Number of similar majors to return
            
        Returns:
            List of similar major dictionaries
        """
        reference = get_major_by_name(major_name, fuzzy=True)
        if not reference:
            return []
        
        majors = load_majors()
        ref_keywords = set(kw.lower() for kw in reference.get("keywords", []))
        
        similarities = []
        
        for major in majors:
            # Skip the reference major itself
            if major["id"] == reference["id"]:
                continue
            
            # Calculate keyword overlap
            major_keywords = set(kw.lower() for kw in major.get("keywords", []))
            overlap = len(ref_keywords & major_keywords)
            
            if overlap > 0:
                similarity = overlap / len(ref_keywords | major_keywords)
                similarities.append((major, similarity))
        
        # Sort by similarity
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return [major for major, _ in similarities[:top_n]]


# ============================================================================
# CONVENIENCE FUNCTIONS
# ============================================================================

def match_interests_to_majors(
    interests: Optional[List[str]] = None,
    favorite_subjects: Optional[List[str]] = None,
    career_goals: Optional[str] = None,
    top_n: int = 5,
) -> List[MajorMatch]:
    """Convenience wrapper for interest matching."""
    # Ensure top_n is an integer (Gemini may pass it as string)
    top_n = int(top_n) if top_n else 5
    return MajorService.match_interests_to_majors(
        interests, favorite_subjects, career_goals, top_n
    )


def get_major_details(major_name: str) -> Optional[Dict]:
    """Convenience wrapper for getting major details."""
    return MajorService.get_major_details(major_name)


def search_majors(query: str, filters: Optional[Dict] = None) -> List[Dict]:
    """Convenience wrapper for major search."""
    return MajorService.search_majors(query, filters)
