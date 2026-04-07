"""
Pydantic schemas for adaptive learning
"""

from pydantic import BaseModel
from typing import Dict, List, Optional, Any


class SessionCreate(BaseModel):
    subject: str
    student_id: Optional[str] = None
    max_questions: int = 20


class SessionResponse(BaseModel):
    session_id: str
    subject: str
    student_id: str
    current_step: int
    max_steps: int
    message: str


class AnswerSubmit(BaseModel):
    session_id: str
    question_id: str
    user_answer: str
    time_elapsed_ms: int


class QuestionResponse(BaseModel):
    question_id: str
    question_text: str
    code: Optional[str]
    options: Dict[str, str]
    part: int
    concept: str
    difficulty: float
    lstm_confidence: float
    step: int
    total_steps: int


class FeedbackResponse(BaseModel):
    is_correct: bool
    correct_answer: str
    explanation: str
    reward: float
    reward_breakdown: Dict[str, float]
    consecutive_correct: int
    consecutive_wrong: int
    should_continue: bool
    next_question: Optional[QuestionResponse]


class ProgressResponse(BaseModel):
    session_id: str
    subject: str
    total_questions_answered: int
    overall_accuracy: float
    concept_mastery: Dict[str, float]
    difficulty_progression: List[float]
    learning_trajectory: List[Dict[str, Any]]
    total_reward: float
    time_spent_seconds: int


class SubjectInfo(BaseModel):
    subject_id: str
    subject_name: str
    description: str
    icon: str
    num_questions: int
    num_concepts: int
    available: bool
