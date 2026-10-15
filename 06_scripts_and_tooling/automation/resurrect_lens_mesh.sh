#!/bin/bash
echo "Resurrecting the Lauburu Omni-Lens Mesh..."

# Kill any stray processes
pkill -f unified_zmq_broker.py || true
pkill -f zmq_telemetry_broadcaster.py || true
pkill -f lens_edge_sensor.py || true
pkill -f lens_headless_brain.py || true
pkill -f lens_shadow_auditor.py || true
pkill -f lens_continuous_lora_harvester.py || true
pkill -f whisper_stt_daemon.py || true

# Launch Core Broker
nohup python3 -u /Volumes/Lauburu-Monorepo/06_scripts_and_tooling/network/unified_zmq_broker.py > /tmp/zmq_broker.log 2>&1 &
sleep 2

# Launch Lens Edge & Brain
nohup python3 -u /Volumes/Lauburu-Monorepo/01_apps/screen_lens/lens_edge_sensor.py > /tmp/lens_sensor.log 2>&1 &
nohup python3 -u /Volumes/Lauburu-Monorepo/01_apps/screen_lens/lens_headless_brain.py > /tmp/lens_brain.log 2>&1 &

# Launch Shadow AI & LoRA Harvester
nohup python3 -u /Volumes/Lauburu-Monorepo/01_apps/screen_lens/lens_shadow_auditor.py > /tmp/shadow_auditor.log 2>&1 &
nohup python3 -u /Volumes/Lauburu-Monorepo/04_data_and_memory/lens_continuous_lora_harvester.py > /tmp/lora_harvester.log 2>&1 &

# Launch Whisper
nohup python3 -u /Volumes/Lauburu-Monorepo/03_biometrics_and_telemetry/audio/whisper_stt_daemon.py > /tmp/whisper_daemon.log 2>&1 &

echo "Resurrection Complete. Mesh is active."
