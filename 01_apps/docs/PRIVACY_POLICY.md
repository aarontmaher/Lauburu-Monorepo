# 🔒 Privacy Policy
**Application:** Sovereign Lauburu (com.lauburu.sovereign / ai.lauburu.sovereign)
**Organization:** Lauburu AI & Ultimate Wrestling Academy
**Effective Date:** 2026-09-10
**Compliance:** GDPR, CCPA, Australian Privacy Principles (APP), Apple Privacy Nutritional Labels

---

## 1. Local-First & Zero Health Data Sales
We adhere to a strict **Local AI First** architectural mandate. Your raw biometric data (ECG streams, heart rate, IMU kinematics) is processed locally on-device using native compiled C11 and Apple Silicon Metal Performance Shaders:
- **Zero Third-Party Advertising Trackers:** We never embed commercial tracking SDKs or ad brokers.
- **Zero Data Brokerage:** We never sell, rent, or trade your personal or health data.

## 2. Information Collected
- **Account & Identity:** Email address, username, and active subscription entitlements managed via Shopify / RevenueCat.
- **Biometrics & Physical Sensor Telemetry:** Bluetooth LE Movesense ECG signals, IMU motion packets, and cadence data processed locally in real time.
- **Hardware Telemetry:** Local RAM headroom and mesh network link states for distributed local inference routing.

## 3. Storage & Encryption
- In-transit biometrics over the local mesh are secured via WireGuard (Tailscale) and authenticated Bluetooth PAN sockets.
- On-device telemetry caches are stored in sandboxed application storage and protected by operating system keychain encryption.

## 4. User Rights & Data Erasure
You have the right to inspect, export, or permanently delete your stored training logs at any time directly through the application settings or by contacting `privacy@lauburu.ai`.
