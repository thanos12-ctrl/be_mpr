"""
Adaptive Learning Router
Handles adaptive learning sessions with RL/LSTM integration
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict
from datetime import datetime
import uuid
import json
import numpy as np

from database import database
from dependencies import get_current_user
from schemas import (
    SessionCreate, SessionResponse, AnswerSubmit, QuestionResponse,
    FeedbackResponse, ProgressResponse, SubjectInfo
)
from ml.rl_helpers import select_next_question, calculate_reward


router = APIRouter(tags=["Adaptive Learning"])

# Global state - will be set by main API
sessions: Dict[str, Dict] = {}
CONTENT_LIBRARIES = {}
SUBJECT_CONFIGS = {}


def set_globals(sess, content_libs, subject_configs):
    """Set global references from main API"""
    global sessions, CONTENT_LIBRARIES, SUBJECT_CONFIGS
    sessions = sess
    CONTENT_LIBRARIES = content_libs
    SUBJECT_CONFIGS = subject_configs


@router.get("/")
async def root():
    """Health check"""
    from ml.rl_helpers import lstm_model, rl_agent
    
    return {
        "status": "running",
        "version": "2.0.0",
        "models_loaded": {
            "lstm": lstm_model is not None,
            "rl_agent": rl_agent is not None,
        },
        "subjects_available": list(CONTENT_LIBRARIES.keys()),
        "active_sessions": len(sessions)
    }


@router.get("/api/subjects", response_model=List[SubjectInfo])
async def list_subjects():
    """Get all available subjects"""
    subjects = []

    for subject_id, config in SUBJECT_CONFIGS.items():
        content_lib = CONTENT_LIBRARIES.get(subject_id, {})

        # Count unique concepts
        if content_lib:
            concepts = set(q.get('concept', 'Unknown') for q in content_lib.values())
            num_concepts = len(concepts)
        else:
            num_concepts = 0

        subjects.append(SubjectInfo(
            subject_id=subject_id,
            subject_name=config['name'],
            description=config['description'],
            icon=config['icon'],
            num_questions=len(content_lib),
            num_concepts=num_concepts,
            available=len(content_lib) > 0
        ))

    return subjects


@router.post("/api/session/start", response_model=SessionResponse)
async def start_session(request: SessionCreate):
    """Start a new learning session"""

    # Validate subject
    if request.subject not in CONTENT_LIBRARIES:
        raise HTTPException(404, f"Subject '{request.subject}' not found or no content available")

    if not CONTENT_LIBRARIES[request.subject]:
        raise HTTPException(400, f"No questions available for {request.subject}")

    session_id = str(uuid.uuid4())
    student_id = request.student_id or f"student_{uuid.uuid4().hex[:8]}"

    n_concepts = SUBJECT_CONFIGS[request.subject]['num_concepts']

    # Initialize session
    sessions[session_id] = {
        'session_id': session_id,
        'subject': request.subject,
        'student_id': student_id,
        'created_at': datetime.now(),
        'current_step': 0,
        'max_steps': request.max_questions,
        'history': [],
        'concept_attempts': np.zeros(n_concepts),
        'concept_correct': np.zeros(n_concepts),
        'consecutive_correct': 0,
        'consecutive_wrong': 0,
        'used_questions': set(),
        'total_reward': 0.0,
        'trajectory': [],
        'n_concepts': n_concepts,
        'warmup_count': 0
    }

    # Warm-up history (used to seed LSTM, not counted in quiz metrics)
    content_lib = CONTENT_LIBRARIES[request.subject]
    sample_questions = list(content_lib.values())[:5]
    sessions[session_id]['warmup_count'] = len(sample_questions)

    for q in sample_questions:
        concept_id = q.get('part', 1) - 1
        diff = q['difficulty']
        is_correct = 1 if np.random.random() < 0.6 else 0

        sessions[session_id]['history'].append([is_correct, diff, 0.5, 0.0, concept_id])
        sessions[session_id]['concept_attempts'][concept_id] += 1
        if is_correct:
            sessions[session_id]['concept_correct'][concept_id] += 1

    return SessionResponse(
        session_id=session_id,
        subject=request.subject,
        student_id=student_id,
        current_step=0,
        max_steps=request.max_questions,
        message="Session started successfully"
    )


@router.post("/api/session/start-lesson", response_model=SessionResponse)
async def start_lesson_session(
    lesson_id: str,
    max_questions: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """
    Start an adaptive quiz session for a specific lesson.
    Fetches questions from the database and uses RL agent for selection.
    """
    
    # Get the quiz for this lesson (including its configured question count)
    quiz_query = "SELECT id, default_num_questions FROM quizzes WHERE lesson_id = :lesson_id LIMIT 1"
    quiz = await database.fetch_one(query=quiz_query, values={"lesson_id": lesson_id})
    
    if not quiz:
        raise HTTPException(status_code=404, detail="No quiz found for this lesson")
    
    # Quiz length set by teacher (how many questions the student sees)
    quiz_num_questions = quiz["default_num_questions"] or max_questions
    
    # Fetch all questions for this quiz
    questions_query = """
        SELECT id, question_text, code_snippet, options, correct_answer, 
               explanation, difficulty, concept, part
        FROM questions
        WHERE quiz_id = :quiz_id
    """
    questions_rows = await database.fetch_all(
        query=questions_query,
        values={"quiz_id": quiz["id"]}
    )
    
    if not questions_rows:
        raise HTTPException(status_code=404, detail="No questions found for this lesson")
    
    # Convert to dictionary format similar to CONTENT_LIBRARIES
    lesson_questions = {}
    concepts = set()
    
    for q in questions_rows:
        q_dict = dict(q)
        
        # Parse options if stored as JSON string
        if isinstance(q_dict["options"], str):
            q_dict["options"] = json.loads(q_dict["options"])
        
        # Format for RL agent
        question_data = {
            'question_id': q_dict['id'],
            'question_text': q_dict['question_text'],
            'code': q_dict['code_snippet'],
            'options': q_dict['options'],
            'correct_answer': q_dict['correct_answer'],
            'explanation': q_dict['explanation'] or "No explanation available",
            'difficulty': q_dict['difficulty'] or 0.5,
            'concept': q_dict['concept'] or "General",
            'part': q_dict['part'] or 1
        }
        
        lesson_questions[q_dict['id']] = question_data
        concepts.add(q_dict['concept'] or "General")
    
    # Create session
    session_id = str(uuid.uuid4())
    student_id = current_user["id"]
    n_concepts = len(concepts)
    
    # Initialize session (similar to regular session but with lesson-specific questions)
    sessions[session_id] = {
        'session_id': session_id,
        'subject': f'lesson_{lesson_id}',  # Mark as lesson-specific
        'lesson_id': lesson_id,
        'quiz_id': quiz["id"],
        'student_id': student_id,
        'created_at': datetime.now(),
        'current_step': 0,
        'max_steps': min(quiz_num_questions, len(lesson_questions)),  # Quiz length (capped to pool size)
        'history': [],
        'concept_attempts': np.zeros(141),
        'concept_correct': np.zeros(141),
        'consecutive_correct': 0,
        'consecutive_wrong': 0,
        'used_questions': set(),
        'total_reward': 0.0,
        'trajectory': [],
        'n_concepts': 141,
        'lesson_questions': lesson_questions,  # Store lesson-specific questions
        'is_lesson_quiz': True,  # Flag to indicate this is a lesson quiz
        'warmup_count': 0
    }
    
    # Warm-up history with sample questions (used to seed LSTM, not counted in quiz metrics)
    sample_questions = list(lesson_questions.values())[:min(3, len(lesson_questions))]
    sessions[session_id]['warmup_count'] = len(sample_questions)
    
    for q in sample_questions:
        concept_id = min(q.get('part', 1) - 1, n_concepts - 1) if n_concepts > 0 else 0
        diff = q['difficulty']
        is_correct = 1 if np.random.random() < 0.6 else 0
        
        sessions[session_id]['history'].append([is_correct, diff, 0.5, 0.0, concept_id])
        sessions[session_id]['concept_attempts'][concept_id] += 1
        if is_correct:
            sessions[session_id]['concept_correct'][concept_id] += 1
    
    return SessionResponse(
        session_id=session_id,
        subject=f'lesson_{lesson_id}',
        student_id=str(student_id),
        current_step=0,
        max_steps=sessions[session_id]['max_steps'],
        message=f"Quiz: {sessions[session_id]['max_steps']} questions selected from pool of {len(lesson_questions)}"
    )


@router.get("/api/session/{session_id}/next-question", response_model=QuestionResponse)
async def get_next_question(session_id: str):
    """Get next question from RL agent"""

    if session_id not in sessions:
        raise HTTPException(404, "Session not found")

    session = sessions[session_id]

    if session['current_step'] >= session['max_steps']:
        raise HTTPException(400, "Session completed")

    # Select question
    question = select_next_question(session)

    # Store for answer validation
    session['current_question'] = question

    return QuestionResponse(
        question_id=str(question['question_id']),
        question_text=question['question_text'],
        code=question['code'],
        options=question['options'],
        part=question['part'],
        concept=question['concept'],
        difficulty=question['difficulty'],
        lstm_confidence=question['lstm_confidence'],
        step=session['current_step'] + 1,
        total_steps=session['max_steps']
    )


@router.post("/api/session/submit-answer", response_model=FeedbackResponse)
async def submit_answer(answer: AnswerSubmit):
    """Submit answer and get feedback"""

    if answer.session_id not in sessions:
        raise HTTPException(404, "Session not found")

    session = sessions[answer.session_id]
    current_q = session.get('current_question')

    if not current_q or str(current_q['question_id']) != answer.question_id:
        raise HTTPException(400, "Question mismatch")

    # Check correctness
    is_correct = answer.user_answer.lower() == current_q['correct_answer'].lower()

    # Update history
    time_normalized = min(answer.time_elapsed_ms / 300000.0, 1.0)
    concept_id = current_q['part'] - 1
    difficulty = float(current_q['difficulty'])

    session['history'].append([
        int(is_correct),
        difficulty,
        time_normalized,
        0.1,
        concept_id
    ])

    # Update tracking
    session['concept_attempts'][concept_id] += 1
    if is_correct:
        session['concept_correct'][concept_id] += 1
        session['consecutive_correct'] += 1
        session['consecutive_wrong'] = 0
    else:
        session['consecutive_wrong'] += 1
        session['consecutive_correct'] = 0

    session['current_step'] += 1
    session['used_questions'].add(answer.question_id)

    # Calculate reward
    reward_breakdown = calculate_reward(
        session, is_correct, difficulty, current_q['lstm_confidence']
    )
    total_reward = reward_breakdown['total']
    session['total_reward'] += total_reward

    # Store trajectory
    session['trajectory'].append({
        'step': session['current_step'],
        'question_id': answer.question_id,
        'difficulty': difficulty,
        'is_correct': is_correct,
        'time_ms': answer.time_elapsed_ms,
        'reward': total_reward
    })

    # Check if continuing
    should_continue = session['current_step'] < session['max_steps']

    # Get next question if continuing
    next_q = None
    if should_continue:
        next_question = select_next_question(session)
        session['current_question'] = next_question

        next_q = QuestionResponse(
            question_id=str(next_question['question_id']),
            question_text=next_question['question_text'],
            code=next_question['code'],
            options=next_question['options'],
            part=next_question['part'],
            concept=next_question['concept'],
            difficulty=next_question['difficulty'],
            lstm_confidence=next_question['lstm_confidence'],
            step=session['current_step'] + 1,
            total_steps=session['max_steps']
        )
    else:
        # Session Completed - Save to Database
        try:
            quiz_id = session.get('quiz_id')
            student_id = session.get('student_id')
            
            # Count correct answers
            correct_count = sum(1 for item in session['history'] if item[0] == 1)
            questions_answered = session['current_step']
            
            if student_id:
                # 1. Insert into quiz_sessions
                # Schema allows: id, student_id, quiz_id, started_at, completed_at, rl_enabled, max_questions, 
                # questions_answered, correct_answers, total_reward, session_state, is_completed
                insert_query = """
                    INSERT INTO quiz_sessions (
                        id, student_id, quiz_id, started_at, completed_at, 
                        is_completed, questions_answered, correct_answers, total_reward
                    )
                    VALUES (
                        :id, :student_id, :quiz_id, :started_at, :completed_at,
                        :is_completed, :questions_answered, :correct_answers, :total_reward
                    )
                    ON CONFLICT (id) DO NOTHING
                """
                
                await database.execute(insert_query, values={
                    "id": session['session_id'],
                    "student_id": student_id,
                    "quiz_id": quiz_id,
                    "started_at": session['created_at'],
                    "completed_at": datetime.now(),
                    "is_completed": True,
                    "questions_answered": questions_answered,
                    "correct_answers": correct_count,
                    "total_reward": session.get('total_reward', 0.0)
                })
                
                # 2. Update Lesson Progress if applicable (Lesson Quiz)
                if session.get('is_lesson_quiz') and session.get('lesson_id'):
                    score = correct_count / questions_answered if questions_answered > 0 else 0.0
                    passing_score = 0.7 # Default passing score
                    
                    if score >= passing_score:
                        lesson_id = session['lesson_id']
                        
                        # Check existing progress
                        check_query = "SELECT id FROM lesson_progress WHERE student_id = :student_id AND lesson_id = :lesson_id"
                        existing_progress = await database.fetch_one(
                            query=check_query,
                            values={"student_id": student_id, "lesson_id": lesson_id}
                        )
                        
                        if existing_progress:
                            # Update existing
                            update_query = """
                                UPDATE lesson_progress
                                SET is_completed = TRUE,
                                    completed_at = CASE WHEN completed_at IS NULL THEN :now ELSE completed_at END
                                WHERE id = :id
                            """
                            await database.execute(update_query, values={
                                "id": existing_progress['id'],
                                "now": datetime.utcnow()
                            })
                        else:
                            # Insert new progress
                            new_lp_id = str(uuid.uuid4())
                            insert_lp_query = """
                                INSERT INTO lesson_progress (
                                    id, student_id, lesson_id, started_at, time_spent_seconds,
                                    last_position, is_completed, completed_at
                                )
                                VALUES (:id, :student_id, :lesson_id, :now, :time, 'end', TRUE, :now)
                            """
                            await database.execute(insert_lp_query, values={
                                "id": new_lp_id,
                                "student_id": student_id,
                                "lesson_id": lesson_id,
                                "now": datetime.utcnow(),
                                "time": int((datetime.now() - session['created_at']).total_seconds())
                            })
                            
        except Exception as e:
            print(f"Error saving session to DB: {e}")

    return FeedbackResponse(
        is_correct=is_correct,
        correct_answer=current_q['correct_answer'],
        explanation=current_q['explanation'],
        reward=total_reward,
        reward_breakdown=reward_breakdown,
        consecutive_correct=session['consecutive_correct'],
        consecutive_wrong=session['consecutive_wrong'],
        should_continue=should_continue,
        next_question=next_q
    )


@router.get("/api/session/{session_id}/progress", response_model=ProgressResponse)
async def get_progress(session_id: str):
    """Get session progress and analytics"""

    if session_id not in sessions:
        raise HTTPException(404, "Session not found")

    session = sessions[session_id]
    history = np.array(session['history'])
    warmup_count = session.get('warmup_count', 0)

    if len(history) <= warmup_count:
        raise HTTPException(400, "No questions answered yet")

    # Exclude warm-up entries from metrics
    real_history = history[warmup_count:]

    # Overall accuracy (real answers only)
    overall_accuracy = float(np.mean(real_history[:, 0]))

    # Difficulty progression (real answers only)
    difficulty_progression = [float(x) for x in real_history[:, 1]]

    # Concept mastery
    concept_mastery_dict = {}
    
    # Get content library - check if this is a lesson-specific quiz
    if session.get('is_lesson_quiz') and 'lesson_questions' in session:
        # Use lesson-specific questions
        content_lib = session['lesson_questions']
    else:
        # Use subject-wide content library
        content_lib = CONTENT_LIBRARIES.get(session['subject'], {})
    
    if content_lib:
        # Get unique concepts from questions
        all_concepts = set(q.get('concept', 'Unknown') for q in content_lib.values())

        for concept in all_concepts:
            # Find concept index
            for i in range(session['n_concepts']):
                if session['concept_attempts'][i] > 0:
                    mastery = session['concept_correct'][i] / session['concept_attempts'][i]
                    concept_mastery_dict[f"{concept}"] = float(mastery)

    # Time spent
    time_spent = int((datetime.now() - session['created_at']).total_seconds())

    return ProgressResponse(
        session_id=session_id,
        subject=session['subject'],
        total_questions_answered=session['current_step'],
        overall_accuracy=overall_accuracy,
        concept_mastery=concept_mastery_dict,
        difficulty_progression=difficulty_progression,
        learning_trajectory=session['trajectory'],
        total_reward=session['total_reward'],
        time_spent_seconds=time_spent
    )


@router.delete("/api/session/{session_id}")
async def end_session(session_id: str):
    """End and clean up session"""
    if session_id in sessions:
        del sessions[session_id]
        return {"message": "Session ended successfully"}
    raise HTTPException(404, "Session not found")
