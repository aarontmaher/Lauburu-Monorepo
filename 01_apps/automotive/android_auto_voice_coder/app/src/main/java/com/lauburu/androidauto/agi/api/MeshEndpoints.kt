package com.lauburu.androidauto.agi.api

/**
 * Constants and dynamic URL builder for Lauburu 7-layer mesh compute endpoints.
 * Provides connectivity configurations for Port 8081 (llama-server), Port 4000 (Hub),
 * and Port 18802 (Self-Healing / WoL).
 */
object MeshEndpoints {

    // Default Node Host Addresses
    const val LOOPBACK_HOST: String = "127.0.0.1" // High-speed ADB reverse tunnel (<0.5ms)
    const val DEFAULT_PRIMARY_HOST: String = "100.119.199.76" // Tailscale L3 overlay (Mac Mini M4 Host)
    const val DEFAULT_FALLBACK_HOST: String = "192.168.8.155" // Local Wi-Fi 7 Subnet LAN (Mac Mini M4 Host)
    const val DEFAULT_LINUX_NODE_HOST: String = "100.101.39.98" // Linux Head Node (Ryzen 7)
    const val DEFAULT_MAC_MINI_MAC_ADDR: String = "1c:f6:4c:7d:d7:0a"

    // Multi-Transport Candidate Hosts for Dynamic Fast Failover
    val CANDIDATE_HOSTS: List<String> = listOf(
        LOOPBACK_HOST,
        DEFAULT_PRIMARY_HOST,
        DEFAULT_FALLBACK_HOST,
        "192.168.8.230"
    )

    // Canonical Subsystem Ports
    const val PORT_LLAMA: Int = 8081
    const val PORT_HUB: Int = 4000
    const val PORT_WOL: Int = 18802
    const val PORT_SSH: Int = 22
    const val PORT_TERMUX: Int = 8022

    // API Paths
    const val PATH_CHAT_COMPLETIONS: String = "/v1/chat/completions"
    const val PATH_VOICE_CODER_DIRECTIVE: String = "/api/voice_coder/directive"
    const val PATH_HEALTH: String = "/health"
    const val PATH_HUB_HEALTH: String = "/api/health"
    const val PATH_WOL_WAKE: String = "/api/wake"
    const val PATH_GIT_STATUS: String = "/api/git/status"
    const val PATH_GIT_DIFF: String = "/api/git/diff"

    // Full Primary URLs
    const val PRIMARY_LLAMA_CHAT_URL: String = "http://$DEFAULT_PRIMARY_HOST:$PORT_LLAMA$PATH_CHAT_COMPLETIONS"
    const val FALLBACK_LLAMA_CHAT_URL: String = "http://$DEFAULT_FALLBACK_HOST:$PORT_LLAMA$PATH_CHAT_COMPLETIONS"
    const val PRIMARY_HUB_DIRECTIVE_URL: String = "http://$DEFAULT_PRIMARY_HOST:$PORT_HUB$PATH_VOICE_CODER_DIRECTIVE"
    const val PRIMARY_HUB_HEALTH_URL: String = "http://$DEFAULT_PRIMARY_HOST:$PORT_HUB$PATH_HEALTH"
    const val PRIMARY_WOL_WAKE_URL: String = "http://$DEFAULT_PRIMARY_HOST:$PORT_WOL$PATH_WOL_WAKE"

    /**
     * Builds the chat completions REST URL for llama.cpp master AI server.
     */
    fun buildLlamaChatCompletionsUrl(host: String = DEFAULT_PRIMARY_HOST): String {
        return "http://$host:$PORT_LLAMA$PATH_CHAT_COMPLETIONS"
    }

    /**
     * Builds the Port 4000 Compute Hub voice coder directive endpoint URL.
     */
    fun buildHubDirectiveUrl(host: String = DEFAULT_PRIMARY_HOST): String {
        return "http://$host:$PORT_HUB$PATH_VOICE_CODER_DIRECTIVE"
    }

    /**
     * Builds the Port 4000 Compute Hub health endpoint URL.
     */
    fun buildHubHealthUrl(host: String = DEFAULT_PRIMARY_HOST): String {
        return "http://$host:$PORT_HUB$PATH_HEALTH"
    }

    /**
     * Builds the Port 18802 Self-Healing Hub WoL wake endpoint URL.
     */
    fun buildWolWakeUrl(host: String = DEFAULT_PRIMARY_HOST): String {
        return "http://$host:$PORT_WOL$PATH_WOL_WAKE"
    }

    /**
     * Builds the Git status endpoint URL on Port 4000 Hub.
     */
    fun buildGitStatusUrl(host: String = DEFAULT_PRIMARY_HOST): String {
        return "http://$host:$PORT_HUB$PATH_GIT_STATUS"
    }
}
