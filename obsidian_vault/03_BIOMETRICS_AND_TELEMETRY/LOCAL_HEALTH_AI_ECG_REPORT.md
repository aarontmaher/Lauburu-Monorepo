# 🩺 Local Health AI ECG & Cardiology Report (Rule #0 Zero-Mock)

- **Timestamp (UTC):** `2026-10-15T00:35:27Z`
- **Sensor Hardware:** `Movesense 261030002013 (74:92:BA:11:36:D6)` (`CoreBluetooth C1DB5043-8F89-88E8-46A3-BBD4ED83FC88`)
- **Live BLE Connection State:** `False` (`RECORDED_MOVESENSE_VAULT (Movesense 261030002013 • 74:92:BA:11:36:D6)`)
- **Pre-Trained Models Executed:** `Gemma-2-2B-ECG (L8 :8092), Hermes-3-8B (L1 :8085), EmbeddingGemma-2-740M (:8087), TemporalKinematicCardiacNet (.pt), Movesense-INT8-Edge-MLP (.h), MovesenseBicepECGEngine (DSP)`

## Pre-Trained Neural Network & DSP Outputs
- **PyTorch 1D-CNN + BiGRU (`movesense_kinematic_cardiac_net.pt`):** `MODERATE_AEROBIC (75-100 BPM)` (`74.0%` confidence, Predicted HR `46.2 BPM`, Val Acc `76.8%`)
- **Movesense HR+ INT8 Edge MLP (`movesense_edge_model.h` + `movesense_micro_mlp.h`):** `Ectopic/PVC` (`100.0%`), Micro-MLP `0.0423`, Ectopic Density `61.0/min`
- **MovesenseBicepECGEngine (`.mecg` 24-Bit ADC):** `384` Pan-Tompkins QRS peaks, SNR Gain `+11.42 dB` (`-4.87 dB -> 5.09 dB`), `68.4%` EMG rejected

## Clinical Synthesis
```text
1. [PRE-TRAINED PYTORCH 1D-CNN+BiGRU • movesense_kinematic_cardiac_net.pt on Apple Silicon Metal (MPS)]: Exertion State = MODERATE_AEROBIC (75-100 BPM) (74.0% conf, Val Acc 76.8%), Kinematic-Predicted HR = 46.2 BPM (Probs: {'REST_RECOVERY (<75 BPM)': 23.1, 'MODERATE_AEROBIC (75-100 BPM)': 74.0, 'HIGH_GRAPPLING (>=100 BPM)': 2.9}).
2. [PRE-TRAINED MOVESENSE EDGE INT8 MLP • movesense_edge_model.h (INT8 [14->12->3]) & movesense_micro_mlp.h (FP32 [32->8->1])]: Beat Classification = Ectopic/PVC (100.0% conf), Micro-MLP Score = 0.0423, Ectopic Density = 61.0/min, 16-Byte BLE Frame = 0x4f1401e803000061013d6402014000aa.
3. [AUTHENTIC 24-BIT .MECG ADC + BICEP/CHEST ADAPTIVE ECG DSP]: 60448 raw 24-bit samples (302.24s @ 200Hz), 384 Pan-Tompkins QRS peaks, NLMS+Wavelet SNR Gain = +11.42 dB (Raw -4.87 dB -> Clean 5.09 dB, 68.4% EMG artifact rejected).
4. [EmbeddingGemma-2-740M • 833ms]: 768-D MRL vector norm=0.602 matched against movesense_clinical_distillation.jsonl (58.4 KB clinical ECG/HRV corpus).
5. [Gemma-2-2B-ECG (L8 :8092) • 2097ms]: The patient exhibits a moderate aerobic heart rate with ectopic beats detected by the INT8-MLP model, suggesting possible arrhythmia.
7. [Hermes-3-8B • 3365ms]: 1. The Movesense device is accurately recording and processing ECG data, with 384 Pan-Tompkins QRS peaks detected at 200Hz, indicating a high-quality signal. The pre-trained PyTorch 1D-CNN+BiGRU model classifies the exertion level as moderate-aerobic (75-100 BPM) with a predicted heart rate of 46.2
```
