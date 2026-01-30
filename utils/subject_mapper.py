"""
Subject name normalization utilities.

Maps Portuguese subject names (from transcripts) to standardized English names
(used in major requirements database).
"""

from typing import Dict


# Portuguese to English subject mapping
SUBJECT_NAME_MAP = {
    # Mathematics variants
    "matematica": "math",
    "matemática": "math", 
    "matemática a": "math",
    "matematica a": "math",
    "mat a": "math",
    
    # Physics variants
    "fisica": "physics",
    "física": "physics",
    "fisica e quimica": "physics",
    "física e química": "physics",
    "física e química a": "physics",
    "fisica e quimica a": "physics",
    "fis quim a": "physics",
    
    # Portuguese language
    "portugues": "portuguese",
    "português": "portuguese",
    "port": "portuguese",
    
    # English language
    "ingles": "english",
    "inglês": "english",
    "ing": "english",
    
    # Biology/Geology
    "biologia": "biology",
    "geologia": "geology",
    "biologia e geologia": "biology",
    "bio geo": "biology",
    
    # History
    "historia": "history",
    "história": "history",
    "história a": "history",
    "historia a": "history",
    
    # Geography
    "geografia": "geography",
    "geografia a": "geography",
    
    # Philosophy
    "filosofia": "philosophy",
    "filos": "philosophy",
    
    # Economics
    "economia": "economics",
    "economia a": "economics",
    
    # Chemistry (standalone)
    "quimica": "chemistry",
    "química": "chemistry",
}


def normalize_subject_name(subject: str) -> str:
    """
    Normalize a subject name to its standard English equivalent.
    
    Args:
        subject: Subject name in Portuguese or English
        
    Returns:
        Standardized English subject name, or original if no mapping exists
        
    Example:
        >>> normalize_subject_name("Matemática A")
        "math"
        >>> normalize_subject_name("Física e Química A")
        "physics"
    """
    subject_lower = subject.lower().strip()
    return SUBJECT_NAME_MAP.get(subject_lower, subject)


def normalize_grade_dict(grades: Dict[str, float]) -> Dict[str, float]:
    """
    Normalize all subject names in a grades dictionary.
    
    Args:
        grades: Dictionary mapping subject names to grades
        
    Returns:
        New dictionary with normalized subject names
        
    Example:
        >>> normalize_grade_dict({"Matemática A": 15, "Português": 14})
        {"math": 15, "portuguese": 14}
    """
    normalized = {}
    for subject, grade in grades.items():
        normalized_name = normalize_subject_name(subject)
        # Keep both original and normalized (for backwards compatibility)
        normalized[subject] = grade
        if normalized_name != subject:
            normalized[normalized_name] = grade
    
    return normalized


def find_matching_grade(grades: Dict[str, float], target_subject: str) -> float | None:
    """
    Find a grade using normalized matching.
    
    This function handles:
    - Case insensitivity: "Math" matches "math" matches "MATH"
    - Portuguese→English: "Matemática A" matches "Math"
    - Accents: "Português" matches "Portuguese"
    
    Args:
        grades: Dictionary of subject names to grades
        target_subject: The subject to look for (e.g., "Math" from requirements)
        
    Returns:
        The grade if found, None otherwise
        
    Example:
        >>> grades = {"Matemática A": 16, "Física e Química A": 15}
        >>> find_matching_grade(grades, "Math")
        16
        >>> find_matching_grade(grades, "Physics")
        15
    """
    # Normalize the target subject
    target_norm = normalize_subject_name(target_subject.lower())
    
    # Search through grades with normalization
    for subject, grade in grades.items():
        subject_norm = normalize_subject_name(subject.lower())
        if subject_norm == target_norm:
            return grade
    
    # Direct lookup as fallback (for exact matches)
    if target_subject in grades:
        return grades[target_subject]
    
    return None
