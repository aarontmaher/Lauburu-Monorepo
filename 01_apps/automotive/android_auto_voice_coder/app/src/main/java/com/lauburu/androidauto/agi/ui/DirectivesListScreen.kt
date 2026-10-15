package com.lauburu.androidauto.agi.ui

import androidx.car.app.CarContext
import androidx.car.app.CarToast
import androidx.car.app.Screen
import androidx.car.app.model.Action
import androidx.car.app.model.ItemList
import androidx.car.app.model.ListTemplate
import androidx.car.app.model.Row
import androidx.car.app.model.Template
import com.lauburu.androidauto.agi.util.AutomotiveConstraints

/**
 * Screen displaying the 5 core hands-free voice coding directives supported by the AGI agent.
 * Maps each VoiceDirective token to a glanceable in-car list item.
 */
class DirectivesListScreen(
    carContext: CarContext,
    private val onDirectiveSelected: ((String) -> Unit)? = null
) : Screen(carContext) {

    /**
     * VoiceDirective item model representing supported in-vehicle coding directives.
     */
    data class DirectiveItem(
        val token: String,
        val title: String,
        val description: String
    )

    // Supported VoiceDirective catalog for AGI agent
    private val supportedDirectives = listOf(
        DirectiveItem("EXPLAIN_DIFF", "Explain Diff", "Explain changes in active repository or file"),
        DirectiveItem("RUN_TESTS", "Run Tests", "Execute verification test suite across mesh"),
        DirectiveItem("REFACTOR", "Refactor Function", "Request targeted AST code refactoring"),
        DirectiveItem("GIT_STATUS", "Show Git Status", "Inspect branch status and modified files"),
        DirectiveItem("COMMIT", "Commit Changes", "Approve and commit drafted code changes")
    )

    override fun onGetTemplate(): Template {
        val listBuilder = ItemList.Builder()
            .setNoItemsMessage("No voice directives available.")

        val rows = supportedDirectives.map { item ->
            Row.Builder()
                .setTitle(AutomotiveConstraints.truncateTitle(item.title))
                .addText(AutomotiveConstraints.truncateRowText(item.description))
                .setOnClickListener {
                    onDirectiveSelected?.invoke(item.token)
                    CarToast.makeText(
                        carContext,
                        "VoiceDirective: ${item.title}",
                        CarToast.LENGTH_SHORT
                    ).show()
                    screenManager.pop()
                }
                .build()
        }

        val safeRows = AutomotiveConstraints.constrainListItems(rows)
        safeRows.forEach { listBuilder.addItem(it) }

        return ListTemplate.Builder()
            .setHeaderAction(Action.BACK)
            .setTitle("Voice Directives (${safeRows.size})")
            .setSingleList(listBuilder.build())
            .build()
    }
}
