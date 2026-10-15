#include "model_merger.h"
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include <time.h>

static double dot_product(const float *a, const float *b, size_t n) {
    double sum = 0.0;
    for (size_t i = 0; i < n; ++i) {
        sum += (double)a[i] * (double)b[i];
    }
    return sum;
}

static double vector_norm(const float *a, size_t n) {
    return sqrt(dot_product(a, a, n));
}

MergeReport merge_slerp(const float *w0, const float *w1, float *out_w, size_t n, double t) {
    MergeReport report;
    memset(&report, 0, sizeof(MergeReport));
    report.method = MERGE_METHOD_SLERP;
    report.vector_size = n;
    report.alpha = t;

    struct timespec t0, t1;
    clock_gettime(CLOCK_MONOTONIC, &t0);

    double norm0 = vector_norm(w0, n);
    double norm1 = vector_norm(w1, n);

    if (norm0 < 1e-9 || norm1 < 1e-9) {
        // Fallback to linear interpolation if vectors are zero
        for (size_t i = 0; i < n; ++i) {
            out_w[i] = (float)((1.0 - t) * w0[i] + t * w1[i]);
        }
        report.success = true;
        return report;
    }

    double dot = dot_product(w0, w1, n) / (norm0 * norm1);
    report.cosine_similarity_before = dot;

    // Clamp dot product to prevent NaN from acos
    if (dot > 0.99999) {
        for (size_t i = 0; i < n; ++i) {
            out_w[i] = (float)((1.0 - t) * w0[i] + t * w1[i]);
        }
    } else if (dot < -0.99999) {
        dot = -0.99999;
    } else {
        double theta = acos(dot);
        double sin_theta = sin(theta);
        double c0 = sin((1.0 - t) * theta) / sin_theta;
        double c1 = sin(t * theta) / sin_theta;

        for (size_t i = 0; i < n; ++i) {
            out_w[i] = (float)(c0 * w0[i] + c1 * w1[i]);
        }
    }

    clock_gettime(CLOCK_MONOTONIC, &t1);
    report.compute_time_us = (t1.tv_sec - t0.tv_sec) * 1e6 + (t1.tv_nsec - t0.tv_nsec) / 1e3;
    report.cosine_similarity_after = dot_product(out_w, w0, n) / (vector_norm(out_w, n) * norm0);
    report.success = true;
    return report;
}

MergeReport merge_dare(const float *w0, const float *w1, float *out_w, size_t n, double drop_rate) {
    MergeReport report;
    memset(&report, 0, sizeof(MergeReport));
    report.method = MERGE_METHOD_DARE;
    report.vector_size = n;
    report.sparsity = drop_rate;

    struct timespec t0, t1;
    clock_gettime(CLOCK_MONOTONIC, &t0);

    double rescale = (drop_rate < 1.0) ? (1.0 / (1.0 - drop_rate)) : 1.0;

    for (size_t i = 0; i < n; ++i) {
        float delta = w1[i] - w0[i];
        // Deterministic pseudo-random dropout based on index and magnitude
        double r = (double)((i * 2654435761u) % 1000) / 1000.0;
        if (r >= drop_rate) {
            out_w[i] = (float)(w0[i] + delta * rescale * 0.5);
        } else {
            out_w[i] = w0[i];
        }
    }

    clock_gettime(CLOCK_MONOTONIC, &t1);
    report.compute_time_us = (t1.tv_sec - t0.tv_sec) * 1e6 + (t1.tv_nsec - t0.tv_nsec) / 1e3;
    report.success = true;
    return report;
}

MergeReport merge_ties(const float *base_w, const float **delta_w, size_t num_models, float *out_w, size_t n, double density) {
    MergeReport report;
    memset(&report, 0, sizeof(MergeReport));
    report.method = MERGE_METHOD_TIES;
    report.vector_size = n;
    report.sparsity = 1.0 - density;

    struct timespec t0, t1;
    clock_gettime(CLOCK_MONOTONIC, &t0);

    for (size_t i = 0; i < n; ++i) {
        double sign_sum = 0.0;
        for (size_t m = 0; m < num_models; ++m) {
            sign_sum += (delta_w[m][i] > 0.0) ? 1.0 : ((delta_w[m][i] < 0.0) ? -1.0 : 0.0);
        }
        int majority_sign = (sign_sum >= 0.0) ? 1 : -1;

        double merged_delta = 0.0;
        size_t count = 0;
        for (size_t m = 0; m < num_models; ++m) {
            int s = (delta_w[m][i] > 0.0) ? 1 : ((delta_w[m][i] < 0.0) ? -1 : 0);
            if (s == majority_sign) {
                merged_delta += delta_w[m][i];
                count++;
            }
        }

        if (count > 0) {
            out_w[i] = (float)(base_w[i] + (merged_delta / (double)count) * density);
        } else {
            out_w[i] = base_w[i];
        }
    }

    clock_gettime(CLOCK_MONOTONIC, &t1);
    report.compute_time_us = (t1.tv_sec - t0.tv_sec) * 1e6 + (t1.tv_nsec - t0.tv_nsec) / 1e3;
    report.success = true;
    return report;
}
