"""
Transcript Analysis Tools

Function calling tools for transcript parsing and grade analysis.
These tools allow the agent to process uploaded transcripts and
analyze academic performance.
"""

import logging
from typing import Dict, Any, Optional
from functools import wraps
import time

from clients.pdf_client import extract_text_from_pdf
from ai import generate_structured_output
from config import TRANSCRIPT_SCHEMA, GAP_ANALYSIS_PROMPT, GAP_ANALYSIS_SCHEMA, format_prompt, get_major_by_name

logger = logging.getLogger(__name__)


# ============================================================================
# ERROR HANDLING DECORATOR
# ============================================================================

def retry_on_failure(max_retries: int = 2):
    """
    Decorator to retry tool execution on failure.
    Required by capstone guidelines for graceful error handling.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_retries:
                        logger.warning(
                            f"⚠️  {func.__name__} failed (attempt {attempt + 1}/{max_retries + 1}): {e}"
                        )
                        time.sleep(1 * (attempt + 1))  # Exponential backoff
                    else:
                        logger.error(f"❌ {func.__name__} failed after {max_retries + 1} attempts: {e}")
            
            # Return error structure instead of raising
            return {
                "success": False,
                "error": str(last_error),
                "tool": func.__name__,
            }
        
        return wrapper
    return decorator


# ============================================================================
# TRANSCRIPT TOOLS
# ============================================================================

@retry_on_failure(max_retries=2)
def parse_transcript(file_path: str) -> Dict[str, Any]:
    """
    Parse a transcript PDF and extract grade information.
    
    This tool:
    1. Extracts text from the PDF using pdfplumber
    2. Uses LLM to parse and structure the grade data
    3. Validates the extracted information
    
    Args:
        file_path: Path to the uploaded transcript PDF file
        
    Returns:
        Dictionary with:
            - success (bool): Whether parsing succeeded
            - grades (dict): Subject → grade mapping
            - student_info (dict): Student name, school, year (if found)
            - raw_text (str): Extracted text for debugging
            - confidence (str): "high", "medium", or "low"
            
    Example:
        >>> result = parse_transcript("/tmp/transcript.pdf")
        >>> print(result["grades"])
        {"Math": 15, "Physics": 17, "Portuguese": 14}
    """
    logger.info(f"📄 Parsing transcript: {file_path}")
    
    try:
        # Step 1: Extract text from PDF
        raw_text = extract_text_from_pdf(file_path)
        
        if not raw_text or len(raw_text.strip()) < 50:
            return {
                "success": False,
                "error": "PDF appears to be empty or unreadable",
                "grades": {},
            }
        
        logger.debug(f"Extracted {len(raw_text)} characters from PDF")
        
        # Step 2: Use LLM to parse grades from text
        parse_prompt = f"""You are analyzing a Portuguese high school transcript. Extract the grades from this text.

**Transcript text:**
{raw_text}

**Instructions:**
- Extract all subject grades (0-20 scale)
- Identify student name, school, and academic year if present
- Common Portuguese subject names: Matemática (Math), Física (Physics), Português (Portuguese), 
  Química (Chemistry), Biologia (Biology), História (History), Geografia (Geography), 
  Inglês (English), Filosofia (Philosophy), Educação Física (PE)
- If you see grades like "13/20" or "15 valores", extract the number
- Set parsing_confidence based on clarity: "high" if clear, "medium" if some ambiguity, "low" if very unclear

Return a JSON object matching the schema."""
        
        parsed_data = generate_structured_output(
            prompt=parse_prompt,
            schema=TRANSCRIPT_SCHEMA,
            temperature=0.1,  # Low temperature for precise extraction
        )
        
        # Step 3: Validate extracted grades
        raw_grades = parsed_data.get("grades", [])
        
        # Convert list of objects to dictionary
        grades = {}
        for item in raw_grades:
            if isinstance(item, dict) and "subject" in item and "grade" in item:
                grades[item["subject"]] = item["grade"]
        
        if not grades:
            return {
                "success": False,
                "error": "No grades found in the transcript",
                "raw_text": raw_text[:500],
            }
        
        # Validate grade values (must be 0-20)
        invalid_grades = {
            subj: grade for subj, grade in grades.items()
            if not isinstance(grade, (int, float)) or not (0 <= grade <= 20)
        }
        
        if invalid_grades:
            logger.warning(f"⚠️  Invalid grades found: {invalid_grades}")
            # Remove invalid grades
            for subj in invalid_grades:
                del grades[subj]
        
        logger.info(f"✅ Parsed {len(grades)} grades with {parsed_data.get('parsing_confidence', 'unknown')} confidence")
        
        return {
            "success": True,
            "grades": grades,
            "student_info": {
                "name": parsed_data.get("student_name"),
                "school": parsed_data.get("school"),
                "year": parsed_data.get("academic_year"),
            },
            "gpa": parsed_data.get("gpa"),
            "confidence": parsed_data.get("parsing_confidence", "medium"),
            "raw_text": raw_text[:500],  # First 500 chars for reference
        }
        
    except Exception as e:
        logger.error(f"❌ Transcript parsing failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Failed to parse transcript: {str(e)}",
            "grades": {},
        }


@retry_on_failure(max_retries=2)
def analyze_grades(
    student_grades: Dict[str, float],
    major_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Analyze student grades and compare to major requirements if specified.
    
    This tool provides:
    - Academic strength/weakness identification
    - GPA calculation
    - Gap analysis if a target major is specified
    - Prioritized improvement recommendations
    
    Args:
        student_grades: Dictionary of subject → grade (0-20 scale)
        major_name: Optional target major to compare against
        
    Returns:
        Dictionary with:
            - success (bool): Whether analysis succeeded
            - analysis (dict): Comprehensive grade analysis
            - gaps (list): Grade gaps if major specified
            - recommendations (list): Prioritized subjects to improve
            
    Example:
        >>> result = analyze_grades(
        ...     student_grades={"Math": 13, "Physics": 15},
        ...     major_name="Computer Science"
        ... )
        >>> print(result["gaps"])
        [{"subject": "Math", "current": 13, "required": 16, "gap": 3}]
    """
    logger.info(f"📊 Analyzing grades" + (f" for {major_name}" if major_name else ""))
    
    try:
        # Local imports to avoid circular dependency
        from services.transcript_service import analyze_transcript
        from utils.subject_mapper import normalize_grade_dict
        
        # Step 0: Handle MapComposite from Gemini function calling
        # Convert to regular dict if it's not already
        if not isinstance(student_grades, dict):
            student_grades = dict(student_grades)
        
        # Step 0.5: Filter out None values and ensure numeric types
        # This prevents "'<=' not supported between instances of 'int' and 'NoneType'" errors
        clean_grades = {}
        for subject, grade in student_grades.items():
            if grade is not None:
                try:
                    clean_grades[subject] = float(grade)
                except (ValueError, TypeError):
                    logger.warning(f"⚠️ Skipping invalid grade for {subject}: {grade}")
        student_grades = clean_grades
        
        if not student_grades:
            return {
                "success": False,
                "error": "No valid grades found in transcript",
            }
        
        # Step 0.75: Normalize subject names (Portuguese → English)
        student_grades = normalize_grade_dict(student_grades)
        
        # Step 1: Basic transcript analysis
        transcript_analysis = analyze_transcript(student_grades)
        
        result = {
            "success": True,
            "analysis": {
                "gpa": transcript_analysis.gpa,
                "overall_quality": transcript_analysis.overall_quality,
                "strengths": transcript_analysis.strengths,
                "weaknesses": transcript_analysis.weaknesses,
                "passing_all": transcript_analysis.passing_all,
            }
        }
        
        # Step 2: Gap analysis if major specified
        if major_name:
            try:
                # Local import to avoid circular dependency
                from services.transcript_service import compare_grades_to_requirements
                
                gap_data = compare_grades_to_requirements(student_grades, major_name)
                gaps, readiness = gap_data
                
                # Format gaps for output
                gap_list = []
                for gap in gaps:
                    if gap.is_gap:  # Only include actual gaps
                        gap_list.append({
                            "subject": gap.subject,
                            "current_grade": gap.student_grade,
                            "required_grade": gap.required_grade,
                            "gap": gap.gap,
                            "severity": gap.severity,
                            "priority": gap.priority,
                        })
                
                # Sort by priority
                gap_list.sort(key=lambda x: x["priority"])
                
                result["gaps"] = gap_list
                result["readiness"] = readiness
                result["major"] = major_name
                
                # Generate LLM-enhanced recommendations using GAP_ANALYSIS_PROMPT
                try:
                    major_data = get_major_by_name(major_name, fuzzy=True)
                    major_requirements = major_data.get("requirements", {}) if major_data else {}
                    
                    # Convert grades to clean JSON string for LLM (handles MapComposite)
                    import json
                    grades_json = json.dumps(dict(student_grades), ensure_ascii=False)
                    requirements_json = json.dumps(major_requirements, ensure_ascii=False)
                    
                    gap_prompt = format_prompt(
                        GAP_ANALYSIS_PROMPT,
                        major_name=major_name,
                        student_grades=grades_json,
                        major_requirements=requirements_json
                    )
                    
                    llm_analysis = generate_structured_output(
                        prompt=gap_prompt,
                        schema=GAP_ANALYSIS_SCHEMA,
                        temperature=0.3,
                    )
                    
                    # Post-process: Sanitize LLM output (truncate overly long subject names)
                    for item in llm_analysis.get("analysis", []):
                        subject = item.get("subject", "")
                        if len(subject) > 30:
                            # Take only first word or truncate
                            item["subject"] = subject.split()[0][:30] if subject.split() else subject[:30]
                        recommendation = item.get("recommendation", "")
                        if len(recommendation) > 150:
                            item["recommendation"] = recommendation[:150] + "..."
                    
                    # Use LLM-generated recommendations
                    result["llm_analysis"] = llm_analysis
                    
                    recommendations = [
                        item.get("recommendation", f"Improve {item.get('subject', 'this subject')}")
                        for item in llm_analysis.get("analysis", [])[:3]
                    ]
                    
                    # If no specific recommendations but summary exists, use summary
                    if not recommendations and llm_analysis.get("summary"):
                        recommendations = [llm_analysis.get("summary")]
                    
                    result["recommendations"] = recommendations or ["Focus on your weakest subjects"]
                    result["summary"] = llm_analysis.get("summary", "")
                    
                    logger.info(f"✅ LLM gap analysis generated")
                    
                except Exception as llm_error:
                    # Fallback to simple recommendations if LLM fails
                    logger.warning(f"⚠️ LLM gap analysis failed, using fallback: {llm_error}")
                    if gap_list:
                        result["recommendations"] = [
                            f"Focus on {g['subject']} (need to improve by {g['gap']:.1f} points)"
                            for g in gap_list[:3]
                        ]
                    else:
                        result["recommendations"] = [
                            f"Your grades meet all requirements for {major_name}!",
                            "Continue maintaining your strong performance"
                        ]
                
                logger.info(f"✅ Gap analysis complete: {readiness}, {len(gap_list)} gaps")
                
            except ValueError as e:
                # Major not found or no requirements
                logger.warning(f"⚠️  Could not perform gap analysis: {e}")
                result["gaps"] = []
                result["readiness"] = "unknown"
                result["recommendations"] = [
                    f"Could not find requirement data for {major_name}",
                    "Please verify the major name or try a different major"
                ]
        
        else:
            # No major specified - general recommendations
            result["recommendations"] = [
                f"Consider strengthening {subj}" 
                for subj in transcript_analysis.weaknesses[:2]
            ]
        
        return result
        
    except Exception as e:
        logger.error(f"❌ Grade analysis failed: {e}", exc_info=True)
        return {
            "success": False,
            "error": f"Failed to analyze grades: {str(e)}",
        }
