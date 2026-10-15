#!/bin/bash
echo "Starting Continuous Movesense Training Loop (Rule 9 Daemon)..."
while true; do
    python3 /Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/03_biometrics_and_telemetry/train_movesense_micro_model.py
    sleep 300
done
