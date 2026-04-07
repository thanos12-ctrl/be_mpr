import gymnasium as gym
from gymnasium import spaces
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import random
import os


# ==========================================
# 1. STUDENT SIMULATOR (Must match training)
# ==========================================
class StudentSimulator(nn.Module):
    def __init__(self, input_dim, hidden_dim, num_layers, dropout=0.3):
        super(StudentSimulator, self).__init__()
        self.lstm = nn.LSTM(
            input_dim, hidden_dim, num_layers,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0
        )
        self.dropout = nn.Dropout(dropout)
        self.fc = nn.Linear(hidden_dim, 1)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        out, _ = self.lstm(x)
        out = self.dropout(out)
        out = self.fc(out[:, -1, :])  # Use last timestep
        return self.sigmoid(out).squeeze(-1)


# ==========================================
# 2. REAL DATA LOADER
# ==========================================
class EdNetDataLoader:
    """
    Loads real EdNet questions and difficulty from preprocessing output.
    """

    def __init__(self, questions_path='./data/questions.csv',
                 metadata_path='ednet_metadata.npz'):

        print("Loading Real EdNet Data...")

        # Load questions metadata
        if os.path.exists(questions_path):
            self.df_questions = pd.read_csv(questions_path)
            print(f"✅ Loaded {len(self.df_questions)} questions from EdNet")

            # Extract concepts from tags
            self.df_questions['concept'] = self.df_questions['tags'].astype(str).apply(
                lambda x: int(x.split(';')[0]) if x != 'nan' else -1
            )

            # Get unique concepts
            self.unique_concepts = sorted(self.df_questions['concept'].unique())
            self.unique_concepts = [c for c in self.unique_concepts if c >= 0]
            self.n_concepts = len(self.unique_concepts)

            print(f"  Concepts found: {self.n_concepts}")
            print(f"  Parts: {sorted(self.df_questions['part'].unique())}")

        else:
            raise FileNotFoundError(f"Questions file not found: {questions_path}")

        # Load difficulty map from preprocessing
        self.difficulty_map = {}
        if os.path.exists(metadata_path):
            metadata = np.load(metadata_path, allow_pickle=True)
            diff_array = metadata['difficulty_map']

            # Convert array back to dictionary
            # EdNet question IDs are STRINGS (e.g., 'q5012'), not integers!
            for qid, diff in diff_array:
                # Keep as string if it starts with 'q', otherwise try int
                if isinstance(qid, str) or (isinstance(qid, (int, float)) and str(qid).startswith('q')):
                    self.difficulty_map[str(qid)] = float(diff)
                else:
                    self.difficulty_map[int(qid)] = float(diff)

            print(f"✅ Loaded difficulty for {len(self.difficulty_map)} questions")
            if len(self.difficulty_map) > 0:
                print(
                    f"  Difficulty range: {min(self.difficulty_map.values()):.2f} - {max(self.difficulty_map.values()):.2f}")
                print(f"  Sample question IDs: {list(self.difficulty_map.keys())[:5]}")
        else:
            print(f"⚠️  Metadata not found, calculating difficulty from questions...")
            # Fallback: assign random difficulties
            for qid in self.df_questions['question_id']:
                self.difficulty_map[qid] = np.random.uniform(0.3, 0.7)

        # Add difficulty to dataframe
        self.df_questions['difficulty'] = self.df_questions['question_id'].map(
            self.difficulty_map
        ).fillna(0.5)

        # Map concepts to 0-indexed range
        self.concept_map = {c: i for i, c in enumerate(self.unique_concepts)}
        self.df_questions['concept_idx'] = self.df_questions['concept'].map(
            self.concept_map
        ).fillna(0).astype(int)

    def get_questions_by_difficulty(self, min_diff, max_diff, max_results=50):
        """
        Get real questions within a difficulty range.
        """
        candidates = self.df_questions[
            (self.df_questions['difficulty'] >= min_diff) &
            (self.df_questions['difficulty'] < max_diff)
            ]

        if len(candidates) > max_results:
            candidates = candidates.sample(max_results)

        return candidates

    def get_question_info(self, question_id):
        """
        Get metadata for a specific question.
        """
        q = self.df_questions[self.df_questions['question_id'] == question_id]
        if len(q) == 0:
            return None

        q = q.iloc[0]
        return {
            'question_id': str(q['question_id']),  # Keep as string
            'difficulty': q['difficulty'],
            'concept_idx': q['concept_idx'],
            'part': q['part'],
            'bundle_id': q.get('bundle_id', -1)
        }


# ==========================================
# 3. ENHANCED GYM ENVIRONMENT WITH REAL DATA
# ==========================================
class EdNetEnv(gym.Env):
    """
    Real EdNet Environment using actual questions and learned difficulty.
    """
    metadata = {'render.modes': ['human']}

    def __init__(self, max_steps=50, data_dir='./data'):
        super(EdNetEnv, self).__init__()

        print("\n" + "=" * 60)
        print("  Initializing EdNet Environment with REAL Data")
        print("=" * 60)

        # --- A. Load Real Question Data ---
        questions_path = os.path.join(data_dir, 'questions.csv')
        metadata_path = 'ednet_metadata.npz'

        self.data_loader = EdNetDataLoader(questions_path, metadata_path)
        self.n_concepts = self.data_loader.n_concepts

        print(f"Environment using {self.n_concepts} concepts")

        # --- B. Load LSTM Simulator ---
        self.device = torch.device("cpu")
        self.simulator = StudentSimulator(input_dim=5, hidden_dim=128, num_layers=2, dropout=0.3)

        try:
            self.simulator.load_state_dict(
                torch.load("student_simulator.pth", map_location=self.device, weights_only=True)
            )
            self.simulator.eval()
            print("✅ Student Simulator Loaded Successfully")
        except FileNotFoundError:
            print("⚠️  WARNING: 'student_simulator.pth' not found.")
            print("    The simulator will use random predictions!")

        # --- C. Action & Observation Spaces ---
        # Action: 10 difficulty levels
        self.action_space = spaces.Discrete(10)

        # Observation: [6 global + N concept masteries]
        obs_dim = 6 + self.n_concepts
        self.observation_space = spaces.Box(
            low=0, high=10, shape=(obs_dim,), dtype=np.float32
        )

        print(f"Observation space dimension: {obs_dim}")

        # --- D. Session Variables ---
        self.max_steps = max_steps
        self.current_step = 0
        self.history = []

        # Concept Tracking
        self.concept_attempts = np.zeros(self.n_concepts)
        self.concept_correct = np.zeros(self.n_concepts)
        self.consecutive_correct = 0
        self.consecutive_wrong = 0
        self.last_reward_breakdown = {}

        # Track which questions have been used (avoid repeats)
        self.used_questions = set()

        print("=" * 60 + "\n")

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)

        self.current_step = 0
        self.history = []
        self.used_questions = set()

        # Reset Stats
        self.concept_attempts = np.zeros(self.n_concepts)
        self.concept_correct = np.zeros(self.n_concepts)
        self.consecutive_correct = 0
        self.consecutive_wrong = 0

        # Warm-up: 5 random interactions from real questions
        warmup_questions = self.data_loader.df_questions.sample(5)

        for _, q in warmup_questions.iterrows():
            concept_idx = int(q['concept_idx'])
            difficulty = q['difficulty']

            # Simulate initial performance (slightly positive bias)
            is_correct = 1 if np.random.random() < 0.6 else 0

            self.history.append([
                is_correct,
                difficulty,
                0.5,  # normalized time
                0.0,  # no lag
                concept_idx
            ])

            self.concept_attempts[concept_idx] += 1
            if is_correct:
                self.concept_correct[concept_idx] += 1

        return self._get_obs(), {}

    def _get_lstm_prediction(self, next_difficulty, next_concept_idx):
        """
        Ask LSTM: 'What's P(correct) for this question?'
        """
        # Get recent history (last 20 steps)
        seq = np.array(self.history[-20:])

        # Pad if needed
        if len(seq) < 20:
            padding = np.zeros((20 - len(seq), 5))
            seq = np.vstack([padding, seq])

        # Create hypothetical next step
        # [is_correct=0 (masked), difficulty, time=0.5, lag=0.1, concept_idx]
        next_features = np.array([[0.0, next_difficulty, 0.5, 0.1, next_concept_idx]])

        # Combine
        full_seq = np.concatenate([seq, next_features], axis=0)

        # Predict
        input_tensor = torch.FloatTensor(full_seq).unsqueeze(0).to(self.device)

        with torch.no_grad():
            prob = self.simulator(input_tensor).item()

        return np.clip(prob, 0.01, 0.99)  # Avoid extreme values

    def _get_obs(self):
        """
        Construct state vector:
        [lstm_pred, recent_acc, avg_diff, streak+, streak-, progress, concept_mastery_0, ..., concept_mastery_N]
        """
        if len(self.history) < 5:
            # Not enough history - return neutral state
            obs = np.zeros(6 + self.n_concepts, dtype=np.float32)
            obs[:6] = [0.5, 0.5, 0.5, 0, 0, 0]  # Neutral values
            obs[6:] = 0.5  # Neutral mastery
            return obs

        # Recent stats
        recent_5 = np.array(self.history[-5:])
        recent_acc = np.mean(recent_5[:, 0])
        avg_diff = np.mean(recent_5[:, 1])

        # LSTM prediction (probe with medium question)
        lstm_pred = self._get_lstm_prediction(0.5, 0)

        # Concept mastery
        concept_mastery = np.zeros(self.n_concepts)
        for i in range(self.n_concepts):
            if self.concept_attempts[i] > 0:
                concept_mastery[i] = self.concept_correct[i] / self.concept_attempts[i]
            else:
                concept_mastery[i] = 0.5  # Neutral for unseen

        # Assemble
        obs = np.concatenate([
            [
                lstm_pred,
                recent_acc,
                avg_diff,
                min(self.consecutive_correct, 10),
                min(self.consecutive_wrong, 10),
                self.current_step / self.max_steps
            ],
            concept_mastery
        ]).astype(np.float32)

        return obs

    def step(self, action):
        """
        Execute one step: agent selects difficulty, we find real question, simulate outcome.
        """
        # 1. Map action to difficulty range
        target_diff_min = action / 10.0
        target_diff_max = (action + 1) / 10.0

        # 2. Get real questions in this range
        candidates = self.data_loader.get_questions_by_difficulty(
            target_diff_min, target_diff_max
        )

        # 3. Filter out already used questions (optional - for variety)
        if len(self.used_questions) < len(self.data_loader.df_questions) * 0.8:
            # Still have enough unused questions
            unused = candidates[~candidates['question_id'].isin(self.used_questions)]
            if len(unused) > 0:
                candidates = unused

        # 4. Select a question
        if candidates.empty:
            # Fallback to random question
            selected_q = self.data_loader.df_questions.sample(1).iloc[0]
        else:
            selected_q = candidates.sample(1).iloc[0]

        chosen_qid = str(selected_q['question_id'])  # Keep as string
        chosen_difficulty = float(selected_q['difficulty'])
        chosen_concept_idx = int(selected_q['concept_idx'])

        self.used_questions.add(chosen_qid)

        # 5. Get LSTM prediction
        prob_correct = self._get_lstm_prediction(chosen_difficulty, chosen_concept_idx)

        # 6. Simulate outcome (stochastic based on LSTM prediction)
        is_correct = 1 if random.random() < prob_correct else 0

        # 7. Update history and tracking
        self.history.append([
            is_correct,
            chosen_difficulty,
            0.5,  # time (normalized)
            0.1,  # lag
            chosen_concept_idx
        ])

        self.concept_attempts[chosen_concept_idx] += 1
        if is_correct:
            self.concept_correct[chosen_concept_idx] += 1
            self.consecutive_correct += 1
            self.consecutive_wrong = 0
        else:
            self.consecutive_wrong += 1
            self.consecutive_correct = 0

        self.current_step += 1

        # 8. Calculate reward
        reward = self._calculate_reward(is_correct, chosen_difficulty, prob_correct)

        # 9. Check termination
        terminated = self.current_step >= self.max_steps
        truncated = False

        info = {
            "prob_correct": prob_correct,
            "chosen_diff": chosen_difficulty,
            "chosen_concept": chosen_concept_idx,
            "is_correct": is_correct,
            "question_id": chosen_qid,
            "reward_breakdown": self.last_reward_breakdown
        }

        return self._get_obs(), reward, terminated, truncated, info

    def _calculate_reward(self, is_correct, difficulty, lstm_pred):
        """
        Enhanced reward function promoting optimal challenge.
        """
        breakdown = {}

        # 1. Base correctness reward (scaled by difficulty)
        if is_correct:
            base_reward = 0.5 + (difficulty * 0.5)  # 0.5 to 1.0
        else:
            base_reward = -0.3  # Small penalty
        breakdown['base'] = base_reward

        # 2. Flow state bonus (optimal challenge zone)
        flow_bonus = 0
        if is_correct and 0.55 <= lstm_pred <= 0.75:
            flow_bonus = 0.5  # Sweet spot!
        breakdown['flow'] = flow_bonus

        # 3. Difficulty-matched bonus
        difficulty_bonus = 0
        if is_correct and difficulty >= 0.6:
            difficulty_bonus = 0.3  # Reward hard questions
        breakdown['difficulty'] = difficulty_bonus

        # 4. Frustration penalty (3+ consecutive wrong)
        frustration_penalty = 0
        if self.consecutive_wrong >= 3:
            if difficulty > 0.5:
                frustration_penalty = -1.5  # Too hard after failures
            else:
                frustration_penalty = -0.3  # Okay, at least trying easier
        breakdown['frustration'] = frustration_penalty

        # 5. Boredom penalty (too easy)
        boredom_penalty = 0
        if self.consecutive_correct >= 5 and lstm_pred > 0.85:
            boredom_penalty = -0.6
        breakdown['boredom'] = boredom_penalty

        # 6. Too-hard penalty (setting up for failure)
        too_hard_penalty = 0
        if not is_correct and lstm_pred < 0.35:
            too_hard_penalty = -0.5  # Agent gave impossible question
        breakdown['too_hard'] = too_hard_penalty

        # Total
        total_reward = (
                base_reward +
                flow_bonus +
                difficulty_bonus +
                frustration_penalty +
                boredom_penalty +
                too_hard_penalty
        )

        self.last_reward_breakdown = breakdown
        return total_reward

    def render(self, mode='human'):
        if len(self.history) > 0:
            last = self.history[-1]
            concept = int(last[4])
            print(f"Step {self.current_step}: "
                  f"Concept={concept} | "
                  f"Diff={last[1]:.2f} | "
                  f"Correct={bool(last[0])} | "
                  f"Streaks: +{self.consecutive_correct}/-{self.consecutive_wrong}")


# ==========================================
# 4. TEST THE ENVIRONMENT
# ==========================================
if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("  TESTING EDNET ENVIRONMENT WITH REAL DATA")
    print("=" * 70 + "\n")

    try:
        env = EdNetEnv(max_steps=20, data_dir='./Data')
        obs, _ = env.reset()

        print(f"Initial Observation Shape: {obs.shape}")
        print(f"Initial State: {obs[:10]}...\n")  # Show first 10 values

        total_reward = 0

        for i in range(20):
            # Random action
            action = env.action_space.sample()

            obs, reward, terminated, truncated, info = env.step(action)
            total_reward += reward

            print(f"Step {i + 1}:")
            print(f"  Action (Difficulty): {action} → {info['chosen_diff']:.2f}")
            print(f"  Question ID: {info['question_id']}")
            print(f"  Concept: {info['chosen_concept']}")
            print(f"  LSTM P(correct): {info['prob_correct']:.3f}")
            print(f"  Result: {'✅ Correct' if info['is_correct'] else '❌ Wrong'}")
            print(f"  Reward: {reward:.2f}")
            print(f"  Breakdown: {info['reward_breakdown']}")
            print()

            if terminated:
                break

        print(f"\n{'=' * 70}")
        print(f"Total Episode Reward: {total_reward:.2f}")
        print(f"Average Reward per Step: {total_reward / 20:.2f}")
        print(f"{'=' * 70}")

        print("\n✅ Environment test successful! Ready for PPO training.")

    except FileNotFoundError as e:
        print(f"\n❌ Error: {e}")
        print("\nMake sure you have:")
        print("  1. Run preprocessing.py to create ednet_metadata.npz")
        print("  2. ./data/questions.csv exists")
        print("  3. Trained student_simulator.pth exists")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback

        traceback.print_exc()