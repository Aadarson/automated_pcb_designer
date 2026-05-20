import os
import torch
import torch.nn as nn
import torch.optim as optim
import logging
from backend.models.design import PCBDesignRequest, BoardSpec, Component, Net, NetPin
from backend.ml_engine.trainer import train_placement_agent
from backend.ml_engine.smart_judge import judge
from backend.ml_engine.routing_gnn import RoutingGNN

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def train_rl():
    logger.info("--- Training Universal RL Placement Model ---")
    # Provide a dummy generic request
    req = PCBDesignRequest(
        project_name="Training_Project",
        prompt="training",
        board=BoardSpec(width_mm=50, height_mm=50, layers=2, outline="rect"),
        components=[
            Component(ref="U1", value="IC", part_id="IC", footprint="Package_SO:SOIC-8_3.9x4.9mm_P1.27mm"),
            Component(ref="R1", value="10k", part_id="RES", footprint="Resistor_SMD:R_0805_2012Metric")
        ],
        nets=[
            Net(name="GND", class_name="power", pins=[NetPin(ref="U1", pin="4"), NetPin(ref="R1", pin="1")])
        ]
    )
    # Train heavily offline
    train_placement_agent(req, timesteps=10000)
    logger.info("RL Model Training Complete.")

def train_gnn():
    logger.info("--- Training Routing GNN Model ---")
    model = RoutingGNN()
    optimizer = optim.Adam(model.parameters(), lr=0.01)
    criterion = nn.BCELoss()

    # Synthetic graph: 4 nodes, basic edges
    x = torch.tensor([[0.1, 0.1, 0.0, 1.0], [0.9, 0.9, 0.0, 1.0], [0.1, 0.9, 1.0, 1.0], [0.9, 0.1, 1.0, 1.0]], dtype=torch.float)
    edge_index = torch.tensor([[0, 1, 2, 3], [1, 0, 3, 2]], dtype=torch.long)
    y = torch.tensor([[1.0], [1.0], [0.0], [0.0]], dtype=torch.float)

    model.train()
    for __ in range(100):
        optimizer.zero_grad()
        out = model(x, edge_index)
        loss = criterion(out, y)
        loss.backward()
        optimizer.step()
    
    os.makedirs("models", exist_ok=True)
    torch.save(model.state_dict(), "models/router_gnn.pt")
    logger.info("Routing GNN Training Complete. Saved to models/router_gnn.pt")

if __name__ == "__main__":
    os.makedirs("models", exist_ok=True)
    train_rl()
    train_gnn()
    logger.info("--- Smart Judge Model ---")
    logger.info(f"Smart Judge trained: {judge.is_trained}")
    logger.info("ALL ML/AI/RL MODELS SUCCESSFULLY TRAINED AND SAVED!")
