"""
Student Progress Tracking Router
Handles lesson progress updates and overview
"""

from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime
import uuid

from database import database
from dependencies import get_current_student
import models as m


router = APIRouter(prefix="/api/progress", tags=["Progress"])


@router.post("/lessons", response_model=m.LessonProgressResponse)
async def update_lesson_progress(
    progress_data: m.LessonProgressUpdate,
    current_user: dict = Depends(get_current_student)
):
    """Update student's lesson progress"""
    
    # Check if progress record exists
    check_query = "SELECT id FROM lesson_progress WHERE student_id = :student_id AND lesson_id = :lesson_id"
    existing = await database.fetch_one(
        query=check_query,
        values={"student_id": current_user["id"], "lesson_id": str(progress_data.lesson_id)}
    )
    
    if existing:
        # Update existing
        query = """
            UPDATE lesson_progress
            SET time_spent_seconds = time_spent_seconds + :time_spent_seconds,
                last_position = :last_position,
                is_completed = :is_completed,
                completed_at = CASE WHEN :is_completed THEN :now ELSE completed_at END
            WHERE id = :id
            RETURNING *
        """
        progress = await database.fetch_one(
            query=query,
            values={
                "id": existing["id"],
                "time_spent_seconds": progress_data.time_spent_seconds,
                "last_position": progress_data.last_position,
                "is_completed": progress_data.is_completed,
                "now": datetime.utcnow()
            }
        )
    else:
        # Create new
        progress_id = uuid.uuid4()
        query = """
            INSERT INTO lesson_progress (
                id, student_id, lesson_id, started_at, time_spent_seconds,
                last_position, is_completed, completed_at
            )
            VALUES (:id, :student_id, :lesson_id, :started_at, :time_spent_seconds,
                    :last_position, :is_completed, :completed_at)
            RETURNING *
        """
        progress = await database.fetch_one(
            query=query,
            values={
                "id": str(progress_id),
                "student_id": current_user["id"],
                "lesson_id": str(progress_data.lesson_id),
                "started_at": datetime.utcnow(),
                "time_spent_seconds": progress_data.time_spent_seconds,
                "last_position": progress_data.last_position,
                "is_completed": progress_data.is_completed,
                "completed_at": datetime.utcnow() if progress_data.is_completed else None
            }
        )
    
    return m.LessonProgressResponse(**dict(progress))


@router.get("/overview", response_model=m.ProgressOverview)
async def get_progress_overview(current_user: dict = Depends(get_current_student)):
    """Get student's overall progress overview"""
    
    # Get lesson stats
    lesson_query = """
        SELECT
            COUNT(*) as total_lessons,
            COUNT(*) FILTER (WHERE is_completed = TRUE) as completed_lessons,
            COALESCE(SUM(time_spent_seconds), 0) as total_time
        FROM lesson_progress
        WHERE student_id = :student_id
    """
    lesson_stats = await database.fetch_one(query=lesson_query, values={"student_id": current_user["id"]})
    
    # Get quiz stats
    quiz_query = """
        SELECT
            COUNT(*) as total_quizzes,
            COUNT(*) FILTER (WHERE is_completed = TRUE) as completed_quizzes,
            AVG(CASE WHEN questions_answered > 0 THEN LEAST(correct_answers::float / questions_answered, 1.0) ELSE 0 END) as avg_score
        FROM quiz_sessions
        WHERE student_id = :student_id
    """
    quiz_stats = await database.fetch_one(query=quiz_query, values={"student_id": current_user["id"]})
    
    return m.ProgressOverview(
        total_lessons=lesson_stats["total_lessons"] or 0,
        completed_lessons=lesson_stats["completed_lessons"] or 0,
        total_quizzes=quiz_stats["total_quizzes"] or 0,
        completed_quizzes=quiz_stats["completed_quizzes"] or 0,
        average_quiz_score=float(quiz_stats["avg_score"] or 0.0),
        total_time_spent_seconds=int(lesson_stats["total_time"] or 0),
        current_streak_days=0  # TODO: Implement streak calculation
    )

@router.get("/subjects-breakdown", response_model=list[m.SubjectProgressBreakdown])
async def get_subjects_breakdown(current_user: dict = Depends(get_current_student)):
    """Get completed vs total lessons for each enrolled subject"""
    
    query = """
        SELECT 
            s.id as subject_id,
            s.name as subject_name,
            COUNT(DISTINCT l.id) as total_lessons,
            COUNT(DISTINCT lp.lesson_id) FILTER (WHERE lp.is_completed = TRUE) as completed_lessons
        FROM enrollments e
        JOIN subjects s ON e.subject_id = s.id
        LEFT JOIN lessons l ON s.id = l.subject_id AND l.is_published = TRUE
        LEFT JOIN lesson_progress lp ON l.id = lp.lesson_id AND lp.student_id = e.student_id
        WHERE e.student_id = :student_id AND s.is_published = TRUE
        GROUP BY s.id, s.name
        ORDER BY s.name
    """
    
    rows = await database.fetch_all(query=query, values={"student_id": current_user["id"]})
    return [m.SubjectProgressBreakdown(**dict(row)) for row in rows]
