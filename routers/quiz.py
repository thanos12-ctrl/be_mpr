"""
Quiz and Question Management Router
Handles quiz and question CRUD operations for teachers/admins
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from datetime import datetime
import uuid
import json

from database import database
from dependencies import require_role
import models as m


router = APIRouter(prefix="/api/admin", tags=["Quiz Management"])


@router.post("/quizzes", response_model=m.QuizResponse)
async def create_quiz(
    quiz_data: m.QuizCreate,
    current_user: dict = Depends(require_role(["teacher", "admin"]))
):
    """Create a new quiz for a lesson"""
    
    # Verify lesson exists and ownership
    lesson_query = """
        SELECT l.id, s.created_by 
        FROM lessons l
        JOIN subjects s ON l.subject_id = s.id
        WHERE l.id = :lesson_id
    """
    lesson = await database.fetch_one(query=lesson_query, values={"lesson_id": str(quiz_data.lesson_id)})
    
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
        
    if current_user["role"] != "admin" and lesson["created_by"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to add quizzes to this lesson")
    
    # Create quiz
    quiz_id = uuid.uuid4()
    query = """
        INSERT INTO quizzes (
            id, lesson_id, title, description, allow_rl_adaptation,
            default_num_questions, passing_score, created_at
        )
        VALUES (:id, :lesson_id, :title, :description, :allow_rl_adaptation,
                :default_num_questions, :passing_score, :created_at)
        RETURNING *
    """
    
    quiz = await database.fetch_one(
        query=query,
        values={
            "id": str(quiz_id),
            "lesson_id": str(quiz_data.lesson_id),
            "title": quiz_data.title,
            "description": quiz_data.description,
            "allow_rl_adaptation": quiz_data.allow_rl_adaptation,
            "default_num_questions": quiz_data.default_num_questions,
            "passing_score": quiz_data.passing_score,
            "created_at": datetime.utcnow()
        }
    )
    
    return m.QuizResponse(**dict(quiz))


@router.post("/quizzes/generate-for-lessons")
async def generate_quizzes_for_lessons(
    current_user: dict = Depends(require_role(m.UserRole.ADMIN, m.UserRole.TEACHER))
):
    """Generate quizzes for all lessons that don't have one"""
    
    # Find lessons without quizzes
    query_conditions = "q.id IS NULL"
    values = {}
    if current_user["role"] != "admin":
        query_conditions += " AND s.created_by = :teacher_id"
        values["teacher_id"] = current_user["id"]
        
    query = f"""
        SELECT l.id, l.title
        FROM lessons l
        JOIN subjects s ON l.subject_id = s.id
        LEFT JOIN quizzes q ON l.id = q.lesson_id
        WHERE {query_conditions}
    """
    
    lessons_without_quizzes = await database.fetch_all(query=query, values=values)
    
    created_count = 0
    for lesson in lessons_without_quizzes:
        quiz_id = uuid.uuid4()
        quiz_query = """
            INSERT INTO quizzes (
                id, lesson_id, title, description, allow_rl_adaptation,
                default_num_questions, passing_score, created_at
            )
            VALUES (
                :id, :lesson_id, :title, :description, :allow_rl_adaptation,
                :default_num_questions, :passing_score, :created_at
            )
        """
        
        await database.execute(
            query=quiz_query,
            values={
                "id": str(quiz_id),
                "lesson_id": str(lesson["id"]),
                "title": f"{lesson['title']} - Quiz",
                "description": f"Quiz for {lesson['title']}",
                "allow_rl_adaptation": True,
                "default_num_questions": 10,
                "passing_score": 0.70,
                "created_at": datetime.utcnow()
            }
        )
        created_count += 1
    
    return {
        "message": f"Successfully created {created_count} quizzes",
        "created_count": created_count
    }


@router.get("/quizzes", response_model=List[m.QuizResponse])
async def list_quizzes(
    lesson_id: Optional[str] = None,
    current_user: dict = Depends(require_role(["teacher", "admin"]))
):
    """List all quizzes, optionally filtered by lesson"""
    
    if lesson_id:
        query = "SELECT * FROM quizzes WHERE lesson_id = :lesson_id ORDER BY created_at DESC"
        quizzes = await database.fetch_all(query=query, values={"lesson_id": lesson_id})
    else:
        query = "SELECT * FROM quizzes ORDER BY created_at DESC"
        quizzes = await database.fetch_all(query=query)
    
    return [m.QuizResponse(**dict(quiz)) for quiz in quizzes]


@router.put("/quizzes/{quiz_id}", response_model=m.QuizResponse)
async def update_quiz(
    quiz_id: str,
    quiz_data: m.QuizUpdate,
    current_user: dict = Depends(require_role(["teacher", "admin"]))
):
    """Update a quiz's settings (title, description, num questions, passing score)"""

    # Verify quiz exists and ownership
    ownership_query = """
        SELECT q.id, s.created_by
        FROM quizzes q
        JOIN lessons l ON q.lesson_id = l.id
        JOIN subjects s ON l.subject_id = s.id
        WHERE q.id = :quiz_id
    """
    quiz = await database.fetch_one(query=ownership_query, values={"quiz_id": quiz_id})

    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")

    if current_user["role"] != "admin" and quiz["created_by"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to edit this quiz")

    # Build dynamic SET clause for only provided fields
    updates = {k: v for k, v in quiz_data.dict().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    set_clause = ", ".join(f"{k} = :{k}" for k in updates)
    updates["quiz_id"] = quiz_id

    query = f"UPDATE quizzes SET {set_clause} WHERE id = :quiz_id RETURNING *"
    updated = await database.fetch_one(query=query, values=updates)

    return m.QuizResponse(**dict(updated))


@router.post("/questions", response_model=m.QuestionResponse)
async def create_question(
    question_data: m.QuestionCreate,
    current_user: dict = Depends(require_role(["teacher", "admin"]))
):
    """Create a new quiz question"""
    
    # Verify quiz exists and user has permission
    quiz_query = """
        SELECT q.id, s.created_by
        FROM quizzes q
        JOIN lessons l ON q.lesson_id = l.id
        JOIN subjects s ON l.subject_id = s.id
        WHERE q.id = :quiz_id
    """
    quiz = await database.fetch_one(query=quiz_query, values={"quiz_id": str(question_data.quiz_id)})
    
    if not quiz:
        raise HTTPException(status_code=404, detail="Quiz not found")
        
    if current_user["role"] != "admin" and quiz["created_by"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to add questions to this quiz")
    
    # Validate correct_answer is in options
    if question_data.correct_answer not in question_data.options:
        raise HTTPException(status_code=400, detail="Correct answer must be one of the options")
    
    # Create question
    question_id = uuid.uuid4()
    query = """
        INSERT INTO questions (
            id, quiz_id, ednet_question_id, question_text, code_snippet,
            options, correct_answer, explanation, difficulty, concept, part, created_at
        )
        VALUES (:id, :quiz_id, :ednet_question_id, :question_text, :code_snippet,
                :options, :correct_answer, :explanation, :difficulty, :concept, :part, :created_at)
        RETURNING *
    """
    
    question = await database.fetch_one(
        query=query,
        values={
            "id": str(question_id),
            "quiz_id": str(question_data.quiz_id),
            "ednet_question_id": question_data.ednet_question_id,
            "question_text": question_data.question_text,
            "code_snippet": question_data.code_snippet,
            "options": json.dumps(question_data.options),
            "correct_answer": question_data.correct_answer,
            "explanation": question_data.explanation,
            "difficulty": question_data.difficulty,
            "concept": question_data.concept,
            "part": question_data.part,
            "created_at": datetime.utcnow()
        }
    )
    question_dict = dict(question)

    # FIX: Parse the 'options' string back into a dictionary
    if isinstance(question_dict["options"], str):
        question_dict["options"] = json.loads(question_dict["options"])

    return m.QuestionResponse(**question_dict)


@router.get("/questions", response_model=List[m.QuestionResponse])
async def list_questions(
        quiz_id: Optional[str] = None,
        concept: Optional[str] = None,
        current_user: dict = Depends(require_role(["teacher", "admin"]))
):
    """List all questions, optionally filtered by quiz or concept"""

    conditions = []
    values = {}

    if quiz_id:
        conditions.append("quiz_id = :quiz_id")
        values["quiz_id"] = quiz_id

    if concept:
        conditions.append("concept = :concept")
        values["concept"] = concept

    where_clause = " AND ".join(conditions) if conditions else "1=1"
    query = f"SELECT * FROM questions WHERE {where_clause} ORDER BY created_at DESC"

    questions = await database.fetch_all(query=query, values=values)

    # --- FIX: Parse options string to dict for every question ---
    results = []
    for q in questions:
        q_dict = dict(q)  # Convert DB row to mutable dict

        # Check and parse JSON string
        if isinstance(q_dict.get('options'), str):
            try:
                q_dict['options'] = json.loads(q_dict['options'])
            except json.JSONDecodeError:
                q_dict['options'] = {}  # Fallback if JSON is corrupt

        results.append(m.QuestionResponse(**q_dict))

    return results

@router.get("/questions/{question_id}", response_model=m.QuestionResponse)
async def get_question(
    question_id: str,
    current_user: dict = Depends(require_role(["teacher", "admin"]))
):
    """Get a specific question by ID"""
    
    query = "SELECT * FROM questions WHERE id = :question_id"
    question = await database.fetch_one(query=query, values={"question_id": question_id})
    
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    
    return m.QuestionResponse(**dict(question))


@router.put("/questions/{question_id}", response_model=m.QuestionResponse)
async def update_question(
    question_id: str,
    question_data: m.QuestionUpdate,
    current_user: dict = Depends(require_role(["teacher", "admin"]))
):
    """Update an existing question"""
    
    # Check if question exists and check permission
    check_query = """
        SELECT q_table.id, s.created_by
        FROM questions q_table
        JOIN quizzes q ON q_table.quiz_id = q.id
        JOIN lessons l ON q.lesson_id = l.id
        JOIN subjects s ON l.subject_id = s.id
        WHERE q_table.id = :question_id
    """
    existing = await database.fetch_one(query=check_query, values={"question_id": question_id})
    
    if not existing:
        raise HTTPException(status_code=404, detail="Question not found")
        
    if current_user["role"] != "admin" and existing["created_by"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to modify questions in this subject")
    
    # Build update query dynamically
    update_fields = []
    values = {"question_id": question_id}
    
    if question_data.question_text is not None:
        update_fields.append("question_text = :question_text")
        values["question_text"] = question_data.question_text
    
    if question_data.code_snippet is not None:
        update_fields.append("code_snippet = :code_snippet")
        values["code_snippet"] = question_data.code_snippet
    
    if question_data.options is not None:
        update_fields.append("options = :options")
        values["options"] = json.dumps(question_data.options)
    
    if question_data.correct_answer is not None:
        update_fields.append("correct_answer = :correct_answer")
        values["correct_answer"] = question_data.correct_answer
    
    if question_data.explanation is not None:
        update_fields.append("explanation = :explanation")
        values["explanation"] = question_data.explanation
    
    if question_data.difficulty is not None:
        update_fields.append("difficulty = :difficulty")
        values["difficulty"] = question_data.difficulty
    
    if question_data.concept is not None:
        update_fields.append("concept = :concept")
        values["concept"] = question_data.concept
    
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    query = f"""
        UPDATE questions
        SET {', '.join(update_fields)}
        WHERE id = :question_id
        RETURNING *
    """
    
    question = await database.fetch_one(query=query, values=values)
    
    if not question:
        raise HTTPException(status_code=404, detail="Failed to update question")
        
    question_dict = dict(question)
    if isinstance(question_dict.get("options"), str):
        try:
            question_dict["options"] = json.loads(question_dict["options"])
        except json.JSONDecodeError:
            question_dict["options"] = {}
            
    return m.QuestionResponse(**question_dict)


@router.delete("/questions/{question_id}")
async def delete_question(
    question_id: str,
    current_user: dict = Depends(require_role(["teacher", "admin"]))
):
    """Delete a question"""
    
    # Check if question exists and check permission
    check_query = """
        SELECT q_table.id, s.created_by
        FROM questions q_table
        JOIN quizzes q ON q_table.quiz_id = q.id
        JOIN lessons l ON q.lesson_id = l.id
        JOIN subjects s ON l.subject_id = s.id
        WHERE q_table.id = :question_id
    """
    existing = await database.fetch_one(query=check_query, values={"question_id": question_id})
    
    if not existing:
        raise HTTPException(status_code=404, detail="Question not found")
        
    if current_user["role"] != "admin" and existing["created_by"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to delete questions in this subject")
    
    # Delete question
    query = "DELETE FROM questions WHERE id = :question_id"
    await database.execute(query=query, values={"question_id": question_id})
    
    return {"message": "Question deleted successfully"}
