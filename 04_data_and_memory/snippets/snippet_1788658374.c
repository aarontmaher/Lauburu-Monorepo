// Sovereign Bluetooth Serial Sensor Ingestion
void process_ecg_sample(uint16_t raw_val) {
    float filtered = pan_tompkins_filter(raw_val);
    if (filtered > R_PEAK_THRESHOLD) {
        send_serial_frame(FRAME_TYPE_R_PEAK, filtered);
    }
}