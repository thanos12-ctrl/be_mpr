"""
Enrollment Management Router
Handles student enrollment in subjects
"""

from fastapi import APIRouter, HTTPException, Depends, status
from pydantic import UUID4
from typing import List
from datetime import datetime
import uuid

from database import database
from dependencies import get_current_student, get_current_teacher
import models as m


router = APIRouter(prefix="/api/enrollments", tags=["Enrollments"])


@router.post("", response_model=m.EnrollmentResponse, status_code=status.HTTP_201_CREATED)
async def enroll_in_subject(
    enrollment_data: m.EnrollmentCreate,
    current_user: dict = Depends(get_current_student)
):
    """Enroll student in a subject"""
    
    # Check if already enrolled
    check_query = "SELECT id FROM enrollments WHERE student_id = :student_id AND subject_id = :subject_id"
    existing = await database.fetch_one(
        query=check_query,
        values={"student_id": current_user["id"], "subject_id": str(enrollment_data.subject_id)}
    )
    
    if existing:
        raise HTTPException(status_code=400, detail="Already enrolled in this subject")
    
    # Create enrollment
    enrollment_id = uuid.uuid4()
    query = """
        INSERT INTO enrollments (id, student_id, subject_id, enrolled_at, rl_enabled)
        VALUES (:id, :student_id, :subject_id, :enrolled_at, :rl_enabled)
        RETURNING id, student_id, subject_id, enrolled_at, completed_at, rl_enabled
    """
    
    enrollment = await database.fetch_one(
        query=query,
        values={
            "id": str(enrollment_id),
            "student_id": current_user["id"],
            "subject_id": str(enrollment_data.subject_id),
            "enrolled_at": datetime.utcnow(),
            "rl_enabled": enrollment_data.rl_enabled
        }
    )
    
    return m.EnrollmentResponse(**dict(enrollment))


@router.get("/my-courses", response_model=List[m.EnrollmentResponse])
async def get_my_enrollments(current_user: dict = Depends(get_current_student)):
    """Get student's enrolled courses"""
    
    query = """
        SELECT id, student_id, subject_id, enrolled_at, completed_at, rl_enabled
        FROM enrollments
        WHERE student_id = :student_id
        ORDER BY enrolled_at DESC
    """
    
    enrollments = await database.fetch_all(query=query, values={"student_id": current_user["id"]})
    return [m.EnrollmentResponse(**dict(e)) for e in enrollments]


@router.patch("/{enrollment_id}/toggle-rl", response_model=m.EnrollmentResponse)
async def toggle_rl_for_enrollment(
    enrollment_id: UUID4,
    toggle_data: m.EnrollmentToggleRL,
    current_user: dict = Depends(get_current_teacher)
):
    """Toggle RL agent for a student's enrollment (Teacher only)"""
    
    # Verify enrollment exists and user has permission
    check_query = """
        SELECT e.id, s.created_by
        FROM enrollments e
        JOIN subjects s ON e.subject_id = s.id
        WHERE e.id = :enrollment_id
    """
    existing = await database.fetch_one(query=check_query, values={"enrollment_id": str(enrollment_id)})
    
    if not existing:
        raise HTTPException(status_code=404, detail="Enrollment not found")
        
    if current_user["role"] != "admin" and existing["created_by"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to modify enrollments for this subject")

    query = """
        UPDATE enrollments
        SET rl_enabled = :rl_enabled
        WHERE id = :enrollment_id
        RETURNING id, student_id, subject_id, enrolled_at, completed_at, rl_enabled
    """
    
    enrollment = await database.fetch_one(
        query=query,
        values={"enrollment_id": str(enrollment_id), "rl_enabled": toggle_data.rl_enabled}
    )
    
    if not enrollment:
        raise HTTPException(status_code=404, detail="Enrollment not found")
    
    return m.EnrollmentResponse(**dict(enrollment))
