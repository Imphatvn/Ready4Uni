"""
Application settings and configuration values.

This module centralizes all configuration values including:
- File paths
- API keys and credentials
- Model parameters
- Application constants
- Data loading utilities

Environment variables are loaded via python-dotenv.
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ============================================================================
# PATHS
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
DATA_DIR = BASE_DIR / "data"
ASSETS_DIR = BASE_DIR / "assets"
DOCS_DIR = BASE_DIR / "docs"

# ============================================================================
# LLM CONFIGURATION
# ============================================================================

# Gemini API Settings
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise ValueError(
        "GOOGLE_API_KEY not found in environment variables. "
        "Please set it in your .env file."
    )

# Model Parameters
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "8192"))
TOP_P = float(os.getenv("TOP_P", "0.95"))
TOP_K = int(os.getenv("TOP_K", "40"))

# Retry and Timeout Settings
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
RETRY_DELAY = float(os.getenv("RETRY_DELAY", "1.0"))  # seconds
TIMEOUT = int(os.getenv("TIMEOUT", "30"))  # seconds

# ============================================================================
# LANGFUSE OBSERVABILITY
# ============================================================================

LANGFUSE_PUBLIC_KEY = os.getenv("LANGFUSE_PUBLIC_KEY")
LANGFUSE_SECRET_KEY = os.getenv("LANGFUSE_SECRET_KEY")
LANGFUSE_HOST = os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")

# Enable/disable Langfuse tracing
LANGFUSE_ENABLED = os.getenv("LANGFUSE_ENABLED", "true").lower() == "true"

if LANGFUSE_ENABLED and (not LANGFUSE_PUBLIC_KEY or not LANGFUSE_SECRET_KEY):
    print("⚠️  Warning: Langfuse is enabled but keys are missing. Tracing will be disabled.")
    LANGFUSE_ENABLED = False

# ============================================================================
# APPLICATION SETTINGS
# ============================================================================

# Grading System (Portuguese 0-20 scale)
DEFAULT_MIN_GRADE = 12  # Minimum grade for university admission (generally)
PASSING_GRADE = 10  # Minimum passing grade in Portuguese system
MAX_GRADE = 20

# File Upload Settings
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))
SUPPORTED_PDF_EXTENSIONS = [".pdf"]

# Session Settings
SESSION_TIMEOUT_MINUTES = int(os.getenv("SESSION_TIMEOUT_MINUTES", "30"))

# UI Settings
APP_TITLE = "Ready4Uni 🎓"
APP_SUBTITLE = "Your intelligent companion for university major selection"
PAGE_ICON = "🎓"

# ============================================================================
# CRISIS/SAFETY DETECTION
# ============================================================================

# Keywords that indicate potential crisis/self-harm situations
# These trigger an immediate compassionate response with helpline resources
CRISIS_KEYWORDS = [
    "hurt myself", "kill myself", "suicide", "end my life",
    "want to die", "self harm", "self-harm", "cutting myself",
    "don't want to live", "no reason to live", "better off dead",
    "end it all", "not worth living", "take my own life",
]

# Compassionate response with crisis resources
CRISIS_RESPONSE = """
I'm really concerned about what you've shared. Your wellbeing matters more than any academic decision.

**Please reach out to someone who can help:**

🇵🇹 **Portugal:**
- SOS Voz Amiga: 213 544 545 (daily 15h-22h)
- Telefone da Amizade: 222 080 707

🌍 **International:**
- International Association for Suicide Prevention: https://www.iasp.info/resources/Crisis_Centres/

You're not alone. Please talk to a trusted adult, counselor, or call one of these helplines. They're there for you. 💙
"""

# ============================================================================
# MAJOR DATA MANAGEMENT
# ============================================================================

# Cache for majors data to avoid repeated file reads
_MAJORS_CACHE: Optional[List[Dict]] = None


def load_majors(force_reload: bool = False) -> List[Dict]:
    """
    Load major data from JSON file with caching.
    
    Args:
        force_reload: If True, bypass cache and reload from disk
        
    Returns:
        List of major dictionaries with metadata and requirements
        
    Raises:
        FileNotFoundError: If majors.json doesn't exist
        ValueError: If JSON is malformed
    """
    global _MAJORS_CACHE
    
    if _MAJORS_CACHE is not None and not force_reload:
        return _MAJORS_CACHE
    
    majors_file = DATA_DIR / "majors.json"
    
    if not majors_file.exists():
        raise FileNotFoundError(
            f"Majors data file not found at {majors_file}. "
            f"Please create data/majors.json with major information."
        )
    
    try:
        with open(majors_file, "r", encoding="utf-8") as f:
            _MAJORS_CACHE = json.load(f)
        
        # Validate structure
        if not isinstance(_MAJORS_CACHE, list):
            raise ValueError("majors.json must contain a list of major objects")
        
        if len(_MAJORS_CACHE) == 0:
            raise ValueError("majors.json is empty")
        
        # Validate each major has required fields
        required_fields = ["id", "name", "description", "requirements"]
        for idx, major in enumerate(_MAJORS_CACHE):
            missing = [f for f in required_fields if f not in major]
            if missing:
                raise ValueError(
                    f"Major at index {idx} is missing required fields: {missing}"
                )
        
        print(f"✅ Loaded {len(_MAJORS_CACHE)} majors from {majors_file}")
        return _MAJORS_CACHE
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in majors.json: {e}")


def get_major_by_id(major_id: str) -> Optional[Dict]:
    """
    Retrieve a major by its ID.
    
    Args:
        major_id: Unique identifier for the major (e.g., "computer_science")
        
    Returns:
        Major dictionary if found, None otherwise
    """
    majors = load_majors()
    return next((m for m in majors if m["id"] == major_id), None)


def get_major_by_name(name: str, fuzzy: bool = False) -> Optional[Dict]:
    """
    Retrieve a major by its name.
    
    Args:
        name: Name of the major (e.g., "Computer Science")
        fuzzy: If True, perform case-insensitive partial matching
        
    Returns:
        Major dictionary if found, None otherwise
    """
    majors = load_majors()
    name_lower = name.lower()
    
    if fuzzy:
        # Try partial match
        for major in majors:
            if name_lower in major["name"].lower():
                return major
            # Also check Portuguese name if it exists
            if "name_pt" in major and name_lower in major["name_pt"].lower():
                return major
    else:
        # Exact match (case-insensitive)
        return next(
            (m for m in majors if m["name"].lower() == name_lower),
            None
        )
    
    return None


def get_all_major_names() -> List[str]:
    """
    Get a list of all available major names.
    
    Returns:
        List of major names in English
    """
    majors = load_majors()
    return [m["name"] for m in majors]


def get_subjects_for_major(major_id: str) -> List[str]:
    """
    Get required subjects for a specific major.
    
    Args:
        major_id: Unique identifier for the major
        
    Returns:
        List of subject names (e.g., ["Math", "Physics"])
    """
    major = get_major_by_id(major_id)
    if major and "requirements" in major:
        return list(major["requirements"].keys())
    return []


# ============================================================================
# VALIDATION HELPERS
# ============================================================================

def validate_grade(grade: float) -> bool:
    """
    Validate if a grade is within the Portuguese grading scale.
    
    Args:
        grade: Grade value to validate
        
    Returns:
        True if valid (0-20), False otherwise
    """
    return 0 <= grade <= MAX_GRADE


def validate_transcript_structure(transcript_data: Dict) -> tuple[bool, Optional[str]]:
    """
    Validate the structure of parsed transcript data.
    
    Args:
        transcript_data: Dictionary containing transcript information
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not isinstance(transcript_data, dict):
        return False, "Transcript data must be a dictionary"
    
    if "grades" not in transcript_data:
        return False, "Missing 'grades' field"
    
    if not isinstance(transcript_data["grades"], dict):
        return False, "'grades' must be a dictionary"
    
    # Validate each grade
    for subject, grade in transcript_data["grades"].items():
        if not isinstance(grade, (int, float)):
            return False, f"Grade for {subject} must be numeric, got {type(grade)}"
        
        if not validate_grade(grade):
            return False, f"Grade for {subject} ({grade}) is out of range (0-20)"
    
    return True, None


# ============================================================================
# DEVELOPMENT / DEBUG SETTINGS
# ============================================================================

DEBUG = os.getenv("DEBUG", "false").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

# Print configuration summary on import (only in debug mode)
if DEBUG:
    print("\n" + "="*60)
    print("🔧 Ready4Uni Configuration Loaded")
    print("="*60)
    print(f"Model: {GEMINI_MODEL}")
    print(f"Temperature: {TEMPERATURE}")
    print(f"Max Tokens: {MAX_TOKENS}")
    print(f"Langfuse: {'✅ Enabled' if LANGFUSE_ENABLED else '❌ Disabled'}")
    print(f"Data Directory: {DATA_DIR}")
    print(f"Debug Mode: {DEBUG}")
    print("="*60 + "\n")
