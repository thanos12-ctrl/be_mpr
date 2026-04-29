"""
Adaptive Learning Router (Domain-Agnostic Edition)
Handles adaptive learning sessions loading memory state from PostgreSQL Agent Memory Table
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
        "version": "2.1.0-Agnostic",
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
        num_concepts = len(set(q.get('concept', 'Unknown') for q in content_lib.values())) if content_lib else 0

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


async def get_subject_uuid(subject_string: str):
    """Utility to map literal subject string to the UUID in DB"""
    query = "SELECT id FROM subjects WHERE subject_id = :sid"
    result = await database.fetch_one(query, {"sid": subject_string})
    if result:
        return result['id']
    return None

async def load_agent_memory(student_id: uuid.UUID, subject_uuid: uuid.UUID):
    query = "SELECT * FROM agent_memory WHERE student_id = :st_id AND subject_id = :su_id"
    mem = await database.fetch_one(query, {"st_id": student_id, "su_id": subject_uuid})
    
    if mem:
        return {
            'history': json.loads(mem['interaction_queue']) if mem['interaction_queue'] else [],
            'consecutive_correct': mem['consecutive_correct'],
            'consecutive_wrong': mem['consecutive_wrong'],
            'concept_attempts': mem['concept_attempts'],
            'concept_correct': mem['concept_correct']
        }
    return {
        'history': [],
        'consecutive_correct': 0,
        'consecutive_wrong': 0,
        'concept_attempts': 0,
        'concept_correct': 0
    }

@router.post("/api/session/start", response_model=SessionResponse)
async def start_session(request: SessionCreate):
    """Start a new learning session"""
    
    if request.subject not in CONTENT_LIBRARIES or not CONTENT_LIBRARIES[request.subject]:
        raise HTTPException(404, f"Subject '{request.subject}' not found or no content available")

    session_id = str(uuid.uuid4())
    student_id_str = request.student_id or f"{uuid.uuid4()}"
    student_uuid = uuid.UUID(student_id_str)
    
    subject_uuid = await get_subject_uuid(request.subject)

    # 1. LOAD State from `agent_memory`
    if subject_uuid:
        memory = await load_agent_memory(student_uuid, subject_uuid)
    else:
        memory = {'history': [], 'consecutive_correct': 0, 'consecutive_wrong': 0, 'concept_attempts': 0, 'concept_correct': 0}

    # Initialize session
    sessions[session_id] = {
        'session_id': session_id,
        'subject': request.subject,
        'subject_uuid': str(subject_uuid) if subject_uuid else None,
        'student_id': student_id_str,
        'created_at': datetime.now(),
        'current_step': 0,
        'max_steps': request.max_questions,
        'history': memory['history'],
        
        # Domain Agnostic Module Tracking
        'concept_attempts': memory['concept_attempts'],
        'concept_correct': memory['concept_correct'],
        
        'consecutive_correct': memory['consecutive_correct'],
        'consecutive_wrong': memory['consecutive_wrong'],
        'used_questions': set(),
        'total_reward': 0.0,
        'trajectory': [],
        'warmup_count': 0
    }

    return SessionResponse(
        session_id=session_id,
        subject=request.subject,
        student_id=student_id_str,
        current_step=0,
        max_steps=request.max_questions,
        message="Session started successfully. Memory loaded."
    )


@router.post("/api/session/start-lesson", response_model=SessionResponse)
async def start_lesson_session(
    lesson_id: str,
    max_questions: int = 10,
    current_user: dict = Depends(get_current_user)
):
    """Start an adaptive quiz session for a lesson."""
    
    quiz_query = "SELECT id, default_num_questions FROM quizzes WHERE lesson_id = :lesson_id LIMIT 1"
    quiz = await database.fetch_one(query=quiz_query, values={"lesson_id": lesson_id})
    if not quiz:
        raise HTTPException(status_code=404, detail="No quiz found for this lesson")
        
    lesson_query = "SELECT subject_id FROM lessons WHERE id = :lesson_id"
    lesson = await database.fetch_one(lesson_query, {"lesson_id": lesson_id})
    subject_uuid = lesson['subject_id'] if lesson else None
    
    quiz_num_questions = quiz["default_num_questions"] or max_questions
    
    questions_query = """
        SELECT id, question_text, code_snippet, options, correct_answer, 
               explanation, difficulty, concept, part
        FROM questions
        WHERE quiz_id = :quiz_id
    """
    questions_rows = await database.fetch_all(query=questions_query, values={"quiz_id": quiz["id"]})
    if not questions_rows:
        raise HTTPException(status_code=404, detail="No questions found for this lesson")
    
    lesson_questions = {}
    for q in questions_rows:
        q_dict = dict(q)
        if isinstance(q_dict["options"], str):
            q_dict["options"] = json.loads(q_dict["options"])
            
        lesson_questions[q_dict['id']] = {
            'question_id': str(q_dict['id']),
            'question_text': q_dict['question_text'],
            'code': q_dict['code_snippet'],
            'options': q_dict['options'],
            'correct_answer': q_dict['correct_answer'],
            'explanation': q_dict['explanation'] or "No explanation available",
            'difficulty': q_dict['difficulty'] or 0.5,
            'concept': q_dict['concept'] or "General",
            'part': q_dict['part'] or 1
        }
    
    session_id = str(uuid.uuid4())
    student_uuid = current_user["id"]
    
    # 1. LOAD State from `agent_memory`
    memory = await load_agent_memory(student_uuid, subject_uuid) if subject_uuid else \
             {'history': [], 'consecutive_correct': 0, 'consecutive_wrong': 0, 'concept_attempts': 0, 'concept_correct': 0}
             
    sessions[session_id] = {
        'session_id': session_id,
        'subject': f'lesson_{lesson_id}',
        'subject_uuid': str(subject_uuid) if subject_uuid else None,
        'lesson_id': lesson_id,
        'quiz_id': quiz["id"],
        'student_id': str(student_uuid),
        'created_at': datetime.now(),
        'current_step': 0,
        'max_steps': min(quiz_num_questions, len(lesson_questions)),
        
        # Restored tracking capability
        'history': memory['history'],
        'concept_attempts': memory['concept_attempts'],
        'concept_correct': memory['concept_correct'],
        'consecutive_correct': memory['consecutive_correct'],
        'consecutive_wrong': memory['consecutive_wrong'],
        
        'used_questions': set(),
        'total_reward': 0.0,
        'trajectory': [],
        'lesson_questions': lesson_questions,
        'is_lesson_quiz': True,
        'warmup_count': 0
    }
    
    return SessionResponse(
        session_id=session_id,
        subject=f'lesson_{lesson_id}',
        student_id=str(student_uuid),
        current_step=0,
        max_steps=sessions[session_id]['max_steps'],
        message=f"Quiz: Memory restored. {sessions[session_id]['max_steps']} questions selected."
    )


@router.get("/api/session/{session_id}/next-question", response_model=QuestionResponse)
async def get_next_question(session_id: str):
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")
    session = sessions[session_id]
    if session['current_step'] >= session['max_steps']:
        raise HTTPException(400, "Session completed")

    question = select_next_question(session)
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
    if answer.session_id not in sessions:
        raise HTTPException(404, "Session not found")

    session = sessions[answer.session_id]
    current_q = session.get('current_question')

    if not current_q or str(current_q['question_id']) != answer.question_id:
        raise HTTPException(400, "Question mismatch")

    is_correct = answer.user_answer.lower() == current_q['correct_answer'].lower()
    time_normalized = min(answer.time_elapsed_ms / 300000.0, 1.0)
    difficulty = float(current_q['difficulty'])
    moved_module = 1 if session.get('agent_moved_concept') else 0

    # 1. Update Domain-Agnostic History
    session['history'].append([
        int(is_correct),
        difficulty,
        time_normalized,
        0.1,  # lag_time_norm
        moved_module
    ])

    # 2. Update tracking
    session['concept_attempts'] += 1
    if is_correct:
        session['concept_correct'] += 1
        session['consecutive_correct'] += 1
        session['consecutive_wrong'] = 0
    else:
        session['consecutive_wrong'] += 1
        session['consecutive_correct'] = 0

    session['current_step'] += 1
    session['used_questions'].add(answer.question_id)

    reward_breakdown = calculate_reward(session, is_correct, difficulty, current_q['lstm_confidence'])
    total_reward = reward_breakdown['total']
    session['total_reward'] += total_reward

    session['trajectory'].append({
        'step': session['current_step'],
        'question_id': answer.question_id,
        'difficulty': difficulty,
        'is_correct': is_correct,
        'time_ms': answer.time_elapsed_ms,
        'reward': total_reward
    })

    # ========================================================
    # DB SYNC: Dump memory state back to Agent Memory Table
    # ========================================================
    student_id = session.get('student_id')
    subject_uuid = session.get('subject_uuid')
    
    if student_id and subject_uuid:
        # Save last 20 history
        trimmed_history = session['history'][-20:]
        
        query = """
            INSERT INTO agent_memory (
                student_id, subject_id, interaction_queue, consecutive_correct, 
                consecutive_wrong, concept_attempts, concept_correct, last_updated
            )
            VALUES (
                :st_id, :su_id, :queue, :cc, :cw, :ca, :cco, NOW()
            )
            ON CONFLICT (student_id, subject_id) DO UPDATE SET
                interaction_queue = EXCLUDED.interaction_queue,
                consecutive_correct = EXCLUDED.consecutive_correct,
                consecutive_wrong = EXCLUDED.consecutive_wrong,
                concept_attempts = EXCLUDED.concept_attempts,
                concept_correct = EXCLUDED.concept_correct,
                last_updated = NOW()
        """
        try:
            await database.execute(query, values={
                "st_id": student_id,
                "su_id": subject_uuid,
                "queue": json.dumps(trimmed_history),
                "cc": session['consecutive_correct'],
                "cw": session['consecutive_wrong'],
                "ca": session['concept_attempts'],
                "cco": session['concept_correct']
            })
        except Exception as e:
            print(f"Failed to save agent_memory: {e}")

    should_continue = session['current_step'] < session['max_steps']
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
        # Wrap up Quiz & update Lesson Progress
        try:
            quiz_id = session.get('quiz_id')
            student_id = session.get('student_id')
            warmup_count = session.get('warmup_count', 0)
            real_history = session['history'][warmup_count:]
            correct_count = sum(1 for item in real_history if item[0] == 1)
            questions_answered = session['current_step']
            
            if student_id:
                await database.execute("""
                    INSERT INTO quiz_sessions (
                        id, student_id, quiz_id, started_at, completed_at, 
                        is_completed, questions_answered, correct_answers, total_reward
                    )
                    VALUES (:id, :student_id, :quiz_id, :started_at, :completed_at, :is_completed, :qa, :ca, :tr)
                    ON CONFLICT (id) DO NOTHING
                """, values={
                    "id": session['session_id'],
                    "student_id": student_id,
                    "quiz_id": quiz_id,
                    "started_at": session['created_at'],
                    "completed_at": datetime.now(),
                    "is_completed": True,
                    "qa": questions_answered,
                    "ca": correct_count,
                    "tr": session.get('total_reward', 0.0)
                })
                
                # Always mark lesson as complete; keep best score across retakes
                if session.get('is_lesson_quiz') and session.get('lesson_id'):
                    score = correct_count / questions_answered if questions_answered > 0 else 0.0
                    lesson_id = session['lesson_id']
                    time_spent = int((datetime.now() - session['created_at']).total_seconds())

                    chk = await database.fetch_one(
                        "SELECT id, is_completed FROM lesson_progress WHERE student_id = :s AND lesson_id = :l",
                        {"s": student_id, "l": lesson_id}
                    )
                    if chk:
                        # Update: always mark complete; do NOT downgrade if already completed
                        await database.execute(
                            "UPDATE lesson_progress SET is_completed = TRUE, completed_at = NOW() WHERE id = :id",
                            {"id": chk['id']}
                        )
                    else:
                        await database.execute("""
                            INSERT INTO lesson_progress (id, student_id, lesson_id, started_at, time_spent_seconds, last_position, is_completed, completed_at)
                            VALUES (:id, :s, :l, NOW(), :time, 'end', TRUE, NOW())
                        """, {"id": str(uuid.uuid4()), "s": student_id, "l": lesson_id, "time": time_spent})
        except Exception as e:
            print(f"Error finalizing DB Session: {e}")

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
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")

    session = sessions[session_id]
    history = np.array(session['history'])
    
    if len(history) == 0:
        raise HTTPException(400, "No questions answered yet")

    overall_accuracy = float(np.mean(history[:, 0]))

    # Use trajectory for difficulty progression — only current session questions
    trajectory = session.get('trajectory', [])
    difficulty_progression = [t['difficulty'] for t in trajectory]

    # Natively show Current Module Mastery!
    topic_attempts = session.get('concept_attempts', 0)
    topic_correct = session.get('concept_correct', 0)
    mastery_ratio = (topic_correct / topic_attempts) if topic_attempts > 0 else 0.0

    return ProgressResponse(
        session_id=session_id,
        subject=session['subject'],
        total_questions_answered=session['current_step'],
        overall_accuracy=overall_accuracy,
        concept_mastery={"Current Lesson Module": float(mastery_ratio)},
        difficulty_progression=difficulty_progression,
        learning_trajectory=session['trajectory'],
        total_reward=session['total_reward'],
        time_spent_seconds=int((datetime.now() - session['created_at']).total_seconds())
    )


@router.delete("/api/session/{session_id}")
async def end_session(session_id: str):
    if session_id in sessions:
        del sessions[session_id]
        return {"message": "Session ended successfully"}
    raise HTTPException(404, "Session not found")
