"""
Pydantic models for request/response validation
"""
from pydantic import BaseModel, EmailStr, Field, UUID4
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


# ==========================================
# ENUMS
# ==========================================

class UserRole(str, Enum):
    STUDENT = "student"
    TEACHER = "teacher"
    ADMIN = "admin"


# ==========================================
# AUTHENTICATION
# ==========================================

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    full_name: str
    role: UserRole = UserRole.STUDENT


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: UUID4
    email: str
    full_name: str
    role: UserRole
    created_at: datetime
    last_login: Optional[datetime]
    is_active: bool


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class TokenRefresh(BaseModel):
    refresh_token: str


# ==========================================
# LESSONS
# ==========================================

class LessonCreate(BaseModel):
    subject_id: UUID4
    lesson_number: int
    title: str
    slug: str
    introduction: str
    code_example: Optional[str] = None
    key_takeaways: List[str]
    estimated_time_minutes: int = 10
    difficulty_level: int = Field(1, ge=1, le=5)
    prerequisites: List[UUID4] = []


class LessonUpdate(BaseModel):
    title: Optional[str] = None
    introduction: Optional[str] = None
    code_example: Optional[str] = None
    key_takeaways: Optional[List[str]] = None
    estimated_time_minutes: Optional[int] = None
    difficulty_level: Optional[int] = None
    prerequisites: Optional[List[UUID4]] = None


class LessonResponse(BaseModel):
    id: UUID4
    subject_id: UUID4
    lesson_number: int
    title: str
    slug: str
    introduction: str
    code_example: Optional[str]
    key_takeaways: List[str]
    estimated_time_minutes: int
    difficulty_level: int
    prerequisites: List[UUID4]
    is_published: bool
    created_at: datetime
    updated_at: datetime


# ==========================================
# QUIZZES & QUESTIONS
# ==========================================

class QuizCreate(BaseModel):
    lesson_id: UUID4
    title: str
    description: Optional[str] = None
    allow_rl_adaptation: bool = True
    default_num_questions: int = 10
    passing_score: float = Field(0.70, ge=0.0, le=1.0)


class QuizUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    default_num_questions: Optional[int] = None
    passing_score: Optional[float] = Field(None, ge=0.0, le=1.0)
    allow_rl_adaptation: Optional[bool] = None



class QuizResponse(BaseModel):
    id: UUID4
    lesson_id: UUID4
    title: str
    description: Optional[str]
    allow_rl_adaptation: bool
    default_num_questions: int
    passing_score: float
    created_at: datetime


class QuestionCreate(BaseModel):
    quiz_id: UUID4
    ednet_question_id: Optional[str] = None
    question_text: str
    code_snippet: Optional[str] = None
    options: Dict[str, str]
    correct_answer: str
    explanation: Optional[str] = None
    difficulty: float = Field(..., ge=0.0, le=1.0)
    concept: str
    part: int


class QuestionUpdate(BaseModel):
    question_text: Optional[str] = None
    code_snippet: Optional[str] = None
    options: Optional[Dict[str, str]] = None
    correct_answer: Optional[str] = None
    explanation: Optional[str] = None
    difficulty: Optional[float] = None
    concept: Optional[str] = None


class QuestionResponse(BaseModel):
    id: UUID4
    quiz_id: UUID4
    ednet_question_id: Optional[str]
    question_text: str
    code_snippet: Optional[str]
    options: Dict[str, str]
    correct_answer: str
    explanation: Optional[str]
    difficulty: float
    concept: str
    part: int
    created_at: datetime


# ==========================================
# ENROLLMENTS
# ==========================================

class EnrollmentCreate(BaseModel):
    subject_id: UUID4
    rl_enabled: bool = True


class EnrollmentResponse(BaseModel):
    id: UUID4
    student_id: UUID4
    subject_id: UUID4
    enrolled_at: datetime
    completed_at: Optional[datetime]
    rl_enabled: bool


class EnrollmentToggleRL(BaseModel):
    rl_enabled: bool


# ==========================================
# PROGRESS
# ==========================================

class LessonProgressUpdate(BaseModel):
    lesson_id: UUID4
    time_spent_seconds: int
    last_position: Optional[str] = None
    is_completed: bool = False


class LessonProgressResponse(BaseModel):
    id: UUID4
    student_id: UUID4
    lesson_id: UUID4
    started_at: datetime
    completed_at: Optional[datetime]
    time_spent_seconds: int
    last_position: Optional[str]
    is_completed: bool


class ProgressOverview(BaseModel):
    total_lessons: int
    completed_lessons: int
    total_quizzes: int
    completed_quizzes: int
    average_quiz_score: float
    total_time_spent_seconds: int
    current_streak_days: int

class SubjectProgressBreakdown(BaseModel):
    subject_id: UUID4
    subject_name: str
    completed_lessons: int
    total_lessons: int


class LessonProgressSummary(BaseModel):
    lesson_id: UUID4
    is_completed: bool
    completed_at: Optional[datetime]


# ==========================================
# TEACHER DASHBOARD
# ==========================================

class StudentProgressSummary(BaseModel):
    student_id: UUID4
    student_name: str
    student_email: str
    enrollment_id: UUID4
    subject_id: UUID4
    subject_name: str
    lessons_completed: int
    quizzes_completed: int
    average_score: float
    total_time_seconds: int
    last_activity: Optional[datetime]
    rl_enabled: bool


class ConceptMastery(BaseModel):
    concept: str
    attempts: int
    correct: int
    mastery_percentage: float


class StudentDetailedProgress(BaseModel):
    student: UserResponse
    enrollment: EnrollmentResponse
    lessons_progress: List[LessonProgressResponse]
    quiz_sessions: List[Dict[str, Any]]
    concept_mastery: List[ConceptMastery]
    daily_stats: List[Dict[str, Any]]


class ClassOverview(BaseModel):
    total_students: int
    active_students: int
    average_completion_rate: float
    average_quiz_score: float
    total_time_spent_seconds: int
    students_with_rl_enabled: int
    students_with_rl_disabled: int


# ==========================================
# SUBJECTS
# ==========================================

class SubjectCreate(BaseModel):
    subject_id: str
    name: str
    description: str
    icon: str = "📚"


class SubjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None
    is_published: Optional[bool] = None


class SubjectResponse(BaseModel):
    id: UUID4
    subject_id: str
    name: str
    description: str
    icon: str
    is_published: bool
    created_by: Optional[UUID4]
    created_at: datetime


# ==========================================
# GROUPS
# ==========================================

class GroupCreate(BaseModel):
    group_name: str


class GroupResponse(BaseModel):
    id: UUID4
    teacher_id: UUID4
    group_name: str
    created_at: datetime
    member_count: int


class GroupAddStudent(BaseModel):
    student_id: UUID4
