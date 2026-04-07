"""
Teacher Dashboard Router
Handles teacher-specific operations including student management and groups
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import UUID4
from typing import List
from datetime import datetime
import uuid

from database import database
from dependencies import get_current_teacher
import models as m


router = APIRouter(prefix="/api/teacher", tags=["Teacher"])


@router.get("/students", response_model=List[m.StudentProgressSummary])
async def get_teacher_students(current_user: dict = Depends(get_current_teacher)):
    """Get all students in teacher's groups with progress summary"""
    
    query = """
        SELECT DISTINCT
            u.id as student_id,
            u.full_name as student_name,
            u.email as student_email,
            e.id as enrollment_id,
            s.id as subject_id,
            s.name as subject_name,
            COUNT(DISTINCT lp.id) FILTER (WHERE lp.is_completed = TRUE) as lessons_completed,
            COUNT(DISTINCT qs.id) FILTER (WHERE qs.is_completed = TRUE) as quizzes_completed,
            AVG(CASE WHEN qs.questions_answered > 0 THEN qs.correct_answers::float / qs.questions_answered ELSE 0 END) as average_score,
            COALESCE(SUM(lp.time_spent_seconds), 0) as total_time_seconds,
            MAX(GREATEST(lp.started_at, qs.started_at)) as last_activity,
            e.rl_enabled
        FROM users u
        INNER JOIN enrollments e ON u.id = e.student_id
        INNER JOIN subjects s ON e.subject_id = s.id
        LEFT JOIN lesson_progress lp ON u.id = lp.student_id AND lp.lesson_id IN (
            SELECT l.id FROM lessons l WHERE l.subject_id = s.id
        )
        LEFT JOIN quiz_sessions qs ON u.id = qs.student_id AND qs.quiz_id IN (
            SELECT q.id FROM quizzes q 
            JOIN lessons l ON q.lesson_id = l.id 
            WHERE l.subject_id = s.id
        )
        WHERE s.created_by = :teacher_id
        GROUP BY u.id, u.full_name, u.email, e.id, s.id, s.name, e.rl_enabled
        ORDER BY last_activity DESC NULLS LAST
    """
    
    students = await database.fetch_all(query=query, values={"teacher_id": current_user["id"]})
    print(students, current_user)
    return [
        m.StudentProgressSummary(
            student_id=s["student_id"],
            student_name=s["student_name"],
            student_email=s["student_email"],
            enrollment_id=s["enrollment_id"],
            subject_id=s["subject_id"],
            subject_name=s["subject_name"],
            lessons_completed=s["lessons_completed"] or 0,
            quizzes_completed=s["quizzes_completed"] or 0,
            average_score=float(s["average_score"] or 0.0),
            total_time_seconds=int(s["total_time_seconds"] or 0),
            last_activity=s["last_activity"],
            rl_enabled=s["rl_enabled"] if s["rl_enabled"] is not None else True
        )
        for s in students
    ]


@router.post("/groups", response_model=m.GroupResponse)
async def create_student_group(
    group_data: m.GroupCreate,
    current_user: dict = Depends(get_current_teacher)
):
    """Create a new student group"""
    
    group_id = uuid.uuid4()
    query = """
        INSERT INTO teacher_student_groups (id, teacher_id, group_name, created_at)
        VALUES (:id, :teacher_id, :group_name, :created_at)
        RETURNING id, teacher_id, group_name, created_at
    """
    
    group = await database.fetch_one(
        query=query,
        values={
            "id": str(group_id),
            "teacher_id": current_user["id"],
            "group_name": group_data.group_name,
            "created_at": datetime.utcnow()
        }
    )
    
    return m.GroupResponse(**dict(group), member_count=0)


@router.post("/groups/{group_id}/students")
async def add_student_to_group(
    group_id: UUID4,
    student_data: m.GroupAddStudent,
    current_user: dict = Depends(get_current_teacher)
):
    """Add a student to a group"""
    
    # Verify group belongs to teacher
    verify_query = "SELECT id FROM teacher_student_groups WHERE id = :group_id AND teacher_id = :teacher_id"
    group = await database.fetch_one(
        query=verify_query,
        values={"group_id": str(group_id), "teacher_id": current_user["id"]}
    )
    
    if not group:
        raise HTTPException(status_code=404, detail="Group not found or access denied")
    
    # Add student
    member_id = uuid.uuid4()
    query = """
        INSERT INTO group_members (id, group_id, student_id, added_at)
        VALUES (:id, :group_id, :student_id, :added_at)
        ON CONFLICT (group_id, student_id) DO NOTHING
        RETURNING id
    """
    
    result = await database.fetch_one(
        query=query,
        values={
            "id": str(member_id),
            "group_id": str(group_id),
            "student_id": str(student_data.student_id),
            "added_at": datetime.utcnow()
        }
    )
    
    if result:
        return {"message": "Student added to group successfully"}
    else:
        return {"message": "Student already in group"}


@router.get("/groups", response_model=List[m.GroupResponse])
async def get_teacher_groups(
    current_user: dict = Depends(get_current_teacher)
):
    """Get all groups for the current teacher"""
    
    query = """
        SELECT 
            tsg.id,
            tsg.teacher_id,
            tsg.group_name,
            tsg.created_at,
            COUNT(gm.id) as member_count
        FROM teacher_student_groups tsg
        LEFT JOIN group_members gm ON tsg.id = gm.group_id
        WHERE tsg.teacher_id = :teacher_id
        GROUP BY tsg.id, tsg.teacher_id, tsg.group_name, tsg.created_at
        ORDER BY tsg.created_at DESC
    """
    
    groups = await database.fetch_all(query=query, values={"teacher_id": current_user["id"]})
    
    return [
        m.GroupResponse(
            id=g["id"],
            teacher_id=g["teacher_id"],
            group_name=g["group_name"],
            created_at=g["created_at"],
            member_count=g["member_count"] or 0
        )
        for g in groups
    ]


@router.get("/groups/{group_id}/members")
async def get_group_members(
    group_id: UUID4,
    current_user: dict = Depends(get_current_teacher)
):
    """Get all members of a specific group"""
    
    # Verify group belongs to teacher
    verify_query = "SELECT id FROM teacher_student_groups WHERE id = :group_id AND teacher_id = :teacher_id"
    group = await database.fetch_one(
        query=verify_query,
        values={"group_id": str(group_id), "teacher_id": current_user["id"]}
    )
    
    if not group:
        raise HTTPException(status_code=404, detail="Group not found or access denied")
    
    # Get members
    query = """
        SELECT 
            u.id as student_id,
            u.full_name as student_name,
            u.email as student_email,
            gm.added_at
        FROM group_members gm
        JOIN users u ON gm.student_id = u.id
        WHERE gm.group_id = :group_id
        ORDER BY gm.added_at DESC
    """
    
    members = await database.fetch_all(query=query, values={"group_id": str(group_id)})
    
    return [
        {
            "student_id": m["student_id"],
            "student_name": m["student_name"],
            "student_email": m["student_email"],
            "added_at": m["added_at"]
        }
        for m in members
    ]


@router.delete("/groups/{group_id}/members/{student_id}")
async def remove_student_from_group(
    group_id: UUID4,
    student_id: UUID4,
    current_user: dict = Depends(get_current_teacher)
):
    """Remove a student from a group"""
    
    # Verify group belongs to teacher
    verify_query = "SELECT id FROM teacher_student_groups WHERE id = :group_id AND teacher_id = :teacher_id"
    group = await database.fetch_one(
        query=verify_query,
        values={"group_id": str(group_id), "teacher_id": current_user["id"]}
    )
    
    if not group:
        raise HTTPException(status_code=404, detail="Group not found or access denied")
    
    # Remove student
    query = "DELETE FROM group_members WHERE group_id = :group_id AND student_id = :student_id"
    await database.execute(
        query=query,
        values={"group_id": str(group_id), "student_id": str(student_id)}
    )
    
    return {"message": "Student removed from group successfully"}


@router.delete("/groups/{group_id}")
async def delete_group(
    group_id: UUID4,
    current_user: dict = Depends(get_current_teacher)
):
    """Delete a group and all its members"""
    
    # Verify group belongs to teacher
    verify_query = "SELECT id FROM teacher_student_groups WHERE id = :group_id AND teacher_id = :teacher_id"
    group = await database.fetch_one(
        query=verify_query,
        values={"group_id": str(group_id), "teacher_id": current_user["id"]}
    )
    
    if not group:
        raise HTTPException(status_code=404, detail="Group not found or access denied")
    
    # Delete group (members will be deleted via CASCADE)
    query = "DELETE FROM teacher_student_groups WHERE id = :group_id"
    await database.execute(query=query, values={"group_id": str(group_id)})
    
    return {"message": "Group deleted successfully"}
