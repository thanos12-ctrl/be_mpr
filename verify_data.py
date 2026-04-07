import asyncio
from database import database

async def verify_data():
    try:
        await database.connect()
        print("Connected to database.")

        # Check Subject
        subject = await database.fetch_one("SELECT id, name FROM subjects WHERE subject_id = 'java_programming'")
        if subject:
            print(f"[OK] Subject found: {subject['name']} (ID: {subject['id']})")
            
            # Check Lessons
            lessons = await database.fetch_all("SELECT id, lesson_number, title FROM lessons WHERE subject_id = :sid ORDER BY lesson_number", values={"sid": subject['id']})
            print(f"[OK] Found {len(lessons)} lessons.")
            
            for lesson in lessons:
                 # Check Quiz
                quiz = await database.fetch_one("SELECT id, title FROM quizzes WHERE lesson_id = :lid", values={"lid": lesson['id']})
                if quiz:
                     # Check Questions
                    question_count = await database.fetch_val("SELECT count(*) FROM questions WHERE quiz_id = :qid", values={"qid": quiz['id']})
                    print(f"   Lesson {lesson['lesson_number']}: {lesson['title']} -> Quiz: {quiz['title']} -> Questions: {question_count}")
                else:
                    print(f"   Lesson {lesson['lesson_number']}: {lesson['title']} -> [MISSING] No Quiz")

        else:
            print("[FAIL] Subject 'java_programming' not found.")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await database.disconnect()

if __name__ == "__main__":
    asyncio.run(verify_data())
