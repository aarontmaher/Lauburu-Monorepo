package com.lauburu.androidauto.agi

import androidx.car.app.OnDoneCallback
import androidx.car.app.SessionInfo
import androidx.car.app.model.Action
import androidx.car.app.model.CarColor
import androidx.car.app.model.ListTemplate
import androidx.car.app.model.PaneTemplate
import androidx.car.app.model.Row
import androidx.car.app.testing.TestCarContext
import androidx.car.app.validation.HostValidator
import androidx.test.core.app.ApplicationProvider
import com.lauburu.androidauto.agi.service.LauburuCarAppService
import com.lauburu.androidauto.agi.service.VoiceCodingSession
import com.lauburu.androidauto.agi.ui.DiffDetailScreen
import com.lauburu.androidauto.agi.ui.DirectivesListScreen
import com.lauburu.androidauto.agi.ui.TestResultScreen
import com.lauburu.androidauto.agi.ui.VoiceCodingHudScreen
import com.lauburu.androidauto.agi.util.AutomotiveConstraints
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertSame
import org.junit.Assert.assertTrue
import org.junit.Before
import org.junit.Test
import org.junit.runner.RunWith
import androidx.test.ext.junit.runners.AndroidJUnit4

@RunWith(AndroidJUnit4::class)
class ScreenTemplatesUnitTest {

    private lateinit var testCarContext: TestCarContext

    private val noOpDoneCallback = object : OnDoneCallback {}

    @Before
    fun setUp() {
        testCarContext = TestCarContext.createCarContext(
            ApplicationProvider.getApplicationContext()
        )
    }

    // =========================================================================
    // 1. LauburuCarAppService & HostValidator Tests
    // =========================================================================

    @Test
    fun testCarAppService_HostValidator() {
        val service = LauburuCarAppService()
        val validator = service.createHostValidator()
        assertNotNull(validator)
        assertSame(HostValidator.ALLOW_ALL_HOSTS_VALIDATOR, validator)
    }

    @Test
    fun testCarAppService_CreateSession() {
        val service = LauburuCarAppService()
        val session = service.onCreateSession(SessionInfo(1, "voice_coding_session"))
        assertNotNull(session)
        assertTrue(session is VoiceCodingSession)
    }

    // =========================================================================
    // 2. VoiceCodingSession Lifecycle Tests
    // =========================================================================

    @Test
    fun testVoiceCodingSession_CreateScreen() {
        val hudScreen = VoiceCodingHudScreen(testCarContext)
        assertNotNull(hudScreen)
        assertTrue(hudScreen.onGetTemplate() is PaneTemplate)
    }

    // =========================================================================
    // 3. AutomotiveConstraints Boundary Tests
    // =========================================================================

    @Test
    fun testAutomotiveConstraints_TruncateText() {
        val shortText = "Normal short diff summary"
        assertEquals(shortText, AutomotiveConstraints.truncateRowText(shortText))

        val longText = "A".repeat(200)
        val truncated = AutomotiveConstraints.truncateRowText(longText, 128)
        assertEquals(128 + 3, truncated.length) // 128 chars + "..."
        assertTrue(truncated.endsWith("..."))
    }

    @Test
    fun testAutomotiveConstraints_TruncateTextFallback() {
        assertEquals("--", AutomotiveConstraints.truncateRowText(null))
        assertEquals("--", AutomotiveConstraints.truncateRowText(""))
        assertEquals("--", AutomotiveConstraints.truncateRowText("   "))
    }

    @Test
    fun testAutomotiveConstraints_TruncateTitle() {
        val shortTitle = "Git Status"
        assertEquals(shortTitle, AutomotiveConstraints.truncateTitle(shortTitle))

        val longTitle = "T".repeat(100)
        val truncated = AutomotiveConstraints.truncateTitle(longTitle, 64)
        assertEquals(64 + 3, truncated.length)
        assertTrue(truncated.endsWith("..."))

        assertEquals("Untitled Directive", AutomotiveConstraints.truncateTitle(null))
        assertEquals("Untitled Directive", AutomotiveConstraints.truncateTitle(""))
    }

    @Test
    fun testAutomotiveConstraints_RowAndActionClamping() {
        val rows = (1..10).map { Row.Builder().setTitle("Row $it").build() }
        val clampedRows = AutomotiveConstraints.constrainRows(rows, 4)
        assertEquals(4, clampedRows.size)

        val actions = (1..5).map { Action.Builder().setTitle("Action $it").build() }
        val clampedActions = AutomotiveConstraints.constrainActions(actions, 2)
        assertEquals(2, clampedActions.size)

        val clampedActionStrip = AutomotiveConstraints.constrainActionStrip(actions, 2)
        assertEquals(2, clampedActionStrip.size)

        val listItems = (1..12).map { Row.Builder().setTitle("Item $it").build() }
        val clampedList = AutomotiveConstraints.constrainListItems(listItems, 6)
        assertEquals(6, clampedList.size)
    }

    @Test
    fun testAutomotiveConstraints_SafeBuildRow() {
        val row = AutomotiveConstraints.safeBuildRow(
            "Very Long Title That Needs Truncating Because Driving Safety Regulations Limit Headings",
            "Very long subtitle text exceeding the 128 character glanceability threshold to ensure driver is not distracted while operating vehicle on public roadways"
        )
        assertNotNull(row)
        assertNotNull(row.title)
        assertNotNull(row.texts)
    }

    // =========================================================================
    // 4. VoiceCodingHudScreen Template & State Mutation Tests
    // =========================================================================

    @Test
    fun testVoiceCodingHudScreen_TemplateStructure() {
        val hudScreen = VoiceCodingHudScreen(testCarContext)
        val template = hudScreen.onGetTemplate()

        assertTrue(template is PaneTemplate)
        val paneTemplate = template as PaneTemplate
        assertEquals(Action.APP_ICON, paneTemplate.headerAction)
        assertEquals("Lauburu Voice Coder", paneTemplate.title?.toString())

        val pane = paneTemplate.pane
        assertNotNull(pane)
        assertEquals(4, pane?.rows?.size)
        assertEquals(2, pane?.actions?.size)

        val actionStrip = paneTemplate.actionStrip
        assertNotNull(actionStrip)
        assertEquals(2, actionStrip?.actions?.size)
    }

    @Test
    fun testVoiceCodingHudScreen_StateMutations() {
        val hudScreen = VoiceCodingHudScreen(testCarContext)
        assertFalse(hudScreen.isListening)

        hudScreen.setListening(true)
        assertTrue(hudScreen.isListening)
        assertTrue(hudScreen.activeDirective.contains("Listening"))

        hudScreen.setDirective("Refactor Movesense packet buffer")
        assertEquals("Refactor Movesense packet buffer", hudScreen.activeDirective)

        hudScreen.setAgentStatus("Processing on Linux Head Node")
        assertEquals("Processing on Linux Head Node", hudScreen.agentStatus)

        hudScreen.setDiffSummary("+12, -4 lines in 2 files")
        assertEquals("+12, -4 lines in 2 files", hudScreen.diffSummary)

        hudScreen.setTestStatus("PASS: 55/55 Tests")
        assertEquals("PASS: 55/55 Tests", hudScreen.testStatus)

        hudScreen.updateState(
            directive = "Final Directive",
            status = "Ready",
            diff = "Clean",
            tests = "All Pass",
            listening = false
        )
        assertEquals("Final Directive", hudScreen.activeDirective)
        assertEquals("Ready", hudScreen.agentStatus)
        assertEquals("Clean", hudScreen.diffSummary)
        assertEquals("All Pass", hudScreen.testStatus)
        assertFalse(hudScreen.isListening)
    }

    @Test
    fun testVoiceCodingHudScreen_ApproveAction() {
        var approved = false
        val hudScreen = VoiceCodingHudScreen(testCarContext, onApproveCallback = {
            approved = true
        })

        val template = hudScreen.onGetTemplate() as PaneTemplate
        val approveAction = template.pane?.actions?.firstOrNull { it.title?.toString() == "Approve & Deploy" }
        assertNotNull(approveAction)
        assertEquals(CarColor.GREEN, approveAction?.backgroundColor)

        // Trigger click delegate
        approveAction?.onClickDelegate?.sendClick(noOpDoneCallback)
        assertTrue(approved)
    }

    // =========================================================================
    // 5. DiffDetailScreen Template Tests
    // =========================================================================

    @Test
    fun testDiffDetailScreen_TemplateStructure() {
        val diffScreen = DiffDetailScreen(testCarContext)
        val template = diffScreen.onGetTemplate()

        assertTrue(template is ListTemplate)
        val listTemplate = template as ListTemplate
        assertEquals(Action.BACK, listTemplate.headerAction)
        assertTrue(listTemplate.title?.toString()?.contains("Repository Diffs") == true)

        val itemList = listTemplate.singleList
        assertNotNull(itemList)
        assertEquals(3, itemList?.items?.size)
    }

    @Test
    fun testDiffDetailScreen_CustomEntriesClamping() {
        val customEntries = (1..10).map {
            DiffDetailScreen.DiffFileEntry("File$it.kt", it, it, "Summary for $it")
        }
        val diffScreen = DiffDetailScreen(testCarContext, customEntries)
        val template = diffScreen.onGetTemplate() as ListTemplate
        val items = template.singleList?.items
        assertNotNull(items)
        assertEquals(6, items?.size) // Clamped to MAX_LIST_ITEMS = 6
    }

    // =========================================================================
    // 6. TestResultScreen Template Tests
    // =========================================================================

    @Test
    fun testTestResultScreen_TemplateStructure_Passing() {
        var rerunCalled = false
        val testScreen = TestResultScreen(
            carContext = testCarContext,
            totalTests = 55,
            passedTests = 55,
            failedTests = 0,
            coveragePercent = 96.5,
            durationMs = 210,
            onRerun = { rerunCalled = true }
        )

        val template = testScreen.onGetTemplate()
        assertTrue(template is PaneTemplate)
        val paneTemplate = template as PaneTemplate
        assertEquals(Action.BACK, paneTemplate.headerAction)
        assertEquals("Verification Test Results", paneTemplate.title?.toString())

        val pane = paneTemplate.pane
        assertEquals(4, pane?.rows?.size)
        assertEquals(2, pane?.actions?.size)

        val rerunAction = pane?.actions?.firstOrNull { it.title?.toString() == "Re-run Tests" }
        assertNotNull(rerunAction)
        assertEquals(CarColor.GREEN, rerunAction?.backgroundColor)

        rerunAction?.onClickDelegate?.sendClick(noOpDoneCallback)
        assertTrue(rerunCalled)
    }

    @Test
    fun testTestResultScreen_TemplateStructure_Failing() {
        val testScreen = TestResultScreen(
            carContext = testCarContext,
            totalTests = 50,
            passedTests = 48,
            failedTests = 2,
            coveragePercent = 85.0
        )

        val template = testScreen.onGetTemplate() as PaneTemplate
        val pane = template.pane
        val rerunAction = pane?.actions?.firstOrNull { it.title?.toString() == "Re-run Tests" }
        assertNotNull(rerunAction)
        assertEquals(CarColor.RED, rerunAction?.backgroundColor)
    }

    // =========================================================================
    // 7. DirectivesListScreen Template Tests
    // =========================================================================

    @Test
    fun testDirectivesListScreen_TemplateStructure() {
        var selectedDirective: String? = null
        val directivesScreen = DirectivesListScreen(
            carContext = testCarContext,
            onDirectiveSelected = { selectedDirective = it }
        )

        val template = directivesScreen.onGetTemplate()
        assertTrue(template is ListTemplate)
        val listTemplate = template as ListTemplate
        assertEquals(Action.BACK, listTemplate.headerAction)
        assertTrue(listTemplate.title?.toString()?.contains("Voice Directives (5)") == true)

        val itemList = listTemplate.singleList
        assertNotNull(itemList)
        assertEquals(5, itemList?.items?.size)

        // Verify the 5 core voice directive titles
        val titles = itemList?.items?.map { (it as Row).title?.toString() } ?: emptyList()
        assertTrue(titles.contains("Explain Diff"))
        assertTrue(titles.contains("Run Tests"))
        assertTrue(titles.contains("Refactor Function"))
        assertTrue(titles.contains("Show Git Status"))
        assertTrue(titles.contains("Commit Changes"))
    }
}
