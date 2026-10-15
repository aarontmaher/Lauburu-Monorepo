import torch
import torch.nn as nn
import torch.optim as optim
import json
import os

class TinyEloSpecialist(nn.Module):
    def __init__(self):
        super().__init__()
        # Learnable K-factor and scale
        self.k_factor = nn.Parameter(torch.tensor(32.0))
        self.scale = nn.Parameter(torch.tensor(400.0))
        
    def forward(self, elo_a, elo_b, outcome_a):
        """
        outcome_a: 1.0 if A wins, 0.0 if B wins, 0.5 for draw
        """
        # Bradley-Terry predicted win probability for A
        prob_a = 1.0 / (1.0 + torch.pow(10.0, (elo_b - elo_a) / self.scale))
        
        # New ELOs
        new_elo_a = elo_a + self.k_factor * (outcome_a - prob_a)
        new_elo_b = elo_b + self.k_factor * ((1.0 - outcome_a) - (1.0 - prob_a))
        
        return new_elo_a, new_elo_b, prob_a

def train_specialist(battles):
    model = TinyEloSpecialist()
    optimizer = optim.Adam(model.parameters(), lr=1.0)
    criterion = nn.BCELoss()
    
    print("Training TinyML ELO Specialist...")
    for epoch in range(100):
        total_loss = 0
        for elo_a, elo_b, outcome in battles:
            optimizer.zero_grad()
            
            elo_a_t = torch.tensor(float(elo_a))
            elo_b_t = torch.tensor(float(elo_b))
            outcome_t = torch.tensor(float(outcome))
            
            _, _, prob_a = model(elo_a_t, elo_b_t, outcome_t)
            
            loss = criterion(prob_a, outcome_t)
            loss.backward()
            optimizer.step()
            total_loss += loss.item()
            
        if (epoch + 1) % 20 == 0:
            print(f"Epoch {epoch+1}, Loss: {total_loss/len(battles):.4f}, K: {model.k_factor.item():.2f}, Scale: {model.scale.item():.2f}")
            
    # Save the model
    os.makedirs(os.path.dirname(os.path.abspath(__file__)), exist_ok=True)
    model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tiny_elo_specialist.pth")
    torch.save(model.state_dict(), model_path)
    return model

def load_battles_from_leaderboard():
    leaderboard_path = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/data/canonical_elo_leaderboard.json"
    if not os.path.exists(leaderboard_path):
        leaderboard_path = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/data/canonical_ai_leaderboard.json"
    battles = []
    if os.path.exists(leaderboard_path):
        with open(leaderboard_path, "r") as f:
            data = json.load(f)
            models = list(data.get("models", {}).values())
            # synthesize battles based on win rates
            for i in range(len(models)):
                for j in range(i + 1, len(models)):
                    elo_a = models[i].get("elo", 1500)
                    elo_b = models[j].get("elo", 1500)
                    win_rate_a = models[i].get("win_rate_pct", 50) / 100.0
                    win_rate_b = models[j].get("win_rate_pct", 50) / 100.0
                    
                    # If A has higher win rate, simulate A winning more often
                    if win_rate_a > win_rate_b:
                        battles.append((elo_a, elo_b, 1.0))
                    elif win_rate_b > win_rate_a:
                        battles.append((elo_a, elo_b, 0.0))
                    else:
                        battles.append((elo_a, elo_b, 0.5))
    if not battles:
        print("Fallback: Using dummy battles")
        battles = [
            (1500, 1500, 1),
            (1600, 1500, 1),
            (1500, 1600, 0),
            (2000, 1500, 1),
            (1500, 2000, 0)
        ] * 10
    return battles

if __name__ == "__main__":
    battles = load_battles_from_leaderboard()
    train_specialist(battles)
