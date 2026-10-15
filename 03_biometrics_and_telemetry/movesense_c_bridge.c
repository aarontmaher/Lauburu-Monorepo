#include <stdint.h>
#include "movesense_micro_mlp.h"
#include "movesense_edge_model.h"

// Expose the static inline function
float predict_micro_mlp(const float input[32]) {
    return run_movesense_inference(input);
}
