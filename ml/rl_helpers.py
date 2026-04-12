"""
RL Helper Functions for Adaptive Learning
"""

from typing import Dict, List
from fastapi import HTTPException
import numpy as np
import torch


# These will be set by the main API
lstm_model = None
rl_agent = None
device = None
CONTENT_LIBRARIES = {}


def set_globals(lstm_mod, rl_ag, dev, content_libs):
    """Set global references from main API"""
    global lstm_model, rl_agent, device, CONTENT_LIBRARIES
    lstm_model = lstm_mod
    rl_agent = rl_ag
    device = dev
    CONTENT_LIBRARIES = content_libs


def get_lstm_prediction(history: List, next_difficulty: float, next_concept: int) -> float:
    """Get LSTM prediction for a question"""
    if lstm_model is None:
        return 0.65  # Fallback

    seq = np.array(history[-20:], dtype=np.float32)

    if len(seq) < 20:
        padding = np.zeros((20 - len(seq), 5))
        seq = np.vstack([padding, seq])

    next_features = np.array([[0.0, float(next_difficulty), 0.5, 0.1, float(next_concept)]])
    full_seq = np.concatenate([seq, next_features], axis=0)
    # print(history, "seq: ", seq, "next features", next_features)
    with torch.no_grad():
        input_tensor = torch.FloatTensor(full_seq).unsqueeze(0).to(device)
        prob = lstm_model(input_tensor).item()

    return np.clip(prob, 0.01, 0.99)


def get_observation(session: Dict) -> np.ndarray:
    """Construct RL observation from session state"""
    history = session['history']
    n_concepts = session['n_concepts']

    if len(history) == 0:
        recent_acc = 0.5
        avg_diff = 0.5
    else:
        recent_5 = np.array(history[-5:], dtype=np.float32)
        recent_acc = float(np.mean(recent_5[:, 0]))
        avg_diff = float(np.mean(recent_5[:, 1]))

    lstm_pred = get_lstm_prediction(history, 0.5, 0)

    # Concept mastery
    concept_mastery = np.zeros(141)
    for i in range(n_concepts):
        if session['concept_attempts'][i] > 0:
            concept_mastery[i] = session['concept_correct'][i] / session['concept_attempts'][i]
        else:
            concept_mastery[i] = 0.5

    obs = np.concatenate([
        [
            lstm_pred,
            recent_acc,
            avg_diff,
            min(session['consecutive_correct'], 10),
            min(session['consecutive_wrong'], 10),
            session['current_step'] / session['max_steps']
        ],
        concept_mastery
    ]).astype(np.float32)

    print("\n" + "="*40)
    print("RL AGENT STATE VECTOR")
    print("="*40)
    print(f"LSTM Prob Correct: {lstm_pred:.3f}")
    print(f"Recent Accuracy:   {recent_acc:.2f}")
    print(f"Avg Difficulty:    {avg_diff:.2f}")
    print(f"Consecutive Right: {session['consecutive_correct']}")
    print(f"Consecutive Wrong: {session['consecutive_wrong']}")
    print(f"Step Progress:     {obs[5]:.2f}")
    
    # Show active concepts
    active_concepts = [(i, m) for i, m in enumerate(concept_mastery) if session['concept_attempts'][i] > 0]
    if active_concepts:
        print(f"Active Concept Masteries: {['C'+str(i)+': '+str(round(m,2)) for i,m in active_concepts]}")
    print("="*40 + "\n")

    return obs


def select_next_question(session: Dict) -> Dict:
    """Use RL agent to select next question"""
    obs = get_observation(session)

    # Get action from RL agent
    if rl_agent is not None:
        action, _ = rl_agent.predict(obs, deterministic=True)
        action = int(action)
    else:
        action = np.random.randint(0, 10)

    # Map action to difficulty range
    target_diff_min = action / 10.0
    target_diff_max = (action + 1) / 10.0

    # Get content library - check if this is a lesson-specific quiz
    if session.get('is_lesson_quiz') and 'lesson_questions' in session:
        # Use lesson-specific questions
        content_lib = session['lesson_questions']
    else:
        # Use subject-wide content library
        subject = session['subject']
        content_lib = CONTENT_LIBRARIES.get(subject, {})

    if not content_lib:
        raise HTTPException(500, f"No content available for this session")

    # Find unused questions in difficulty range
    candidates = [
        q for q in content_lib.values()
        if target_diff_min <= q['difficulty'] < target_diff_max
           and q['question_id'] not in session['used_questions']
    ]

    # Fallback 1: unused questions in expanded difficulty range (±0.2)
    if not candidates:
        expanded_min = max(0.0, target_diff_min - 0.2)
        expanded_max = min(1.0, target_diff_max + 0.2)
        candidates = [
            q for q in content_lib.values()
            if expanded_min <= q['difficulty'] < expanded_max
               and q['question_id'] not in session['used_questions']
        ]

    # Fallback 2: any unused question regardless of difficulty
    if not candidates:
        candidates = [
            q for q in content_lib.values()
            if q['question_id'] not in session['used_questions']
        ]

    # Fallback 3: allow repeats only when ALL questions have been used
    if not candidates:
        candidates = list(content_lib.values())

    # Select randomly from candidates
    selected = candidates[np.random.randint(0, len(candidates))]

    # Get LSTM prediction
    concept_id = selected.get('part', 1) - 1  # 0-indexed
    lstm_conf = get_lstm_prediction(
        session['history'],
        selected['difficulty'],
        concept_id
    )

    return {
        'question_id': selected['question_id'],
        'question_text': selected['question_text'],
        'code': selected.get('code'),
        'options': selected['options'],
        'part': selected.get('part', 1),
        'concept': selected.get('concept', 'General'),
        'difficulty': selected['difficulty'],
        'correct_answer': selected['correct_answer'],
        'explanation': selected.get('explanation', ''),
        'lstm_confidence': lstm_conf
    }


def calculate_reward(session: Dict, is_correct: bool, difficulty: float, lstm_pred: float) -> Dict:
    """Calculate RL reward"""
    breakdown = {}

    # Base reward
    if is_correct:
        base = 0.5 + (difficulty * 0.5)
    else:
        base = -0.3
    breakdown['base'] = base

    # Flow bonus (optimal challenge)
    flow = 0.5 if (is_correct and 0.55 <= lstm_pred <= 0.75) else 0
    breakdown['flow'] = flow

    # Difficulty bonus
    diff_bonus = 0.3 if (is_correct and difficulty >= 0.6) else 0
    breakdown['difficulty'] = diff_bonus

    # Frustration penalty
    frust = -1.5 if session['consecutive_wrong'] >= 3 else 0
    breakdown['frustration'] = frust

    # Boredom penalty
    boredom = -0.6 if (session['consecutive_correct'] >= 5 and lstm_pred > 0.85) else 0
    breakdown['boredom'] = boredom

    # Too hard penalty
    too_hard = -0.5 if (not is_correct and lstm_pred < 0.35) else 0
    breakdown['too_hard'] = too_hard

    total = base + flow + diff_bonus + frust + boredom + too_hard
    breakdown['total'] = total

    return breakdown
