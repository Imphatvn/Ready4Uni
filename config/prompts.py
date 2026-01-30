"""
Prompt templates and tool definitions for Ready4Uni.

This module contains:
- System prompts for the agent
- Task-specific prompt templates
- Function calling tool definitions
- JSON schemas for structured outputs

All prompts should be maintained here (not hardcoded in services/tools).
"""

from typing import Dict, List

# ============================================================================
# SYSTEM PROMPTS
# ============================================================================

SYSTEM_PROMPT = """You are Ready4Uni, an intelligent and empathetic university counselor assistant helping high school students navigate major selection and university preparation.

**IMPORTANT: Always respond in English.**

Your core capabilities:
1. **Interest-based major discovery**: Analyze students' hobbies, favorite subjects, and career aspirations to suggest suitable university majors
2. **Transcript analysis**: Parse uploaded high school transcripts (PDF) to evaluate academic strengths and weaknesses
3. **Gap analysis**: Compare student grades against typical university entry requirements for specific majors
4. **Resource recommendations**: Suggest study materials, online courses, and practice resources to help students improve weak areas

Your knowledge base:
- You have curated information on 10-15 popular majors (Computer Science, Engineering, Medicine, Business, etc.)
- You know typical grade requirements for these majors at universities
- You can generate personalized study resource recommendations
- You understand the 0-20 grading scale used in Portuguese education

Your personality:
- Encouraging but realistic: Acknowledge challenges while highlighting opportunities
- Data-driven: Base recommendations on actual grades and requirements
- Student-focused: Prioritize the student's interests and career goals

Important guidelines:
- **Always respond in English**, regardless of the language of the user's message
- Always cite your data source (curated database vs general knowledge)
- When analyzing grades, be specific (e.g., "Your Math grade of 13/20 is 3 points below the typical CS requirement of 16/20")
- Explain WHY a major fits their interests, don't just list options
- Recommend free or affordable resources when possible
- If uncertain, say so and offer to explore options together
- Use a friendly, conversational tone while remaining professional

Remember: Your goal is to empower students with information and actionable steps, not to make decisions for them."""

# ============================================================================
# ROUTER PROMPT (Intent Classification)
# ============================================================================

ROUTER_PROMPT = """Analyze the user's message and classify their intent into ONE of these categories:

**Intent Categories:**

1. **major_discovery** - User wants to explore which majors fit their interests
   Examples: 
   - "I love math and physics, what should I study?"
   - "I want to work with computers, what majors are good?"
   - "Help me find a major that matches my interests"

2. **transcript_analysis** - User wants to upload/analyze their academic transcript
   Examples:
   - "Can you look at my grades?"
   - "I uploaded my transcript, am I ready for engineering?"
   - "Here's my report card"

3. **gap_analysis** - User wants to know if their grades meet requirements for a specific major
   Examples:
   - "Do I have good enough grades for Computer Science?"
   - "What subjects do I need to improve to study Medicine?"
   - "Am I ready for this major?"

4. **resource_request** - User needs study materials or course recommendations
   Examples:
   - "How can I improve my math?"
   - "What courses should I take to prepare?"
   - "Recommend resources for calculus"

5. **general_question** - General questions about universities, majors, careers, or the system
   Examples:
   - "What's the difference between CS and Software Engineering?"
   - "How does university admission work in Portugal?"
   - "What careers can I pursue with a business degree?"

6. **greeting_or_chitchat** - Greetings, thank yous, or off-topic conversation
   Examples:
   - "Hello!"
   - "Thanks for your help"
   - "What's the weather like?"

**Context awareness:**
- Consider conversation history - if they just uploaded a transcript, "analyze this" means transcript_analysis
- If multiple intents are present, prioritize the primary/explicit one
- Default to general_question if truly ambiguous

Respond with ONLY the intent category name (e.g., "major_discovery"). No explanation needed."""

# ============================================================================
# TASK-SPECIFIC PROMPTS
# ============================================================================

GAP_ANALYSIS_PROMPT = """You are analyzing a student's readiness for a specific university major based on their transcript grades.

**Task:** Compare the student's grades against the typical entry requirements for {major_name} and identify gaps.

**Student's Grades:**
{student_grades}

**Requirements for {major_name}:**
{major_requirements}

**Analysis Framework:**
1. For each required subject, calculate the gap (requirement - student_grade)
2. Categorize gaps:
   - ✅ **Meets requirement**: Student grade >= requirement
   - ⚠️ **Close** (1-2 points below): Achievable with focused effort
   - 🔴 **Significant gap** (3+ points below): Requires substantial improvement
3. Identify the student's strengths (subjects where they exceed requirements)

**Output Requirements:**
Provide a JSON object with this structure:
{{
  "overall_readiness": "ready" | "mostly_ready" | "needs_improvement" | "significant_gaps",
  "analysis": [
    {{
      "subject": "Math",
      "student_grade": 13,
      "required_grade": 16,
      "gap": 3,
      "status": "significant_gap",
      "recommendation": "Focus on calculus and algebra fundamentals"
    }}
  ],
  "strengths": ["Physics", "Portuguese"],
  "priority_subjects": ["Math"],
  "summary": "You're close to ready for Computer Science, but need to strengthen your Math foundation..."
}}

Be encouraging but honest. Highlight both strengths and areas for improvement."""

RESOURCE_GENERATION_PROMPT = """Generate personalized study resource recommendations for a high school student in Portugal.

**Context:**
- Subject: {subject}
- Specific Topic: {topic}
- Student Level: {level}
- Goal: {goal}

**Requirements:**
1. Recommend 3-5 high-quality, accessible resources
2. Prioritize FREE or low-cost options
3. Include Portuguese language resources when available (note if English-only)
4. Focus on platforms like:
   - Khan Academy (has Portuguese version for many topics)
   - YouTube (educational channels)
   - Coursera, edX, Udemy (many free courses)
   - Interactive practice sites

**Output Format (JSON):**
{{
  "subject": "{subject}",
  "resources": [
    {{
      "type": "video_course",
      "name": "Khan Academy: Cálculo Diferencial",
      "provider": "Khan Academy",
      "language": "PT",
      "free": true,
      "description": "Interactive lessons with practice problems, perfect for building calculus foundations",
      "search_hint": "Search 'Khan Academy cálculo' or visit pt.khanacademy.org"
    }},
    {{
      "type": "online_course",
      "name": "Introduction to Calculus",
      "provider": "Coursera",
      "language": "EN (PT subtitles available)",
      "free": true,
      "description": "University-level course with video lectures and assignments",
      "search_hint": "Search 'Coursera calculus free' and filter for Portuguese subtitles"
    }},
    {{
      "type": "practice_platform",
      "name": "Brilliant.org Math Fundamentals",
      "provider": "Brilliant",
      "language": "EN",
      "free": false,
      "description": "Interactive problem-solving approach (free trial available)",
      "search_hint": "Visit brilliant.org/courses/math-fundamentals"
    }}
  ],
  "study_plan": "Start with Khan Academy for foundational concepts, then move to Coursera for deeper understanding. Practice daily with exercises.",
  "estimated_time": "2-3 months with 1 hour/day"
}}

**Important:** 
- Do NOT invent URLs. Provide search hints instead.
- Be realistic about time commitment
- Explain WHY each resource is recommended"""

# ============================================================================
# TOOL DEFINITIONS (Function Calling)
# ============================================================================

TOOL_DEFINITIONS = [
    {
        "name": "parse_transcript",
        "description": "Extracts and parses grade information from an uploaded high school transcript PDF. Returns structured grade data for all subjects.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "file_path": {
                    "type": "STRING",
                    "description": "Path to the uploaded PDF file. MUST be a valid path from the Uploaded files section."
                }
            },
            "required": ["file_path"]
        }
    },
    {
        "name": "get_major_info",
        "description": "Retrieves comprehensive information about a specific university major from the curated database. Returns major description, typical requirements, career paths, and related information.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "major_name": {
                    "type": "STRING",
                    "description": "Name of the major to look up (e.g., 'Computer Science', 'Engineering', 'Medicine')"
                },
                "include_similar": {
                    "type": "BOOLEAN",
                    "description": "If true, also return similar/related majors"
                }
            },
            "required": ["major_name"]
        }
    },
    {
        "name": "get_major_suggestions",
        "description": "Suggests suitable university majors based on student's interests, favorite subjects, hobbies, and career goals. Uses semantic matching against major descriptions and keywords.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "interests": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                    "description": "List of student interests, hobbies, or favorite activities"
                },
                "favorite_subjects": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                    "description": "List of favorite school subjects"
                },
                "career_goals": {
                    "type": "STRING",
                    "description": "Student's career aspirations or dream jobs (optional)"
                },
                "top_n": {
                    "type": "INTEGER",
                    "description": "Number of major suggestions to return"
                }
            }
        }
    },
    {
        "name": "analyze_grades",
        "description": "Compares student's current grades against requirements for a specific major. Identifies which subjects meet requirements and which need improvement.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "student_grades": {
                    "type": "OBJECT",
                    "description": "Dictionary mapping subjects to grades (e.g., {\"Math\": 13, \"Physics\": 15})"
                },
                "major_name": {
                    "type": "STRING",
                    "description": "Name of the target major to compare against"
                }
            },
            "required": ["student_grades", "major_name"]
        }
    },
    {
        "name": "find_study_resources",
        "description": "Generates personalized study resource recommendations (courses, videos, practice sites) for a specific subject or topic. Resources are tailored to the student's level and goals.",
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "subject": {
                    "type": "STRING",
                    "description": "Subject area (e.g., 'Math', 'Physics', 'Portuguese')"
                },
                "topic": {
                    "type": "STRING",
                    "description": "Specific topic within the subject (e.g., 'Calculus', 'Mechanics'). Optional but helps narrow recommendations."
                },
                "level": {
                    "type": "STRING",
                    "description": "Student's current level: high_school, university_prep, beginner, or intermediate"
                },
                "goal": {
                    "type": "STRING",
                    "description": "Student's goal (e.g., 'improve from 13 to 16', 'prepare for university entrance exam')"
                }
            },
            "required": ["subject"]
        }
    }
]

# ============================================================================
# JSON SCHEMAS (Structured Outputs)
# ============================================================================

TRANSCRIPT_SCHEMA = {
    "type": "object",
    "properties": {
        "student_name": {"type": "string"},
        "school": {"type": "string"},
        "academic_year": {"type": "string"},
        "grades": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "subject": {"type": "string"},
                    "grade": {"type": "number"}
                },
                "required": ["subject", "grade"]
            }
        },
        "gpa": {"type": "number"},
        "parsing_confidence": {
            "type": "string",
            "enum": ["high", "medium", "low"]
        },
        "notes": {"type": "string"}
    },
    "required": ["grades"]
}

MAJOR_INFO_SCHEMA = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "name": {"type": "string"},
        "description": {"type": "string"},
        "requirements": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "subject": {"type": "string"},
                    "grade": {"type": "number"}
                },
                "required": ["subject", "grade"]
            }
        },
        "keywords": {
            "type": "array",
            "items": {"type": "string"}
        },
        "career_paths": {
            "type": "array",
            "items": {"type": "string"}
        },
        "universities": {
            "type": "array",
            "items": {"type": "string"}
        }
    },
    "required": ["name", "description", "requirements"]
}

GAP_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "overall_readiness": {
            "type": "string",
            "enum": ["ready", "mostly_ready", "needs_improvement", "significant_gaps"]
        },
        "analysis": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "subject": {
                        "type": "string",
                        "description": "ONLY the subject name (e.g., 'Math', 'Physics', 'Portuguese'). Maximum 30 characters. Do NOT include grades, explanations, or any other text."
                    },
                    "student_grade": {"type": "number"},
                    "required_grade": {"type": "number"},
                    "gap": {"type": "number"},
                    "status": {
                        "type": "string",
                        "enum": ["meets_requirement", "close", "significant_gap"]
                    },
                    "recommendation": {
                        "type": "string",
                        "description": "Brief study recommendation. Maximum 100 characters."
                    }
                }
            }
        },
        "strengths": {
            "type": "array",
            "items": {"type": "string"}
        },
        "priority_subjects": {
            "type": "array",
            "items": {"type": "string"}
        },
        "summary": {"type": "string"}
    },
    "required": ["overall_readiness", "analysis", "summary"]
}

RESOURCE_SCHEMA = {
    "type": "object",
    "properties": {
        "subject": {"type": "string"},
        "resources": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["video_course", "online_course", "practice_platform", "textbook", "youtube_channel"]
                    },
                    "name": {"type": "string"},
                    "provider": {"type": "string"},
                    "language": {"type": "string"},
                    "free": {"type": "boolean"},
                    "description": {"type": "string"},
                    "search_hint": {"type": "string"}
                },
                "required": ["type", "name", "provider", "language", "description", "search_hint"]
            }
        },
        "study_plan": {"type": "string"},
        "estimated_time": {"type": "string"}
    },
    "required": ["subject", "resources"]
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def format_prompt(template: str, **kwargs) -> str:
    """
    Format a prompt template with provided variables.
    
    Args:
        template: Prompt template string with {placeholders}
        **kwargs: Variables to substitute into the template
        
    Returns:
        Formatted prompt string
    """
    try:
        return template.format(**kwargs)
    except KeyError as e:
        raise ValueError(f"Missing required prompt variable: {e}")


def get_tool_by_name(tool_name: str) -> Dict:
    """
    Retrieve tool definition by name.
    
    Args:
        tool_name: Name of the tool to retrieve
        
    Returns:
        Tool definition dictionary
        
    Raises:
        ValueError: If tool name not found
    """
    tool = next((t for t in TOOL_DEFINITIONS if t["name"] == tool_name), None)
    if not tool:
        available = [t["name"] for t in TOOL_DEFINITIONS]
        raise ValueError(f"Tool '{tool_name}' not found. Available: {available}")
    return tool
