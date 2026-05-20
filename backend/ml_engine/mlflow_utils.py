import mlflow
import logging
from typing import Dict

logger = logging.getLogger(__name__)

def setup_mlflow(experiment_name: str = "PCB_Automation"):
    """Initializes MLflow tracking settings."""
    try:
        mlflow.set_experiment(experiment_name)
        logger.info(f"MLflow experiment set to: {experiment_name}")
    except Exception as e:
        logger.warning(f"Failed to setup MLflow: {e}")

def log_design_metrics(metrics: Dict[str, float], tags: Dict[str, str] = {}):
    """Logs Design-specific metrics to the active MLflow run."""
    if not mlflow.active_run():
        return
    
    for k, v in metrics.items():
        mlflow.log_metric(k, v)
    
    if tags:
        mlflow.set_tags(tags)

def start_run(run_name: str = "Design_Iteration"):
    """Starts a new MLflow run context."""
    return mlflow.start_run(run_name=run_name)
