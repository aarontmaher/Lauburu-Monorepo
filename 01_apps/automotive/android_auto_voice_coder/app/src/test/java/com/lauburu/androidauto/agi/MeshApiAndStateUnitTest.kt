package com.lauburu.androidauto.agi

import com.lauburu.androidauto.agi.api.MeshApiClient
import com.lauburu.androidauto.agi.api.MeshEndpoints
import com.lauburu.androidauto.agi.api.ParsedVoiceDirective
import com.lauburu.androidauto.agi.api.VoiceDirective
import com.lauburu.androidauto.agi.api.VoiceDirectiveParser
import com.lauburu.androidauto.agi.data.AgentState
import com.lauburu.androidauto.agi.data.ChatCompletionRequest
import com.lauburu.androidauto.agi.data.ChatCompletionResponse
import com.lauburu.androidauto.agi.data.ChatMessage
import com.lauburu.androidauto.agi.data.DiffStatsData
import com.lauburu.androidauto.agi.data.GitDiffSummary
import com.lauburu.androidauto.agi.data.GitStatusSummary
import com.lauburu.androidauto.agi.data.HudCardData
import com.lauburu.androidauto.agi.data.RefactorProposal
import com.lauburu.androidauto.agi.data.TestVerificationStatus
import com.lauburu.androidauto.agi.data.VoiceCodingDirectiveRequest
import com.lauburu.androidauto.agi.data.VoiceCodingDirectiveResponse
import com.lauburu.androidauto.agi.data.VoiceCodingRepository
import com.lauburu.androidauto.agi.data.VoiceCodingUiState
import com.lauburu.androidauto.agi.data.meshJson
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.TestScope
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.runTest
import kotlinx.serialization.encodeToString
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

@OptIn(ExperimentalCoroutinesApi::class)
class MeshApiAndStateUnitTest {

    // =========================================================================
    // 1. VoiceDirective & Parser Tests
    // =========================================================================

    @Test
    fun testCore5DirectivesEnumValues() {
        val directives = VoiceDirective.values()
        assertEquals(8, directives.size)
        assertTrue(directives.contains(VoiceDirective.EXPLAIN_DIFF))
        assertTrue(directives.contains(VoiceDirective.RUN_TESTS))
        assertTrue(directives.contains(VoiceDirective.REFACTOR))
        assertTrue(directives.contains(VoiceDirective.GIT_STATUS))
        assertTrue(directives.contains(VoiceDirective.COMMIT))
        assertTrue(directives.contains(VoiceDirective.REGION_BACKSPACE))
        assertTrue(directives.contains(VoiceDirective.UNDO_LAST_ACTION))
        assertTrue(directives.contains(VoiceDirective.UNKNOWN))
    }

    @Test
    fun testVoiceDirectiveFromToken() {
        assertEquals(VoiceDirective.EXPLAIN_DIFF, VoiceDirective.fromToken("EXPLAIN_DIFF"))
        assertEquals(VoiceDirective.EXPLAIN_DIFF, VoiceDirective.fromToken("EXPLAIN_GIT_DIFF"))
        assertEquals(VoiceDirective.RUN_TESTS, VoiceDirective.fromToken("RUN_TESTS"))
        assertEquals(VoiceDirective.RUN_TESTS, VoiceDirective.fromToken("RUN_VERIFICATION_TESTS"))
        assertEquals(VoiceDirective.REFACTOR, VoiceDirective.fromToken("REFACTOR"))
        assertEquals(VoiceDirective.REFACTOR, VoiceDirective.fromToken("DRAFT_FUNCTION_REFACTOR"))
        assertEquals(VoiceDirective.GIT_STATUS, VoiceDirective.fromToken("GIT_STATUS"))
        assertEquals(VoiceDirective.GIT_STATUS, VoiceDirective.fromToken("QUERY_GIT_STATUS"))
        assertEquals(VoiceDirective.COMMIT, VoiceDirective.fromToken("COMMIT"))
        assertEquals(VoiceDirective.COMMIT, VoiceDirective.fromToken("CONFIRM_GIT_COMMIT"))
        assertEquals(VoiceDirective.UNKNOWN, VoiceDirective.fromToken("NON_EXISTENT_TOKEN"))
        assertEquals(VoiceDirective.UNKNOWN, VoiceDirective.fromToken(null))
    }

    @Test
    fun testParserCore5Directives() {
        val cases = listOf(
            "Explain the latest diff in Movesense hub" to VoiceDirective.EXPLAIN_DIFF,
            "Run verification tests on Lauburu monorepo" to VoiceDirective.RUN_TESTS,
            "Refactor function zero-copy ring buffer" to VoiceDirective.REFACTOR,
            "Show git status and modified files" to VoiceDirective.GIT_STATUS,
            "Confirm commit and deploy changes" to VoiceDirective.COMMIT
        )

        for ((transcript, expectedDirective) in cases) {
            val parsed = VoiceDirectiveParser.parse(transcript)
            assertEquals("Expected $expectedDirective for '$transcript'", expectedDirective, parsed.directive)
            assertEquals(expectedDirective.token, parsed.action)
            assertEquals(expectedDirective.actionIntent, parsed.actionIntent)
            assertEquals(transcript, parsed.rawTranscript)
        }
    }

    @Test
    fun testParserBoundaryFillerWords() {
        val raw = "uh please could you hey agent explain diff right now"
        val parsed = VoiceDirectiveParser.parse(raw)
        assertEquals(VoiceDirective.EXPLAIN_DIFF, parsed.directive)
    }

    @Test
    fun testParserBoundaryMixedCasePunctuation() {
        val raw = "RUN TESTS NOW!!!"
        val parsed = VoiceDirectiveParser.parse(raw)
        assertEquals(VoiceDirective.RUN_TESTS, parsed.directive)
    }

    @Test
    fun testParserBoundaryUnsupportedDirective() {
        val raw = "Order a large pepperoni pizza"
        val parsed = VoiceDirectiveParser.parse(raw)
        assertEquals(VoiceDirective.UNKNOWN, parsed.directive)
    }

    @Test
    fun testParserBoundarySpecialCharactersInCode() {
        val raw = "refactor function parse_node<T>(\$id: Int)"
        val parsed = VoiceDirectiveParser.parse(raw)
        assertEquals(VoiceDirective.REFACTOR, parsed.directive)
        assertTrue(parsed.target.contains("parse_node"))
    }

    @Test
    fun testParserBoundaryEmptyAndNull() {
        assertEquals(VoiceDirective.UNKNOWN, VoiceDirectiveParser.parse("").directive)
        assertEquals(VoiceDirective.UNKNOWN, VoiceDirectiveParser.parse("   ").directive)
        assertEquals(VoiceDirective.UNKNOWN, VoiceDirectiveParser.parse(null).directive)
    }

    // =========================================================================
    // 2. MeshEndpoints URL Formatting Tests
    // =========================================================================

    @Test
    fun testMeshEndpointsConstants() {
        assertEquals("100.119.199.76", MeshEndpoints.DEFAULT_PRIMARY_HOST)
        assertEquals("192.168.8.230", MeshEndpoints.DEFAULT_FALLBACK_HOST)
        assertEquals(8081, MeshEndpoints.PORT_LLAMA)
        assertEquals(4000, MeshEndpoints.PORT_HUB)
        assertEquals(18802, MeshEndpoints.PORT_WOL)
        assertEquals(22, MeshEndpoints.PORT_SSH)
        assertEquals(8022, MeshEndpoints.PORT_TERMUX)
    }

    @Test
    fun testMeshEndpointsUrlBuilders() {
        assertEquals(
            "http://100.119.199.76:8081/v1/chat/completions",
            MeshEndpoints.buildLlamaChatCompletionsUrl()
        )
        assertEquals(
            "http://192.168.8.230:8081/v1/chat/completions",
            MeshEndpoints.buildLlamaChatCompletionsUrl(MeshEndpoints.DEFAULT_FALLBACK_HOST)
        )
        assertEquals(
            "http://100.119.199.76:4000/api/voice_coder/directive",
            MeshEndpoints.buildHubDirectiveUrl()
        )
        assertEquals(
            "http://100.119.199.76:4000/health",
            MeshEndpoints.buildHubHealthUrl()
        )
        assertEquals(
            "http://100.119.199.76:18802/api/wake",
            MeshEndpoints.buildWolWakeUrl()
        )
        assertEquals(
            "http://100.119.199.76:4000/api/git/status",
            MeshEndpoints.buildGitStatusUrl()
        )
    }

    // =========================================================================
    // 3. Models JSON Serialization & Deserialization Tests
    // =========================================================================

    @Test
    fun testChatCompletionRequestSerialization() {
        val req = ChatCompletionRequest(
            model = "qwen2.5-coder-7b-instruct",
            messages = listOf(
                ChatMessage("system", "You are the Lauburu in-car voice coding assistant."),
                ChatMessage("user", "Explain diff in Movesense BLE module")
            ),
            temperature = 0.2,
            max_tokens = 256
        )
        val jsonStr = req.toJson()
        assertTrue(jsonStr.contains("\"model\":\"qwen2.5-coder-7b-instruct\""))
        assertTrue(jsonStr.contains("\"max_tokens\":256"))
        assertTrue(jsonStr.contains("\"temperature\":0.2"))
        assertTrue(jsonStr.contains("Movesense BLE module"))
    }

    @Test
    fun testChatCompletionResponseDeserialization() {
        val jsonStr = """
            {
                "id": "chatcmpl-12345",
                "model": "qwen2.5-coder-7b-instruct",
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "Refactored Movesense ring buffer with zero-copy circular queue."
                        },
                        "finish_reason": "stop"
                    }
                ]
            }
        """.trimIndent()

        val resp = ChatCompletionResponse.fromJson(jsonStr)
        assertEquals("chatcmpl-12345", resp.id)
        assertEquals("qwen2.5-coder-7b-instruct", resp.model)
        assertEquals(1, resp.choices.size)
        assertEquals("Refactored Movesense ring buffer with zero-copy circular queue.", resp.assistantContent)
    }

    @Test
    fun testVoiceCodingDirectiveRequestAndResponseSerialization() {
        val req = VoiceCodingDirectiveRequest(
            directive = "RUN_TESTS",
            target = "all",
            timestamp = "2026-08-27T07:14:00Z",
            device = "Pixel 10 Pro XL (In-Vehicle)"
        )
        val jsonReq = req.toJson()
        assertTrue(jsonReq.contains("\"directive\":\"RUN_TESTS\""))
        assertTrue(jsonReq.contains("\"target\":\"all\""))

        val respJson = """
            {
                "directive_id": "c17e45a2-3f11-4712-8e10-91823ab49120",
                "timestamp_utc": "2026-08-27T07:16:05.450Z",
                "status": "SUCCESS",
                "action_executed": "RUN_VERIFICATION_TESTS",
                "spoken_summary": "All 42 test cases passed with zero errors across all 8 active mesh nodes.",
                "hud_card": {
                    "title": "Mesh Verification Suite",
                    "headline": "Tests: 100% PASS (42/42 Passed)",
                    "details": "0 Failures | Duration: 1.42s | 8/8 Nodes Nominal",
                    "diff_stats": {"files_changed": 0, "lines_added": 0, "lines_deleted": 0},
                    "status_indicator": "GREEN_PASS",
                    "actions": [
                        {"action_id": "re_run", "label": "Re-run", "is_primary": false}
                    ]
                },
                "lora_logged": true
            }
        """.trimIndent()

        val resp = VoiceCodingDirectiveResponse.fromJson(respJson)
        assertEquals("SUCCESS", resp.status)
        assertEquals("RUN_VERIFICATION_TESTS", resp.actionExecuted)
        assertEquals(true, resp.loraLogged)
        assertNotNull(resp.hudCard)
        assertEquals("Mesh Verification Suite", resp.hudCard?.title)
        assertEquals("GREEN_PASS", resp.hudCard?.statusIndicator)
    }

    @Test
    fun testDataModelsFormatting() {
        val diff = GitDiffSummary(filesChanged = 3, linesAdded = 45, linesDeleted = 3, details = "auth/security.py")
        assertEquals("+45, -3 (3 files)", diff.formattedStats)

        val testStatusPass = TestVerificationStatus(
            totalTests = 42,
            passedTests = 42,
            failedTests = 0,
            durationMs = 1420
        )
        assertTrue(testStatusPass.isPass)
        assertTrue(testStatusPass.formattedHeadline.contains("100% PASS"))

        val testStatusFail = TestVerificationStatus(
            totalTests = 42,
            passedTests = 40,
            failedTests = 2,
            durationMs = 2100
        )
        assertFalse(testStatusFail.isPass)
        assertTrue(testStatusFail.formattedHeadline.contains("FAIL (2/42 Failed)"))

        val gitStatusClean = GitStatusSummary(branch = "main", modifiedFiles = emptyList())
        assertTrue(gitStatusClean.isClean)
        assertTrue(gitStatusClean.formattedSummary.contains("Clean working tree"))

        val gitStatusDirty = GitStatusSummary(branch = "main", modifiedFiles = listOf("server.py", "README.md"))
        assertFalse(gitStatusDirty.isClean)
        assertTrue(gitStatusDirty.formattedSummary.contains("2 Modified Files"))
    }

    // =========================================================================
    // 4. MeshApiClient Payload Truncation & Offline Fallback Tests
    // =========================================================================

    @Test
    fun testPayloadTruncationBoundary() {
        val client = MeshApiClient()
        val shortPayload = "Short normal response"
        assertEquals(shortPayload, client.truncatePayloadIfNeeded(shortPayload))

        val jumboPayload = "A".repeat(15000)
        val truncated = client.truncatePayloadIfNeeded(jumboPayload)
        assertTrue(truncated.length < 2000)
        assertTrue(truncated.contains("Truncated 15000 bytes"))
    }

    @Test
    fun testOfflineFallbackCreation() {
        val fallback = VoiceCodingDirectiveResponse.createFallback(
            action = "EXPLAIN_GIT_DIFF",
            errorMessage = "ConnectException: Connection refused"
        )
        assertEquals("FAILED", fallback.status)
        assertEquals("EXPLAIN_GIT_DIFF", fallback.actionExecuted)
        assertTrue(fallback.spokenSummary.contains("unreachable"))
        assertNotNull(fallback.hudCard)
        assertEquals("RED_FAIL", fallback.hudCard?.statusIndicator)
    }

    // =========================================================================
    // 5. VoiceCodingUiState Immutability & Defaults
    // =========================================================================

    @Test
    fun testUiStateDefaultsAndImmutability() {
        val initial = VoiceCodingUiState.INITIAL
        assertEquals(AgentState.IDLE, initial.status)
        assertFalse(initial.isListening)
        assertFalse(initial.isSpeaking)
        assertFalse(initial.isLoading)
        assertNull(initial.errorMessage)
        assertEquals("Lauburu Voice Coder", initial.headerTitle)

        val updated = initial.copy(
            isListening = true,
            status = AgentState.LISTENING,
            speechTranscript = "Run tests"
        )
        // Original unchanged
        assertFalse(initial.isListening)
        assertEquals(AgentState.IDLE, initial.status)

        // Updated has new values
        assertTrue(updated.isListening)
        assertEquals(AgentState.LISTENING, updated.status)
        assertEquals("Run tests", updated.speechTranscript)
    }

    // =========================================================================
    // 6. VoiceCodingRepository UDF State Transitions
    // =========================================================================

    @Test
    fun testRepositoryVoiceListeningTransitions() = runTest {
        val testDispatcher = StandardTestDispatcher(testScheduler)
        val repo = VoiceCodingRepository(
            meshApiClient = MeshApiClient(ioDispatcher = testDispatcher),
            coroutineScope = this,
            ioDispatcher = testDispatcher
        )

        assertEquals(AgentState.IDLE, repo.uiState.value.status)
        assertFalse(repo.uiState.value.isListening)

        repo.startVoiceListening()
        assertTrue(repo.uiState.value.isListening)
        assertEquals(AgentState.LISTENING, repo.uiState.value.status)

        repo.stopVoiceListening()
        assertFalse(repo.uiState.value.isListening)
    }

    @Test
    fun testRepositoryExecuteDirectiveStateTransition() = runTest {
        val testDispatcher = StandardTestDispatcher(testScheduler)
        val repo = VoiceCodingRepository(
            meshApiClient = MeshApiClient(ioDispatcher = testDispatcher),
            coroutineScope = this,
            ioDispatcher = testDispatcher
        )

        repo.executeDirective(VoiceDirective.RUN_TESTS, mapOf("target" to "all"))
        // Synchronously enters processing state
        assertTrue(repo.uiState.value.isProcessing || repo.uiState.value.status == AgentState.PROCESSING_DIRECTIVE)
        assertTrue(repo.uiState.value.activeDirective.contains("Run Tests"))

        // Advance dispatcher
        advanceUntilIdle()

        // After execution completes, finishes safely
        assertFalse(repo.uiState.value.isProcessing)
    }

    @Test
    fun testRepositoryConcurrentDirectiveCancellation() = runTest {
        val testDispatcher = StandardTestDispatcher(testScheduler)
        val repo = VoiceCodingRepository(
            meshApiClient = MeshApiClient(ioDispatcher = testDispatcher),
            coroutineScope = this,
            ioDispatcher = testDispatcher
        )

        repo.executeDirective(VoiceDirective.EXPLAIN_DIFF)
        assertTrue(repo.uiState.value.activeDirective.contains("Explain Diff"))

        // Immediately trigger another directive
        repo.executeDirective(VoiceDirective.RUN_TESTS)
        assertTrue(repo.uiState.value.activeDirective.contains("Run Tests"))

        advanceUntilIdle()
        assertFalse(repo.uiState.value.isProcessing)
    }

    @Test
    fun testRepositoryStateReducerUpdate() {
        val repo = VoiceCodingRepository(
            meshApiClient = MeshApiClient(),
            coroutineScope = CoroutineScope(Dispatchers.Unconfined)
        )

        repo.updateUiState {
            it.copy(
                diffSummary = "5 Files Changed (+120, -10 lines)",
                testStatus = "PASS (50/50 Tests)"
            )
        }

        assertEquals("5 Files Changed (+120, -10 lines)", repo.uiState.value.diffSummary)
        assertEquals("PASS (50/50 Tests)", repo.uiState.value.testStatus)

        repo.resetState()
        assertEquals(VoiceCodingUiState.INITIAL, repo.uiState.value)
    }
}
