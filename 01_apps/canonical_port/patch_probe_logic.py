import re
with open("tui/services/blackboard_store.py", "r") as f:
    content = f.read()

replacement = """            if (
                bio_data is None
                or not bio_data.get("metrics", {}).get("sensor_connected", False)
            ):
                snapshot.layer_2_biometrics.movesense_stream.connected = False
                snapshot.layer_2_biometrics.movesense_stream.ecg_snr_db = 0.0
                snapshot.layer_2_biometrics.heart_rate_bpm = None
                snapshot.layer_2_biometrics.rr_intervals_ms = []
                snapshot.layer_2_biometrics.rmssd_ms = None
                snapshot.layer_2_biometrics.dfa_alpha1 = None
                snapshot.layer_2_biometrics.zone2_status = "AWAITING_BLUETOOTH_SENSORS"
                snapshot.layer_2_biometrics.vo2_max_ml_kg_min = None
                snapshot.layer_2_biometrics.ptt_blood_pressure = PttBloodPressure(
                    systolic_mmhg=None,
                    diastolic_mmhg=None,
                    pulse_transit_time_ms=None,
                    status="OFFLINE"
                )
            else:
                metrics = bio_data.get("metrics", {})
                snapshot.layer_2_biometrics.movesense_stream.connected = True
                hr = metrics.get("heart_rate_bpm")
                snapshot.layer_2_biometrics.heart_rate_bpm = hr
                snapshot.layer_2_biometrics.rmssd_ms = metrics.get("rr_interval_ms")  # Map to rmssd appropriately
                snapshot.layer_2_biometrics.dfa_alpha1 = metrics.get("dfa_alpha1")
                if hr and 130 <= hr <= 145:
                    snapshot.layer_2_biometrics.zone2_status = "ZONE_2_OPTIMAL"
                elif hr:
                    snapshot.layer_2_biometrics.zone2_status = "ACTIVE"
"""

content = re.sub(
    r"            if \(\n                bio_data is None\n.*?snapshot\.layer_2_biometrics\.zone2_status = \"ACTIVE\"",
    replacement,
    content,
    flags=re.DOTALL
)

with open("tui/services/blackboard_store.py", "w") as f:
    f.write(content)
