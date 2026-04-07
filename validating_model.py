import gymnasium as gym
from stable_baselines3 import PPO
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns  # pip install seaborn
from ednet_env import EdNetEnv


def run_validation(model_path="ppo_ednet_teacher.zip", steps=100):
    print(f"--- 🔍 Loading Model: {model_path} ---")

    # 1. Load Env & Model
    env = EdNetEnv(max_steps=steps)
    try:
        model = PPO.load(model_path)
    except FileNotFoundError:
        print("❌ Model not found! Train your agent first.")
        return None

    # 2. Storage
    logs = []

    # 3. Start Simulation
    print(f"--- Starting Simulation ({steps} Steps) ---")
    obs, _ = env.reset()

    for step in range(steps):
        # Predict
        action, _ = model.predict(obs, deterministic=True)

        # Act
        obs, reward, terminated, truncated, info = env.step(action)

        # Safe extraction of scalar values
        action_val = int(action) if np.ndim(action) == 0 else int(action[0])

        # Log Data
        entry = {
            "Step": step + 1,
            "Action_Diff_Bin": action_val,
            "Assigned_Diff": round(info['chosen_diff'], 2),
            "Concept_ID": info['chosen_concept'],
            "LSTM_Confidence": round(info['prob_correct'], 2),
            "Is_Correct": 1 if info['is_correct'] else 0,
            "Streak_Correct": int(obs[3]),  # From observation vector
            "Streak_Wrong": int(obs[4]),
            "Reward_Total": round(reward, 3),
            "Reward_Base": round(info['reward_breakdown']['base'], 2),
            "Reward_Flow": round(info['reward_breakdown']['flow'], 2),
            "Reward_Frustration": round(info['reward_breakdown']['frustration'], 2)
        }
        logs.append(entry)

        if terminated:
            print("Session Limit Reached.")
            break

    # 4. Save
    df = pd.DataFrame(logs)
    df.to_csv("validation_log.csv", index=False)
    print(f"✅ Data logged to 'validation_log.csv'")
    return df


def analyze_and_plot(df):
    if df is None: return

    print("\n" + "=" * 40)
    print(" 📊 FORENSIC ANALYSIS")
    print("=" * 40)

    # 1. Concept Analysis
    print("\n1. Concept Coverage:")
    concept_counts = df['Concept_ID'].value_counts().sort_index()
    print(concept_counts)

    # 2. Adaptivity Check (Did it drop difficulty after failure?)
    print("\n2. Reaction to Failure:")
    failures = df[df['Is_Correct'] == 0]
    reactions = []
    for idx in failures.index:
        if idx + 1 < len(df):
            diff_before = df.loc[idx, 'Assigned_Diff']
            diff_after = df.loc[idx + 1, 'Assigned_Diff']
            if diff_after < diff_before:
                reactions.append("Dropped")
            else:
                reactions.append("Raised/Same")

    if len(reactions) > 0:
        drop_rate = reactions.count("Dropped") / len(reactions)
        print(f"   Agent dropped difficulty in {drop_rate * 100:.1f}% of failures.")
    else:
        print("   (No failures observed)")

    # --- PLOTTING ---
    fig, axes = plt.subplots(2, 1, figsize=(12, 10))

    # Plot A: Adaptive Path
    ax1 = axes[0]
    # Draw the line
    ax1.plot(df['Step'], df['Assigned_Diff'], color='gray', alpha=0.5, label='Difficulty')

    # Draw points colored by Correct/Wrong
    # Green = Correct, Red = Wrong
    colors = ['green' if x == 1 else 'red' for x in df['Is_Correct']]
    sizes = [100 if x == 1 else 150 for x in df['Is_Correct']]  # Make failures bigger

    ax1.scatter(df['Step'], df['Assigned_Diff'], c=colors, s=sizes, zorder=5)

    # Draw "Flow Zone"
    ax1.fill_between(df['Step'], 0.6, 0.8, color='green', alpha=0.1, label='Target Flow Zone')

    ax1.set_title("Student Learning Path (Green=Correct, Red=Wrong)")
    ax1.set_ylabel("Difficulty (0-1)")
    ax1.set_ylim(0, 1.1)
    ax1.grid(True, alpha=0.3)

    # Plot B: Concept Focus
    ax2 = axes[1]
    sns.scatterplot(data=df, x='Step', y='Concept_ID', hue='Is_Correct',
                    palette={0: 'red', 1: 'green'}, s=100, ax=ax2, legend=False)
    ax2.set_yticks(range(10))
    ax2.set_ylabel("Concept ID (Topic)")
    ax2.set_title("Concept Rotation & Mastery")
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    data = run_validation()
    analyze_and_plot(data)