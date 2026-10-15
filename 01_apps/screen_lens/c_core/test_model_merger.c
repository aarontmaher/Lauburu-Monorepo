#include "model_merger.h"
#include <stdio.h>
#include <stdlib.h>

int main() {
    size_t n = 100000; // 100,000 parameters
    float *w0 = (float *)malloc(n * sizeof(float));
    float *w1 = (float *)malloc(n * sizeof(float));
    float *out = (float *)malloc(n * sizeof(float));

    for (size_t i = 0; i < n; ++i) {
        w0[i] = (float)(i % 100) / 100.0f;
        w1[i] = (float)((i + 25) % 100) / 100.0f;
    }

    printf("================================================================================\n");
    printf("🧬 NATIVE C AI MODEL MERGING BENCHMARK (100,000 PARAMETERS)\n");
    printf("================================================================================\n");

    // 1. SLERP Benchmark
    MergeReport slerp_rep = merge_slerp(w0, w1, out, n, 0.5);
    printf("SLERP (t=0.5):        %.2f microseconds (Cosine Before: %.4f -> After: %.4f)\n", 
           slerp_rep.compute_time_us, slerp_rep.cosine_similarity_before, slerp_rep.cosine_similarity_after);

    // 2. DARE Benchmark
    MergeReport dare_rep = merge_dare(w0, w1, out, n, 0.2);
    printf("DARE (drop=0.2):      %.2f microseconds\n", dare_rep.compute_time_us);

    // 3. TIES Benchmark
    const float *deltas[2] = {w0, w1};
    MergeReport ties_rep = merge_ties(w0, deltas, 2, out, n, 0.8);
    printf("TIES (density=0.8):   %.2f microseconds\n", ties_rep.compute_time_us);
    printf("================================================================================\n");

    free(w0);
    free(w1);
    free(out);
    return 0;
}
