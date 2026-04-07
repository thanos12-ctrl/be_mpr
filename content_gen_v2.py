"""
Smart Batch Content Generator with:
- Checkpointing (resume from where you left off)
- Deduplication (never generate same question_id twice)
- Concept-based filtering (generate N questions per concept)
- Rate limit handling
- Progress saving every N questions
"""

import pandas as pd
import numpy as np
import json
import google.generativeai as genai
from typing import Dict, List, Optional
import os
import time
import sys
from pathlib import Path
from collections import defaultdict

# ==========================================
# CONCEPT MAPPINGS
# ==========================================

CONCEPT_MAPPINGS = {
    "java_programming": {
        1: "Basic Syntax & Data Types",
        2: "Operators & Expressions",
        3: "Control Flow (If/Else, Loops)",
        4: "Arrays & Strings",
        5: "Methods & Encapsulation",
        6: "Object-Oriented Programming",
        7: "Exception Handling & Collections"
    },
    "python_programming": {
        1: "Variables & Basic Types",
        2: "Lists & Tuples",
        3: "Conditionals & Loops",
        4: "Functions & Modules",
        5: "Dictionaries & Sets",
        6: "Classes & Objects",
        7: "File I/O & Exceptions"
    }
}


# ==========================================
# CHECKPOINT MANAGER
# ==========================================

class CheckpointManager:
    """Manages checkpoints for resumable generation"""

    def __init__(self, checkpoint_file: str):
        self.checkpoint_file = checkpoint_file
        self.data = self._load_checkpoint()

    def _load_checkpoint(self) -> Dict:
        """Load existing checkpoint or create new"""
        if os.path.exists(self.checkpoint_file):
            with open(self.checkpoint_file, 'r') as f:
                data = json.load(f)
            print(f"✅ Loaded checkpoint: {len(data['generated'])} questions already generated")
            return data
        else:
            return {
                'generated': [],  # List of generated questions
                'processed_ids': set(),  # Set of question IDs already done
                'concept_counts': {},  # Count per concept
                'last_updated': None,
                'errors': []
            }

    def save_checkpoint(self):
        """Save current state"""
        # Convert set to list for JSON serialization
        save_data = self.data.copy()
        save_data['processed_ids'] = list(self.data['processed_ids'])
        save_data['last_updated'] = time.strftime('%Y-%m-%d %H:%M:%S')

        with open(self.checkpoint_file, 'w') as f:
            json.dump(save_data, f, indent=2)

        print(f"💾 Checkpoint saved: {len(self.data['generated'])} questions")

    def add_question(self, question: Dict):
        """Add a generated question"""
        self.data['generated'].append(question)
        self.data['processed_ids'].add(question['question_id'])

        # Update concept count
        concept = question.get('concept', 'unknown')
        self.data['concept_counts'][concept] = self.data['concept_counts'].get(concept, 0) + 1

    def is_processed(self, question_id: str) -> bool:
        """Check if question_id already generated"""
        return question_id in self.data['processed_ids']

    def get_concept_count(self, concept: str) -> int:
        """Get count of questions for a concept"""
        return self.data['concept_counts'].get(concept, 0)

    def add_error(self, question_id: str, error: str):
        """Log an error"""
        self.data['errors'].append({
            'question_id': question_id,
            'error': error,
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')
        })


# ==========================================
# ENHANCED CONTENT GENERATOR
# ==========================================

class SmartContentGenerator:
    """Enhanced generator with batching and checkpointing"""

    def __init__(self, subject: str, api_key: str):
        self.subject = subject
        self.concept_mapping = CONCEPT_MAPPINGS.get(subject, {})

        # Configure Gemini
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemma-3-27b-it')

        # Rate limiting
        self.requests_per_minute = 15  # Gemini free tier
        self.last_request_time = 0

    def _wait_for_rate_limit(self):
        """Ensure we don't exceed rate limits"""
        time_since_last = time.time() - self.last_request_time
        min_interval = 60.0 / self.requests_per_minute  # seconds between requests

        if time_since_last < min_interval:
            sleep_time = min_interval - time_since_last
            print(f"  ⏳ Rate limit: waiting {sleep_time:.1f}s...")
            time.sleep(sleep_time)

        self.last_request_time = time.time()

    def generate_question(
            self,
            question_id: str,
            difficulty: float,
            part: int,
            max_retries: int = 3
    ) -> Optional[Dict]:
        """Generate a single question with retries"""

        concept = self.concept_mapping.get(part, f"Concept {part}")

        # Difficulty description
        if difficulty < 0.3:
            diff_level = "easy"
            diff_desc = "beginner-friendly, basic syntax, direct application"
        elif difficulty < 0.6:
            diff_level = "medium"
            diff_desc = "requires understanding, some reasoning"
        else:
            diff_level = "hard"
            diff_desc = "advanced, complex logic, edge cases"

        prompt = f"""Generate a {self.subject} multiple-choice question:

Concept: {concept}
Difficulty: {difficulty:.2f} ({diff_level})
Description: {diff_desc}

Return ONLY valid JSON (no markdown):
{{
  "question_text": "...",
  "code_snippet": "..." or null,
  "options": {{"a": "...", "b": "...", "c": "...", "d": "..."}},
  "correct_answer": "a",
  "explanation": "..."
}}
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

                # Add metadata
                content['question_id'] = question_id
                content['difficulty'] = difficulty
                content['part'] = part
                content['concept'] = concept

                return content

            except json.JSONDecodeError as e:
                print(f"  ⚠️  JSON parse error (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(2)
                else:
                    raise Exception(f"Failed to parse JSON after {max_retries} attempts")

            except Exception as e:
                print(f"  ⚠️  Error (attempt {attempt + 1}/{max_retries}): {str(e)}")
                if attempt < max_retries - 1:
                    time.sleep(5)
                else:
                    raise

        return None


# ==========================================
# BATCH GENERATION ORCHESTRATOR
# ==========================================

def generate_content_batched(
        subject: str,
        api_key: str,
        questions_csv: str = './data/questions.csv',
        difficulty_map_path: Optional[str] = 'ednet_metadata.npz',
        output_dir: str = './generated_content',

        # Filtering options
        target_concepts: Optional[List[str]] = None,  # Specific concepts to generate
        questions_per_concept: Optional[int] = None,  # N questions per concept

        # Batching options
        batch_size: int = 10,  # Save checkpoint every N questions
        total_limit: Optional[int] = None,  # Total questions to generate

        # Resume options
        resume: bool = True  # Resume from checkpoint if exists
):
    """
    Main batch generation function with all features.

    Examples:
        # Generate 5 questions per concept
        generate_content_batched('java_programming', api_key, questions_per_concept=5)

        # Generate only for specific concepts
        generate_content_batched('java_programming', api_key,
                                target_concepts=['Basic Syntax & Data Types', 'Loops'])

        # Generate 100 questions total, save every 10
        generate_content_batched('java_programming', api_key,
                                total_limit=100, batch_size=10)
    """

    print(f"\n{'=' * 70}")
    print(f"  Smart Batch Content Generator - {subject.upper()}")
    print(f"{'=' * 70}\n")

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Setup checkpoint
    checkpoint_file = os.path.join(output_dir, f'{subject}_checkpoint.json')
    checkpoint = CheckpointManager(checkpoint_file)

    # Load EdNet questions
    print(f"Loading questions from {questions_csv}...")
    df_questions = pd.read_csv(questions_csv)
    print(f"✅ Loaded {len(df_questions)} total questions")

    # Load difficulty map
    difficulty_map = {}
    if difficulty_map_path and os.path.exists(difficulty_map_path):
        try:
            metadata = np.load(difficulty_map_path, allow_pickle=True)
            for qid, diff in metadata['difficulty_map']:
                difficulty_map[str(qid)] = float(diff)
            print(f"✅ Loaded {len(difficulty_map)} difficulty scores")
        except Exception as e:
            print(f"⚠️  Could not load difficulty map: {e}")

    # Map EdNet parts to concept names
    concept_mapping = CONCEPT_MAPPINGS.get(subject, {})
    df_questions['concept_name'] = df_questions['part'].map(concept_mapping)

    # Filter by target concepts if specified
    if target_concepts:
        df_questions = df_questions[df_questions['concept_name'].isin(target_concepts)]
        print(f"📍 Filtered to {len(df_questions)} questions in target concepts: {target_concepts}")

    # Group by concept
    concept_groups = df_questions.groupby('concept_name')

    # Initialize generator
    generator = SmartContentGenerator(subject, api_key)

    # Determine what to generate
    questions_to_generate = []

    if questions_per_concept:
        # Generate N questions per concept
        print(f"\n🎯 Target: {questions_per_concept} questions per concept")

        for concept_name, group in concept_groups:
            current_count = checkpoint.get_concept_count(concept_name)
            remaining = questions_per_concept - current_count

            if remaining > 0:
                # Get questions for this concept that haven't been processed
                available = group[~group['question_id'].astype(str).isin(
                    checkpoint.data['processed_ids']
                )]

                # Take up to 'remaining' questions
                to_add = available.head(remaining)
                questions_to_generate.extend(to_add.to_dict('records'))

                print(f"  {concept_name}: {current_count}/{questions_per_concept} done, "
                      f"adding {len(to_add)} more")
            else:
                print(f"  {concept_name}: {current_count}/{questions_per_concept} ✅ Complete")

    else:
        # Generate all questions (respecting total_limit)
        questions_to_generate = df_questions[
            ~df_questions['question_id'].astype(str).isin(checkpoint.data['processed_ids'])
        ].to_dict('records')

        if total_limit:
            questions_to_generate = questions_to_generate[:total_limit]

    if not questions_to_generate:
        print("\n✅ All target questions already generated!")
        print(f"📊 Total generated: {len(checkpoint.data['generated'])}")
        return checkpoint.data['generated']

    print(f"\n🚀 Starting generation: {len(questions_to_generate)} questions")
    print(f"💾 Auto-save every {batch_size} questions")
    print(f"⏱️  Estimated time: {len(questions_to_generate) * 4 / 60:.1f} minutes\n")

    # Generation loop
    start_time = time.time()
    success_count = 0
    error_count = 0

    for idx, q_row in enumerate(questions_to_generate, 1):
        question_id = str(q_row['question_id'])
        part = int(q_row['part'])
        difficulty = difficulty_map.get(question_id, 0.5)
        concept_name = q_row.get('concept_name', f'Concept {part}')

        # Skip if already processed (safety check)
        if checkpoint.is_processed(question_id):
            print(f"⏭️  [{idx}/{len(questions_to_generate)}] Skipping {question_id} (already done)")
            continue

        try:
            print(f"📝 [{idx}/{len(questions_to_generate)}] Generating {question_id} "
                  f"(Concept: {concept_name}, Diff: {difficulty:.2f})...")

            content = generator.generate_question(question_id, difficulty, part)

            if content:
                checkpoint.add_question(content)
                success_count += 1
                print(f"   ✅ Success!")
            else:
                checkpoint.add_error(question_id, "Generation returned None")
                error_count += 1
                print(f"   ❌ Failed")

            # Save checkpoint every batch_size questions
            if idx % batch_size == 0:
                checkpoint.save_checkpoint()
                elapsed = time.time() - start_time
                rate = idx / elapsed * 60  # questions per minute
                print(f"\n📊 Progress: {success_count} success, {error_count} errors")
                print(f"⚡ Rate: {rate:.1f} questions/minute\n")

        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
            checkpoint.add_error(question_id, str(e))
            error_count += 1

    # Final checkpoint save
    checkpoint.save_checkpoint()

    # Save final output
    output_file = os.path.join(output_dir, f'question_content_{subject}.json')
    with open(output_file, 'w') as f:
        json.dump(checkpoint.data['generated'], f, indent=2)

    # Summary
    print(f"\n{'=' * 70}")
    print(f"  GENERATION COMPLETE")
    print(f"{'=' * 70}")
    print(f"✅ Successfully generated: {success_count}")
    print(f"❌ Errors: {error_count}")
    print(f"📊 Total in library: {len(checkpoint.data['generated'])}")
    print(f"💾 Saved to: {output_file}")
    print(f"⏱️  Total time: {(time.time() - start_time) / 60:.1f} minutes")

    # Concept breakdown
    print(f"\n📊 Questions per Concept:")
    for concept, count in sorted(checkpoint.data['concept_counts'].items()):
        print(f"  {concept}: {count}")

    if checkpoint.data['errors']:
        error_file = os.path.join(output_dir, f'{subject}_errors.json')
        with open(error_file, 'w') as f:
            json.dump(checkpoint.data['errors'], f, indent=2)
        print(f"\n⚠️  Error log saved to: {error_file}")

    return checkpoint.data['generated']


# ==========================================
# CONVENIENCE FUNCTIONS
# ==========================================

def resume_generation(subject: str, api_key: str, batch_size: int = 10):
    """Resume a previously started generation"""
    return generate_content_batched(
        subject=subject,
        api_key=api_key,
        batch_size=batch_size,
        resume=True
    )


def generate_for_concepts(
        subject: str,
        api_key: str,
        concepts: List[str],
        questions_per_concept: int = 5
):
    """Generate specific number of questions for specific concepts"""
    return generate_content_batched(
        subject=subject,
        api_key=api_key,
        target_concepts=concepts,
        questions_per_concept=questions_per_concept
    )


# ==========================================
# CLI
# ==========================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Smart Batch Content Generator')
    parser.add_argument('subject', help='Subject (e.g., java_programming)')
    parser.add_argument('api_key', help='Gemini API key')
    parser.add_argument('--questions-per-concept', type=int,
                        help='Generate N questions per concept')
    parser.add_argument('--concepts', nargs='+',
                        help='Specific concepts to generate for')
    parser.add_argument('--batch-size', type=int, default=10,
                        help='Save checkpoint every N questions (default: 10)')
    parser.add_argument('--total-limit', type=int,
                        help='Total questions to generate')
    parser.add_argument('--output-dir', default='./generated_content',
                        help='Output directory')
    parser.add_argument('--resume', action='store_true',
                        help='Resume from checkpoint (default behavior)')

    args = parser.parse_args()

    # Map concept numbers to names if provided as numbers
    if args.concepts:
        concept_mapping = CONCEPT_MAPPINGS.get(args.subject, {})
        mapped_concepts = []
        for c in args.concepts:
            if c.isdigit():
                # Convert part number to concept name
                mapped_concepts.append(concept_mapping.get(int(c), c))
            else:
                mapped_concepts.append(c)
        args.concepts = mapped_concepts

    generate_content_batched(
        subject=args.subject,
        api_key=args.api_key,
        target_concepts=args.concepts,
        questions_per_concept=args.questions_per_concept,
        batch_size=args.batch_size,
        total_limit=args.total_limit,
        output_dir=args.output_dir,
        resume=args.resume
    )