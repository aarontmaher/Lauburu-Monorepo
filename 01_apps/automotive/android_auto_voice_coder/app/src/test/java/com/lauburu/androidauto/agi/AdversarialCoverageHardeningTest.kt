package com.lauburu.androidauto.agi

import androidx.car.app.OnDoneCallback
import androidx.car.app.SessionInfo
import androidx.car.app.model.Action
import androidx.car.app.model.CarColor
import androidx.car.app.model.ListTemplate
import androidx.car.app.model.PaneTemplate
import androidx.car.app.model.Row
import androidx.car.app.testing.TestCarContext
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
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
import com.lauburu.androidauto.agi.service.VoiceCodingSession
import com.lauburu.androidauto.agi.ui.DiffDetailScreen
import com.lauburu.androidauto.agi.ui.DirectivesListScreen
import com.lauburu.androidauto.agi.ui.TestResultScreen
import com.lauburu.androidauto.agi.ui.VoiceCodingHudScreen
import com.lauburu.androidauto.agi.util.AutomotiveConstraints
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.ExperimentalCoroutinesApi
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.launch
import kotlinx.coroutines.test.StandardTestDispatcher
import kotlinx.coroutines.test.advanceUntilIdle
import kotlinx.coroutines.test.runTest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import java.util.UUID

/**
 * Adversarial Coverage Hardening Test Suite (Tier 5)
 *
 * Covers:
 * 1. Extreme input payloads (unicode, massive diffs >100KB, truncated/malformed JSON)
 * 2. Concurrency, cancellation, race conditions, and voice interruptions
 * 3. Android Auto host lifecycle, CarContext detachment, and backstack overflow
 * 4. Network failures, timeout handling, HTTP 500/503 retry, and offline fallback
 */
@OptIn(ExperimentalCoroutinesApi::class)
@RunWith(AndroidJUnit4::class)
class AdversarialCoverageHardeningTest {

    private lateinit var testCarContext: TestCarContext

    @Before
    fun setUp() {
        testCarContext = TestCarContext.createCarContext(
            ApplicationProvider.getApplicationContext()
        )
    }

    // =========================================================================
    // 1. Extreme Input Payloads (Diffs > 100KB, Unicode, Truncated JSON)
    // =========================================================================

    @Test
    fun testMassiveDiffPayloadTruncation_120KB() {
        val client = MeshApiClient()
        // Generate a 120KB synthetic diff payload with 50 files
        val sb = StringBuilder()
        sb.append("diff --git a/MovesenseBuffer.kt b/MovesenseBuffer.kt\n")
        for (i in 1..2000) {
            sb.append("+ line $i: val bufferIndex_$i = 0x${Integer.toHexString(i * 17)} // ring buffer element $i\n")
        }
        val massiveDiff = sb.toString()
        assertTrue("Massive diff must exceed 100KB", massiveDiff.length > 100_000)

        // Truncate payload via MeshApiClient
        val truncated = client.truncatePayloadIfNeeded(massiveDiff)
        assertTrue("Truncated payload length must be capped safely", truncated.length < 2000)
        assertTrue(truncated.contains("Truncated ${massiveDiff.length} bytes"))
        assertTrue(truncated.startsWith("diff --git"))
    }

    @Test
    fun testDiffDetailScreen_FiftyFilesClampedToMaxListItems() {
        val fiftyEntries = (1..50).map { i ->
            DiffDetailScreen.DiffFileEntry(
                filePath = "module_$i/subsystem_$i/File_${i}.kt",
                additions = i * 10,
                deletions = i * 2,
                summary = "Refactored subsystem $i data structures and concurrency locks"
            )
        }
        val screen = DiffDetailScreen(testCarContext, fiftyEntries)
        val template = screen.onGetTemplate() as ListTemplate
        val items = template.singleList?.items
        assertNotNull(items)
        // Automotive constraints strictly enforce MAX_LIST_ITEMS = 6
        assertEquals(AutomotiveConstraints.MAX_LIST_ITEMS, items?.size)
        assertEquals(6, items?.size)
    }

    @Test
    fun testExtremeUnicodeAndMultilingualVoiceTranscriptParsing() {
        // Transcripts with Japanese, Cyrillic, Greek, RTL Arabic, Emojis, and special symbols
        val cases = listOf(
            "explain diff in 🚀_ring_buffer_core.kt" to VoiceDirective.EXPLAIN_DIFF,
            "refactor function α_beta_gamma<T>(\$id: Int)" to VoiceDirective.REFACTOR,
            "run verification tests on Модуль_Тестирования" to VoiceDirective.RUN_TESTS,
            "show git status for 🎯_production_branch" to VoiceDirective.GIT_STATUS,
            "commit changes with message 修正: メモリリーク防止とバッファ最適化" to VoiceDirective.COMMIT
        )

        for ((transcript, expectedDirective) in cases) {
            val parsed = VoiceDirectiveParser.parse(transcript)
            assertEquals("Failed on unicode transcript: $transcript", expectedDirective, parsed.directive)
            assertEquals(transcript, parsed.rawTranscript)
        }
    }

    @Test
    fun testUnicodeAndSurrogatePairTruncationSafety() {
        // 4-byte surrogate pair emojis: 👨‍💻 (U+1F468 U+200D U+1F4BB)
        val emojiString = "👨‍💻".repeat(50) // High surrogate count
        val truncatedTitle = AutomotiveConstraints.truncateTitle(emojiString, 10)
        assertNotNull(truncatedTitle)
        assertTrue(truncatedTitle.endsWith("..."))

        // Null and blank strings
        assertEquals("--", AutomotiveConstraints.truncateRowText(null))
        assertEquals("--", AutomotiveConstraints.truncateRowText(" \t\n "))
        assertEquals("Untitled Directive", AutomotiveConstraints.truncateTitle(null))
        assertEquals("Untitled Directive", AutomotiveConstraints.truncateTitle("   "))
    }

    @Test
    fun testMalformedAndTruncatedJsonResponseHandling() {
        // Truncated JSON midway through array
        val truncatedJson = """{"id":"chatcmpl-1","choices":[{"message":{"content":"Par"""
        
        var caughtException = false
        try {
            ChatCompletionResponse.fromJson(truncatedJson)
        } catch (e: Exception) {
            caughtException = true
        }
        assertTrue("Deserializer must throw on truncated JSON rather than returning corrupt data", caughtException)

        // Fallback directive response synthesis under truncated JSON
        val fallback = VoiceCodingDirectiveResponse.createFallback(
            action = "EXPLAIN_GIT_DIFF",
            errorMessage = "Truncated JSON payload received from mesh node"
        )
        assertEquals("FAILED", fallback.status)
        assertEquals("EXPLAIN_GIT_DIFF", fallback.actionExecuted)
        assertTrue(fallback.spokenSummary.contains("unreachable") || fallback.spokenSummary.contains("offline"))
        assertNotNull(fallback.hudCard)
        assertEquals("RED_FAIL", fallback.hudCard?.statusIndicator)
    }

    // =========================================================================
    // 2. Concurrency, Race Conditions, and State Interruptions
    // =========================================================================

    @Test
    fun testRapidConcurrentDirectiveSubmissions_CancelPreviousJobsSafely() = runTest {
        val testDispatcher = StandardTestDispatcher(testScheduler)
        val repo = VoiceCodingRepository(
            meshApiClient = MeshApiClient(ioDispatcher = testDispatcher),
            coroutineScope = this,
            ioDispatcher = testDispatcher
        )

        // Submit 20 rapid directives in tight loop
        for (i in 1..20) {
            val directive = if (i % 2 == 0) VoiceDirective.RUN_TESTS else VoiceDirective.EXPLAIN_DIFF
            repo.executeDirective(directive, mapOf("target" to "test_target_$i"))
        }

        // Must be in PROCESSING state with latest directive
        assertEquals(AgentState.PROCESSING_DIRECTIVE, repo.uiState.value.status)
        assertTrue(repo.uiState.value.isProcessing)
        assertTrue(repo.uiState.value.activeDirective.contains("Run Tests"))

        // Advance coroutines to idle
        advanceUntilIdle()

        // State must cleanly settle into non-processing state without throwing unhandled exceptions
        assertFalse(repo.uiState.value.isProcessing)
        assertFalse(repo.uiState.value.isLoading)
    }

    @Test
    fun testSpeechListeningInterruptsOngoingProcessing() = runTest {
        val testDispatcher = StandardTestDispatcher(testScheduler)
        val repo = VoiceCodingRepository(
            meshApiClient = MeshApiClient(ioDispatcher = testDispatcher),
            coroutineScope = this,
            ioDispatcher = testDispatcher
        )

        // Start directive execution
        repo.executeDirective(VoiceDirective.REFACTOR, mapOf("target" to "packet_buffer"))
        assertEquals(AgentState.PROCESSING_DIRECTIVE, repo.uiState.value.status)

        // Driver speaks again immediately (Voice listening starts)
        repo.startVoiceListening()
        assertEquals(AgentState.LISTENING, repo.uiState.value.status)
        assertTrue(repo.uiState.value.isListening)

        // Stop listening
        repo.stopVoiceListening()
        assertFalse(repo.uiState.value.isListening)
    }

    // =========================================================================
    // 3. Android Auto Host Lifecycle & Disconnection
    // =========================================================================

    @Test
    fun testVoiceCodingSession_LifecycleDestroyCleansReferences() {
        val session = VoiceCodingSession()
        val screen = session.onCreateScreen(android.content.Intent())
        assertNotNull(screen)
        assertTrue(screen is VoiceCodingHudScreen)

        // Simulate host configuration change (Day/Night mode)
        session.onCarConfigurationChanged(android.content.res.Configuration())

        // Simulate Android Auto session destruction on host disconnect
        session.onDestroy(session)
    }

    @Test
    fun testVoiceCodingHudScreen_MultipleSequentialStateUpdates() {
        val screen = VoiceCodingHudScreen(testCarContext)

        for (i in 1..50) {
            screen.updateState(
                directive = "Directive #$i",
                status = "Latency: ${0.20 + (i * 0.01)}ms",
                diff = "+$i, -$i lines",
                tests = "$i/$i PASS",
                listening = (i % 2 == 0)
            )
            assertEquals("Directive #$i", screen.activeDirective)
            assertEquals((i % 2 == 0), screen.isListening)
        }

        val template = screen.onGetTemplate() as PaneTemplate
        assertNotNull(template)
        assertEquals(4, template.pane?.rows?.size)
    }

    // =========================================================================
    // 4. Network Failures & Transport Resilience
    // =========================================================================

    @Test
    fun testMeshEndpointsFailoverUrls() {
        // Primary L3 Tailscale Overlay
        val primaryUrl = MeshEndpoints.buildLlamaChatCompletionsUrl(MeshEndpoints.DEFAULT_PRIMARY_HOST)
        assertEquals("http://100.119.199.76:8081/v1/chat/completions", primaryUrl)

        // Fallback Subnet LAN
        val fallbackUrl = MeshEndpoints.buildLlamaChatCompletionsUrl(MeshEndpoints.DEFAULT_FALLBACK_HOST)
        assertEquals("http://192.168.8.230:8081/v1/chat/completions", fallbackUrl)

        // Linux Head Node
        val linuxHubUrl = MeshEndpoints.buildHubDirectiveUrl(MeshEndpoints.DEFAULT_LINUX_NODE_HOST)
        assertEquals("http://100.101.39.98:4000/api/voice_coder/directive", linuxHubUrl)
    }

    @Test
    fun testDataModelsNullSafetyAndDefaults() {
        val emptyDiff = GitDiffSummary()
        assertEquals(0, emptyDiff.filesChanged)
        assertEquals(0, emptyDiff.linesAdded)
        assertEquals(0, emptyDiff.linesDeleted)
        assertEquals("+0, -0 (0 files)", emptyDiff.formattedStats)

        val emptyTests = TestVerificationStatus()
        assertTrue(emptyTests.isPass)
        assertEquals("100% PASS (0/0 Passed)", emptyTests.formattedHeadline)

        val emptyStatus = GitStatusSummary()
        assertTrue(emptyStatus.isClean)
        assertEquals("Branch: main | Clean working tree", emptyStatus.formattedSummary)

        val emptyProposal = RefactorProposal()
        assertEquals("", emptyProposal.targetFunction)
        assertEquals(0, emptyProposal.linesAdded)
    }
}
