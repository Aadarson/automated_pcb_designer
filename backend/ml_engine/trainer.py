import os
import logging
import gymnasium as gym
from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from backend.ml_engine.environments.pcb_placement_env import PCBPlacementEnv
from backend.models.design import PCBDesignRequest
from backend.ml_engine import mlflow_utils

logger = logging.getLogger(__name__)

class MLflowCallback(BaseCallback):
    def __init__(self, verbose=0):
        super(MLflowCallback, self).__init__(verbose)

    def _on_step(self) -> bool:
        return True

def train_placement_agent(request: PCBDesignRequest, timesteps: int = 5000, initial_placements=None):
    """
    Trains the Universal PPO agent.
    """
    logger.info(f"Starting Universal RL training for {timesteps} steps...")
    
    env = PCBPlacementEnv(request=request, initial_placements=initial_placements)
    model_path = "models/ppo_pcb_universal"

    
    if os.path.exists(f"{model_path}.zip"):
        logger.info(f"Loading existing Universal PPO model for fine-tuning...")
        model = PPO.load(model_path, env=env)
    else:
        logger.info(f"Initializing new Universal PPO model...")
        model = PPO("MlpPolicy", env, verbose=0)

    model.learn(total_timesteps=timesteps, callback=MLflowCallback())
    
    os.makedirs("models", exist_ok=True)
    model.save(model_path)
    logger.info(f"Universal PPO model saved to {model_path}")
    
    return model

def get_rl_placement(request: PCBDesignRequest, initial_placements=None):
    """
    Uses the Universal RL agent to refine component placement.
    If the model doesn't exist, performs a quick synchronous 100-step training pass.
    """
    env = PCBPlacementEnv(request=request, initial_placements=initial_placements)
    model_path = "models/ppo_pcb_universal"
    
    if not os.path.exists(f"{model_path}.zip"):
        logger.warning(f"Universal RL model missing! Compiling and bootstrapping (100 steps) for instant use...")
        train_placement_agent(request, timesteps=100, initial_placements=initial_placements)

    try:
        model = PPO.load(model_path, env=env)
    except Exception as e:
        logger.error(f"Failed to load Universal RL model {model_path}: {e}")
        return None

    obs, _ = env.reset()
    
    # Run 200 refinement steps
    for _ in range(200):
        action, _states = model.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = env.step(action)
        if terminated or truncated: break
    
    from backend.design_engine.placement import PlacedComponent
    placements = []
    boxes = obs.reshape(-1, 4)
    # Only map back the active components
    for i in range(env.num_components):
        p = boxes[i]
        comp = request.components[i]
        c_data = env.comp_data[i]
        placements.append(PlacedComponent(
            ref=comp.ref, 
            x=float(p[0]), 
            y=float(p[1]), 
            rotation=0.0, 
            layer="F.Cu",
            footprint=comp.footprint,
            w=c_data["w"],
            h=c_data["h"],
            cx=c_data["cx"],
            cy=c_data["cy"]
        ))
    
    return placements
