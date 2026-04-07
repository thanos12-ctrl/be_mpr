import asyncio
import json
import os
import uuid
from database import database
from models import UserRole

# Paths to JSON files
LESSONS_FILE = "lessons/lesson_content_java_programming.json"
QUESTIONS_FILE = "generated_content/question_content_java_programming.json"

async def insert_data():
    print("Connecting to database...")
    await database.connect()
    
    try:
        # 1. Insert Subject
        print("Inserting Subject: Java Programming...")
        subject_id = str(uuid.uuid4())
        subject_query = """
            INSERT INTO subjects (id, subject_id, name, description, icon, is_published, created_at)
            VALUES (:id, :subject_id, :name, :description, :icon, :is_published, NOW())
            ON CONFLICT (subject_id) DO UPDATE 
            SET name = EXCLUDED.name, 
                description = EXCLUDED.description
            RETURNING id;
        """
        existing_subject = await database.fetch_one("SELECT id FROM subjects WHERE subject_id = 'java_programming'")
        
        if existing_subject:
             subject_uuid = existing_subject['id']
             print(f"Subject already exists: {subject_uuid}")
        else:
             subject_values = {
                "id": subject_id,
                "subject_id": "java_programming",
                "name": "Java Programming",
                "description": "Comprehensive Java course for beginners to advanced learners.",
                "icon": "☕",
                "is_published": True
            }
             await database.execute(query=subject_query, values=subject_values)
             subject_uuid = subject_id
             print(f"Inserted Subject: {subject_uuid}")

        # 2. Load Lessons and Questions
        with open(LESSONS_FILE, 'r', encoding='utf-8') as f:
            lessons_data = json.load(f)
        
        with open(QUESTIONS_FILE, 'r', encoding='utf-8') as f:
            questions_data = json.load(f)

        # 3. Insert Lessons
        print(f"Inserting {len(lessons_data)} lessons...")
        for lesson in lessons_data:
            lesson_id = str(uuid.uuid4())
            lesson_number = lesson['lesson_number']
            
            # Check if lesson exists to update or insert
            existing_lesson = await database.fetch_one(
                "SELECT id FROM lessons WHERE subject_id = :subject_id AND lesson_number = :lesson_number",
                values={"subject_id": subject_uuid, "lesson_number": lesson_number}
            )

            if existing_lesson:
                lesson_uuid = existing_lesson['id']
                # Update existing lesson
                update_query = """
                    UPDATE lessons 
                    SET title = :title, slug = :slug, introduction = :introduction, 
                        code_example = :code_example, key_takeaways = :key_takeaways,
                        estimated_time_minutes = :estimated_time_minutes, 
                        difficulty_level = :difficulty_level
                    WHERE id = :id
                """
                # Level map: beginner -> 1, intermediate -> 3, advanced -> 5
                diff_map = {"beginner": 1, "intermediate": 3, "advanced": 5}
                difficulty = diff_map.get(lesson.get('difficulty_level', 'beginner'), 1)

                await database.execute(update_query, values={
                    "id": lesson_uuid,
                    "title": lesson['title'],
                    "slug": lesson['slug'],
                    "introduction": lesson['introduction'],
                    "code_example": lesson.get('code_example'),
                    "key_takeaways": lesson['key_takeaways'],
                    "estimated_time_minutes": lesson['estimated_time_minutes'],
                    "difficulty_level": difficulty
                })
                print(f"Updated Lesson {lesson_number}: {lesson['title']}")
            else:
                lesson_uuid = lesson_id
                insert_lesson_query = """
                    INSERT INTO lessons (id, subject_id, lesson_number, title, slug, introduction, 
                                       code_example, key_takeaways, estimated_time_minutes, 
                                       difficulty_level, is_published)
                    VALUES (:id, :subject_id, :lesson_number, :title, :slug, :introduction, 
                            :code_example, :key_takeaways, :estimated_time_minutes, 
                            :difficulty_level, :is_published)
                """
                
                diff_map = {"beginner": 1, "intermediate": 3, "advanced": 5}
                difficulty = diff_map.get(lesson.get('difficulty_level', 'beginner'), 1)

                await database.execute(insert_lesson_query, values={
                    "id": lesson_uuid,
                    "subject_id": subject_uuid,
                    "lesson_number": lesson_number,
                    "title": lesson['title'],
                    "slug": lesson['slug'],
                    "introduction": lesson['introduction'],
                    "code_example": lesson.get('code_example'),
                    "key_takeaways": lesson['key_takeaways'],
                    "estimated_time_minutes": lesson['estimated_time_minutes'],
                    "difficulty_level": difficulty,
                    "is_published": True
                })
                print(f"Inserted Lesson {lesson_number}: {lesson['title']}")

            # 4. Create/Update Quiz for the Lesson
            quiz_id = str(uuid.uuid4())
            # Check if quiz exists for this lesson
            existing_quiz = await database.fetch_one(
                "SELECT id FROM quizzes WHERE lesson_id = :lesson_id",
                values={"lesson_id": lesson_uuid}
            )

            if existing_quiz:
                quiz_uuid = existing_quiz['id']
            else:
                quiz_uuid = quiz_id
                insert_quiz_query = """
                    INSERT INTO quizzes (id, lesson_id, title, description, allow_rl_adaptation, passing_score)
                    VALUES (:id, :lesson_id, :title, :description, :allow_rl_adaptation, :passing_score)
                """
                await database.execute(insert_quiz_query, values={
                    "id": quiz_uuid,
                    "lesson_id": lesson_uuid,
                    "title": f"Quiz: {lesson['title']}",
                    "description": f"Test your knowledge on {lesson['title']}",
                    "allow_rl_adaptation": True,
                    "passing_score": 0.70
                })
                print(f"  Created Quiz for Lesson {lesson_number}")

            # 5. Insert Questions for this Quiz (matching part == lesson_number)
            lesson_questions = [q for q in questions_data if q.get('part') == lesson_number]
            
            print(f"  Found {len(lesson_questions)} questions for Lesson {lesson_number}")
            
            for q in lesson_questions:
                # Check if question exists (by question text to avoid dups if run multiple times)
                # Ideally we'd use a unique ID from source if available, but text is a reasonable proxy here 
                # or just delete all and recreate. Updating is safer.
                existing_question = await database.fetch_one(
                    "SELECT id FROM questions WHERE quiz_id = :quiz_id AND question_text = :question_text",
                    values={"quiz_id": quiz_uuid, "question_text": q['question_text']}
                )

                if not existing_question:
                    q_id = str(uuid.uuid4())
                    insert_q_query = """
                        INSERT INTO questions (id, quiz_id, ednet_question_id, question_text, code_snippet, 
                                             options, correct_answer, explanation, difficulty, concept, part)
                        VALUES (:id, :quiz_id, :ednet_question_id, :question_text, :code_snippet, 
                                :options, :correct_answer, :explanation, :difficulty, :concept, :part)
                    """
                    
                    # Ensure options is a JSON string
                    options_json = json.dumps(q['options'])
                    
                    await database.execute(insert_q_query, values={
                        "id": q_id,
                        "quiz_id": quiz_uuid,
                        "ednet_question_id": q.get('question_id'),
                        "question_text": q['question_text'],
                        "code_snippet": q.get('code_snippet'),
                        "options": options_json,
                        "correct_answer": q['correct_answer'],
                        "explanation": q.get('explanation'),
                        "difficulty": q.get('difficulty', 0.5), # Default difficulty
                        "concept": q.get('concept', 'General'),
                        "part": q.get('part')
                    })
    
    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("Disconnecting...")
        await database.disconnect()

if __name__ == "__main__":
    asyncio.run(insert_data())
