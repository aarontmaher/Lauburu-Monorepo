#ifndef MOVESENSE_EDGE_AI_MODEL_H
#define MOVESENSE_EDGE_AI_MODEL_H
// Movesense HR+ (nRF52832 Cortex-M4F) INT8 Edge AI Model
// Training accuracy: 100.0% | Scale L1=16 | Scale L2=64
// Flash: 219 bytes | Stack RAM: 60 bytes
// Classes: 0=Normal Sinus, 1=Ectopic/PVC, 2=Motion Artifact

#define NUM_FEATURES 14
#define HIDDEN_DIM   12
#define NUM_CLASSES  3
#define SCALE_L1     16
#define SCALE_L2     64

static const int8_t W1[HIDDEN_DIM][NUM_FEATURES] = {
    {   2,    1,    0,   -1,    1,    0,    1,   -1,    2,    2,    0,    0,   -1,   -1},
    { -17,  -18,  -15,   31,  -16,  -17,  -14,   19,   -4,   -5,   -6,   -5,   -5,   -4},
    {   1,    1,    1,    2,    3,    1,    2,   -1,    1,    1,    2,    0,    1,    2},
    { -15,  -17,  -14,   30,  -13,  -12,  -13,   19,   -4,   -3,   -3,   -5,   -4,   -2},
    {  -6,   -5,   -3,   11,   -4,   -5,   -4,    7,   -2,    0,   -1,   -1,   -1,   -2},
    { -12,  -13,  -11,   17,  -11,  -12,  -11,   14,   -6,   -5,   -5,   -7,   -7,   -6},
    {  -3,   -3,   -4,   -4,   -4,   -4,   -4,    3,   -5,   -6,   -5,   -7,   -5,   -4},
    { -25,  -25,  -22,   16,  -24,  -24,  -25,   25,  -19,  -18,  -18,  -18,  -19,  -19},
    {  -5,   -3,  -10,  -25,   -8,   -7,   -7,    2,  -15,  -16,  -15,  -16,  -16,  -15},
    {   1,    1,    1,    0,    1,    0,    1,    0,    0,    1,    1,    1,    1,    2},
    { -16,  -16,  -15,   17,  -14,  -13,  -14,   16,   -8,   -9,   -9,   -9,   -8,   -9},
    {   0,    2,    0,    2,    1,    0,    0,    0,    0,    2,    0,   -1,    2,    1}
};
static const int8_t B1[HIDDEN_DIM] = {
       0,    0,    0,    0,    0,    0,    0,    1,    1,    0,    0,    0
};
static const int8_t W2[NUM_CLASSES][HIDDEN_DIM] = {
    {  -7,   33,   -6,   33,   12,   14,  -16,   -9,  -64,    3,    8,   -1},
    {  -2,  -31,   -1,  -34,  -12,   -9,   15,   17,   64,   -6,   -5,   -5},
    {   0,    2,    7,    0,    0,   -7,   -2,   -6,   -6,    6,   -6,    1}
};
static const int8_t B2[NUM_CLASSES] = {
      -2,    2,    0
};

static const int8_t sample_normal[NUM_FEATURES]   = {-25, -25, -23, 30, -25, -29, -26, 30, -16, -17, -17, -17, -16, -16};
static const int8_t sample_ectopic[NUM_FEATURES]  = {-3, 2, -13, -29, -7, -5, -2, 3, -16, -16, -16, -16, -16, -16};
static const int8_t sample_artifact[NUM_FEATURES] = {46, 35, 34, 3, 26, 47, 26, -19, 36, 31, 33, 36, 27, 31};

#endif // MOVESENSE_EDGE_AI_MODEL_H
