"""
RL Helper Functions for Adaptive Learning (Domain-Agnostic)
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


def get_lstm_prediction(history: List, next_difficulty: float, is_new_concept: int) -> float:
    """Get domain-agnostic LSTM prediction for a question"""
    if lstm_model is None:
        return 0.65  # Fallback

    if not history:
        seq = np.zeros((20, 5), dtype=np.float32)
    else:
        seq = np.array(history[-20:], dtype=np.float32)
        if len(seq) < 20:
            padding = np.zeros((20 - len(seq), 5), dtype=np.float32)
            seq = np.vstack([padding, seq])

    # Ensure everything is a float32 explicitly to avoid type errors
    next_features = np.array([[0.0, float(next_difficulty), 0.5, 0.1, float(is_new_concept)]], dtype=np.float32)
    full_seq = np.concatenate([seq, next_features], axis=0)
    
    with torch.no_grad():
        input_tensor = torch.FloatTensor(full_seq).unsqueeze(0).to(device)
        prob = lstm_model(input_tensor).item()

    return np.clip(prob, 0.01, 0.99)


def get_observation(session: Dict) -> np.ndarray:
    """Construct Domain-Agnostic RL observation from session state"""
    history = session['history']
    
    if len(history) == 0:
        recent_acc = 0.5
        avg_diff = 0.5
        diff_trend = 0.0
    else:
        recent_5 = np.array(history[-5:], dtype=np.float32)
        recent_acc = float(np.mean(recent_5[:, 0]))
        avg_diff = float(np.mean(recent_5[:, 1]))
        if len(history) >= 2:
            diff_trend = avg_diff - float(history[-2][1])
        else:
            diff_trend = 0.0

    lstm_pred = get_lstm_prediction(history, 0.5, 0)

    # Concept mastery for the current topic
    c_attempts = session.get('concept_attempts', 0)
    c_correct = session.get('concept_correct', 0)
    concept_mastery = (c_correct / c_attempts) if c_attempts > 0 else 0.5

    obs = np.array([
        lstm_pred,
        recent_acc,
        avg_diff,
        min(session.get('consecutive_correct', 0), 10),
        min(session.get('consecutive_wrong', 0), 10),
        session.get('current_step', 0) / max(session.get('max_steps', 10), 1),
        diff_trend,
        concept_mastery
    ], dtype=np.float32)

    print("\n" + "="*40)
    print("RL AGENT STATE VECTOR (DOMAIN-AGNOSTIC)")
    print("="*40)
    print(f"LSTM Prob Correct: {lstm_pred:.3f}")
    print(f"Recent Accuracy:   {recent_acc:.2f}")
    print(f"Avg Difficulty:    {avg_diff:.2f}")
    print(f"Consecutive Right: {int(obs[3])}")
    print(f"Consecutive Wrong: {int(obs[4])}")
    print(f"Step Progress:     {obs[5]:.2f}")
    print(f"Diff Trend:        {diff_trend:.2f}")
    print(f"Current Topic Mastery: {concept_mastery:.2f}")
    print("="*40 + "\n")

    return obs


def select_next_question(session: Dict) -> Dict:
    """Use RL agent to select next question and decide if we move topics"""
    obs = get_observation(session)

    # Get action from RL agent
    if rl_agent is not None:
        action, _ = rl_agent.predict(obs, deterministic=True)
        action = int(action)
    else:
        action = int(np.random.randint(0, 20))

    # Parse the Discrete(20) Action Space
    target_diff_min = (action % 10) / 10.0
    target_diff_max = target_diff_min + 0.1
    move_to_next = action >= 10

    # Let the session know what the agent decided so the reward function can read it
    session['agent_moved_concept'] = move_to_next

    # Get content library
    if session.get('is_lesson_quiz') and 'lesson_questions' in session:
        content_lib = session['lesson_questions']
    else:
        subject = session.get('subject', 'unknown')
        content_lib = CONTENT_LIBRARIES.get(subject, {})

    if not content_lib:
        raise HTTPException(500, f"No content available for this session")

    # Group available questions by concept ID to enforce progression order
    unique_concepts = sorted(list(set(q.get('part', 1) for q in content_lib.values())))
    
    # Initialize the topic pointer if it doesn't exist
    if 'current_concept_idx' not in session:
        session['current_concept_idx'] = 0

    if move_to_next:
        # Advance the pointer to the next available module
        session['current_concept_idx'] = min(session['current_concept_idx'] + 1, len(unique_concepts) - 1)
        # Reset local mastery stats when skipping a topic
        session['concept_attempts'] = 0
        session['concept_correct'] = 0

    current_concept_val = unique_concepts[session['current_concept_idx']]

    # Filter candidates by the active module AND difficulty
    candidates = [
        q for q in content_lib.values()
        if q.get('part', 1) == current_concept_val
        and target_diff_min <= q['difficulty'] < target_diff_max
        and q['question_id'] not in session.get('used_questions', set())
    ]

    # Fallback 1: Any unused question in the current module (ignore difficulty)
    if not candidates:
        candidates = [
            q for q in content_lib.values()
            if q.get('part', 1) == current_concept_val
            and q['question_id'] not in session.get('used_questions', set())
        ]
        
    # Fallback 2: Any unused question matching the difficulty anywhere
    if not candidates:
        candidates = [
            q for q in content_lib.values()
            if target_diff_min <= q['difficulty'] <= target_diff_max
            and q['question_id'] not in session.get('used_questions', set())
        ]

    # Fallback 3: Random unused
    if not candidates:
        candidates = [
            q for q in content_lib.values()
            if q['question_id'] not in session.get('used_questions', set())
        ]

    # Fallback 4: Repeat
    if not candidates:
        candidates = list(content_lib.values())

    selected = candidates[np.random.randint(0, len(candidates))]

    # Get LSTM prediction
    lstm_conf = get_lstm_prediction(
        session['history'],
        selected['difficulty'],
        1 if move_to_next else 0
    )

    return {
        'question_id': str(selected['question_id']),
        'question_text': selected['question_text'],
        'code': selected.get('code'),
        'options': selected['options'],
        'part': selected.get('part', 1),
        'concept': selected.get('concept', 'General'),
        'difficulty': float(selected['difficulty']),
        'correct_answer': selected['correct_answer'],
        'explanation': selected.get('explanation', ''),
        'lstm_confidence': float(lstm_conf)
    }


def calculate_reward(session: Dict, is_correct: bool, difficulty: float, lstm_pred: float) -> Dict:
    """Calculate the Domain-Agnostic RL reward (with Progression)"""
    breakdown = {}

    # Core
    breakdown['base'] = 0.5 + (difficulty * 0.5) if is_correct else -0.3
    breakdown['flow'] = 0.5 if (is_correct and 0.55 <= lstm_pred <= 0.75) else 0
    breakdown['difficulty'] = 0.3 if (is_correct and difficulty >= 0.6) else 0
    breakdown['frustration'] = -1.5 if (session.get('consecutive_wrong', 0) >= 3 and difficulty > 0.5) else 0
    breakdown['boredom'] = -0.6 if (session.get('consecutive_correct', 0) >= 5 and lstm_pred > 0.85) else 0
    breakdown['too_hard'] = -0.5 if (not is_correct and lstm_pred < 0.35) else 0
    
    # Progression
    moved_module = session.get('agent_moved_concept', False)
    c_attempts = session.get('concept_attempts', 0)
    c_correct = session.get('concept_correct', 0)
    concept_mastery = (c_correct / c_attempts) if c_attempts > 0 else 0.5
    
    if moved_module:
        if is_correct:
            breakdown['progression'] = 2.0  # Huge reward
        else:
            breakdown['progression'] = -1.0 # Early transition penalty
    else:
        if concept_mastery > 0.85 and c_attempts > 5:
            breakdown['stagnation'] = -0.5  # Penalize camping a mastered module
        else:
            breakdown['stagnation'] = 0.0

    breakdown['total'] = sum(breakdown.values())
    return breakdown
