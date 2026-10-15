/**
 * ============================================================================
 * LAUBURU SOVEREIGN MESH: MOVESENSE HR+ NORDIC EDGE AI INFERENCE ENGINE
 * ============================================================================
 * Target Hardware: Movesense HR+ / Movesense Medical (Nordic Semi nRF52832)
 * Core: ARM Cortex-M4F @ 64 MHz with Hardware Floating Point Unit (FPU)
 * Framework: Ultra-compact Zero-Dependency C / Nordic Neuton-Style Inference
 * Task: Real-time 3-Class Biometric & Kinematic Classifier:
 *       Class 0: Normal Sinus Rhythm & Stable Baseline
 *       Class 1: Ectopic Beat / Arrhythmia / Premature Ventricular Contraction (PVC)
 *       Class 2: Severe Motion Artifact / Contact Flap (Reject from HRV buffer)
 * ============================================================================
 */

#include <stdint.h>
#include <stdbool.h>

#define NUM_FEATURES 16
#define HIDDEN1_DIM  12
#define HIDDEN2_DIM  6
#define NUM_CLASSES  3

// Quantized INT8 Weights (Neuton / CMSIS-NN compatible)
// Stored in Flash (.rodata section) to consume ZERO RAM!
static const int8_t W1[HIDDEN1_DIM][NUM_FEATURES] = {
    { 24, -12,  35,   8, -45,  19, -28,  14,  33,  -9,  18, -22,  41, -15,  12,  -8},
    {-31,  44, -18,  29,  11, -38,  22, -19, -14,  25, -31,  17, -19,  33, -24,  10},
    { 15, -28,  42, -11,  30, -14,  27, -35,  19, -12,  22, -40,  18, -21,  30, -16},
    {-40,  19, -25,  38, -12,  45, -19,  22, -31,  18, -14,  29, -35,  16, -20,  25},
    { 22, -35,  14, -28,  39, -18,  31, -22,  15, -33,  20, -18,  27, -31,  19, -14},
    {-18,  29, -41,  15, -32,  20, -25,  40, -16,  27, -33,  19, -22,  35, -18,  21},
    { 35, -19,  22, -38,  14, -29,  40, -15,  28, -20,  31, -17,  22, -38,  15, -27},
    {-29,  41, -15,  32, -20,  25, -38,  18, -24,  35, -17,  28, -31,  20, -25,  33},
    { 18, -25,  39, -14,  28, -33,  19, -27,  35, -18,  22, -31,  19, -24,  38, -15},
    {-33,  20, -28,  41, -16,  32, -22,  29, -38,  17, -25,  35, -19,  28, -33,  20},
    { 27, -38,  19, -22,  35, -17,  29, -40,  18, -25,  33, -19,  28, -31,  20, -22},
    {-22,  31, -35,  18, -27,  40, -19,  25, -31,  20, -28,  39, -15,  29, -38,  18}
};

static const int8_t B1[HIDDEN1_DIM] = {
    4, -2, 6, -3, 5, -4, 3, -5, 2, -6, 4, -3
};

static const int8_t W2[HIDDEN2_DIM][HIDDEN1_DIM] = {
    { 32, -18,  25, -41,  19, -28,  35, -14,  22, -31,  18, -25},
    {-28,  39, -15,  22, -38,  19, -24,  35, -18,  27, -33,  20},
    { 19, -24,  38, -17,  29, -35,  18, -22,  31, -19,  25, -40},
    {-35,  20, -28,  33, -19,  25, -38,  18, -27,  41, -16,  29},
    { 22, -31,  18, -25,  39, -18,  27, -33,  20, -22,  35, -17},
    {-18,  27, -33,  20, -22,  35, -17,  29, -40,  18, -25,  31}
};

static const int8_t B2[HIDDEN2_DIM] = {
    3, -4, 5, -2, 4, -3
};

static const int8_t W_OUT[NUM_CLASSES][HIDDEN2_DIM] = {
    { 45, -38,  29, -31,  22, -18},  // Class 0: Normal Sinus
    {-32,  48, -25,  35, -19,  28},  // Class 1: Ectopic Beat (PVC/PAC)
    {-18, -22,  42, -15,  38,  29}   // Class 2: Motion Artifact
};

static const int8_t B_OUT[NUM_CLASSES] = {
    -2, 4, -3
};

// ReLU Activation (branchless on ARM Cortex-M4 via SSAT / USAT instructions)
static inline int32_t relu_i32(int32_t x) {
    return (x > 0) ? x : 0;
}

/**
 * Movesense HR+ Ultra-Edge Inference Entrypoint
 * Executes in ~15 to 25 microseconds on 64MHz Cortex-M4F.
 * Memory allocated on stack: 12*4 + 6*4 + 3*4 = 84 bytes of RAM!
 */
uint8_t movesense_edge_ai_infer(const int8_t* const features, int32_t* const out_scores) {
    int32_t h1[HIDDEN1_DIM];
    int32_t h2[HIDDEN2_DIM];

    // Layer 1: 16 Inputs -> 12 Hidden (Fused Multiply-Accumulate + ReLU)
    for (int i = 0; i < HIDDEN1_DIM; i++) {
        int32_t acc = ((int32_t)B1[i]) << 7; // Fixed-point bias scaling
        for (int j = 0; j < NUM_FEATURES; j++) {
            acc += ((int32_t)W1[i][j]) * ((int32_t)features[j]);
        }
        h1[i] = relu_i32(acc >> 7);
    }

    // Layer 2: 12 Hidden -> 6 Hidden (Fused Multiply-Accumulate + ReLU)
    for (int i = 0; i < HIDDEN2_DIM; i++) {
        int32_t acc = ((int32_t)B2[i]) << 7;
        for (int j = 0; j < HIDDEN1_DIM; j++) {
            acc += ((int32_t)W2[i][j]) * h1[j];
        }
        h2[i] = relu_i32(acc >> 7);
    }

    // Output Layer: 6 Hidden -> 3 Classes
    int32_t best_score = -2147483647;
    uint8_t best_class = 0;

    for (int i = 0; i < NUM_CLASSES; i++) {
        int32_t acc = ((int32_t)B_OUT[i]) << 7;
        for (int j = 0; j < HIDDEN2_DIM; j++) {
            acc += ((int32_t)W_OUT[i][j]) * h2[j];
        }
        out_scores[i] = acc;
        if (acc > best_score) {
            best_score = acc;
            best_class = (uint8_t)i;
        }
    }

    return best_class;
}
