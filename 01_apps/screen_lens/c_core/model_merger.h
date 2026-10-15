#ifndef MODEL_MERGER_H
#define MODEL_MERGER_H

#include <stddef.h>
#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

typedef enum {
    MERGE_METHOD_LINEAR = 0,
    MERGE_METHOD_SLERP = 1,
    MERGE_METHOD_TIES = 2,
    MERGE_METHOD_DARE = 3,
    MERGE_METHOD_MOE_UPCYCLE = 4
} MergeMethod;

typedef struct {
    MergeMethod method;
    size_t vector_size;
    double alpha;         // Interpolation factor or weight
    double sparsity;      // Trimming threshold (e.g. 0.2 = top 80%)
    double compute_time_us;
    double cosine_similarity_before;
    double cosine_similarity_after;
    bool success;
} MergeReport;

/**
 * Spherical Linear Interpolation (SLERP) between two weight vectors.
 */
MergeReport merge_slerp(const float *w0, const float *w1, float *out_w, size_t n, double t);

/**
 * TIES Merging across multiple task delta vectors.
 */
MergeReport merge_ties(const float *base_w, const float **delta_w, size_t num_models, float *out_w, size_t n, double density);

/**
 * DARE (Drop And REscale) merging.
 */
MergeReport merge_dare(const float *w0, const float *w1, float *out_w, size_t n, double drop_rate);

#ifdef __cplusplus
}
#endif

#endif // MODEL_MERGER_H
