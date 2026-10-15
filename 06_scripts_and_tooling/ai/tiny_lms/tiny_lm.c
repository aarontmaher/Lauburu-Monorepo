#include <stdio.h>
#include <stdlib.h>
#include <math.h>

// Tiny LM built from scratch in C, inspired by Karpathy's llm.c
// Minimal implementation of a transformer forward pass

typedef struct {
    int vocab_size;
    int hidden_dim;
    int num_layers;
    int num_heads;
    int seq_len;
} Config;

typedef struct {
    float* token_embedding_table;
    float* wq;
    float* wk;
    float* wv;
    float* wo;
    float* w1;
    float* w2;
    float* ln_gamma;
    float* ln_beta;
} Weights;

typedef struct {
    float* x;
    float* q;
    float* k;
    float* v;
    float* att;
    float* ffn_hidden;
} RunState;

// Simple matmul: out = x * W, where x is (seq_len, in_dim), W is (in_dim, out_dim)
void matmul(float* out, float* x, float* w, int seq_len, int in_dim, int out_dim) {
    for (int s = 0; s < seq_len; s++) {
        for (int i = 0; i < out_dim; i++) {
            float val = 0.0f;
            for (int j = 0; j < in_dim; j++) {
                val += x[s * in_dim + j] * w[j * out_dim + i];
            }
            out[s * out_dim + i] = val;
        }
    }
}

void softmax(float* x, int size) {
    float max_val = x[0];
    for (int i = 1; i < size; i++) {
        if (x[i] > max_val) max_val = x[i];
    }
    float sum = 0.0f;
    for (int i = 0; i < size; i++) {
        x[i] = expf(x[i] - max_val);
        sum += x[i];
    }
    for (int i = 0; i < size; i++) {
        x[i] /= sum;
    }
}

void forward(Config* config, Weights* weights, RunState* state, int* tokens) {
    int seq_len = config->seq_len;
    int dim = config->hidden_dim;
    
    // 1. Token Embedding
    for (int s = 0; s < seq_len; s++) {
        int token = tokens[s];
        for (int i = 0; i < dim; i++) {
            state->x[s * dim + i] = weights->token_embedding_table[token * dim + i];
        }
    }
    
    // 2. Transformer layers (Self-Attention + FFN)
    for (int l = 0; l < config->num_layers; l++) {
        // Compute Q, K, V
        matmul(state->q, state->x, weights->wq, seq_len, dim, dim);
        matmul(state->k, state->x, weights->wk, seq_len, dim, dim);
        matmul(state->v, state->x, weights->wv, seq_len, dim, dim);
        
        // Attention (Simplified: un-multiheaded, O(N^2) dot product)
        for (int s = 0; s < seq_len; s++) {
            for (int t = 0; t <= s; t++) { // Causal mask
                float score = 0.0f;
                for (int i = 0; i < dim; i++) {
                    score += state->q[s * dim + i] * state->k[t * dim + i];
                }
                score /= sqrtf((float)dim);
                state->att[s * seq_len + t] = score;
            }
            // Mask out future tokens
            for (int t = s + 1; t < seq_len; t++) {
                state->att[s * seq_len + t] = -1e9f;
            }
            softmax(&state->att[s * seq_len], seq_len);
        }
        
        // Output of attention
        // (Just a simple template logic for learning purposes, not full multi-head)
        printf("Layer %d forward pass simulated.\n", l);
    }
}

int main() {
    printf("Tiny LM in C (llm.c style) - Minimal implementation initialized.\n");
    Config config = { .vocab_size = 32000, .hidden_dim = 256, .num_layers = 1, .num_heads = 4, .seq_len = 8 };
    
    // In a real scenario, allocate memory and load weights
    printf("Config: %d layers, %d hidden_dim\n", config.num_layers, config.hidden_dim);
    return 0;
}
