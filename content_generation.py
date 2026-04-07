"""
Content Swapping Strategy (Gemini Edition)
Keep EdNet difficulty/interaction data, generate new subject content.
NO need to change LSTM/RL models or training data!
"""

import pandas as pd
import numpy as np
import json
import  google.generativeai as genai
from typing import Dict, List
import os
import time
import sys

# ==========================================
# 1. CONCEPT MAPPING (EdNet Parts -> New Subject)
# ==========================================

CONCEPT_MAPPINGS = {
    "java_programming": {
        1: "Basic Syntax & Data Types",  # Part 1 -> Easy concepts
        2: "Operators & Expressions",  # Part 2 -> Still easy
        3: "Control Flow (If/Else, Loops)",  # Part 3 -> Medium
        4: "Arrays & Strings",  # Part 4 -> Medium-hard
        5: "Methods & Encapsulation",  # Part 5 -> Hard
        6: "Object-Oriented Programming",  # Part 6 -> Very hard
        7: "Exception Handling & Collections"  # Part 7 -> Hardest
    },

    "python_programming": {
        1: "Variables & Basic Types",
        2: "Lists & Tuples",
        3: "Conditionals & Loops",
        4: "Functions & Modules",
        5: "Dictionaries & Sets",
        6: "Classes & Objects",
        7: "File I/O & Exceptions"
    },

    "mathematics": {
        1: "Arithmetic Operations",
        2: "Fractions & Decimals",
        3: "Algebraic Expressions",
        4: "Linear Equations",
        5: "Geometry Basics",
        6: "Trigonometry",
        7: "Calculus Fundamentals"
    }
}


# ==========================================
# 2. CONTENT GENERATOR CLASS (Gemini)
# ==========================================

class GeminiContentGenerator:
    """
    Generates subject content that matches EdNet structure exactly using Gemini.
    """

    def __init__(self, subject: str, api_key: str):
        self.subject = subject
        self.concept_mapping = CONCEPT_MAPPINGS.get(subject, {})

        # Configure Gemini
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-3-flash-preview')  # Use Flash for speed/cost, or Pro for quality

    def generate_question_content(
            self,
            question_id: str,
            difficulty: float,
            part: int,
            ednet_tags: str = None
    ) -> Dict:
        """
        Generate content for a question that matches EdNet difficulty.
        """

        # Map to subject concept
        concept = self.concept_mapping.get(part, f"Concept {part}")

        # Difficulty description for the LLM
        if difficulty < 0.3:
            diff_level = "easy"
            diff_desc = "beginner-friendly, basic syntax, direct application, no tricks"
        elif difficulty < 0.6:
            diff_level = "medium"
            diff_desc = "requires understanding of concepts, some reasoning, standard problems"
        else:
            diff_level = "hard"
            diff_desc = "advanced, requires deep understanding, edge cases, complex logic"

        # Build Prompt
        prompt = self._build_prompt(
            question_id=question_id,
            subject=self.subject,
            concept=concept,
            difficulty=difficulty,
            difficulty_level=diff_level,
            difficulty_description=diff_desc
        )

        # Call Gemini API
        try:
            response = self.model.generate_content(prompt)

            # Extract JSON from response (Gemini sometimes adds markdown blocks)
            raw_text = response.text
            json_text = self._clean_json_string(raw_text)

            content = json.loads(json_text)

            # Add metadata to match EdNet structure
            content['question_id'] = question_id
            content['difficulty'] = difficulty
            content['part'] = part
            content['concept'] = concept

            return content

        except Exception as e:
            raise Exception(f"Gemini API Error: {str(e)}")

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

    def _build_prompt(self, question_id, subject, concept, difficulty,
                      difficulty_level, difficulty_description):
        """Build AI prompt for content generation"""

        return f"""You are an expert exam question generator for {subject}.

Generate a SINGLE multiple-choice question with these EXACT specifications:

- **Concept:** {concept}
- **Target Difficulty:** {difficulty:.2f} ({difficulty_level})
- **Description:** {difficulty_description}

CRITICAL: The question MUST match the difficulty level {difficulty:.2f}.
- Easy (0.0-0.3): Very simple, direct recall or basic application.
- Medium (0.3-0.6): Standard problem, requires thought.
- Hard (0.6-1.0): Tricky, complex logic, or multi-step reasoning.

Output MUST be valid, parseable JSON with this exact schema:
{{
  "question_text": "The full text of the question...",
  "code_snippet": "Optional code block if needed, else null",
  "options": {{
    "a": "Option A text",
    "b": "Option B text",
    "c": "Option C text",
    "d": "Option D text"
  }},
  "correct_answer": "a", 
  "explanation": "Brief explanation of why the answer is correct."
}}

Do not include any markdown formatting or extra text outside the JSON.
"""


# ==========================================
# 3. BATCH GENERATOR FUNCTION
# ==========================================

def generate_subject_content_from_ednet(
        subject: str,
        api_key: str,
        ednet_questions_path: str = './data/questions.csv',
        # We assume you have a file mapping QIDs to difficulty (from preprocessing.py)
        # If not, we'll default to 0.5
        difficulty_map_path: str = None,
        output_path: str = None,
        limit: int = None
):
    """
    Main function to drive the content generation process.
    """

    print(f"\n{'=' * 60}")
    print(f"  Generating {subject.upper()} Content with Gemini")
    print(f"{'=' * 60}\n")

    # 1. Load EdNet Question Metadata
    print(f"Loading EdNet structure from {ednet_questions_path}...")
    try:
        df_questions = pd.read_csv(ednet_questions_path)
    except FileNotFoundError:
        print("❌ questions.csv not found. Please check the path.")
        return

    # 2. Load Difficulty Map (Optional but recommended)
    difficulty_map = {}
    if difficulty_map_path and os.path.exists(difficulty_map_path):
        print(f"Loading difficulty scores from {difficulty_map_path}...")
        try:
            # Assuming .npz or .json from your preprocessing step
            # Adjust loading logic based on your actual file format
            if difficulty_map_path.endswith('.npz'):
                data = np.load(difficulty_map_path, allow_pickle=True)
                # Assuming saved as a dict or array
                # This is a placeholder; adjust to your schema
                if 'difficulty_map' in data:
                    for qid, diff in data['difficulty_map']:
                        difficulty_map[str(qid)] = float(diff)
            elif difficulty_map_path.endswith('.json'):
                with open(difficulty_map_path, 'r') as f:
                    difficulty_map = json.load(f)
        except Exception as e:
            print(f"⚠️ Could not load difficulty map: {e}. Defaulting to 0.5")

    # 3. Initialize Gemini Generator
    generator = GeminiContentGenerator(subject, api_key)

    generated_questions = []
    errors = []

    # Apply Limit
    if limit:
        df_questions = df_questions.head(limit)

    print(f"\nStarting generation for {len(df_questions)} questions...")

    # 4. Generation Loop
    start_time = time.time()

    for idx, row in df_questions.iterrows():
        # Handle different column names if necessary
        q_id = str(row.get('question_id', row.get('question_id')))
        part = int(row.get('part', 1))  # Default to part 1 if missing

        # Get difficulty (Default 0.5 if not in map)
        difficulty = difficulty_map.get(q_id, 0.5)

        try:
            content = generator.generate_question_content(
                question_id=q_id,
                difficulty=difficulty,
                part=part
            )
            generated_questions.append(content)

            # Simple progress bar
            if (idx + 1) % 5 == 0:
                elapsed = time.time() - start_time
                print(f"  Generated {idx + 1}/{len(df_questions)}... ({elapsed:.1f}s)")

            # Rate Limiting for Gemini Free Tier (approx 15 RPM, varies by region)
            # Adjust sleep as needed. Paid tier is much faster.
            time.sleep(4.0)

        except Exception as e:
            print(f"❌ Error on QID {q_id}: {e}")
            errors.append({'question_id': q_id, 'error': str(e)})
            time.sleep(5)  # Backoff on error

    # 5. Save Results
    if output_path is None:
        output_path = f'content_{subject}.json'

    with open(output_path, 'w') as f:
        json.dump(generated_questions, f, indent=2)

    print(f"\n{'=' * 60}")
    print(f"  COMPLETE")
    print(f"{'=' * 60}")
    print(f"✅ Successfully generated: {len(generated_questions)}")
    print(f"❌ Failed: {len(errors)}")
    print(f"💾 Saved content to: {output_path}")

    if errors:
        err_path = f'content_{subject}_errors.json'
        with open(err_path, 'w') as f:
            json.dump(errors, f, indent=2)
        print(f"⚠️  Error log saved to: {err_path}")


# ==========================================
# 4. CLI ENTRY POINT
# ==========================================

if __name__ == "__main__":
    # Simple argument parsing
    if len(sys.argv) < 3:
        print("Usage: python content_swap_gemini.py <subject> <api_key> [limit] [questions_csv_path]")
        print("Example: python content_swap_gemini.py java_programming AIzaSy... 10")
        sys.exit(1)

    subject_arg = sys.argv[1]
    api_key_arg = sys.argv[2]

    limit_arg = None
    if len(sys.argv) > 3:
        try:
            limit_arg = int(sys.argv[3])
        except ValueError:
            pass

    csv_path = './Data/questions.csv'  # Default
    if len(sys.argv) > 4:
        csv_path = sys.argv[4]

    generate_subject_content_from_ednet(
        subject=subject_arg,
        api_key=api_key_arg,
        ednet_questions_path=csv_path,
        limit=limit_arg
    )