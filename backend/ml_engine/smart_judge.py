import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
import logging
import pickle
import os

logger = logging.getLogger(__name__)

class DesignJudge:
    def __init__(self):
        self.model = RandomForestClassifier(n_estimators=10)
        self.is_trained = False
        self._load_or_train_synthetic()

    def _load_or_train_synthetic(self):
        """Mock learning from past designs: Train a synthetic model if no state exists."""
        # Simple features: [num_comp, num_nets, density, avg_ratsnest_dist]
        # Label: 1 (Easy), 0 (Difficult/Risky)
        synthetic_data = [
            [2, 2, 0.01, 10.0, 1], # Small, simple -> Easy
            [5, 5, 0.1, 50.0, 1],
            [10, 10, 0.2, 100.0, 1],
            [50, 40, 0.8, 500.0, 0], # Dense, many nets -> Difficult
            [20, 25, 0.6, 300.0, 0],
        ]
        X = np.array([d[:4] for d in synthetic_data])
        y = np.array([d[4] for d in synthetic_data])
        
        self.model.fit(X, y)
        self.is_trained = True
        logger.info("SmartJudge: Initialized with synthetic training data.")

    def judge_placement(self, components, nets, placements, board_spec):
        """
        Rank the current placement quality using the ML model.
        Returns: Score (0.0 to 1.0), and Status ('good', 'risky')
        """
        num_comp = len(components)
        num_nets = len(nets)
        area = board_spec.width_mm * board_spec.height_mm
        density = (num_comp * 25.0) / area if area > 0 else 1.0 # approx 5x5mm per comp
        
        # Calculate avg ratsnest
        total_ratsnest = 0.0
        pos_map = {p.ref: (p.x, p.y) for p in placements}
        for net in nets:
            if len(net.pins) < 2: continue
            pins = [pos_map[pin.ref] for pin in net.pins if pin.ref in pos_map]
            if pins:
                cx = sum(p[0] for p in pins) / len(pins)
                cy = sum(p[1] for p in pins) / len(pins)
                total_ratsnest += sum(abs(p[0]-cx) + abs(p[1]-cy) for p in pins)
        
        avg_ratsnest = total_ratsnest / num_nets if num_nets > 0 else 0.0
        
        features = np.array([[num_comp, num_nets, density, avg_ratsnest]])
        prob = self.model.predict_proba(features)[0][1] # Probability of 'Easy' (Success)
        
        status = "good" if prob > 0.6 else "risky"
        logger.info(f"SmartJudge: Predicted routability score: {prob:.2f} ({status})")
        
        return prob, status

judge = DesignJudge()
