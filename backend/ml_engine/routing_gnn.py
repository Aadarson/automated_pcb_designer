import torch
import torch.nn as nn
import torch.nn.functional as F
from torch_geometric.nn import GCNConv, global_mean_pool
import logging

logger = logging.getLogger(__name__)

class RoutingGNN(nn.Module):
    """
    A simple GNN to predict routing 'corridors' for PCB nets.
    Input: Graph nodes (pins/cells), Edges (net connectivity).
    Output: Probability/Heuristic value for each node.
    """
    def __init__(self, in_channels=4, hidden_channels=32, out_channels=1):
        super(RoutingGNN, self).__init__()
        self.conv1 = GCNConv(in_channels, hidden_channels)
        self.conv2 = GCNConv(hidden_channels, hidden_channels)
        self.conv3 = GCNConv(hidden_channels, out_channels)

    def forward(self, x, edge_index):
        # x shape: [num_nodes, in_channels] (e.g., [x, y, net_id, is_pin])
        x = self.conv1(x, edge_index)
        x = F.relu(x)
        x = self.conv2(x, edge_index)
        x = F.relu(x)
        x = self.conv3(x, edge_index)
        return torch.sigmoid(x)

def get_routing_suggestions(board_w, board_h, nets, placements):
    """
    Constructs a graph from the current design and runs the GNN to get routing suggestions.
    In Phase 2, we use a pre-trained (dummy) model to demonstrate the pipeline integration.
    """
    # 1. Build Node Features
    # For simplicity: nodes are pins of all nets
    nodes = []
    edges = []
    pos_map = {p.ref: (p.x, p.y) for p in placements}
    
    net_to_nodes = {}
    for net_idx, net in enumerate(nets):
        net_to_nodes[net.name] = []
        for pin in net.pins:
            if pin.ref in pos_map:
                x, y = pos_map[pin.ref]
                nodes.append([x/board_w, y/board_h, net_idx/len(nets), 1.0])
                net_to_nodes[net.name].append(len(nodes) - 1)

    # 2. Build Edges (Clique per net)
    for net_name, node_indices in net_to_nodes.items():
        for i in range(len(node_indices)):
            for j in range(i + 1, len(node_indices)):
                edges.append([node_indices[i], node_indices[j]])
                edges.append([node_indices[j], node_indices[i]])

    if not nodes: return {}

    x = torch.tensor(nodes, dtype=torch.float)
    edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous() if edges else torch.empty((2, 0), dtype=torch.long)
    
    # 3. Predict (Forward pass)
    model = RoutingGNN()
    # model.load_state_dict(...) # In real life, load weights
    model.eval()
    
    with torch.no_grad():
        preds = model(x, edge_index)
    
    # Map predictions back to (x, y) coordinates for the router
    # In Phase 2, we provide a dictionary of 'bonus' hotspots
    suggestions = {}
    for i, p in enumerate(preds):
        coord = (int(nodes[i][0] * board_w * 10), int(nodes[i][1] * board_h * 10))
        suggestions[coord] = float(p[0])
        
    return suggestions
