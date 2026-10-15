import os
import json
import time
import torch
import torch.nn as nn
import torch.optim as optim

LOG_FILE = "/Volumes/Lauburu-Monorepo/03_biometrics_and_telemetry/movesense_pull/live_movesense_mds_stream.log"
CHECKPOINT_DIR = "/Volumes/Lauburu-Monorepo/04_data_and_memory/data/movesense_checkpoints/"

os.makedirs(CHECKPOINT_DIR, exist_ok=True)

class TinyECGAutoencoder(nn.Module):
    def __init__(self, seq_len=128):
        super(TinyECGAutoencoder, self).__init__()
        self.encoder = nn.Sequential(
            nn.Conv1d(1, 16, kernel_size=3, stride=2, padding=1),
            nn.ReLU(),
            nn.Conv1d(16, 8, kernel_size=3, stride=2, padding=1),
            nn.ReLU()
        )
        self.decoder = nn.Sequential(
            nn.ConvTranspose1d(8, 16, kernel_size=3, stride=2, padding=1, output_padding=1),
            nn.ReLU(),
            nn.ConvTranspose1d(16, 1, kernel_size=3, stride=2, padding=1, output_padding=1),
            nn.Tanh()
        )

    def forward(self, x):
        encoded = self.encoder(x)
        decoded = self.decoder(encoded)
        return decoded

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
            payload = json.loads(json_str)
            # Movesense ECG streams typically contain a "Body" with "Array" or "Samples"
            body = payload.get("Body", payload)
            for key in ["Array", "Samples", "Data", "array", "samples", "data"]:
                if key in body and isinstance(body[key], list):
                    # Ensure they are numbers
                    return [float(x) for x in body[key] if isinstance(x, (int, float))]
    except Exception:
        pass
    return None

def train():
    device = torch.device("cpu")
    model = TinyECGAutoencoder(seq_len=128).to(device)
    optimizer = optim.Adam(model.parameters(), lr=1e-3)
    criterion = nn.MSELoss()

    buffer = []
    
    print(f"Starting continuous training on {LOG_FILE}...")
    try:
        with open(LOG_FILE, "r") as f:
            loglines = follow(f)
            for line in loglines:
                samples = parse_log_line(line)
                if samples is not None and len(samples) > 0:
                    for val in samples:
                        norm_val = (val - 100.0) / 100.0
                        buffer.append(norm_val)
                        
                        if len(buffer) == 128:
                            tensor_data = torch.tensor(buffer, dtype=torch.float32).unsqueeze(0).unsqueeze(0).to(device)
                            
                            optimizer.zero_grad()
                            output = model(tensor_data)
                            loss = criterion(output, tensor_data)
                            loss.backward()
                            optimizer.step()
                            
                            print(f"Trained on window. Loss: {loss.item():.4f}")
                            
                            buffer = []
                            
                            pt_path = os.path.join(CHECKPOINT_DIR, "movesense_tiny_ae.pt")
                            torch.save(model.state_dict(), pt_path)
                            
                            onnx_path = os.path.join(CHECKPOINT_DIR, "movesense_tiny_ae.onnx")
                            torch.onnx.export(model, tensor_data, onnx_path, export_params=True, opset_version=10)
    except FileNotFoundError:
        print(f"File not found: {LOG_FILE}")
    except KeyboardInterrupt:
        print("Training interrupted.")

if __name__ == "__main__":
    train()
