"""
Lesson Content Generator with Gemini AI
Generates comprehensive lesson content including:
- Introduction
- Code Examples
- Key Takeaways
- Estimated Time
"""

import json
import google.generativeai as genai
from typing import Dict, List, Optional
import os
import time
from pathlib import Path

# ==========================================
# LESSON STRUCTURE MAPPINGS
# ==========================================

LESSON_STRUCTURES = {
    "java_programming": [
        {
            "lesson_number": 1,
            "title": "Basic Syntax & Data Types",
            "slug": "basic-syntax-data-types",
            "topics": [
                "Variables and naming conventions",
                "Primitive data types (int, double, boolean, char)",
                "Type casting and conversion",
                "String basics",
                "Constants with final keyword"
            ],
            "difficulty_level": "beginner",
            "estimated_time_minutes": 45
        },
        {
            "lesson_number": 2,
            "title": "Operators & Expressions",
            "slug": "operators-expressions",
            "topics": [
                "Arithmetic operators",
                "Comparison and logical operators",
                "Assignment operators",
                "Operator precedence",
                "Increment/decrement operators"
            ],
            "difficulty_level": "beginner",
            "estimated_time_minutes": 40
        },
        {
            "lesson_number": 3,
            "title": "Control Flow (If/Else, Loops)",
            "slug": "control-flow",
            "topics": [
                "If-else statements",
                "Switch statements",
                "For loops",
                "While and do-while loops",
                "Break and continue"
            ],
            "difficulty_level": "beginner",
            "estimated_time_minutes": 50
        },
        {
            "lesson_number": 4,
            "title": "Arrays & Strings",
            "slug": "arrays-strings",
            "topics": [
                "Array declaration and initialization",
                "Array manipulation",
                "Multi-dimensional arrays",
                "String methods",
                "StringBuilder and StringBuffer"
            ],
            "difficulty_level": "intermediate",
            "estimated_time_minutes": 55
        },
        {
            "lesson_number": 5,
            "title": "Methods & Encapsulation",
            "slug": "methods-encapsulation",
            "topics": [
                "Method declaration and parameters",
                "Return types and values",
                "Method overloading",
                "Access modifiers",
                "Getters and setters"
            ],
            "difficulty_level": "intermediate",
            "estimated_time_minutes": 50
        },
        {
            "lesson_number": 6,
            "title": "Object-Oriented Programming",
            "slug": "oop-basics",
            "topics": [
                "Classes and objects",
                "Constructors",
                "Inheritance",
                "Polymorphism",
                "Abstract classes and interfaces"
            ],
            "difficulty_level": "intermediate",
            "estimated_time_minutes": 60
        },
        {
            "lesson_number": 7,
            "title": "Exception Handling & Collections",
            "slug": "exceptions-collections",
            "topics": [
                "Try-catch blocks",
                "Throwing exceptions",
                "ArrayList and LinkedList",
                "HashMap and HashSet",
                "Iterators"
            ],
            "difficulty_level": "advanced",
            "estimated_time_minutes": 60
        }
    ],
    "python_programming": [
        {
            "lesson_number": 1,
            "title": "Variables & Basic Types",
            "slug": "variables-basic-types",
            "topics": [
                "Variable assignment",
                "Numbers (int, float)",
                "Strings and string methods",
                "Boolean values",
                "Type conversion"
            ],
            "difficulty_level": "beginner",
            "estimated_time_minutes": 40
        },
        {
            "lesson_number": 2,
            "title": "Lists & Tuples",
            "slug": "lists-tuples",
            "topics": [
                "List creation and indexing",
                "List methods",
                "List comprehensions",
                "Tuples and immutability",
                "Slicing"
            ],
            "difficulty_level": "beginner",
            "estimated_time_minutes": 45
        },
        {
            "lesson_number": 3,
            "title": "Conditionals & Loops",
            "slug": "conditionals-loops",
            "topics": [
                "If-elif-else statements",
                "For loops",
                "While loops",
                "Range function",
                "Break and continue"
            ],
            "difficulty_level": "beginner",
            "estimated_time_minutes": 45
        }
    ]
}


# ==========================================
# LESSON CONTENT GENERATOR
# ==========================================

class LessonContentGenerator:
    """Generate comprehensive lesson content using Gemini AI"""

    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemma-3-27b-it')
        
        # Rate limiting
        self.requests_per_minute = 15
        self.last_request_time = 0

    def _wait_for_rate_limit(self):
        """Ensure we don't exceed rate limits"""
        time_since_last = time.time() - self.last_request_time
        min_interval = 60.0 / self.requests_per_minute

        if time_since_last < min_interval:
            sleep_time = min_interval - time_since_last
            print(f"  ⏳ Rate limit: waiting {sleep_time:.1f}s...")
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def generate_lesson_content(
        self,
        subject: str,
        lesson_info: Dict,
        max_retries: int = 3
    ) -> Optional[Dict]:
        """Generate comprehensive content for a single lesson"""

        topics_list = "\n".join([f"- {topic}" for topic in lesson_info['topics']])
        
        prompt = f"""Generate comprehensive lesson content for a {subject} course.

Lesson: {lesson_info['title']}
Difficulty: {lesson_info['difficulty_level']}
Topics to cover:
{topics_list}

Generate content in the following JSON format (no markdown, just valid JSON):
{{
  "introduction": "A compelling 2-3 paragraph introduction that explains what students will learn and why it's important. Make it engaging and motivating.",
  
  "code_example": "A complete, well-commented code example that demonstrates the key concepts. Use realistic examples that students can relate to. Include comments explaining each part.",
  
  "key_takeaways": [
    "First key concept or skill learned",
    "Second key concept or skill learned",
    "Third key concept or skill learned",
    "Fourth key concept or skill learned",
    "Fifth key concept or skill learned"
  ]
}}

Requirements:
- Introduction should be 150-250 words, engaging and clear
- Code example should be complete, runnable code with helpful comments
- Include 5 key takeaways that summarize the most important points
- Use proper {subject} syntax and best practices
- Make it suitable for {lesson_info['difficulty_level']} level students
"""

        for attempt in range(max_retries):
            try:
                self._wait_for_rate_limit()

                response = self.model.generate_content(prompt)
                raw_text = response.text.strip()

                # Clean JSON
                if raw_text.startswith("```json"):
                    raw_text = raw_text[7:]
                if raw_text.startswith("```"):
                    raw_text = raw_text[3:]
                if raw_text.endswith("```"):
                    raw_text = raw_text[:-3]
                raw_text = raw_text.strip()

                content = json.loads(raw_text)

                # Validate structure
                required_keys = ['introduction', 'code_example', 'key_takeaways']
                if not all(key in content for key in required_keys):
                    raise ValueError(f"Missing required keys. Got: {content.keys()}")

                if not isinstance(content['key_takeaways'], list):
                    raise ValueError("key_takeaways must be a list")

                return content

            except json.JSONDecodeError as e:
                print(f"  ⚠️  JSON parse error (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    print(f"  ❌ Failed to parse JSON after {max_retries} attempts")
                    return None

            except Exception as e:
                print(f"  ⚠️  Error (attempt {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(5)
                else:
                    print(f"  ❌ Failed after {max_retries} attempts")
                    return None

        return None


# ==========================================
# BATCH GENERATION
# ==========================================

def generate_lessons_for_subject(
    subject: str,
    api_key: str,
    output_dir: str = './generated_content',
    subject_id: Optional[str] = None
):
    """
    Generate lesson content for all lessons in a subject.
    
    Args:
        subject: Subject name (e.g., 'java_programming')
        api_key: Gemini API key
        output_dir: Directory to save output
        subject_id: UUID of the subject (if known)
    """
    
    print(f"\n{'=' * 70}")
    print(f"  Lesson Content Generator - {subject.upper()}")
    print(f"{'=' * 70}\n")

    # Get lesson structure
    lesson_structure = LESSON_STRUCTURES.get(subject)
    if not lesson_structure:
        print(f"❌ No lesson structure defined for '{subject}'")
        print(f"Available subjects: {list(LESSON_STRUCTURES.keys())}")
        return None

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Initialize generator
    generator = LessonContentGenerator(api_key)

    # Generate content for each lesson
    lessons = []
    success_count = 0
    error_count = 0

    print(f"📚 Generating content for {len(lesson_structure)} lessons...\n")

    for idx, lesson_info in enumerate(lesson_structure, 1):
        print(f"📝 [{idx}/{len(lesson_structure)}] Generating: {lesson_info['title']}...")
        
        try:
            content = generator.generate_lesson_content(subject, lesson_info)
            
            if content:
                # Combine lesson info with generated content
                lesson_data = {
                    "lesson_number": lesson_info['lesson_number'],
                    "title": lesson_info['title'],
                    "slug": lesson_info['slug'],
                    "difficulty_level": lesson_info['difficulty_level'],
                    "estimated_time_minutes": lesson_info['estimated_time_minutes'],
                    "introduction": content['introduction'],
                    "code_example": content['code_example'],
                    "key_takeaways": content['key_takeaways'],
                    "topics": lesson_info['topics']
                }
                
                # Add subject_id if provided
                if subject_id:
                    lesson_data['subject_id'] = subject_id
                
                lessons.append(lesson_data)
                success_count += 1
                print(f"   ✅ Success!\n")
            else:
                error_count += 1
                print(f"   ❌ Failed\n")
                
        except Exception as e:
            print(f"   ❌ Error: {str(e)}\n")
            error_count += 1

    # Save output
    output_file = os.path.join(output_dir, f'lesson_content_{subject}.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(lessons, f, indent=2, ensure_ascii=False)

    # Summary
    print(f"\n{'=' * 70}")
    print(f"  GENERATION COMPLETE")
    print(f"{'=' * 70}")
    print(f"✅ Successfully generated: {success_count}")
    print(f"❌ Errors: {error_count}")
    print(f"💾 Saved to: {output_file}")
    print(f"\n📊 Lessons Generated:")
    for lesson in lessons:
        print(f"  {lesson['lesson_number']}. {lesson['title']} ({lesson['difficulty_level']})")

    return lessons


# ==========================================
# CLI
# ==========================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Lesson Content Generator')
    parser.add_argument('subject', help='Subject (e.g., java_programming, python_programming)')
    parser.add_argument('api_key', help='Gemini API key')
    parser.add_argument('--output-dir', default='./generated_content',
                        help='Output directory (default: ./generated_content)')
    parser.add_argument('--subject-id', help='Subject UUID (optional)')

    args = parser.parse_args()

    generate_lessons_for_subject(
        subject=args.subject,
        api_key=args.api_key,
        output_dir=args.output_dir,
        subject_id=args.subject_id
    )
