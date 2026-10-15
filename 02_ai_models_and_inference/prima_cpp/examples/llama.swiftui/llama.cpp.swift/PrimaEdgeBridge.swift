// ============================================================================
// PrimaEdgeBridge.swift — iOS Metal / Swift In-Process prima.cpp Edge Client
// Subsystem: 02_ai_models_and_inference / prima_cpp / examples / llama.swiftui
// Lauburu Mesh Ecosystem — 2026
// ============================================================================

import Foundation

/// In-Process prima.cpp Edge Client for iOS & macOS
///
/// Strictly abides by iOS background execution restrictions:
/// 1. Runs IN-PROCESS as an embedded Metal C++ engine (no detached daemon / no background port bind).
/// 2. Manages 3B MoE model (4-bit Q4_K_M) with zero-copy mmap.
/// 3. Executes 150ms speculative handshake fallback over Tailscale/LAN.
public final class PrimaEdgeBridge {

    public struct InferenceResult {
        public let text: String
        public let mode: String
        public let tokensPerSecond: Float
        public let latencyMs: Float
        public let isMeshCoupled: Bool
    }

    private var clientHandle: OpaquePointer?
    private let modelPath: String
    private let meshUrl: String
    private let timeoutMs: Float

    public init(
        modelPath: String,
        meshUrl: String = "http://100.119.199.76:8082",
        timeoutMs: Float = 150.0
    ) {
        self.modelPath = modelPath
        self.meshUrl = meshUrl
        self.timeoutMs = timeoutMs
        
        self.clientHandle = prima_edge_client_create(
            (modelPath as NSString).utf8String,
            (meshUrl as NSString).utf8String,
            timeoutMs
        )
    }

    deinit {
        if let handle = clientHandle {
            prima_edge_client_destroy(handle)
            clientHandle = nil
        }
    }

    /// Verifies that memory usage is <= 1,500 MB (Gate 9 Mobile Envelope)
    public func checkEnvelope() -> (isCompliant: Bool, marginMb: Float) {
        guard let handle = clientHandle else { return (false, 0) }
        var margin: Float = 0.0
        let status = prima_edge_client_check_envelope(handle, &margin)
        return (status != 0, margin)
    }

    /// Strict 150ms mesh probe
    public func probeMesh() -> (isOnline: Bool, rttMs: Float) {
        guard let handle = clientHandle else { return (false, -1) }
        var rtt: Float = 0.0
        let status = prima_edge_client_probe_mesh(handle, &rtt)
        return (status != 0, rtt)
    }

    /// Primary chat generation with speculative acceleration and local fallback
    public func generateChat(prompt: String, forceLocal: Bool = false) -> InferenceResult {
        guard let handle = clientHandle else {
            return InferenceResult(text: "Error: Uninitialized", mode: "ERROR", tokensPerSecond: 0, latencyMs: 0, isMeshCoupled: false)
        }

        var mode: Int32 = 0
        var tokPerSec: Float = 0.0
        var latencyMs: Float = 0.0

        let cStr = prima_edge_client_generate_chat(
            handle,
            (prompt as NSString).utf8String,
            forceLocal ? 1 : 0,
            &mode,
            &tokPerSec,
            &latencyMs
        )

        let resultText = cStr != nil ? String(cString: cStr!) : ""
        prima_edge_client_free_string(cStr)

        let modeStr = (mode == 1) ? "SPECULATIVE_RING_COUPLED" : "OFFLINE_STANDALONE"

        return InferenceResult(
            text: resultText,
            mode: modeStr,
            tokensPerSecond: tokPerSec,
            latencyMs: latencyMs,
            isMeshCoupled: (mode == 1)
        )
    }
}

// C-ABI declarations matching prima_edge_client.hpp
@_silgen_name("prima_edge_client_create")
private func prima_edge_client_create(
    _ modelPath: UnsafePointer<CChar>?,
    _ meshUrl: UnsafePointer<CChar>?,
    _ timeoutMs: Float
) -> OpaquePointer?

@_silgen_name("prima_edge_client_destroy")
private func prima_edge_client_destroy(_ client: OpaquePointer?)

@_silgen_name("prima_edge_client_check_envelope")
private func prima_edge_client_check_envelope(
    _ client: OpaquePointer?,
    _ outMarginMb: UnsafeMutablePointer<Float>?
) -> Int32

@_silgen_name("prima_edge_client_probe_mesh")
private func prima_edge_client_probe_mesh(
    _ client: OpaquePointer?,
    _ outRttMs: UnsafeMutablePointer<Float>?
) -> Int32

@_silgen_name("prima_edge_client_generate_chat")
private func prima_edge_client_generate_chat(
    _ client: OpaquePointer?,
    _ prompt: UnsafePointer<CChar>?,
    _ forceLocal: Int32,
    _ outMode: UnsafeMutablePointer<Int32>?,
    _ outTokPerSec: UnsafeMutablePointer<Float>?,
    _ outLatencyMs: UnsafeMutablePointer<Float>?
) -> UnsafeMutablePointer<CChar>?

@_silgen_name("prima_edge_client_free_string")
private func prima_edge_client_free_string(_ str: UnsafeMutablePointer<CChar>?)
