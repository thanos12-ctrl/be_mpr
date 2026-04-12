import asyncio
import json
import uuid
import random
import os
from database import database

async def prefill_dummy_data():
    print("Connecting to database...")
    await database.connect()
    
    try:
        print("Clearing existing data...")
        await database.execute("TRUNCATE TABLE subjects CASCADE;")
        await database.execute("TRUNCATE TABLE quiz_sessions CASCADE;")
        await database.execute("TRUNCATE TABLE lesson_progress CASCADE;")
        print("Data cleared.")
        
        # Load Java
        with open('lessons/lesson_content_java_programming.json', 'r') as f:
            java_lessons = json.load(f)
            
        # Load Python provided by user
        python_lessons = [
            {
                "lesson_number": 1,
                "title": "Basic Syntax & Data Types",
                "slug": "basic-syntax-data-types",
                "difficulty_level": "beginner",
                "estimated_time_minutes": 45,
                "introduction": "Welcome to the world of Python! This lesson introduces you to the 'Zen of Python'...",
                "code_example": "age = 30\nprice = 19.99\nis_student = True",
                "key_takeaways": [],
                "topics": ["Variables", "Dynamic typing", "Integers"]
            },
            {
                "lesson_number": 2,
                "title": "Operators & Expressions",
                "slug": "operators-expressions",
                "difficulty_level": "beginner",
                "estimated_time_minutes": 40,
                "introduction": "In Python, operators are the verbs of the language.",
                "code_example": "sum_val = 10 + 3",
                "key_takeaways": [],
                "topics": ["Arithmetic", "Logical"]
            },
            {
                "lesson_number": 3,
                "title": "Control Flow (If/Else, Loops)",
                "slug": "control-flow",
                "difficulty_level": "beginner",
                "estimated_time_minutes": 50,
                "introduction": "Control flow is how you give your program a brain.",
                "code_example": "if age < 13: print('Child')",
                "key_takeaways": [],
                "topics": ["If statements", "Loops"]
            },
            {
                "lesson_number": 4,
                "title": "Data Structures (Lists & Dictionaries)",
                "slug": "data-structures",
                "difficulty_level": "intermediate",
                "estimated_time_minutes": 55,
                "introduction": "Python's built-in data structures are its greatest strength.",
                "code_example": "numbers = [10, 20, 30]",
                "key_takeaways": [],
                "topics": ["Lists", "Dictionaries", "Tuples"]
            },
            {
                "lesson_number": 5,
                "title": "Functions & Modules",
                "slug": "functions-modules",
                "difficulty_level": "intermediate",
                "estimated_time_minutes": 50,
                "introduction": "Functions are the building blocks of reusable code.",
                "code_example": "def greet(name): return f'Hello {name}'",
                "key_takeaways": [],
                "topics": ["Functions", "Modules"]
            },
            {
                "lesson_number": 6,
                "title": "Object-Oriented Programming (OOP)",
                "slug": "oop-basics",
                "difficulty_level": "intermediate",
                "estimated_time_minutes": 60,
                "introduction": "Object-Oriented Programming in Python is designed to be intuitive.",
                "code_example": "class Animal: pass",
                "key_takeaways": [],
                "topics": ["Classes", "Objects", "Inheritance"]
            },
            {
                "lesson_number": 7,
                "title": "Exception Handling & File I/O",
                "slug": "exceptions-files",
                "difficulty_level": "advanced",
                "estimated_time_minutes": 60,
                "introduction": "Professional programs must handle errors gracefully.",
                "code_example": "try: 100/0 except: pass",
                "key_takeaways": [],
                "topics": ["Exceptions", "File I/O"]
            }
        ]

        subjects_data = [
            {"id": "python_basics", "name": "Python Programming", "icon": "🐍", "desc": "Master the fundamentals of Python programming.", "lessons": python_lessons},
            {"id": "java_programming", "name": "Java Engineering", "icon": "☕", "desc": "Learn enterprise-level programming utilizing the JVM.", "lessons": java_lessons}
        ]

        print("Generating database content...")
        
        # A quick generator for valid, randomized quiz questions per lesson type
        def generate_questions(subject_name, lesson_idx, count=15):
            questions = []
            
            # Seed combinations to create actual distinct valid coding knowledge
            if subject_name == "Python Programming":
                bases = [
                    ["What is the output of `type(5)`?", {"a": "int", "b": "float", "c": "str", "d": "bool"}, "a"],
                    ["How do you insert an element at the end of a list?", {"a": "list.add()", "b": "list.insert()", "c": "list.append()", "d": "list.push()"}, "c"],
                    ["Which of these is immutable?", {"a": "List", "b": "Dictionary", "c": "Set", "d": "Tuple"}, "d"],
                    ["How do you create a function in Python?", {"a": "def func():", "b": "function func():", "c": "create func():", "d": "func def():"}, "a"],
                    ["What keyword is used for exception handling?", {"a": "catch", "b": "except", "c": "error", "d": "handle"}, "b"],
                    ["Which operator performs floor division?", {"a": "/", "b": "//", "c": "%", "d": "**"}, "b"],
                    ["What is the result of `2 ** 3`?", {"a": "6", "b": "8", "c": "9", "d": "5"}, "b"],
                    ["How is an empty dictionary declared?", {"a": "{}", "b": "[]", "c": "()", "d": "{0}"}, "a"],
                    ["Which method removes the last item from a list?", {"a": "remove()", "b": "delete()", "c": "pop()", "d": "discard()"}, "c"],
                    ["What is the output of `len('hello')`?", {"a": "4", "b": "5", "c": "6", "d": "0"}, "b"],
                    ["How do you read a file in Python safely?", {"a": "open(f)", "b": "read(f)", "c": "with open(f)", "d": "load(f)"}, "c"],
                    ["Which class method acts as a constructor?", {"a": "__init__", "b": "constructor", "c": "new", "d": "__main__"}, "a"],
                    ["How do you import the math module?", {"a": "import math", "b": "include math", "c": "require math", "d": "using math"}, "a"],
                    ["What does `break` do in a loop?", {"a": "Skips iteration", "b": "Exits loop completely", "c": "Pauses loop", "d": "Ends program"}, "b"],
                    ["Which of these is NOT a core data type?", {"a": "Tuple", "b": "List", "c": "Class", "d": "Dictionary"}, "c"],
                    ["What does `str(123)` return?", {"a": "123", "b": "'123'", "c": "Error", "d": "None"}, "b"],
                    ["How do you check if a key exists in a dict?", {"a": "key in dict", "b": "dict.has(key)", "c": "dict.exists(key)", "d": "key.exists()"}, "a"],
                    ["What does `random.randint(1, 10)` do?", {"a": "Generates 1 to 9", "b": "Generates 1 to 10", "c": "Returns float", "d": "Syntax Error"}, "b"],
                    ["How do you concatenate strings?", {"a": "str1 + str2", "b": "str1 . str2", "c": "str1 & str2", "d": "str1 * str2"}, "a"],
                    ["What is the boolean evaluation of an empty list? `bool([])`", {"a": "True", "b": "False", "c": "None", "d": "Error"}, "b"]
                ]
            else:
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
                INSERT INTO subjects (id, subject_id, name, description, icon, is_published, created_at)
                VALUES (:id, :subject_id, :name, :description, :icon, :is_published, NOW())
                """,
                values={
                    "id": subject_uuid,
                    "subject_id": s["id"],
                    "name": s["name"],
                    "description": s["desc"],
                    "icon": s["icon"],
                    "is_published": True
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

                # Generate 15 distinct questions for THIS lesson spreading difficulty from 0.1 -> 1.0
                questions_pool = generate_questions(s["name"], l_idx, count=15)
                
                for q_idx, q_data in enumerate(questions_pool):
                    q_text, opts, correct, diff = q_data
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
                            "explanation": f"The correct answer is {correct}.",
                            "difficulty": float(diff),
                            "concept": str(lesson.get("title")),
                            "part": l_idx + 1
                        }
                    )

        print("\nSuccessfully prefilled 15 questions per lesson!")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("Disconnecting...")
        await database.disconnect()

if __name__ == "__main__":
    asyncio.run(prefill_dummy_data())
