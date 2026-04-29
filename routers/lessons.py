"""
Lesson Management Router
Handles lesson creation, updates, retrieval, and publishing
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import UUID4
from typing import List, Optional
from datetime import datetime
import uuid

from database import database
from dependencies import require_role
import models as m


router = APIRouter(prefix="/api/lessons", tags=["Lessons"])


@router.post("", response_model=m.LessonResponse)
async def create_lesson(
    lesson_data: m.LessonCreate,
    current_user: dict = Depends(require_role(m.UserRole.ADMIN, m.UserRole.TEACHER))
):
    """Create a new lesson (Admin/Teacher only)"""
    
    # Verify subject exists and user has permission
    subject_query = "SELECT created_by FROM subjects WHERE id = :subject_id"
    subject = await database.fetch_one(query=subject_query, values={"subject_id": str(lesson_data.subject_id)})
    
    if not subject:
        raise HTTPException(status_code=404, detail="Subject not found")
        
    if current_user["role"] != "admin" and subject["created_by"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to add lessons to this subject")

    lesson_id = uuid.uuid4()
    query = """
        INSERT INTO lessons (
            id, subject_id, lesson_number, title, slug, introduction,
            code_example, key_takeaways, estimated_time_minutes, difficulty_level,
            prerequisites, is_published, created_at, updated_at
        )
        VALUES (
            :id, :subject_id, :lesson_number, :title, :slug, :introduction,
            :code_example, :key_takeaways, :estimated_time_minutes, :difficulty_level,
            :prerequisites, :is_published, :created_at, :updated_at
        )
        RETURNING *
    """
    
    lesson = await database.fetch_one(
        query=query,
        values={
            "id": str(lesson_id),
            "subject_id": str(lesson_data.subject_id),
            "lesson_number": lesson_data.lesson_number,
            "title": lesson_data.title,
            "slug": lesson_data.slug,
            "introduction": lesson_data.introduction,
            "code_example": lesson_data.code_example,
            "key_takeaways": lesson_data.key_takeaways,
            "estimated_time_minutes": lesson_data.estimated_time_minutes,
            "difficulty_level": lesson_data.difficulty_level,
            "prerequisites": [str(p) for p in lesson_data.prerequisites],
            "is_published": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
    )
    
    if not lesson:
        raise HTTPException(status_code=500, detail="Failed to create lesson")
    
    # Automatically create a quiz for this lesson
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
        RETURNING id
    """
    
    await database.fetch_one(
        query=quiz_query,
        values={
            "id": str(quiz_id),
            "lesson_id": str(lesson_id),
            "title": f"{lesson_data.title} - Quiz",
            "description": f"Quiz for {lesson_data.title}",
            "allow_rl_adaptation": True,
            "default_num_questions": 10,
            "passing_score": 0.70,
            "created_at": datetime.utcnow()
        }
    )
    
    return m.LessonResponse(**format_lesson_response(lesson))


@router.get("", response_model=List[m.LessonResponse])
async def get_lessons(subject_id: Optional[UUID4] = None):
    """Get all lessons, optionally filtered by subject"""
    
    if subject_id:
        query = "SELECT * FROM lessons WHERE subject_id = :subject_id AND is_published = TRUE ORDER BY lesson_number"
        lessons = await database.fetch_all(query=query, values={"subject_id": str(subject_id)})
    else:
        query = "SELECT * FROM lessons WHERE is_published = TRUE ORDER BY lesson_number"
        lessons = await database.fetch_all(query=query)
    
    return [m.LessonResponse(**{**dict(l), "prerequisites": l["prerequisites"] or []})
    for l in lessons]


@router.get("/{lesson_id}", response_model=m.LessonResponse)
async def get_lesson(lesson_id: UUID4):
    """Get a specific lesson by ID"""
    
    query = "SELECT * FROM lessons WHERE id = :lesson_id"
    lesson = await database.fetch_one(query=query, values={"lesson_id": str(lesson_id)})
    
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    lesson_data = dict(lesson)
    if lesson_data.get("prerequisites") is None:
        lesson_data["prerequisites"] = []
    
    return m.LessonResponse(**lesson_data)


@router.put("/{lesson_id}", response_model=m.LessonResponse)
async def update_lesson(
    lesson_id: UUID4,
    lesson_data: m.LessonUpdate,
    current_user: dict = Depends(require_role(m.UserRole.ADMIN, m.UserRole.TEACHER))
):
    """Update a lesson (Admin/Teacher only)"""

    # Verify lesson exists and user has permission
    check_query = """
        SELECT l.id, s.created_by 
        FROM lessons l
        JOIN subjects s ON l.subject_id = s.id
        WHERE l.id = :lesson_id
    """
    existing = await database.fetch_one(query=check_query, values={"lesson_id": str(lesson_id)})
    
    if not existing:
        raise HTTPException(status_code=404, detail="Lesson not found")
        
    if current_user["role"] != "admin" and existing["created_by"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to update lessons in this subject")
    
    # Build dynamic update query
    updates = []
    values = {"lesson_id": str(lesson_id), "updated_at": datetime.utcnow()}
    
    for field, value in lesson_data.dict(exclude_unset=True).items():
        if value is not None:
            updates.append(f"{field} = :{field}")
            values[field] = value
    
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    updates.append("updated_at = :updated_at")
    query = f"UPDATE lessons SET {', '.join(updates)} WHERE id = :lesson_id RETURNING *"
    
    lesson = await database.fetch_one(query=query, values=values)
    
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    return m.LessonResponse(**format_lesson_response(lesson))


@router.patch("/{lesson_id}/publish", response_model=m.LessonResponse)
async def toggle_lesson_publish(
    lesson_id: UUID4,
    current_user: dict = Depends(require_role(m.UserRole.ADMIN, m.UserRole.TEACHER))
):
    """Toggle lesson publish status"""
    
    # Verify lesson exists and user has permission
    check_query = """
        SELECT l.id, s.created_by 
        FROM lessons l
        JOIN subjects s ON l.subject_id = s.id
        WHERE l.id = :lesson_id
    """
    existing = await database.fetch_one(query=check_query, values={"lesson_id": str(lesson_id)})
    
    if not existing:
        raise HTTPException(status_code=404, detail="Lesson not found")
        
    if current_user["role"] != "admin" and existing["created_by"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to modify publish status of lessons in this subject")

    query = """
        UPDATE lessons
        SET is_published = NOT is_published, updated_at = :updated_at
        WHERE id = :lesson_id
        RETURNING *
    """
    
    lesson = await database.fetch_one(
        query=query,
        values={"lesson_id": str(lesson_id), "updated_at": datetime.utcnow()}
    )
    
    if not lesson:
        raise HTTPException(status_code=404, detail="Lesson not found")
    
    return m.LessonResponse(**format_lesson_response(lesson))

def format_lesson_response(lesson_row):
    """Converts a database row to a dict and ensures prerequisites is a list."""
    data = dict(lesson_row)
    if data.get("prerequisites") is None:
        data["prerequisites"] = []
    return data

@router.delete("/{lesson_id}")
async def delete_lesson(
    lesson_id: UUID4,
    current_user: dict = Depends(require_role(m.UserRole.ADMIN, m.UserRole.TEACHER))
):
    """Delete an existing lesson (Admin/Teacher only)"""
    
    # Verify lesson exists and user has permission
    check_query = """
        SELECT l.id, s.created_by 
        FROM lessons l
        JOIN subjects s ON l.subject_id = s.id
        WHERE l.id = :lesson_id
    """
    existing = await database.fetch_one(query=check_query, values={"lesson_id": str(lesson_id)})
    
    if not existing:
        raise HTTPException(status_code=404, detail="Lesson not found")
        
    if current_user["role"] != "admin" and existing["created_by"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to delete lessons in this subject")
    
    # Delete the lesson (cascades or handle relations appropriately depending on DB schema)
    # If quizzes are tied to lessons, deleting the lesson might need to cascade to quizzes.
    # We will just delete the lesson for now.
    query = "DELETE FROM lessons WHERE id = :lesson_id"
    await database.execute(query=query, values={"lesson_id": str(lesson_id)})
    
    return {"message": "Lesson deleted successfully"}