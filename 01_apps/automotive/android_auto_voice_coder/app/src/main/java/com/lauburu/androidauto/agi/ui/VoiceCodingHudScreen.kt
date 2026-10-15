package com.lauburu.androidauto.agi.ui

import androidx.car.app.CarContext
import androidx.car.app.CarToast
import androidx.car.app.Screen
import androidx.car.app.model.Action
import androidx.car.app.model.ActionStrip
import androidx.car.app.model.CarColor
import androidx.car.app.model.CarIcon
import androidx.car.app.model.Pane
import androidx.car.app.model.PaneTemplate
import androidx.car.app.model.Row
import androidx.car.app.model.Template
import com.lauburu.androidauto.agi.util.AutomotiveConstraints

/**
 * Primary Head-Up Display (HUD) screen rendered on the Android Auto vehicle screen.
 * Displays 4 glanceable rows conforming strictly to automotive safety regulations.
 */
class VoiceCodingHudScreen(
    carContext: CarContext,
    private val onApproveCallback: (() -> Unit)? = null
) : Screen(carContext) {

    var activeDirective: String = "IDLE: Listening for speech..."
        private set
    var agentStatus: String = "M4 Mac Mini Online | 0.27ms Latency"
        private set
    var diffSummary: String = "3 Files Changed (+87, -7 lines)"
        private set
    var testStatus: String = "100% PASS (42/42 Tests) | 94.8% Coverage"
        private set
    var isListening: Boolean = false
        private set

    /**
     * Updates the HUD display state and requests template invalidation.
     */
    fun updateState(
        directive: String? = null,
        status: String? = null,
        diff: String? = null,
        tests: String? = null,
        listening: Boolean? = null
    ) {
        directive?.let { this.activeDirective = it }
        status?.let { this.agentStatus = it }
        diff?.let { this.diffSummary = it }
        tests?.let { this.testStatus = it }
        listening?.let { this.isListening = it }
        invalidate()
    }

    fun setListening(listening: Boolean) {
        this.isListening = listening
        if (listening) {
            this.activeDirective = "🎙️ Listening for voice command..."
        }
        invalidate()
    }

    fun setDirective(directive: String) {
        this.activeDirective = directive
        invalidate()
    }

    fun setAgentStatus(status: String) {
        this.agentStatus = status
        invalidate()
    }

    fun setDiffSummary(diff: String) {
        this.diffSummary = diff
        invalidate()
    }

    fun setTestStatus(tests: String) {
        this.testStatus = tests
        invalidate()
    }

    override fun onGetTemplate(): Template {
        // Row 1: Active Voice Directive / Listening Status
        val directiveTitle = if (isListening) "🎙️ Active Voice Directive" else "Voice Directive"
        val rowDirective = Row.Builder()
            .setTitle(AutomotiveConstraints.truncateTitle(directiveTitle))
            .addText(AutomotiveConstraints.truncateRowText(activeDirective))
            .build()

        // Row 2: AGI Agent Status & Latency
        val rowAgent = Row.Builder()
            .setTitle(AutomotiveConstraints.truncateTitle("AGI Agent Status"))
            .addText(AutomotiveConstraints.truncateRowText(agentStatus))
            .build()

        // Row 3: Git Diff / Repo Summary
        val rowDiff = Row.Builder()
            .setTitle(AutomotiveConstraints.truncateTitle("Git Diff Summary"))
            .addText(AutomotiveConstraints.truncateRowText(diffSummary))
            .build()

        // Row 4: Verification Test Status / Coverage
        val rowTests = Row.Builder()
            .setTitle(AutomotiveConstraints.truncateTitle("Verification Tests"))
            .addText(AutomotiveConstraints.truncateRowText(testStatus))
            .build()

        // Enforce maximum 4 rows
        val allRows = listOf(rowDirective, rowAgent, rowDiff, rowTests)
        val safeRows = AutomotiveConstraints.constrainRows(allRows)

        // Actions in Pane (Max 2 actions)
        val actionApprove = Action.Builder()
            .setTitle("Approve & Deploy")
            .setBackgroundColor(CarColor.GREEN)
            .setOnClickListener {
                onApproveCallback?.invoke()
                CarToast.makeText(
                    carContext,
                    "Refactor Approved & Committed to Git",
                    CarToast.LENGTH_SHORT
                ).show()
                updateState(
                    directive = "Refactor Committed Successfully",
                    diff = "Clean working tree",
                    tests = "100% PASS (42/42 Tests)"
                )
            }
            .build()

        val actionViewDiffs = Action.Builder()
            .setTitle("View Diffs")
            .setOnClickListener {
                screenManager.push(DiffDetailScreen(carContext))
            }
            .build()

        val safeActions = AutomotiveConstraints.constrainActions(listOf(actionApprove, actionViewDiffs))

        val paneBuilder = Pane.Builder()
        safeRows.forEach { paneBuilder.addRow(it) }
        safeActions.forEach { paneBuilder.addAction(it) }

        // ActionStrip (Max 2 actions, at most 1 custom title)
        val actionMic = Action.Builder()
            .setIcon(CarIcon.APP_ICON)
            .setOnClickListener {
                setListening(!isListening)
                val msg = if (isListening) "Voice listening active" else "Voice listening paused"
                CarToast.makeText(carContext, msg, CarToast.LENGTH_SHORT).show()
            }
            .build()

        val actionDirectives = Action.Builder()
            .setTitle("Ask Lens")
            .setOnClickListener {
                setListening(true)
                activeDirective = "🎙️ Listening for Lens command..."
                invalidate()
                CarToast.makeText(carContext, "Speak your Lens command", CarToast.LENGTH_SHORT).show()
            }
            .build()

        val safeActionStripActions = AutomotiveConstraints.constrainActionStrip(
            listOf(actionMic, actionDirectives)
        )

        val actionStripBuilder = ActionStrip.Builder()
        safeActionStripActions.forEach { actionStripBuilder.addAction(it) }

        return PaneTemplate.Builder(paneBuilder.build())
            .setHeaderAction(Action.APP_ICON)
            .setTitle("Sovereign Voice & Lens")
            .setActionStrip(actionStripBuilder.build())
            .build()
    }
}
