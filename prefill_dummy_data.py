import asyncio
import json
import uuid
import random
import os
from database import database
from auth import hash_password

async def prefill_dummy_data():
    print("Connecting to database...")
    await database.connect()
    
    try:
        print("Setting up teacher account...")
        email = "manish.ghindwani@gmail.com"
        existing_user = await database.fetch_one("SELECT id FROM users WHERE email = :email", {"email": email})
        
        if existing_user:
            teacher_uuid = existing_user["id"]
            print(f"Found existing teacher Manish Ghindwani: {teacher_uuid}")
        else:
            teacher_uuid = str(uuid.uuid4())
            await database.execute(
                """
                INSERT INTO users (id, email, password_hash, full_name, role, is_active)
                VALUES (:id, :email, :password_hash, :full_name, :role, :is_active)
                """,
                values={
                    "id": teacher_uuid,
                    "email": email,
                    "password_hash": hash_password("password123"),
                    "full_name": "Manish Ghindwani",
                    "role": "teacher",
                    "is_active": True
                }
            )
            print(f"Created new teacher Manish Ghindwani: {teacher_uuid}")

        print("Clearing existing data...")
        await database.execute("TRUNCATE TABLE subjects CASCADE;")
        await database.execute("TRUNCATE TABLE quiz_sessions CASCADE;")
        await database.execute("TRUNCATE TABLE lesson_progress CASCADE;")
        print("Data cleared.")
        
        # Load Java
        with open('java.txt', 'r', encoding='utf-8') as f:
            java_lessons = json.load(f)
            
        # Load Python provided by user
        with open('python.txt', 'r', encoding='utf-8') as f:
            python_lessons = json.load(f)

        # Load DSA provided by user
        with open('dsa.txt', 'r', encoding='utf-8') as f:
            dsa_lessons = json.load(f)

        # Load DL provided by user
        with open('dl.txt', 'r', encoding='utf-8') as f:
            dl_lessons = json.load(f)

        subjects_data = [
            {"id": "java_programming", "name": "Java Programming", "icon": "☕", "desc": "Learn enterprise-level programming utilizing the JVM.", "lessons": java_lessons},
            {"id": "python_basics", "name": "Python Programming", "icon": "🐍", "desc": "Master the fundamentals of Python programming.", "lessons": python_lessons},
            {"id": "dsa_basics", "name": "Data Structures & Algorithms", "icon": "🧮", "desc": "Learn the fundamental algorithms and data structures.", "lessons": dsa_lessons},
            {"id": "deep_learning", "name": "Deep Learning", "icon": "🧠", "desc": "Discover the magic of neural networks and AI.", "lessons": dl_lessons}
        ]

        print("Generating database content...")
        
        # A quick generator for valid, randomized quiz questions per lesson type
        def generate_questions(subject_name, lesson_idx, count=15):
            # Seed combinations to create actual distinct valid coding knowledge
            bases = [
                ["Which keyword is used to allocate memory for an object?", {"a": "import", "b": "new", "c": "alloc", "d": "create"}, "b"],
                ["What is the size of an int in Java?", {"a": "16 bit", "b": "32 bit", "c": "64 bit", "d": "8 bit"}, "b"],
                ["Which of these is not an access modifier?", {"a": "public", "b": "private", "c": "protected", "d": "void"}, "d"],
                ["What is the root class of all classes in Java?", {"a": "Base", "b": "Object", "c": "Main", "d": "Root"}, "b"],
                ["Which execution engine runs Java bytecode?", {"a": "JDK", "b": "JRE", "c": "JVM", "d": "JIT"}, "c"],
                ["Can an Interface implement another Interface?", {"a": "Yes, using implements", "b": "Yes, using extends", "c": "No", "d": "Only static interfaces"}, "b"],
                ["Which statement is used to jump to the next iteration of a loop?", {"a": "break", "b": "next", "c": "pass", "d": "continue"}, "d"],
                ["Which of the following is immutable?", {"a": "StringBuilder", "b": "StringBuffer", "c": "String", "d": "ArrayList"}, "c"],
                ["What exception is thrown when dividing by zero in integer arithmetic?", {"a": "ArithmeticException", "b": "ZeroDivisionException", "c": "MathException", "d": "NumberException"}, "a"],
                ["How do you get the length of an array `arr`?", {"a": "arr.length()", "b": "arr.size()", "c": "arr.length", "d": "arr.count"}, "c"],
                ["What keyword is used to prevent method overriding?", {"a": "static", "b": "final", "c": "abstract", "d": "private"}, "b"],
                ["Which collection allows duplicate elements?", {"a": "HashSet", "b": "TreeSet", "c": "ArrayList", "d": "HashMap"}, "c"],
                ["What is the default value of a local boolean variable?", {"a": "false", "b": "true", "c": "null", "d": "No default value (compilation error)"}, "d"],
                ["Which method must be implemented by a class implementing Runnable?", {"a": "start()", "b": "run()", "c": "init()", "d": "execute()"}, "b"],
                ["What maps keys to values?", {"a": "List", "b": "Set", "c": "Map", "d": "Queue"}, "c"],
                ["Which of these handles compilation?", {"a": "javac", "b": "java", "c": "jar", "d": "jvm"}, "a"],
                ["Can an abstract class have constructors?", {"a": "Yes", "b": "No", "c": "Only empty constructors", "d": "Only if private"}, "a"],
                ["What is the primitive wrapper class for `int`?", {"a": "Integer", "b": "Int", "c": "Number", "d": "Double"}, "a"],
                ["What indicates that a method does not return anything?", {"a": "null", "b": "void", "c": "empty", "d": "nothing"}, "b"],
                ["Which map implementation maintains insertion order?", {"a": "HashMap", "b": "LinkedHashMap", "c": "TreeMap", "d": "HashTable"}, "b"]
            ]
            
            # Shuffle and pick combinations based on lesson index to simulate real variation
            random.seed(lesson_idx * 10)
            sampled = random.sample(bases, min(count, len(bases)))
            
            # Guarantee exactly `count` questions per lesson with dynamic distributed difficulties from 0.1 to 1.0
            generated = []
            for i, q in enumerate(sampled):
                diff = round(0.1 + (i / float(count)) * 0.9, 2)
                # Introduce slight random perturbance
                diff = max(0.1, min(0.99, diff + random.uniform(-0.1, 0.1)))
                generated.append((q[0], q[1], q[2], round(diff, 2)))
        
            return generated

        for s_idx, s in enumerate(subjects_data):
            subject_uuid = str(uuid.uuid4())
            print(f"---\nInserting {s['name']} ...")
            
            await database.execute(
                """
                INSERT INTO subjects (id, subject_id, name, description, icon, is_published, created_by, created_at)
                VALUES (:id, :subject_id, :name, :description, :icon, :is_published, :created_by, NOW())
                """,
                values={
                    "id": subject_uuid,
                    "subject_id": s["id"],
                    "name": s["name"],
                    "description": s["desc"],
                    "icon": s["icon"],
                    "is_published": True,
                    "created_by": teacher_uuid
                }
            )

            for l_idx, lesson in enumerate(s["lessons"]):
                lesson_uuid = str(uuid.uuid4())
                
                await database.execute(
                    """
                    INSERT INTO lessons (id, subject_id, lesson_number, title, slug, introduction, 
                                       code_example, key_takeaways, estimated_time_minutes, 
                                       difficulty_level, is_published)
                    VALUES (:id, :subject_id, :lesson_number, :title, :slug, :introduction, 
                            :code_example, :key_takeaways, :estimated_time_minutes, 
                            :difficulty_level, :is_published)
                    """,
                    values={
                        "id": lesson_uuid,
                        "subject_id": subject_uuid,
                        "lesson_number": lesson.get("lesson_number", l_idx + 1),
                        "title": lesson.get("title"),
                        "slug": lesson.get("slug", f"lesson-{l_idx+1}"),
                        "introduction": lesson.get("introduction"),
                        "code_example": lesson.get("code_example"),
                        "key_takeaways": lesson.get("key_takeaways", []),
                        "estimated_time_minutes": lesson.get("estimated_time_minutes", 15),
                        "difficulty_level": (l_idx + 1),
                        "is_published": True
                    }
                )

                quiz_uuid = str(uuid.uuid4())
                
                # Default 5 questions per quiz
                await database.execute(
                    """
                    INSERT INTO quizzes (id, lesson_id, title, description, allow_rl_adaptation, passing_score, default_num_questions)
                    VALUES (:id, :lesson_id, :title, :description, :allow_rl_adaptation, :passing_score, :default_num_questions)
                    """,
                    values={
                        "id": quiz_uuid,
                        "lesson_id": lesson_uuid,
                        "title": f"Quiz: {lesson.get('title')}",
                        "description": f"Test yourself on {lesson.get('title')}",
                        "allow_rl_adaptation": True,
                        "passing_score": 0.70,
                        "default_num_questions": 5
                    }
                )

                questions_pool = []
                if "quiz_questions" in lesson:
                    for q in lesson["quiz_questions"]:
                        opts_dict = {}
                        correct_mapping = {0: "a", 1: "b", 2: "c", 3: "d", 4: "e", 5: "f"}
                        for i, opt_val in enumerate(q.get("options", [])):
                            opts_dict[correct_mapping.get(i, str(i))] = str(opt_val)
                        
                        correct_key = correct_mapping.get(q.get("correct_answer", 0), "a")
                        
                        # Handle difficulty mapping
                        diff_str = str(q.get("difficulty", "medium")).lower()
                        if diff_str == "easy":
                            diff_val = round(random.uniform(0.1, 0.35), 2)
                        elif diff_str == "medium":
                            diff_val = round(random.uniform(0.4, 0.7), 2)
                        elif diff_str == "hard":
                            diff_val = round(random.uniform(0.75, 1.0), 2)
                        else:
                            diff_val = 0.5
                            
                        explanation = q.get("explanation", f"The correct answer is {correct_key}.")
                        
                        questions_pool.append((q.get("question_text"), opts_dict, correct_key, diff_val, explanation))
                else:
                    # Generate 15 distinct questions for THIS lesson spreading difficulty from 0.1 -> 1.0
                    questions_generated = generate_questions(s["name"], l_idx, count=15)
                    for q in questions_generated:
                        questions_pool.append((q[0], q[1], q[2], q[3], f"The correct answer is {q[2]}."))
                
                for q_idx, q_data in enumerate(questions_pool):
                    q_text, opts, correct, diff, explanation = q_data
                    q_uuid = str(uuid.uuid4())
                    
                    await database.execute(
                        """
                        INSERT INTO questions (id, quiz_id, ednet_question_id, question_text, code_snippet, 
                                             options, correct_answer, explanation, difficulty, concept, part)
                        VALUES (:id, :quiz_id, :ednet_question_id, :question_text, :code_snippet, 
                                :options, :correct_answer, :explanation, :difficulty, :concept, :part)
                        """,
                        values={
                            "id": q_uuid,
                            "quiz_id": quiz_uuid,
                            "ednet_question_id": f"q{s_idx}{l_idx}{q_idx}",
                            "question_text": q_text,
                            "code_snippet": None,
                            "options": json.dumps(opts),
                            "correct_answer": correct,
                            "explanation": explanation,
                            "difficulty": float(diff),
                            "concept": str(lesson.get("title")),
                            "part": l_idx + 1
                        }
                    )

        print("\nSuccessfully prefilled questions per lesson!")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("Disconnecting...")
        await database.disconnect()

if __name__ == "__main__":
    asyncio.run(prefill_dummy_data())
