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
 * Screen displaying modified files, line additions/deletions, and hunk summaries
 * resulting from AGI voice refactor directives.
 */
class DiffDetailScreen(
    carContext: CarContext,
    private val diffEntries: List<DiffFileEntry> = defaultDiffEntries
) : Screen(carContext) {

    data class DiffFileEntry(
        val filePath: String,
        val additions: Int,
        val deletions: Int,
        val summary: String
    )

    companion object {
        val defaultDiffEntries = listOf(
            DiffFileEntry(
                filePath = "MovesensePacketBuffer.kt",
                additions = 14,
                deletions = 2,
                summary = "Lockless ring buffer with zero-copy DMA packet handling"
            ),
            DiffFileEntry(
                filePath = "LauburuCarAppService.kt",
                additions = 28,
                deletions = 0,
                summary = "Android Auto Service binding and AllowAllHosts validator"
            ),
            DiffFileEntry(
                filePath = "VoiceCodingHudScreen.kt",
                additions = 45,
                deletions = 5,
                summary = "Glanceable 4-row HUD with reactive StateFlow template updates"
            )
        )
    }

    override fun onGetTemplate(): Template {
        val listBuilder = ItemList.Builder()
            .setNoItemsMessage("Working tree clean — No modified files.")

        val rows = diffEntries.map { entry ->
            val fileName = entry.filePath.substringAfterLast("/")
            val diffStats = "+${entry.additions}, -${entry.deletions} | ${entry.summary}"
            
            Row.Builder()
                .setTitle(AutomotiveConstraints.truncateTitle(fileName))
                .addText(AutomotiveConstraints.truncateRowText(diffStats))
                .setOnClickListener {
                    CarToast.makeText(
                        carContext,
                        "${entry.filePath}: +${entry.additions}/-${entry.deletions}",
                        CarToast.LENGTH_SHORT
                    ).show()
                }
                .build()
        }

        val safeRows = AutomotiveConstraints.constrainListItems(rows)
        safeRows.forEach { listBuilder.addItem(it) }

        return ListTemplate.Builder()
            .setHeaderAction(Action.BACK)
            .setTitle("Repository Diffs (${safeRows.size} Files)")
            .setSingleList(listBuilder.build())
            .build()
    }
}
