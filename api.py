"""
Production API for Multi-Subject Adaptive Learning Platform
Simplified main file that orchestrates all routers
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict
import numpy as np
import torch
from stable_baselines3 import PPO
import json
import os
import uvicorn

# Configuration and database
from config import settings
from database import database, connect_db, disconnect_db

# ML components
from ml.lstm_model import StudentSimulator
import ml.rl_helpers as rl_helpers

# Routers
from routers import auth, subjects, lessons, enrollments, progress, teacher, quiz, adaptive


# ==========================================
# FASTAPI APP
# ==========================================

app = FastAPI(
    title="Adaptive Learning API",
    description="Multi-subject adaptive learning with RL and LSTM",
    version="2.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==========================================
# GLOBAL STATE
# ==========================================

device = torch.device("cpu")
lstm_model = None
rl_agent = None
sessions: Dict[str, Dict] = {}

# Content libraries - loaded at startup
CONTENT_LIBRARIES = {}
SUBJECT_CONFIGS = {}


# ==========================================
# STARTUP: LOAD MODELS & CONTENT
# ==========================================

@app.on_event("startup")
async def startup_event():
    """Load all models and question content"""
    global lstm_model, rl_agent, CONTENT_LIBRARIES, SUBJECT_CONFIGS

    print("\n" + "=" * 60)
    print("  ADAPTIVE LEARNING API - STARTING UP")
    print("=" * 60 + "\n")
    
    # 0. Connect to database
    await connect_db()

    # 1. Load LSTM
    try:
        lstm_model = StudentSimulator(input_dim=5, hidden_dim=128, num_layers=2)
        lstm_model.load_state_dict(
            torch.load("general_agent/general_student_simulator.pth", map_location=device, weights_only=True)
        )
        lstm_model.eval()
        print("[SUCCESS] LSTM Student Simulator loaded")
    except Exception as e:
        print(f"⚠️  LSTM not loaded: {e}")
        lstm_model = None

    # 2. Load RL Agent
    try:
        rl_agent = PPO.load("general_agent/ppo_general_teacher", device=device)
        print("[SUCCESS] RL Teaching Agent loaded")
    except Exception as e:
        print(f"⚠️  RL Agent not loaded: {e}")
        rl_agent = None

    # 3. Load Question Content Libraries
    content_files = {
        'english_ednet': 'question_content_english_ednet.json',
        'java_programming': 'question_content_java_programming.json',
        'python_programming': 'question_content_python_programming.json',
        'mathematics': 'question_content_mathematics.json',
    }

    for subject_id, filename in content_files.items():
        if os.path.exists(filename):
            try:
                with open(filename, 'r') as f:
                    questions = json.load(f)

                # Create lookup dictionary
                CONTENT_LIBRARIES[subject_id] = {
                    q['question_id']: q for q in questions
                }

                # Count concepts
                concepts = set(q.get('concept', 'Unknown') for q in questions)

                print(f"[SUCCESS] Loaded {len(questions)} questions for {subject_id} ({len(concepts)} concepts)")

            except Exception as e:
                print(f"⚠️  Error loading {subject_id}: {e}")
        else:
            print(f"⚠️  {filename} not found - {subject_id} unavailable")

    # 4. Define Subject Configurations
    SUBJECT_CONFIGS = {
        'english_ednet': {
            'name': 'English Language (TOEIC)',
            'description': 'Master English grammar and reading comprehension',
            'icon': '🇬🇧',
            'num_concepts': 7,  # 7 parts
        },
        'java_programming': {
            'name': 'Java Programming',
            'description': 'Learn Java from basics to advanced OOP',
            'icon': '☕',
            'num_concepts': 7,
        },
        'python_programming': {
            'name': 'Python Programming',
            'description': 'Master Python programming fundamentals',
            'icon': '🐍',
            'num_concepts': 7,
        },
        'mathematics': {
            'name': 'Mathematics',
            'description': 'Algebra, Calculus, and Problem Solving',
            'icon': '📐',
            'num_concepts': 7,
        }
    }

    # 5. Set globals for ML helpers and adaptive router
    rl_helpers.set_globals(lstm_model, rl_agent, device, CONTENT_LIBRARIES)
    adaptive.set_globals(sessions, CONTENT_LIBRARIES, SUBJECT_CONFIGS)

    print(f"\n[SUCCESS] API Ready - {len(CONTENT_LIBRARIES)} subjects available")
    print("=" * 60 + "\n")


@app.on_event("shutdown")
async def shutdown_event():
    """Disconnect from database"""
    await disconnect_db()


# ==========================================
# INCLUDE ROUTERS
# ==========================================

app.include_router(adaptive.router)  # Root and adaptive learning endpoints
app.include_router(auth.router)
app.include_router(subjects.router)
app.include_router(lessons.router)
app.include_router(enrollments.router)
app.include_router(progress.router)
app.include_router(teacher.router)
app.include_router(quiz.router)


# ==========================================
# RUN SERVER
# ==========================================

if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("  Starting Adaptive Learning API")
    print("=" * 60)
    print("\n  Prerequisites:")
    print("  1. LSTM model: general_agent/general_student_simulator.pth")
    print("  2. RL model: general_agent/ppo_general_teacher.zip")
    print("  3. Question content JSON files")
    print("  4. PostgreSQL database running")
    print("  5. .env file with DATABASE_URL")
    print("\n" + "=" * 60 + "\n")

    uvicorn.run(
        "api:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True
    )
