import gymnasium as gym
import torch
import os
from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import SubprocVecEnv, DummyVecEnv
from stable_baselines3.common.callbacks import CheckpointCallback

# Import your custom environment
from ednet_env import EdNetEnv


def make_env():
    """
    Utility function for multiprocessed env.
    """

    def _init():
        env = EdNetEnv()
        return env

    return _init


def train_parallel_teacher():
    print("--- 🚀 INITIALIZING PARALLEL TRAINING SETUP ---")

    # 1. CONFIGURE PARALLELISM
    # How many CPU cores do you have? (Leave 1-2 free for the OS)
    # If you have 8 cores, use 6. If 16, use 12.
    num_cpu = os.cpu_count()
    n_envs = max(1, num_cpu - 2)

    print(f"Detected {num_cpu} Cores. Launching {n_envs} Parallel Classrooms...")

    # 2. CREATE VECTORIZED ENVIRONMENT
    # 'SubprocVecEnv' runs each env in a separate process (True Parallelism)
    # This acts like a batch: The agent receives 12 observations at once.
    env = make_vec_env(
        EdNetEnv,
        n_envs=n_envs,
        vec_env_cls=SubprocVecEnv
    )

    # 3. CONFIGURE HYPERPARAMETERS FOR BATCHED LEARNING
    print("--- Initializing PPO Agent ---")

    model = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        learning_rate=0.0003,
        gamma=0.99,
        ent_coef=0.05,  # Force exploration (The fix for stubbornness)
        batch_size=256,  # Larger batch size for stable updates
        n_steps=2048,  # Steps to collect per env before updating
        device="cuda" if torch.cuda.is_available() else "cpu"
    )

    # 4. START TRAINING
    # 500k steps in parallel is much faster than 50k serial steps.
    # Total interactions = n_envs * steps
    total_timesteps = 500000

    print(f"--- Starting Training ({total_timesteps} Steps) ---")
    model.learn(total_timesteps=total_timesteps)

    print("\n✅ Parallel Training Complete.")
    model.save("ppo_ednet_teacher_parallel")
    print("Saved model to 'ppo_ednet_teacher_parallel.zip'")

    return model


if __name__ == "__main__":
    # Windows requires this check for multiprocessing
    train_parallel_teacher()