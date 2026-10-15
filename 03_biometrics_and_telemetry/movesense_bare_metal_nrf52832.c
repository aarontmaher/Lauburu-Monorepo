#include <stdint.h>
#include "movesense_edge_model.h"

/**
 * Movesense HR+ Bare-Metal Inference (nRF52832, no libc, no printf)
 * Conforms to Nordic nRF Connect SDK / Movesense Whiteboard API calling convention.
 */
static uint8_t movesense_edge_ai_classify(const int8_t* features, int32_t* out_logits) {
    int32_t h1[HIDDEN_DIM];
    for (int i = 0; i < HIDDEN_DIM; i++) {
        int64_t acc = (int64_t)B1[i] * SCALE_L1;
        for (int j = 0; j < NUM_FEATURES; j++)
            acc += (int64_t)W1[i][j] * (int32_t)features[j];
        int32_t val = (int32_t)(acc / SCALE_L1);
        h1[i] = val > 0 ? val : 0;
    }
    int64_t best = -9223372036854775807LL;
    uint8_t best_class = 0;
    for (int i = 0; i < NUM_CLASSES; i++) {
        int64_t acc = (int64_t)B2[i] * SCALE_L2;
        for (int j = 0; j < HIDDEN_DIM; j++)
            acc += (int64_t)W2[i][j] * h1[j];
        out_logits[i] = (int32_t)(acc >> 8);
        if (acc > best) { best = acc; best_class = (uint8_t)i; }
    }
    return best_class;
}

/* Entry point stub for Movesense Whiteboard API integration.
   In production: replace with wb::ResourceClient::onTimer() / onEcgData() callback */
void movesense_ecg_ai_tick(const int8_t* feature_vector) {
    int32_t logits[NUM_CLASSES];
    uint8_t cls = movesense_edge_ai_classify(feature_vector, logits);
    // In real firmware: trigger BLE GATT notify only if cls != 0 (alert state)
    // nrf_gpio_pin_toggle(LED_PIN);  // Visual confirmation
    (void)cls;
}
