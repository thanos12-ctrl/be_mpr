"""
Content Swapping Strategy
Keep EdNet difficulty/interaction data, generate new subject content
NO need to change LSTM/RL models or training data!
"""

import pandas as pd
import numpy as np
import json
import  google.generativeai as genai
from typing import Dict, List
import os

# ==========================================
# CORE CONCEPT: Question ID Mapping
# ==========================================

"""
The Strategy:
1. Keep EdNet question IDs (q1, q2, q3...)
2. Keep EdNet difficulty scores (0.0-1.0)
3. Keep EdNet concept/part structure (Part 1-7)
4. Keep all student interaction data unchanged

Just generate NEW CONTENT that matches:
- Same question_id
- Same difficulty level
- Same part/concept

Example:
EdNet q5012: difficulty=0.65, part=5 (grammar)
→ Java q5012: difficulty=0.65, concept=Methods (matching complexity)
"""

# ==========================================
# STEP 1: Map EdNet Concepts to New Subject
# ==========================================

# EdNet has 7 parts, let's map them to any subject
CONCEPT_MAPPINGS = {
    "java_programming": {
        1: "Basic Syntax",  # Part 1 → Easy concepts
        2: "Variables & Types",  # Part 2 → Still easy
        3: "Control Flow",  # Part 3 → Medium
        4: "Methods & Functions",  # Part 4 → Medium-hard
        5: "Object-Oriented Basics",  # Part 5 → Hard (like EdNet grammar)
        6: "Advanced OOP",  # Part 6 → Very hard
        7: "Collections & Generics"  # Part 7 → Hardest (like reading comp)
    },

    "python_programming": {
        1: "Basic Syntax",
        2: "Variables & Types",
        3: "Control Flow",
        4: "Functions",
        5: "Data Structures",
        6: "OOP Concepts",
        7: "Advanced Topics"
    },

    "mathematics": {
        1: "Basic Arithmetic",
        2: "Algebra Basics",
        3: "Linear Equations",
        4: "Quadratic Equations",
        5: "Functions & Graphs",
        6: "Trigonometry",
        7: "Calculus Basics"
    },

    "data_structures": {
        1: "Arrays & Lists",
        2: "Stacks & Queues",
        3: "Linked Lists",
        4: "Trees",
        5: "Graphs",
        6: "Hash Tables",
        7: "Advanced Algorithms"
    }
}


# ==========================================
# STEP 2: Generate Content Matching EdNet Structure
# ==========================================

class ContentGenerator:
    """
    Generates subject content that matches EdNet structure exactly
    """

    def __init__(self, subject: str, anthropic_api_key: str):
        self.subject = subject
        genai.configure(api_key=anthropic_api_key)
        self.client = genai.GenerativeModel('gemma-3-27b-it')
        self.concept_mapping = CONCEPT_MAPPINGS.get(subject, {})

    def _clean_json_string(self, text):
        """Helper to extract JSON from markdown code blocks if present"""
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    def generate_question_content(
            self,
            question_id: str,
            difficulty: float,
            part: int,
            ednet_tags: str = None
    ) -> Dict:
        """
        Generate content for a question that matches EdNet difficulty

        Args:
            question_id: Original EdNet ID (e.g., "q5012")
            difficulty: EdNet calculated difficulty (0.0-1.0)
            part: EdNet part number (1-7)
            ednet_tags: Original EdNet tags (optional, for context)

        Returns:
            Question content matching the difficulty/complexity
        """

        # Map to subject concept
        concept = self.concept_mapping.get(part, f"Concept {part}")

        # Difficulty description
        if difficulty < 0.3:
            diff_level = "easy"
            diff_desc = "beginner-friendly, basic syntax, direct application"
        elif difficulty < 0.6:
            diff_level = "medium"
            diff_desc = "requires understanding of concepts, some problem-solving"
        else:
            diff_level = "hard"
            diff_desc = "advanced, requires deep understanding, edge cases"

        # Generate using AI
        prompt = self._build_prompt(
            question_id=question_id,
            subject=self.subject,
            concept=concept,
            difficulty=difficulty,
            difficulty_level=diff_level,
            difficulty_description=diff_desc
        )
        response = self.client.generate_content(prompt)
        response = self.client.generate_content(prompt)

        raw_text = response.text
        json_text = self._clean_json_string(raw_text)
        # Parse response
        content = json.loads(json_text)

        # Add metadata to match EdNet structure
        content['question_id'] = question_id
        content['difficulty'] = difficulty
        content['part'] = part
        content['concept'] = concept

        return content

    def _build_prompt(self, question_id, subject, concept, difficulty,
                      difficulty_level, difficulty_description):
        """Build AI prompt for content generation"""

        if subject == "java_programming":
            return f"""Generate a Java programming question with these EXACT specifications:

Question ID: {question_id}
Concept: {concept}
Difficulty: {difficulty:.2f} ({difficulty_level})
Difficulty Description: {difficulty_description}

CRITICAL: The question MUST match the difficulty level {difficulty:.2f}
- Easy (0.0-0.3): Basic syntax, no tricks
- Medium (0.3-0.6): Requires understanding, some reasoning
- Hard (0.6-1.0): Complex logic, edge cases, advanced concepts

Format:
{{
  "question_text": "...",
  "code": "..." (if applicable),
  "options": {{
    "a": "...",
    "b": "...",
    "c": "...",
    "d": "..."
  }},
  "correct_answer": "a/b/c/d",
  "explanation": "..."
}}

Example for difficulty={difficulty:.2f}:
{self._get_example(subject, difficulty_level)}
"""

        elif subject == "mathematics":
            return f"""Generate a mathematics question:

Concept: {concept}
Difficulty: {difficulty:.2f} ({difficulty_level})

The question must be at difficulty {difficulty:.2f}:
- Use appropriate mathematical complexity
- Match the concept: {concept}

Return as JSON with fields: question_text, options, correct_answer, explanation
"""

        else:
            # Generic template
            return f"""Generate a {subject} question:
Concept: {concept}
Difficulty: {difficulty:.2f}
Return as JSON with: question_text, options (a,b,c,d), correct_answer, explanation
"""

    def _get_example(self, subject, difficulty_level):
        """Get example question for reference"""

        examples = {
            "java_programming": {
                "easy": "What is the correct syntax to declare an integer?\nCode: ___ x = 5;",
                "medium": "What will this code output?\nCode: int[] arr = {1,2,3}; System.out.println(arr[1]);",
                "hard": "Identify the bug in this recursive method that causes stack overflow"
            },
            "mathematics": {
                "easy": "Solve: 2x + 3 = 7",
                "medium": "Solve: x² - 5x + 6 = 0",
                "hard": "Find the derivative of f(x) = (x² + 1) / (x - 2)"
            }
        }

        return examples.get(subject, {}).get(difficulty_level, "")


# ==========================================
# STEP 3: Batch Generate for All EdNet Questions
# ==========================================

def generate_subject_content_from_ednet(
        subject: str,
        ednet_questions_path: str = './Data/questions.csv',
        ednet_metadata_path: str = 'ednet_metadata.npz',
        output_path: str = None,
        anthropic_api_key: str = None,
        limit: int = None
):
    """
    Generate content for a new subject using EdNet structure

    Args:
        subject: Target subject (e.g., 'java_programming')
        ednet_questions_path: Path to EdNet questions.csv
        ednet_metadata_path: Path to difficulty metadata
        output_path: Where to save generated content
        anthropic_api_key: Your Anthropic API key
        limit: Only generate N questions (for testing)
    """

    print(f"\n{'=' * 60}")
    print(f"  Generating {subject.upper()} Content from EdNet Structure")
    print(f"{'=' * 60}\n")

    # Load EdNet data
    print("Loading EdNet structure...")
    df_questions = pd.read_csv(ednet_questions_path)

    # Load difficulty scores
    metadata = np.load(ednet_metadata_path, allow_pickle=True)
    difficulty_map = {}
    for qid, diff in metadata['difficulty_map']:
        difficulty_map[str(qid)] = float(diff)

    print(f"✅ Loaded {len(df_questions)} EdNet questions")
    print(f"✅ Loaded {len(difficulty_map)} difficulty scores")

    # Initialize generator
    generator = ContentGenerator(subject, anthropic_api_key)

    # Generate content
    generated_questions = []
    errors = []

    # Limit for testing
    if limit:
        df_questions = df_questions.head(limit)

    print(f"\nGenerating content for {len(df_questions)} questions...")
    print("This may take a while...\n")

    for idx, row in df_questions.iterrows():
        question_id = str(row['question_id'])
        part = int(row['part'])
        difficulty = difficulty_map.get(question_id, 0.5)
        tags = row.get('tags', '')

        try:
            # Generate content
            content = generator.generate_question_content(
                question_id=question_id,
                difficulty=difficulty,
                part=part,
                ednet_tags=tags
            )

            generated_questions.append(content)

            # Progress
            if (idx + 1) % 10 == 0:
                print(f"Generated {idx + 1}/{len(df_questions)} questions...")

            # Rate limiting (Anthropic allows ~50 requests/min)
            import time
            time.sleep(1.2)  # ~50 requests per minute

        except Exception as e:
            errors.append({
                'question_id': question_id,
                'error': str(e)
            })
            print(f"⚠️  Error on {question_id}: {e}")

    # Save results
    if output_path is None:
        output_path = f'question_content_{subject}.json'

    with open(output_path, 'w') as f:
        json.dump(generated_questions, f, indent=2)

    print(f"\n{'=' * 60}")
    print(f"  GENERATION COMPLETE")
    print(f"{'=' * 60}")
    print(f"✅ Generated: {len(generated_questions)} questions")
    print(f"❌ Errors: {len(errors)}")
    print(f"💾 Saved to: {output_path}")

    # Save errors if any
    if errors:
        error_path = output_path.replace('.json', '_errors.json')
        with open(error_path, 'w') as f:
            json.dump(errors, f, indent=2)
        print(f"⚠️  Errors saved to: {error_path}")

    # Cost estimate
    cost = len(generated_questions) * 0.015  # ~$0.015 per question
    print(f"\n💰 Estimated cost: ${cost:.2f}")

    return generated_questions


# ==========================================
# STEP 4: Use Generated Content in API
# ==========================================

def load_subject_content(subject: str):
    """
    Load generated content for a subject
    Maps question_id → content
    """

    content_file = f'question_content_{subject}.json'

    if not os.path.exists(content_file):
        raise FileNotFoundError(
            f"Content file not found: {content_file}\n"
            f"Run: python generate_subject_content.py --subject {subject}"
        )

    with open(content_file, 'r') as f:
        questions = json.load(f)

    # Create lookup: question_id → content
    lookup = {q['question_id']: q for q in questions}

    print(f"✅ Loaded {len(lookup)} {subject} questions")

    return lookup


# ==========================================
# STEP 5: Integration Example
# ==========================================
#
# class MultiSubjectAPI:
#     """
#     Example of how to use this in your API
#     """
#
#     def __init__(self):
#         # Load content for all subjects
#         self.content_libraries = {
#             'english_ednet': self._load_ednet_original(),
#             'java_programming': load_subject_content('java_programming'),
#             'python_programming': load_subject_content('python_programming'),
#             # Add more subjects...
#         }
#
#         # Your existing models work as-is!
#         self.lstm_model = load_lstm_model()  # Same model for all subjects
#         self.rl_agent = load_rl_agent()  # Same agent for all subjects
#
#     def _load_ednet_original(self):
#         """Load original EdNet content (if you have it)"""
#         # Or use generated content for English too
#         return load_subject_content('english_ednet')
#
#     def get_question(self, subject: str, question_id: str):
#         """
#         Get question content for any subject
#
#         The question_id is the SAME as EdNet
#         But the content is different!
#         """
#
#         content_library = self.content_libraries.get(subject)
#
#         if not content_library:
#             raise ValueError(f"Subject {subject} not loaded")
#
#         content = content_library.get(question_id)
#
#         if not content:
#             # Fallback
#             return {
#                 'question_id': question_id,
#                 'question_text': f'Question {question_id}',
#                 'options': {'a': 'Option A', 'b': 'Option B', 'c': 'Option C', 'd': 'Option D'},
#                 'correct_answer': 'a'
#             }
#
#         return content
#
#     def select_next_question(self, subject: str, student_state):
#         """
#         Use RL agent to select next question
#         Agent works the SAME for all subjects!
#         """
#
#         # RL agent selects question ID based on difficulty/concept
#         # This is SUBJECT-AGNOSTIC!
#         question_id = self.rl_agent.select(student_state)
#
#         # Get content for the selected subject
#         content = self.get_question(subject, question_id)
#
#         return content


# ==========================================
# USAGE EXAMPLES
# ==========================================

if __name__ == "__main__":
    import sys

    # Example 1: Generate Java content
    print("=" * 60)
    print("  USAGE EXAMPLE")
    print("=" * 60)
    print()
    print("Generate Java content from EdNet structure:")
    print()
    print("  python content_swap_strategy.py \\")
    print("    --subject java_programming \\")
    print("    --api-key sk-ant-... \\")
    print("    --limit 100  # Generate 100 questions for testing")
    print()
    print("This will:")
    print("  1. Load EdNet questions.csv")
    print("  2. Load difficulty scores from ednet_metadata.npz")
    print("  3. Generate Java content matching each EdNet question")
    print("  4. Save to: question_content_java_programming.json")
    print()
    print("Cost: ~$0.015 per question")
    print("  - 100 questions = $1.50")
    print("  - 1000 questions = $15")
    print("  - 13000 questions (full EdNet) = $195")
    print()
    print("=" * 60)

    # Parse arguments (simple version)
    if len(sys.argv) > 1:
        if '--subject' in sys.argv:
            idx = sys.argv.index('--subject')
            subject = sys.argv[idx + 1]

            api_key = None
            if '--api-key' in sys.argv:
                idx = sys.argv.index('--api-key')
                api_key = sys.argv[idx + 1]

            limit = None
            if '--limit' in sys.argv:
                idx = sys.argv.index('--limit')
                limit = int(sys.argv[idx + 1])

            # Generate!
            generate_subject_content_from_ednet(
                subject=subject,
                anthropic_api_key=api_key,
                limit=limit
            )