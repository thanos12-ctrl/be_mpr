import torch
import torch.nn as nn
import numpy as np


# ==========================================
# 1. DEFINE MODEL CLASS (Must match training)
# ==========================================
class StudentSimulator(nn.Module):
    def __init__(self, input_dim, hidden_dim, num_layers):
        super(StudentSimulator, self).__init__()
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_dim, 1)
        self.sigmoid = nn.Sigmoid()

    def forward(self, x):
        out, _ = self.lstm(x)
        out = self.fc(out)
        return self.sigmoid(out).squeeze(-1)


# ==========================================
# 2. HELPER FUNCTION: PREPARE INPUT
# ==========================================
def predict_outcome(model, history, next_difficulty, next_part=5):
    """
    history: List of [is_correct, diff, elapsed, lag, part]
    next_difficulty: Float (0.0 to 1.0)
    """
    # 1. Construct the sequence
    # We take the history and append the 'next question' features
    # For the 'next question', we don't know 'is_correct' yet, so we put a placeholder (0)
    # The model's last output step is the prediction for this 'next question'.

    # Feature order: [is_correct, difficulty, elapsed_time, lag_time, part]
    next_step = [0, next_difficulty, 0.5, 0.1, next_part]
    full_seq = history + [next_step]

    # 2. Convert to Tensor
    input_tensor = torch.FloatTensor([full_seq])  # Add batch dimension (1, Seq_Len, 5)

    # 3. Predict
    model.eval()
    with torch.no_grad():
        preds = model(input_tensor)
        # We want the prediction for the very last step
        prob = preds[0, -1].item()

    return prob


# ==========================================
# 3. RUN SCENARIOS
# ==========================================
if __name__ == "__main__":
    print("--- Loading Student Simulator ---")

    # Hyperparameters must match what you trained with
    INPUT_DIM = 5
    HIDDEN_DIM = 64
    NUM_LAYERS = 2

    model = StudentSimulator(INPUT_DIM, HIDDEN_DIM, NUM_LAYERS)

    try:
        model.load_state_dict(torch.load("student_simulator.pth", map_location=torch.device('cpu')))
        print("✅ Model loaded successfully.\n")
    except FileNotFoundError:
        print("❌ Error: 'student_simulator.pth' not found.")
        exit()

    # --- Scenario A: The "Genius" Student ---
    # History: 5 questions, all CORRECT (1), High Difficulty (0.8)
    genius_history = [
        [1, 0.8, 0.5, 0.1, 5],
        [1, 0.8, 0.5, 0.1, 5],
        [1, 0.8, 0.5, 0.1, 5],
        [1, 0.8, 0.5, 0.1, 5],
        [1, 0.9, 0.5, 0.1, 5]
    ]

    print("--- Test 1: The Genius Student ---")
    p_easy = predict_outcome(model, genius_history, next_difficulty=0.2)
    p_hard = predict_outcome(model, genius_history, next_difficulty=0.9)

    print(f"Given an EASY question (0.2), prob success: {p_easy:.2f}")
    print(f"Given a HARD question (0.9), prob success: {p_hard:.2f}")

    if p_hard < p_easy:
        print("✅ Logic Check: Prob dropped for harder question.")
    else:
        print("⚠️ Warning: Model ignores difficulty?")

    # --- Scenario B: The "Struggling" Student ---
    # History: 5 questions, all WRONG (0), Medium Difficulty (0.5)
    struggle_history = [
        [0, 0.5, 0.5, 0.1, 5],
        [0, 0.5, 0.5, 0.1, 5],
        [0, 0.5, 0.5, 0.1, 5],
        [0, 0.5, 0.5, 0.1, 5],
        [0, 0.5, 0.5, 0.1, 5]
    ]

    print("\n--- Test 2: The Struggling Student ---")
    p_easy = predict_outcome(model, genius_history, next_difficulty=0.2)
    p_struggle_hard = predict_outcome(model, struggle_history, next_difficulty=0.9)
    print(f"Given an EASY question (0.2), prob success: {p_easy:.2f}")
    print(f"Given a HARD question (0.9), prob success: {p_struggle_hard:.2f}")

    if p_struggle_hard < p_hard:  # Compare to Genius on same hard question
        print("✅ Logic Check: Struggling student has lower chance than Genius.")
    else:
        print("⚠️ Warning: Model ignores student history?")

    # --- Scenario C: Cold Start (New Student) ---
    # History: Empty or just 1 initialization step
    new_history = [[1, 0.5, 0.5, 0.0, 5]]

    print("\n--- Test 3: New Student (Cold Start) ---")
    p_start = predict_outcome(model, new_history, next_difficulty=0.5)
    print(f"First question (Diff 0.5) prob: {p_start:.2f}")