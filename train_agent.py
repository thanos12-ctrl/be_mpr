import gymnasium as gym
from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.callbacks import EvalCallback, BaseCallback
from stable_baselines3.common.vec_env import DummyVecEnv
import numpy as np
import matplotlib.pyplot as plt
import os

# Import your custom environment
# Ensure ednet_env.py is in the same folder
from ednet_env import EdNetEnv


# ==========================================
# CUSTOM CALLBACK FOR MONITORING
# ==========================================
class RewardLoggingCallback(BaseCallback):
    """
    Custom callback to log rewards and other metrics during training.
    """

    def __init__(self, verbose=0):
        super(RewardLoggingCallback, self).__init__(verbose)
        self.episode_rewards = []
        self.episode_lengths = []

    def _on_step(self) -> bool:
        # Check if episode is done
        # 'dones' is a list of booleans (one for each env in the batch)
        if self.locals.get('dones')[0]:
            # Get the episode info
            infos = self.locals.get('infos', [{}])
            info = infos[0]

            # Stable Baselines Monitor wrapper adds 'episode' key
            if 'episode' in info:
                self.episode_rewards.append(info['episode']['r'])
                self.episode_lengths.append(info['episode']['l'])

                # Print stats every 20 episodes
                if len(self.episode_rewards) % 20 == 0:
                    avg_reward = np.mean(self.episode_rewards[-20:])
                    print(f"Episodes: {len(self.episode_rewards)} | "
                          f"Avg Reward (last 20): {avg_reward:.2f}")
        return True


# ==========================================
# 1. TRAINING FUNCTION
# ==========================================
def train_teacher(total_timesteps=100000):
    """
    Train the PPO agent to be an adaptive teacher.
    """
    print("=" * 60)
    print("  TRAINING ADAPTIVE TEACHING AGENT")
    print("=" * 60)

    # Create vectorized environment
    # We use DummyVecEnv for a single process, but it wraps the env correctly for PPO
    env = make_vec_env(lambda: EdNetEnv(max_steps=50), n_envs=1)

    print("\n--- Initializing PPO Agent ---")
    print("Policy: MlpPolicy (Multi-Layer Perceptron)")
    print("Algorithm: Proximal Policy Optimization")

    # Tuned Hyperparameters for Education
    model = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        learning_rate=0.0003,  # 3e-4 is standard and stable
        gamma=0.99,  # Care about future rewards
        gae_lambda=0.95,  # Smoothed advantage
        ent_coef=0.05,  # <--- CRITICAL: High entropy to prevent "Stubbornness"
        vf_coef=0.5,  # Value function weight
        max_grad_norm=0.5,  # Prevent gradient explosions
        n_steps=2048,  # Collect plenty of data before updating
        batch_size=64,
        tensorboard_log="./ppo_ednet_logs/"
    )

    # Setup callbacks
    reward_callback = RewardLoggingCallback()

    print(f"\n--- Starting Training ({total_timesteps:,} timesteps) ---")
    print("This allows the agent to teach approx. 2,000 students (if episodes=50 steps).")

    # Train
    model.learn(
        total_timesteps=total_timesteps,
        callback=reward_callback,
        progress_bar=True
    )

    print("\n✅ Training Complete!")

    # Save model
    model.save("ppo_ednet_teacher")
    print("Model saved to 'ppo_ednet_teacher.zip'")

    # Plot training progress
    if len(reward_callback.episode_rewards) > 0:
        plot_training_results(reward_callback)

    return model


def plot_training_results(callback):
    plt.figure(figsize=(12, 5))

    # Reward Plot
    plt.subplot(1, 2, 1)
    rewards = callback.episode_rewards
    plt.plot(rewards, alpha=0.3, color='gray', label='Raw Reward')

    # Calculate Moving Average
    window = 20
    if len(rewards) >= window:
        moving_avg = np.convolve(rewards, np.ones(window) / window, mode='valid')
        plt.plot(range(window - 1, len(rewards)), moving_avg, 'b-', linewidth=2, label=f'Moving Avg ({window})')

    plt.xlabel('Episode')
    plt.ylabel('Total Reward')
    plt.title('Learning Curve (Higher is Better)')
    plt.legend()
    plt.grid(True, alpha=0.3)

    # Length Plot (Optional check)
    plt.subplot(1, 2, 2)
    plt.plot(callback.episode_lengths)
    plt.xlabel('Episode')
    plt.ylabel('Steps Taken')
    plt.title('Episode Length (Should stay at 50)')
    plt.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('training_progress.png')
    print("Training plots saved to 'training_progress.png'")
    # plt.show() # Uncomment if running locally with a screen


# ==========================================
# 2. EVALUATION FUNCTION
# ==========================================
def evaluate_teacher(model, n_episodes=20):
    """
    Evaluate the trained agent against baselines.
    """
    print("\n" + "=" * 60)
    print("  EVALUATION: COMPARING TEACHING STRATEGIES")
    print("=" * 60)

    test_env = EdNetEnv(max_steps=50)

    # ===== BASELINE 1: Random Strategy =====
    print("\n[1/3] Testing Random Difficulty Selection...")
    random_rewards = []

    for _ in range(n_episodes):
        obs, _ = test_env.reset()
        episode_reward = 0
        terminated = False
        while not terminated:
            action = test_env.action_space.sample()
            obs, reward, terminated, _, _ = test_env.step(action)
            episode_reward += reward
        random_rewards.append(episode_reward)

    # ===== BASELINE 2: Fixed Medium Difficulty =====
    print("[2/3] Testing Fixed Medium Difficulty (action=5)...")
    fixed_rewards = []

    for _ in range(n_episodes):
        obs, _ = test_env.reset()
        episode_reward = 0
        terminated = False
        while not terminated:
            action = 5  # Always medium difficulty
            obs, reward, terminated, _, _ = test_env.step(action)
            episode_reward += reward
        fixed_rewards.append(episode_reward)

    # ===== TRAINED AI TEACHER =====
    print("[3/3] Testing Trained AI Teacher...")
    ai_rewards = []
    ai_diff_progression = []  # Store one example path

    for i in range(n_episodes):
        obs, _ = test_env.reset()
        episode_reward = 0
        diffs = []
        terminated = False
        while not terminated:
            # Predict action
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, _, info = test_env.step(action)
            episode_reward += reward
            diffs.append(info['chosen_diff'])

        ai_rewards.append(episode_reward)
        if i == 0: ai_diff_progression = diffs  # Save first episode for plotting

    # ===== RESULTS TABLE =====
    print("\n" + "=" * 60)
    print(f"  RESULTS (Average over {n_episodes} episodes)")
    print("=" * 60)
    print(f"{'Strategy':<20} | {'Avg Reward':<10} | {'Std Dev':<10}")
    print("-" * 46)
    print(f"{'Random':<20} | {np.mean(random_rewards):<10.2f} | {np.std(random_rewards):<10.2f}")
    print(f"{'Fixed Medium':<20} | {np.mean(fixed_rewards):<10.2f} | {np.std(fixed_rewards):<10.2f}")
    print(f"{'AI Teacher':<20} | {np.mean(ai_rewards):<10.2f} | {np.std(ai_rewards):<10.2f}")
    print("-" * 46)

    # Check for success
    if np.mean(ai_rewards) > np.mean(random_rewards):
        print("\n🚀 SUCCESS: AI Teacher is smarter than random guessing!")

    # Visualizing Results
    visualize_comparison(random_rewards, fixed_rewards, ai_rewards, ai_diff_progression)


def visualize_comparison(rand, fixed, ai, ai_path):
    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Boxplot
    axes[0].boxplot([rand, fixed, ai], labels=['Random', 'Fixed', 'AI Teacher'])
    axes[0].set_title("Total Reward Distribution")
    axes[0].set_ylabel("Total Score")
    axes[0].grid(True, alpha=0.3)

    # Path Plot
    axes[1].plot(ai_path, marker='o', label='AI Difficulty Path')
    axes[1].axhline(y=0.5, color='r', linestyle='--', alpha=0.5, label='Medium Diff')
    axes[1].fill_between(range(len(ai_path)), 0.6, 0.8, color='green', alpha=0.1, label='Flow Zone')
    axes[1].set_title("AI Adaptive Path (Single Episode)")
    axes[1].set_xlabel("Question Number")
    axes[1].set_ylabel("Difficulty (0-1)")
    axes[1].set_ylim(0, 1)
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('evaluation_results.png')
    print("Evaluation plots saved to 'evaluation_results.png'")
    # plt.show() # Uncomment if local


# ==========================================
# 3. MAIN EXECUTION
# ==========================================
if __name__ == "__main__":

    print("\n--- Project: Adaptive Learning RL System ---")

    if os.path.exists("ppo_ednet_teacher.zip"):
        print("Found existing model.")
        choice = input("Type 'new' to retrain, 'eval' to evaluate, 'cont' to continue training: ").strip().lower()

        if choice == 'new':
            model = train_teacher(total_timesteps=100000)
            evaluate_teacher(model)
        elif choice == 'cont':
            model = PPO.load("ppo_ednet_teacher")
            env = make_vec_env(lambda: EdNetEnv(max_steps=50), n_envs=1)
            model.set_env(env)
            print("Continuing training for 50k steps...")
            model.learn(total_timesteps=50000)
            model.save("ppo_ednet_teacher")
            evaluate_teacher(model)
        else:
            model = PPO.load("ppo_ednet_teacher")
            evaluate_teacher(model)
    else:
        print("No model found. Starting training...")
        model = train_teacher(total_timesteps=100000)
        evaluate_teacher(model)