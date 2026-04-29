import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import random
import os

class StudentSimulator(nn.Module):
    def __init__(self, input_dim=5, hidden_dim=128, num_layers=2, dropout=0.3):
        super(StudentSimulator, self).__init__()
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers, batch_first=True, dropout=dropout if num_layers > 1 else 0)
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_dim, 1)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        out, _ = self.lstm(x)
        out = self.dropout(out)
        out = self.fc(out[:, -1, :])  
        return self.sigmoid(out).squeeze(-1)

class EdNetDataLoader:
    def __init__(self, questions_path='../data/questions.csv', metadata_path='general_metadata.npz'):
        self.df_questions = pd.read_csv(questions_path)
        self.df_questions['concept'] = self.df_questions['tags'].astype(str).apply(
            lambda x: int(x.split(';')[0]) if x != 'nan' else -1
        )
        self.unique_concepts = sorted([c for c in self.df_questions['concept'].unique() if c >= 0])
        
        self.difficulty_map = {}
        if os.path.exists(metadata_path):
            metadata = np.load(metadata_path, allow_pickle=True)
            for qid, diff in metadata['difficulty_map']:
                key = str(qid) if isinstance(qid, str) or str(qid).startswith('q') else int(qid)
                self.difficulty_map[key] = float(diff)
        
        self.df_questions['difficulty'] = self.df_questions['question_id'].map(self.difficulty_map).fillna(0.5)
        self.concept_map = {c: i for i, c in enumerate(self.unique_concepts)}
        self.df_questions['concept_idx'] = self.df_questions['concept'].map(self.concept_map).fillna(0).astype(int)

    def get_questions_by_difficulty_and_concept(self, concept_idx, min_diff, max_diff, max_results=50):
        candidates = self.df_questions[
            (self.df_questions['concept_idx'] == concept_idx) &
            (self.df_questions['difficulty'] >= min_diff) &
            (self.df_questions['difficulty'] < max_diff + 0.1) # Soft upper bound
        ]
        
        # Fallback if no questions found in exact range
        if candidates.empty:
            candidates = self.df_questions[self.df_questions['concept_idx'] == concept_idx]
            
        if len(candidates) > max_results:
            candidates = candidates.sample(max_results)
            
        return candidates

class EdNetEnv(gym.Env):
    metadata = {'render.modes': ['human']}

    def __init__(self, max_steps=50, data_dir='../data'):
        super(EdNetEnv, self).__init__()

        self.data_loader = EdNetDataLoader(os.path.join(data_dir, 'questions.csv'), 'general_metadata.npz')
        self.n_concepts_total = len(self.data_loader.unique_concepts)
        
        self.device = torch.device("cpu")
        self.simulator = StudentSimulator(input_dim=5, hidden_dim=128, num_layers=2, dropout=0.3)
        try:
            self.simulator.load_state_dict(torch.load("general_student_simulator.pth", map_location=self.device, weights_only=True))
            self.simulator.eval()
        except FileNotFoundError:
            print("⚠️ WARNING: 'general_student_simulator.pth' not found. Will use random predictions!")

        # DOMAIN AGNOSTIC ACTION SPACE
        # 0-9: Stay on current concept. Difficulty: 0.0 - 0.9
        # 10-19: Move to next concept. Difficulty: 0.0 - 0.9
        self.action_space = spaces.Discrete(20)

        # DOMAIN AGNOSTIC OBSERVATION SPACE
        # [lstm_pred, recent_acc, avg_diff, streak+, streak-, progress, difficulty_trend, concept_mastery]
        self.observation_space = spaces.Box(low=-1, high=10, shape=(8,), dtype=np.float32)

        self.max_steps = max_steps
        self.reset()

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.current_step = 0
        self.history = []
        self.used_questions = set()
        
        self.consecutive_correct = 0
        self.consecutive_wrong = 0
        
        self.current_concept_idx = 0
        self.concept_attempts = 0
        self.concept_correct = 0
        self.last_difficulty = 0.5
        
        # Warmup
        for _ in range(5):
            is_correct = 1 if np.random.random() < 0.6 else 0
            self.history.append([is_correct, 0.5, 0.5, 0.0, 0])
            self.concept_attempts += 1
            if is_correct:
                self.concept_correct += 1

        return self._get_obs(), {}

    def _get_lstm_prediction(self, next_difficulty, is_new_concept):
        seq = np.array(self.history[-20:])
        if len(seq) < 20:
            padding = np.zeros((20 - len(seq), 5))
            seq = np.vstack([padding, seq])
            
        next_features = np.array([[0.0, next_difficulty, 0.5, 0.1, is_new_concept]])
        full_seq = np.concatenate([seq, next_features], axis=0)

        input_tensor = torch.FloatTensor(full_seq).unsqueeze(0).to(self.device)
        with torch.no_grad():
            prob = self.simulator(input_tensor).item()
            
        return np.clip(prob, 0.01, 0.99)

    def _get_obs(self):
        recent_5 = np.array(self.history[-5:])
        recent_acc = np.mean(recent_5[:, 0])
        avg_diff = np.mean(recent_5[:, 1])

        lstm_pred = self._get_lstm_prediction(0.5, 0)
        
        concept_mastery = (self.concept_correct / self.concept_attempts) if self.concept_attempts > 0 else 0.5
        diff_trend = avg_diff - self.last_difficulty
        self.last_difficulty = avg_diff

        obs = np.array([
            lstm_pred,
            recent_acc,
            avg_diff,
            min(self.consecutive_correct, 10),
            min(self.consecutive_wrong, 10),
            self.current_step / self.max_steps,
            diff_trend,
            concept_mastery
        ], dtype=np.float32)

        return obs

    def step(self, action):
        target_diff = (action % 10) / 10.0
        move_to_next = action >= 10
        
        moved_concept_flag = 0
        if move_to_next:
            self.current_concept_idx = min(self.current_concept_idx + 1, self.n_concepts_total - 1)
            self.concept_attempts = 0  # reset for new concept
            self.concept_correct = 0
            moved_concept_flag = 1

        candidates = self.data_loader.get_questions_by_difficulty_and_concept(
            self.current_concept_idx, target_diff, target_diff + 0.1
        )
        
        if len(self.used_questions) < len(self.data_loader.df_questions) * 0.8:
            unused = candidates[~candidates['question_id'].isin(self.used_questions)]
            if len(unused) > 0:
                candidates = unused

        if candidates.empty:
            selected_q = self.data_loader.df_questions.sample(1).iloc[0]
        else:
            selected_q = candidates.sample(1).iloc[0]

        chosen_difficulty = float(selected_q['difficulty'])
        self.used_questions.add(str(selected_q['question_id']))

        prob_correct = self._get_lstm_prediction(chosen_difficulty, moved_concept_flag)
        is_correct = 1 if random.random() < prob_correct else 0

        self.history.append([is_correct, chosen_difficulty, 0.5, 0.1, moved_concept_flag])
        self.concept_attempts += 1
        if is_correct:
            self.concept_correct += 1
            self.consecutive_correct += 1
            self.consecutive_wrong = 0
        else:
            self.consecutive_wrong += 1
            self.consecutive_correct = 0

        self.current_step += 1
        concept_mastery = (self.concept_correct / self.concept_attempts) if self.concept_attempts > 0 else 0.5
        reward = self._calculate_reward(is_correct, chosen_difficulty, prob_correct, move_to_next, concept_mastery)
        
        terminated = self.current_step >= self.max_steps
        info = {
            "is_correct": is_correct,
            "chosen_diff": chosen_difficulty,
            "concept_mastery": concept_mastery
        }

        return self._get_obs(), reward, terminated, False, info

    def _calculate_reward(self, is_correct, difficulty, lstm_pred, moved_module, concept_mastery):
        breakdown = {}
        
        # Difficulty Adaptation core
        breakdown['base'] = 0.5 + (difficulty * 0.5) if is_correct else -0.3
        breakdown['flow'] = 0.5 if (is_correct and 0.55 <= lstm_pred <= 0.75) else 0
        breakdown['difficulty'] = 0.3 if (is_correct and difficulty >= 0.6) else 0
        breakdown['frustration'] = -1.5 if (self.consecutive_wrong >= 3 and difficulty > 0.5) else 0
        breakdown['boredom'] = -0.6 if (self.consecutive_correct >= 5 and lstm_pred > 0.85) else 0
        breakdown['too_hard'] = -0.5 if (not is_correct and lstm_pred < 0.35) else 0
        
        # Progression Incentives
        if moved_module:
            if is_correct:
                breakdown['progression'] = 2.0  # Huge reward for progressing successfully
            else:
                breakdown['progression'] = -1.0 # Penalty for moving too early
        else:
            if concept_mastery > 0.85 and self.concept_attempts > 5:
                breakdown['stagnation'] = -0.5  # Penalty for camping a mastered concept
            else:
                breakdown['stagnation'] = 0
                
        return sum(breakdown.values())
