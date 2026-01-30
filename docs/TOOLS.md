# Function Calling Tools Documentation

This document describes the function calling tools available to the Ready4Uni agent.

## Overview

Ready4Uni uses 5 core tools that enable the agent to help students with university major selection and academic planning.

---

## Tools

### 1. `parse_transcript`

**Purpose:** Extracts and parses grade information from an uploaded high school transcript PDF.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `file_path` | string | Yes | Path to the uploaded PDF file |

**Returns:**
```json
{
  "success": true,
  "grades": {"Math": 15, "Physics": 17, "Portuguese": 14},
  "student_info": {"name": "...", "school": "...", "year": "..."},
  "confidence": "high" | "medium" | "low"
}
```

---

### 2. `get_major_info`

**Purpose:** Retrieves comprehensive information about a specific university major from the curated database.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `major_name` | string | Yes | Name of the major (e.g., "Computer Science") |
| `include_similar` | boolean | No | If true, also return similar/related majors |

**Returns:**
```json
{
  "success": true,
  "major": {
    "name": "Computer Science",
    "description": "...",
    "requirements": {"Math": 16, "Physics": 14},
    "career_paths": ["Software Engineer", "Data Scientist"]
  },
  "source": "curated_data"
}
```

---

### 3. `get_major_suggestions`

**Purpose:** Suggests suitable university majors based on student's interests, favorite subjects, and career goals using semantic matching.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `interests` | array[string] | Yes | List of interests/hobbies |
| `favorite_subjects` | array[string] | No | List of favorite school subjects |
| `career_goals` | string | No | Career aspirations |
| `top_n` | integer | No | Number of suggestions to return (default: 5) |

**Returns:**
```json
{
  "success": true,
  "suggestions": [
    {
      "name": "Computer Science",
      "score": 0.85,
      "reasons": ["Matches your interests: programming, algorithms"],
      "requirements": {"Math": 16}
    }
  ]
}
```

---

### 4. `analyze_grades`

**Purpose:** Compares student's grades against requirements for a specific major to identify gaps.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `student_grades` | string | Yes | JSON string of subject-to-grade mapping |
| `major_name` | string | Yes | Target major to compare against |

**Returns:**
```json
{
  "success": true,
  "readiness": "needs_improvement",
  "gaps": [
    {"subject": "Math", "current": 13, "required": 16, "gap": 3}
  ],
  "recommendations": ["Focus on Math (need to improve by 3 points)"]
}
```

---

### 5. `find_study_resources`

**Purpose:** Generates personalized study resource recommendations for a specific subject or topic.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `subject` | string | Yes | Subject area (e.g., "Math", "Physics") |
| `topic` | string | No | Specific topic within subject |
| `level` | string | No | Student's level: high_school, university_prep, beginner, intermediate |
| `goal` | string | No | Student's goal (e.g., "improve from 13 to 16") |

**Returns:**
```json
{
  "success": true,
  "resources": [
    {
      "name": "Khan Academy: Calculus",
      "provider": "Khan Academy",
      "type": "video_course",
      "free": true,
      "search_hint": "Visit pt.khanacademy.org"
    }
  ],
  "study_plan": "Start with basics, practice daily",
  "estimated_time": "2-3 months"
}
```

---

## Error Handling

All tools implement retry logic with exponential backoff. If a tool fails, it returns:

```json
{
  "success": false,
  "error": "Error message describing what went wrong"
}
```

## Tool Selection Flow

```
User Message → Intent Classification → Tool Selection → Execution → Response
                    ↓
         major_discovery → get_major_suggestions
         transcript_analysis → parse_transcript
         gap_analysis → analyze_grades + find_study_resources
         resource_request → find_study_resources
         general_question → get_major_info (if specific major mentioned)
```
