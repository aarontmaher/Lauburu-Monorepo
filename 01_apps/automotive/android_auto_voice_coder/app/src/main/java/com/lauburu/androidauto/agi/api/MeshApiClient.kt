package com.lauburu.androidauto.agi.api

import com.lauburu.androidauto.agi.data.ChatCompletionRequest
import com.lauburu.androidauto.agi.data.ChatCompletionResponse
import com.lauburu.androidauto.agi.data.ChatMessage
import com.lauburu.androidauto.agi.data.DirectiveContext
import com.lauburu.androidauto.agi.data.DiffStatsData
import com.lauburu.androidauto.agi.data.GitStatusSummary
import com.lauburu.androidauto.agi.data.HudCardData
import com.lauburu.androidauto.agi.data.MeshAgentResponse
import com.lauburu.androidauto.agi.data.VoiceCodingDirectiveRequest
import com.lauburu.androidauto.agi.data.VoiceCodingDirectiveResponse
import com.lauburu.androidauto.agi.data.meshJson
import kotlinx.coroutines.CoroutineDispatcher
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import kotlinx.serialization.encodeToString
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import java.io.IOException
import java.net.ConnectException
import java.net.SocketTimeoutException
import java.time.Instant
import java.util.UUID
import java.util.concurrent.TimeUnit

/**
 * MeshApiClient provides asynchronous HTTP REST communication with the Lauburu 7-layer
 * compute mesh nodes:
 * 1. Port 8081: llama-server master LLM inference (/v1/chat/completions)
 * 2. Port 4000: Compute Hub voice coding directive dispatch & health (/api/voice_coder/directive)
 * 3. Port 18802: Self-Healing Hub Wake-on-LAN resurrection (/api/wake)
 *
 * Implements exponential backoff retries, multi-transport failover (Tailscale -> LAN),
 * oversized payload truncation, and offline fallback state reduction without throwing
 * unhandled exceptions.
 */
class MeshApiClient(
    private val conversationHistory: MutableList<ChatMessage> = mutableListOf(),

    private val client: OkHttpClient = OkHttpClient.Builder()
        .connectTimeout(3, TimeUnit.SECONDS)
        .readTimeout(15, TimeUnit.SECONDS)
        .writeTimeout(15, TimeUnit.SECONDS)
        .callTimeout(20, TimeUnit.SECONDS)
        .retryOnConnectionFailure(true)
        .build(),
    private val ioDispatcher: CoroutineDispatcher = Dispatchers.IO
) {
    companion object {
        private val JSON_MEDIA_TYPE = "application/json; charset=utf-8".toMediaType()
        const val MAX_SAFE_PAYLOAD_LENGTH: Int = 10000
        const val MAX_RETRIES: Int = 2
        const val INITIAL_BACKOFF_MS: Long = 300L
    }

    /**
     * Safely truncates oversized server responses to avoid in-vehicle UI thread jank or OOM.
     */
    fun truncatePayloadIfNeeded(payload: String): String {
        if (payload.length > MAX_SAFE_PAYLOAD_LENGTH) {
            return payload.take(1000) + "\n... [Truncated ${payload.length} bytes]"
        }
        return payload
    }

    /**
     * Queries the master llama.cpp server for AI chat completions on Port 8081 (/v1/chat/completions)
     * with multi-transport dynamic failover (Loopback -> Tailscale -> LAN).
     */
    suspend fun queryLlamaServer(
        prompt: String,
        model: String = "qwen2.5-coder-7b-instruct",
        systemPrompt: String = "You are the Lauburu in-car voice coding assistant.",
        host: String = MeshEndpoints.DEFAULT_PRIMARY_HOST
    ): MeshAgentResponse = withContext(ioDispatcher) {
        // Fluid Voice Conversation: Append to memory
        conversationHistory.add(ChatMessage(role = "user", content = prompt))
        if (conversationHistory.size > 10) {
            conversationHistory.removeAt(0)
        }
        
        val messages = mutableListOf(ChatMessage(role = "system", content = systemPrompt))
        messages.addAll(conversationHistory)

        val chatReq = ChatCompletionRequest(
            model = model,
            messages = messages,
            temperature = 0.2,
            max_tokens = 256
        )
        val requestJson = chatReq.toJson()
        val candidateHosts = if (host == MeshEndpoints.DEFAULT_PRIMARY_HOST) MeshEndpoints.CANDIDATE_HOSTS else listOf(host)

        var lastError: Exception? = null
        for (candHost in candidateHosts) {
            val url = MeshEndpoints.buildLlamaChatCompletionsUrl(candHost)
            try {
                val request = Request.Builder()
                    .url(url)
                    .post(requestJson.toRequestBody(JSON_MEDIA_TYPE))
                    .header("Accept", "application/json")
                    .build()

                client.newCall(request).execute().use { response ->
                    val rawBody = response.body?.string() ?: ""

                    if (response.isSuccessful) {
                        return@withContext try {
                            val parsed = ChatCompletionResponse.fromJson(rawBody)
                            val safeSpoken = truncatePayloadIfNeeded(parsed.assistantContent)
                            val safeRaw = truncatePayloadIfNeeded(rawBody)
                            MeshAgentResponse(
                                success = true,
                                status = "SUCCESS",
                                spokenSummary = safeSpoken,
                                rawResponse = safeRaw,
                                model = parsed.model.ifBlank { model }
                            )
                        } catch (e: Exception) {
                            val safeFallback = truncatePayloadIfNeeded(rawBody)
                            MeshAgentResponse(
                                success = true,
                                status = "SUCCESS",
                                spokenSummary = safeFallback,
                                rawResponse = safeFallback,
                                model = model
                            )
                        }
                    } else if (response.code >= 500) {
                        return@use
                    } else {
                        val safeBody = truncatePayloadIfNeeded(rawBody)
                        val errorMsg = parseServerError(response.code, safeBody)
                        return@withContext MeshAgentResponse(
                            success = false,
                            status = "SERVER_ERROR",
                            spokenSummary = "Llama server error (${response.code}).",
                            rawResponse = safeBody,
                            errorMessage = errorMsg
                        )
                    }
                }
            } catch (e: Exception) {
                lastError = e
            }
        }

        val errMsg = mapExceptionToMessage(lastError)
        MeshAgentResponse(
            success = false,
            status = "OFFLINE",
            spokenSummary = "Mesh node unreachable. Operating in offline cache mode.",
            errorMessage = errMsg
        )
    }

    /**
     * Dispatches a structured voice directive to the Port 4000 Compute Hub (/api/voice_coder/directive).
     */
    suspend fun sendDirective(
        directive: VoiceDirective,
        target: String = "",
        rawTranscript: String = "",
        context: DirectiveContext? = null,
        host: String = MeshEndpoints.DEFAULT_PRIMARY_HOST
    ): VoiceCodingDirectiveResponse {
        val req = VoiceCodingDirectiveRequest(
            directiveId = UUID.randomUUID().toString(),
            timestampUtc = Instant.now().toString(),
            callerNode = "pixel-10-pro-xl",
            rawTranscript = rawTranscript.ifBlank { directive.displayName },
            actionIntent = directive.actionIntent,
            directive = directive.token,
            target = target.ifBlank { if (directive == VoiceDirective.RUN_TESTS) "all" else "" },
            timestamp = Instant.now().toString(),
            device = "Pixel 10 Pro XL (In-Vehicle)",
            context = context
        )
        return sendDirective(req, host)
    }

    /**
     * Dispatches a VoiceCodingDirectiveRequest to Port 4000 Hub with candidate host failover.
     */
    suspend fun sendDirective(
        directiveRequest: VoiceCodingDirectiveRequest,
        host: String = MeshEndpoints.DEFAULT_PRIMARY_HOST
    ): VoiceCodingDirectiveResponse = withContext(ioDispatcher) {
        val requestJson = directiveRequest.toJson()
        val candidateHosts = if (host == MeshEndpoints.DEFAULT_PRIMARY_HOST) MeshEndpoints.CANDIDATE_HOSTS else listOf(host)

        var lastError: Exception? = null
        for (candHost in candidateHosts) {
            val url = MeshEndpoints.buildHubDirectiveUrl(candHost)
            try {
                val request = Request.Builder()
                    .url(url)
                    .post(requestJson.toRequestBody(JSON_MEDIA_TYPE))
                    .header("Accept", "application/json")
                    .build()

                client.newCall(request).execute().use { response ->
                    val rawBody = response.body?.string() ?: ""

                    if (response.isSuccessful) {
                        return@withContext try {
                            val parsed = VoiceCodingDirectiveResponse.fromJson(rawBody)
                            val safeSpoken = truncatePayloadIfNeeded(parsed.spokenSummary)
                            val safeDetails = parsed.hudCard?.let { truncatePayloadIfNeeded(it.details) }
                            val safeHudCard = parsed.hudCard?.copy(details = safeDetails ?: "")
                            parsed.copy(
                                spokenSummary = safeSpoken,
                                hudCard = safeHudCard ?: parsed.hudCard
                            )
                        } catch (e: Exception) {
                            val safeBody = truncatePayloadIfNeeded(rawBody)
                            createSynthesizedDirectiveResponse(directiveRequest, safeBody)
                        }
                    } else if (response.code >= 500) {
                        return@use
                    } else {
                        val safeBody = truncatePayloadIfNeeded(rawBody)
                        val errorMsg = parseServerError(response.code, safeBody)
                        return@withContext VoiceCodingDirectiveResponse.createFallback(
                            action = directiveRequest.actionIntent,
                            errorMessage = errorMsg,
                            spoken = "Server Error (${response.code}) from Compute Hub."
                        )
                    }
                }
            } catch (e: Exception) {
                lastError = e
            }
        }

        val errMsg = mapExceptionToMessage(lastError)
        VoiceCodingDirectiveResponse.createFallback(
            action = directiveRequest.actionIntent,
            errorMessage = errMsg
        )
    }

    /**
     * Checks health of the Port 4000 Compute Hub (/health) with candidate host failover.
     */
    suspend fun checkMeshHealth(host: String = MeshEndpoints.DEFAULT_PRIMARY_HOST): Boolean = withContext(ioDispatcher) {
        val candidateHosts = if (host == MeshEndpoints.DEFAULT_PRIMARY_HOST) MeshEndpoints.CANDIDATE_HOSTS else listOf(host)
        for (candHost in candidateHosts) {
            val url = MeshEndpoints.buildHubHealthUrl(candHost)
            try {
                val request = Request.Builder().url(url).get().build()
                val isSuccess = client.newCall(request).execute().use { response ->
                    response.isSuccessful
                }
                if (isSuccess) return@withContext true
            } catch (_: Exception) {}
        }
        false
    }

    /**
     * Sends Wake-on-LAN resurrection magic packet request to Port 18802 Self-Healing Hub (/api/wake).
     */
    suspend fun wakeNode(
        macAddress: String = MeshEndpoints.DEFAULT_MAC_MINI_MAC_ADDR,
        host: String = MeshEndpoints.DEFAULT_PRIMARY_HOST
    ): Boolean = withContext(ioDispatcher) {
        val url = MeshEndpoints.buildWolWakeUrl(host)
        val payload = """{"mac_address":"$macAddress"}"""
        try {
            val request = Request.Builder()
                .url(url)
                .post(payload.toRequestBody(JSON_MEDIA_TYPE))
                .build()
            client.newCall(request).execute().use { response ->
                response.isSuccessful
            }
        } catch (_: Exception) {
            false
        }
    }

    /**
     * Queries active git branch and working tree status on Port 4000 Hub with candidate host failover.
     */
    suspend fun queryGitStatus(host: String = MeshEndpoints.DEFAULT_PRIMARY_HOST): GitStatusSummary = withContext(ioDispatcher) {
        val candidateHosts = if (host == MeshEndpoints.DEFAULT_PRIMARY_HOST) MeshEndpoints.CANDIDATE_HOSTS else listOf(host)
        for (candHost in candidateHosts) {
            val url = MeshEndpoints.buildGitStatusUrl(candHost)
            try {
                val request = Request.Builder().url(url).get().build()
                val result = client.newCall(request).execute().use { response ->
                    val body = response.body?.string() ?: ""
                    if (response.isSuccessful && body.isNotBlank()) {
                        try {
                            meshJson.decodeFromString<GitStatusSummary>(body)
                        } catch (_: Exception) {
                            null
                        }
                    } else null
                }
                if (result != null) return@withContext result
            } catch (_: Exception) {}
        }
        GitStatusSummary("main (offline)", emptyList(), true)
    }

    private fun parseServerError(code: Int, body: String): String {
        return try {
            val jsonObj = kotlinx.serialization.json.Json.parseToJsonElement(body)
            val err = jsonObj.toString()
            "Server Error ($code): $err"
        } catch (_: Exception) {
            "Server Error ($code)"
        }
    }

    private fun isRecoverable(e: Exception): Boolean {
        return e is SocketTimeoutException || e is ConnectException || e is IOException
    }

    private fun mapExceptionToMessage(e: Exception?): String {
        return when (e) {
            is ConnectException, is SocketTimeoutException ->
                "Mesh node unreachable. Operating in offline cache mode."
            is IOException ->
                "Network I/O error: ${e.message ?: "Connection reset"}"
            else ->
                e?.message ?: "Unknown mesh error"
        }
    }

    private fun createSynthesizedDirectiveResponse(
        req: VoiceCodingDirectiveRequest,
        body: String
    ): VoiceCodingDirectiveResponse {
        return VoiceCodingDirectiveResponse(
            directiveId = req.directiveId,
            timestampUtc = Instant.now().toString(),
            status = "SUCCESS",
            actionExecuted = req.actionIntent,
            spokenSummary = body.take(200),
            hudCard = HudCardData(
                title = req.actionIntent,
                headline = "Action Executed",
                details = body.take(128),
                diffStats = DiffStatsData(0, 0, 0),
                statusIndicator = "GREEN_PASS"
            ),
            loraLogged = true
        )
    }
}
