#pragma once
// ============================================================================
// prima_edge_client.hpp — C++20 Embedded Edge Client for 3B MoE & PRP Ring
// Subsystem: 02_ai_models_and_inference / prima_cpp / include
// Lauburu Mesh Ecosystem — 2026
// ============================================================================

#include <string>
#include <vector>
#include <chrono>
#include <memory>
#include <functional>
#include <cstdint>

namespace lauburu::prima {

enum class ExecutionMode {
    OFFLINE_STANDALONE = 0,
    SPECULATIVE_RING_COUPLED = 1
};

struct EdgeClientConfig {
    std::string model_path = "";
    std::string model_name = "Qwen-3B-MoE-Chat-Q4_K_M";
    std::string active_parameters = "0.8B";
    std::string mesh_daemon_url = "http://127.0.0.1:8082";
    float vram_footprint_mb = 1180.0f;
    float kv_cache_mb = 120.0f;
    float max_device_ram_cap_mb = 1500.0f; // Gate 9 Mobile Constraint
    float handshake_timeout_ms = 150.0f;   // 150ms timeout invariant
    int speculative_draft_k = 5;
    bool enable_mmap = true;               // Zero-copy mmap
};

struct EdgeInferenceMetrics {
    std::string response_text;
    ExecutionMode mode;
    int tokens_generated;
    int draft_tokens_count;
    int accepted_tokens_count;
    float acceptance_rate;
    float latency_ms;
    float tokens_per_second;
    float memory_rss_mb;
    float cluster_speedup;
    bool mesh_connected;
    float handshake_rtt_ms;
};

class PrimaEdgeClient {
public:
    explicit PrimaEdgeClient(const EdgeClientConfig& config);
    ~PrimaEdgeClient();

    // Verification of Gate 9 Customer Mobile Envelope
    bool verify_customer_device_envelope(float& out_margin_mb) const;

    // Strict 150ms handshake check with back-end PRP mesh
    bool probe_mesh_daemon(float& out_rtt_ms);

    // Draft K tokens locally on on-device 3B MoE model (0.8B active params)
    std::vector<std::string> draft_tokens_locally(const std::string& prompt, int k, float& out_draft_ms);

    // Verify draft tokens via back-end 80B MoE cluster in a single PRP forward pass
    std::vector<std::string> verify_tokens_with_mesh(
        const std::string& prompt,
        const std::vector<std::string>& drafts,
        float mesh_rtt_ms,
        int& out_accepted_count,
        float& out_verify_ms
    );

    // Primary end-to-end chat generation with automatic fallback
    EdgeInferenceMetrics generate_chat(
        const std::string& prompt,
        const std::string& system_prompt = "",
        bool force_local = false
    );

private:
    EdgeClientConfig config_;
    uint64_t total_sessions_{0};
    uint64_t total_drafts_{0};
    uint64_t total_accepted_{0};
};

} // namespace lauburu::prima

// C-ABI for JNI and Swift/Objective-C FFI Interoperability
#ifdef __cplusplus
extern "C" {
#endif

typedef void* prima_edge_client_t;

prima_edge_client_t prima_edge_client_create(
    const char* model_path,
    const char* mesh_url,
    float timeout_ms
);

void prima_edge_client_destroy(prima_edge_client_t client);

int prima_edge_client_check_envelope(
    prima_edge_client_t client,
    float* out_margin_mb
);

int prima_edge_client_probe_mesh(
    prima_edge_client_t client,
    float* out_rtt_ms
);

char* prima_edge_client_generate_chat(
    prima_edge_client_t client,
    const char* prompt,
    int force_local,
    int* out_mode,
    float* out_tok_per_sec,
    float* out_latency_ms
);

void prima_edge_client_free_string(char* str);

#ifdef __cplusplus
}
#endif
