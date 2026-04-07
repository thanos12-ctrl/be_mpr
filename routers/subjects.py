"""
Subject Management Router
Handles subject creation, updates, and retrieval
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import UUID4
from typing import List
from datetime import datetime
import uuid

from database import database
from dependencies import require_role
import models as m


router = APIRouter(prefix="/api", tags=["Subjects"])


@router.post("/admin/subjects", response_model=m.SubjectResponse)
async def create_subject(
    subject_data: m.SubjectCreate,
    current_user: dict = Depends(require_role(m.UserRole.ADMIN, m.UserRole.TEACHER))
):
    """Create a new subject (Admin/Teacher only)"""
    
    subject_id = uuid.uuid4()
    query = """
        INSERT INTO subjects (id, subject_id, name, description, icon, is_published, created_by, created_at)
        VALUES (:id, :subject_id, :name, :description, :icon, :is_published, :created_by, :created_at)
        RETURNING id, subject_id, name, description, icon, is_published, created_by, created_at
    """
    
    subject = await database.fetch_one(
        query=query,
        values={
            "id": str(subject_id),
            "subject_id": subject_data.subject_id,
            "name": subject_data.name,
            "description": subject_data.description,
            "icon": subject_data.icon,
            "is_published": True,
            "created_by": current_user["id"],
            "created_at": datetime.utcnow()
        }
    )
    
    return m.SubjectResponse(**dict(subject))


@router.put("/admin/subjects/{subject_id}", response_model=m.SubjectResponse)
async def update_subject(
    subject_id: UUID4,
    subject_data: m.SubjectUpdate,
    current_user: dict = Depends(require_role(m.UserRole.ADMIN, m.UserRole.TEACHER))
):
    """Update an existing subject (Admin/Teacher only)"""
    
    # Verify subject exists and user has permission
    check_query = "SELECT id, created_by FROM subjects WHERE id = :subject_id"
    existing = await database.fetch_one(query=check_query, values={"subject_id": str(subject_id)})
    
    if not existing:
        raise HTTPException(status_code=404, detail="Subject not found")
    
    # Only allow creator or admin to update
    if current_user["role"] != "admin" and existing["created_by"] != current_user["id"]:
        raise HTTPException(status_code=403, detail="Not authorized to update this subject")
    
    # Build update query dynamically based on provided fields
    update_fields = []
    values = {"subject_id": str(subject_id)}
    
    if subject_data.name is not None:
        update_fields.append("name = :name")
        values["name"] = subject_data.name
    
    if subject_data.description is not None:
        update_fields.append("description = :description")
        values["description"] = subject_data.description
    
    if subject_data.icon is not None:
        update_fields.append("icon = :icon")
        values["icon"] = subject_data.icon
    
    if subject_data.is_published is not None:
        update_fields.append("is_published = :is_published")
        values["is_published"] = subject_data.is_published
    
    if not update_fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    
    query = f"""
        UPDATE subjects
        SET {', '.join(update_fields)}
        WHERE id = :subject_id
        RETURNING id, subject_id, name, description, icon, is_published, created_by, created_at
    """
    
    subject = await database.fetch_one(query=query, values=values)
    
    if not subject:
        raise HTTPException(status_code=500, detail="Failed to update subject")
    
    return m.SubjectResponse(**dict(subject))


@router.get("/subjects/published", response_model=List[m.SubjectResponse])
async def get_published_subjects():
    """Get all published subjects (public endpoint)"""
    
    query = """
        SELECT id, subject_id, name, description, icon, is_published, created_by, created_at
        FROM subjects
        WHERE is_published = TRUE
        ORDER BY created_at DESC
    """
    
    subjects = await database.fetch_all(query=query)
    return [m.SubjectResponse(**dict(s)) for s in subjects]
