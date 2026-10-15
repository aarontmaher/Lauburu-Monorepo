#!/usr/bin/env python3
"""
Movesense Kinematic & Cardiac Physical Silicon Neural Network Trainer
Trains a temporal 1D-CNN + GRU model on authentic Movesense 9-axis movement and ECG telemetry.
Follows Rule 1: Zero-Mock Empirical Truth (Physical Silicon Gradient Steps on Apple Silicon Metal MPS).
"""

import os
import sys
import json
import sqlite3
import hashlib
import time
import numpy as np

# Ensure execution under PyTorch virtual environment if available
try:
    import torch
    import torch.nn as nn
    from torch.utils.data import TensorDataset, DataLoader
except ImportError:
    venv_py = "/Users/aaron/primary_workstation_venv/bin/python3"
    if os.path.exists(venv_py) and sys.executable != venv_py:
        os.execv(venv_py, [venv_py] + sys.argv)
    raise

DB_PATH = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/grappling_history.db"
MODEL_DIR = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/models"
METRICS_PATH = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/models/movesense_model_metrics.json"

os.makedirs(MODEL_DIR, exist_ok=True)

class TemporalKinematicCardiacNet(nn.Module):
    """
    1D Temporal Convolution + Recurrent Network for Movement & Cardiac Exertion Prediction.
    Input shape: (batch_size, channels=8, window_size=32)
    """
    def __init__(self, in_channels=8, hidden_dim=64, num_classes=3):
        super().__init__()
        self.conv1 = nn.Conv1d(in_channels, 32, kernel_size=3, padding=1)
        self.bn1 = nn.BatchNorm1d(32)
        self.relu = nn.ReLU()
        self.pool = nn.MaxPool1d(kernel_size=2)
        
        self.conv2 = nn.Conv1d(32, 64, kernel_size=3, padding=1)
        self.bn2 = nn.BatchNorm1d(64)
        
        # Recurrent layer over downsampled sequence
        self.gru = nn.GRU(64, hidden_dim, batch_first=True, bidirectional=True)
        
        # Classification head: 0 = Low/Resting, 1 = Moderate/Aerobic, 2 = High-Intensity Grappling
        self.classifier = nn.Sequential(
            nn.Linear(hidden_dim * 2, 32),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(32, num_classes)
        )
        
        # Regression head: Predicted Heart Rate (BPM)
        self.hr_regressor = nn.Sequential(
            nn.Linear(hidden_dim * 2, 32),
            nn.ReLU(),
            nn.Linear(32, 1)
        )

    def forward(self, x):
        # x: (B, C, L)
        out = self.pool(self.relu(self.bn1(self.conv1(x))))
        out = self.pool(self.relu(self.bn2(self.conv2(out))))
        # Permute for GRU: (B, L_down, C_down)
        out = out.permute(0, 2, 1)
        gru_out, _ = self.gru(out)
        # Take the last time step
        last_hidden = gru_out[:, -1, :]
        logits = self.classifier(last_hidden)
        hr_pred = self.hr_regressor(last_hidden)
        return logits, hr_pred.squeeze(-1)

def load_authentic_movesense_data(limit=100000, window_size=32, step=16):
    """
    Loads 100% authentic IMU and cardiac data recorded from physical Movesense sensors.
    Strictly complies with Rule 1: Zero-Mock Empirical Truth.
    Joins physical 9-axis IMU kinematic frames with recorded RR-interval heart rate (BPM).
    """
    print(f">>> [1/4] Loading authentic Movesense telemetry from Parquet / SQLite...")
    import pandas as pd
    parquet_dir = os.path.join(os.path.dirname(DB_PATH), "movesense_parquet")
    imu_parquet = os.path.join(parquet_dir, "grappling_imu_telemetry.parquet")
    rr_parquet = os.path.join(parquet_dir, "grappling_rr_intervals.parquet")
    
    loaded_parquet = False
    if os.path.exists(imu_parquet) and os.path.exists(rr_parquet):
        try:
            imu_df = pd.read_parquet(imu_parquet)
            rr_df = pd.read_parquet(rr_parquet)
            loaded_parquet = True
        except Exception as e:
            print(f"  (Parquet engine not available in venv, falling back to SQLite: {e})")

    if not loaded_parquet:
        conn = sqlite3.connect(DB_PATH)
        imu_df = pd.read_sql_query("SELECT timestamp, acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z, g_force FROM imu_motion_telemetry", conn)
        rr_df = pd.read_sql_query("SELECT timestamp, bpm, rr_ms FROM rr_interval_history", conn)
        conn.close()
        imu_df["acc_mag"] = np.sqrt(imu_df["acc_x"]**2 + imu_df["acc_y"]**2 + imu_df["acc_z"]**2)

    # Convert timestamps to exact epoch seconds for synchronization
    imu_df["epoch_sec"] = pd.to_datetime(imu_df["timestamp"]).values.astype("datetime64[s]").astype("int64")
    rr_df["epoch_sec"] = pd.to_datetime(rr_df["timestamp"]).values.astype("datetime64[s]").astype("int64")

    # Aggregate authentic cardiac ground truth per second
    cardiac = rr_df.groupby("epoch_sec")["bpm"].mean().reset_index()
    merged = pd.merge(imu_df, cardiac, on="epoch_sec", how="inner")
    
    if len(merged) < window_size * 10:
        raise ValueError(f"Insufficient synchronized authentic rows ({len(merged)}) to train.")

    if limit and len(merged) > limit:
        merged = merged.iloc[:limit]

    print(f"  ✓ Synchronized {len(merged):,} authentic IMU frames with physical Movesense HR telemetry.")

    feature_cols = ["acc_x", "acc_y", "acc_z", "gyro_x", "gyro_y", "gyro_z", "g_force", "acc_mag"]
    raw_features = merged[feature_cols].values.astype(np.float32)
    raw_bpm = merged["bpm"].values.astype(np.float32)

    # Standardize input features
    mean = np.mean(raw_features, axis=0)
    std = np.std(raw_features, axis=0) + 1e-6
    data_norm = (raw_features - mean) / std

    # Create temporal sliding windows with genuine physiological targets
    X_list = []
    y_class_list = []
    y_hr_list = []

    for i in range(0, len(data_norm) - window_size, step):
        window = data_norm[i:i+window_size].T  # (8, window_size)
        win_bpm = float(np.mean(raw_bpm[i:i+window_size]))
        
        # Physiological exertion categorization based on authentic recorded BPM:
        # Class 0: Low / Resting recovery (< 75 BPM)
        # Class 1: Moderate Aerobic Exertion (75 <= BPM < 100)
        # Class 2: High Cardiovascular Exertion / Active Grappling (>= 100 BPM)
        if win_bpm < 75.0:
            cls = 0
        elif win_bpm < 100.0:
            cls = 1
        else:
            cls = 2

        X_list.append(window)
        y_class_list.append(cls)
        y_hr_list.append(win_bpm)

    X = torch.tensor(np.array(X_list), dtype=torch.float32)
    y_class = torch.tensor(np.array(y_class_list), dtype=torch.long)
    y_hr = torch.tensor(np.array(y_hr_list), dtype=torch.float32)

    print(f"  ✓ Prepared {len(X):,} authentic temporal windows of shape {list(X.shape[1:])}")
    print(f"  ✓ Authentic BPM range: [{float(y_hr.min()):.1f}, {float(y_hr.max()):.1f}] BPM")
    return X, y_class, y_hr

def train():
    print("=================================================================")
    print("Movesense Physical Silicon Neural Network Training (Rule 1 Truth)")
    print("=================================================================")
    
    # Detect physical silicon
    if torch.backends.mps.is_available():
        device = torch.device("mps")
        device_name = "Apple Silicon Metal (MPS)"
    elif torch.cuda.is_available():
        device = torch.device("cuda:0")
        device_name = torch.cuda.get_device_name(0)
    else:
        device = torch.device("cpu")
        device_name = "Host CPU"
        
    print(f"Target Silicon Device: {device} ({device_name})")
    
    X, y_class, y_hr = load_authentic_movesense_data(limit=30000, window_size=32)
    
    # Split train/val
    n_samples = len(X)
    n_train = int(n_samples * 0.8)
    
    train_dataset = TensorDataset(X[:n_train], y_class[:n_train], y_hr[:n_train])
    val_dataset = TensorDataset(X[n_train:], y_class[n_train:], y_hr[n_train:])
    
    train_loader = DataLoader(train_dataset, batch_size=64, shuffle=True)
    val_loader = DataLoader(val_dataset, batch_size=64, shuffle=False)
    
    print(">>> [2/4] Initializing TemporalKinematicCardiacNet...")
    model = TemporalKinematicCardiacNet().to(device)
    
    criterion_cls = nn.CrossEntropyLoss()
    criterion_hr = nn.MSELoss()
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    
    print(f">>> [3/4] Commencing genuine physical gradient updates on {device}...")
    start_time = time.time()
    num_epochs = 5
    history = []
    
    for epoch in range(1, num_epochs + 1):
        model.train()
        running_cls_loss = 0.0
        running_hr_loss = 0.0
        correct = 0
        total = 0
        
        for batch_x, batch_cls, batch_hr in train_loader:
            batch_x = batch_x.to(device)
            batch_cls = batch_cls.to(device)
            batch_hr = batch_hr.to(device)
            
            optimizer.zero_grad()
            logits, hr_pred = model(batch_x)
            
            loss_cls = criterion_cls(logits, batch_cls)
            loss_hr = criterion_hr(hr_pred, batch_hr)
            total_loss = loss_cls + 0.05 * loss_hr
            
            total_loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            
            running_cls_loss += loss_cls.item() * len(batch_cls)
            running_hr_loss += loss_hr.item() * len(batch_hr)
            
            preds = logits.argmax(dim=-1)
            correct += (preds == batch_cls).sum().item()
            total += len(batch_cls)
            
        epoch_cls_loss = running_cls_loss / total
        epoch_hr_loss = running_hr_loss / total
        epoch_acc = (correct / total) * 100.0
        
        # Validation
        model.eval()
        val_correct = 0
        val_total = 0
        with torch.no_grad():
            for vx, vcls, vhr in val_loader:
                vx, vcls = vx.to(device), vcls.to(device)
                vlogits, _ = model(vx)
                vpreds = vlogits.argmax(dim=-1)
                val_correct += (vpreds == vcls).sum().item()
                val_total += len(vcls)
        val_acc = (val_correct / val_total) * 100.0
        
        print(f"  Epoch {epoch}/{num_epochs} [{device_name}] - "
              f"Cls Loss: {epoch_cls_loss:.4f} | HR MSE: {epoch_hr_loss:.2f} | "
              f"Train Acc: {epoch_acc:.1f}% | Val Acc: {val_acc:.1f}%")
              
        history.append({
            "epoch": epoch,
            "train_cls_loss": float(epoch_cls_loss),
            "train_hr_mse": float(epoch_hr_loss),
            "train_acc_pct": float(epoch_acc),
            "val_acc_pct": float(val_acc)
        })
        
    duration = time.time() - start_time
    print(f"\n✓ Training completed in {duration:.2f} seconds on physical silicon.")
    
    # Save model weights
    save_path = os.path.join(MODEL_DIR, "movesense_kinematic_cardiac_net.pt")
    torch.save(model.state_dict(), save_path)
    file_bytes = os.path.getsize(save_path)
    
    with open(save_path, "rb") as f:
        sha256 = hashlib.sha256(f.read()).hexdigest()
        
    print(f">>> [4/4] Model artifact saved to: {save_path}")
    print(f"  Bytes: {file_bytes:,} | SHA256: {sha256}")
    
    metrics = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "device": str(device),
        "device_name": device_name,
        "training_duration_sec": round(duration, 2),
        "total_windows": n_samples,
        "epochs": num_epochs,
        "final_train_acc_pct": round(history[-1]["train_acc_pct"], 2),
        "final_val_acc_pct": round(history[-1]["val_acc_pct"], 2),
        "artifact_path": save_path,
        "artifact_bytes": file_bytes,
        "artifact_sha256": sha256,
        "history": history
    }
    
    with open(METRICS_PATH, "w") as f:
        json.dump(metrics, f, indent=2)
        
    print(f"  Verification metrics logged to: {METRICS_PATH}")
    return metrics

if __name__ == "__main__":
    train()
