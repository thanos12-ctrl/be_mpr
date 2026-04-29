import gymnasium as gym
from stable_baselines3 import PPO
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.callbacks import BaseCallback
import numpy as np
import os
from ednet_env import EdNetEnv

class RewardLoggingCallback(BaseCallback):
    def __init__(self, verbose=0):
        super(RewardLoggingCallback, self).__init__(verbose)
        self.episode_rewards = []
        self.episode_lengths = []

    def _on_step(self) -> bool:
        if self.locals.get('dones')[0]:
            infos = self.locals.get('infos', [{}])
            info = infos[0]
            if 'episode' in info:
                self.episode_rewards.append(info['episode']['r'])
                self.episode_lengths.append(info['episode']['l'])
                if len(self.episode_rewards) % 20 == 0:
                    avg_reward = np.mean(self.episode_rewards[-20:])
                    print(f"Episodes: {len(self.episode_rewards)} | Avg Reward (last 20): {avg_reward:.2f}")
        return True

def train_general_teacher(total_timesteps=100000):
    print("=" * 60)
    print("  TRAINING DOMAIN-AGNOSTIC ADAPTIVE AGENT")
    print("=" * 60)

    env = make_vec_env(lambda: EdNetEnv(max_steps=50), n_envs=1)

    model = PPO(
        "MlpPolicy",
        env,
        verbose=1,
        learning_rate=0.0003,
        gamma=0.99,
        gae_lambda=0.95,
        ent_coef=0.08, # Increased entropy to encourage trying module switches
        vf_coef=0.5,
        max_grad_norm=0.5,
        n_steps=2048,
        batch_size=64,
        tensorboard_log="./ppo_general_logs/"
    )

    reward_callback = RewardLoggingCallback()

    model.learn(
        total_timesteps=total_timesteps,
        callback=reward_callback,
        progress_bar=True
    )

    model.save("ppo_general_teacher")
    print("Model saved to 'ppo_general_teacher.zip'")

if __name__ == "__main__":
    train_general_teacher(total_timesteps=100000)
