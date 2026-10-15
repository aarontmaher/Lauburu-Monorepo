import os
import json
import time
import torch
import torch.nn as nn
import torch.optim as optim
import fcntl

LOG_FILE = "/Volumes/Lauburu-Monorepo/03_biometrics_and_telemetry/movesense_pull/live_movesense_mds_stream.log"
CHECKPOINT_DIR = "/Volumes/Lauburu-Monorepo/04_data_and_memory/data/movesense_checkpoints/generations/"
LEADERBOARD = "/Volumes/Lauburu-Monorepo/04_data_and_memory/data/canonical_elo_leaderboard.json"

os.makedirs(CHECKPOINT_DIR, exist_ok=True)

# 1. Nano Tier (≤ 1M params, ultra-fast convergence, plateaus early)
class NanoECG(nn.Module):
    def __init__(self):
        super(NanoECG, self).__init__()
        self.encoder = nn.Sequential(nn.Conv1d(1, 4, 3, 2, 1), nn.ReLU())
        self.decoder = nn.Sequential(nn.ConvTranspose1d(4, 1, 3, 2, 1, 1), nn.Tanh())
    def forward(self, x): return self.decoder(self.encoder(x))

# 2. Tiny Tier (~10-20M params, good middle ground)
class TinyECG(nn.Module):
    def __init__(self):
        super(TinyECG, self).__init__()
        self.encoder = nn.Sequential(nn.Conv1d(1, 16, 3, 2, 1), nn.ReLU(), nn.Conv1d(16, 8, 3, 2, 1), nn.ReLU())
        self.decoder = nn.Sequential(nn.ConvTranspose1d(8, 16, 3, 2, 1, 1), nn.ReLU(), nn.ConvTranspose1d(16, 1, 3, 2, 1, 1), nn.Tanh())
    def forward(self, x): return self.decoder(self.encoder(x))

# 3. Mini Tier (~100M+ params, slower convergence but high latent capacity)
class MiniECG(nn.Module):
    def __init__(self):
        super(MiniECG, self).__init__()
        self.encoder = nn.Sequential(nn.Conv1d(1, 64, 3, 2, 1), nn.ReLU(), nn.Conv1d(64, 128, 3, 2, 1), nn.ReLU())
        self.decoder = nn.Sequential(nn.ConvTranspose1d(128, 64, 3, 2, 1, 1), nn.ReLU(), nn.ConvTranspose1d(64, 1, 3, 2, 1, 1), nn.Tanh())
    def forward(self, x): return self.decoder(self.encoder(x))

class GenerationalTrainer:
    def __init__(self):
        self.device = torch.device("cpu")
        
        self.generations = {
            "Nano_ECG_0.1M": {"model": NanoECG().to(self.device), "lr": 5e-3, "loss": 0.0},
            "Tiny_ECG_15M":  {"model": TinyECG().to(self.device), "lr": 1e-3, "loss": 0.0},
            "Mini_ECG_120M": {"model": MiniECG().to(self.device), "lr": 1e-4, "loss": 0.0},
        }
        
        self.optimizers = {
            name: optim.Adam(gen["model"].parameters(), lr=gen["lr"]) 
            for name, gen in self.generations.items()
        }
        self.criterion = nn.MSELoss()

    def load_leaderboard(self):
        if not os.path.exists(LEADERBOARD):
            os.makedirs(os.path.dirname(LEADERBOARD), exist_ok=True)
            return {"models": {}}
        with open(LEADERBOARD, "r") as f:
            try: return json.load(f)
            except: return {"models": {}}

    def update_elo(self):
        board = self.load_leaderboard()
        with open(LEADERBOARD, 'r+') as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            
            # Map Loss directly to ELO (lower loss = higher ELO)
            # Baseline: 1000 ELO = 1.0 Loss. ELO = 1000 + ((1.0 - Loss) * 500)
            print("\n[Generational Leaderboard Update]")
            for name, gen in self.generations.items():
                if gen["loss"] > 0:
                    new_elo = max(400, int(1000 + ((1.0 - gen["loss"]) * 500)))
                    board["models"][name] = {"elo": new_elo, "matches": board["models"].get(name, {}).get("matches", 0) + 1}
                    print(f" -> {name}: Loss {gen['loss']:.4f} | ELO {new_elo}")
            
            f.seek(0)
            json.dump(board, f, indent=2)
            f.truncate()
            fcntl.flock(f, fcntl.LOCK_UN)

    def train_step(self, tensor_data):
        for name, gen in self.generations.items():
            model = gen["model"]
            opt = self.optimizers[name]
            
            opt.zero_grad()
            output = model(tensor_data)
            loss = self.criterion(output, tensor_data)
            loss.backward()
            opt.step()
            
            gen["loss"] = loss.item()
            
            # Save checkpoint
            pt_path = os.path.join(CHECKPOINT_DIR, f"{name}.pt")
            torch.save(model.state_dict(), pt_path)

def follow(thefile):
    thefile.seek(0, 2)
    while True:
        line = thefile.readline()
        if not line:
            time.sleep(0.1)
            continue
        yield line

def parse_log_line(line):
    try:
        if "{" in line:
            json_str = line[line.find("{"):]
            import json
            payload = json.loads(json_str)
            body = payload.get("Body", payload)
            for key in ["Array", "Samples", "Data", "array", "samples", "data"]:
                if key in body and isinstance(body[key], list):
                    return [float(x) for x in body[key] if isinstance(x, (int, float))]
    except Exception:
        pass
    return None

def main():
    trainer = GenerationalTrainer()
    buffer = []
    print(f"Initiating Generational Parallel Training (Nano, Tiny, Mini) on CPU...")
    
    step_count = 0
    try:
        with open(LOG_FILE, "r") as f:
            loglines = follow(f)
            for line in loglines:
                samples = parse_log_line(line)
                if samples and len(samples) > 0:
                    for val in samples:
                        norm_val = (val - 100.0) / 100.0
                        buffer.append(norm_val)
                        
                        if len(buffer) == 128:
                            tensor_data = torch.tensor(buffer, dtype=torch.float32).unsqueeze(0).unsqueeze(0).to(trainer.device)
                            trainer.train_step(tensor_data)
                            step_count += 1
                            
                            if step_count % 10 == 0:
                                trainer.update_elo()
                            buffer = []
    except FileNotFoundError:
        print(f"File not found: {LOG_FILE}. Ensure the Bluetooth stream is running.")

if __name__ == "__main__":
    main()
