package com.lauburu.androidauto.agi.util

import androidx.car.app.model.Action
import androidx.car.app.model.Row

/**
 * Enforces strict Android Auto Jetpack Car App safety limits to prevent
 * driver distraction and runtime template construction exceptions.
 */
object AutomotiveConstraints {
    const val MAX_PANE_ROWS = 4
    const val MAX_PANE_ACTIONS = 2
    const val MAX_ACTION_STRIP_ACTIONS = 2
    const val MAX_ACTION_STRIP_CUSTOM_TITLES = 1
    const val MAX_LIST_ITEMS = 6
    const val MAX_ROW_TEXT_LENGTH = 128
    const val MAX_ROW_TITLE_LENGTH = 64
    const val MAX_BACKSTACK_DEPTH = 5

    /**
     * Truncates row subtitle text to glanceable length, appending ellipsis if truncated.
     * Returns fallback "--" if input is null or blank.
     */
    fun truncateRowText(text: String?, maxLength: Int = MAX_ROW_TEXT_LENGTH): String {
        if (text.isNullOrBlank()) return "--"
        val trimmed = text.trim()
        return if (trimmed.length > maxLength) {
            trimmed.take(maxLength) + "..."
        } else {
            trimmed
        }
    }

    /**
     * Truncates row title to glanceable length.
     * Returns fallback "Untitled" if input is null or blank.
     */
    fun truncateTitle(title: String?, maxLength: Int = MAX_ROW_TITLE_LENGTH): String {
        if (title.isNullOrBlank()) return "Untitled Directive"
        val trimmed = title.trim()
        return if (trimmed.length > maxLength) {
            trimmed.take(maxLength) + "..."
        } else {
            trimmed
        }
    }

    /**
     * Enforces maximum row count for a Pane (max 4 rows).
     */
    fun constrainRows(rows: List<Row>, maxRows: Int = MAX_PANE_ROWS): List<Row> {
        return rows.take(maxRows)
    }

    /**
     * Enforces maximum action count for a Pane (max 2 actions).
     */
    fun constrainActions(actions: List<Action>, maxActions: Int = MAX_PANE_ACTIONS): List<Action> {
        return actions.take(maxActions)
    }

    /**
     * Enforces maximum action count for an ActionStrip (max 2 actions).
     */
    fun constrainActionStrip(actions: List<Action>, maxActions: Int = MAX_ACTION_STRIP_ACTIONS): List<Action> {
        return actions.take(maxActions)
    }

    /**
     * Enforces maximum item count for a ListTemplate under driving motion (max 6 items).
     */
    fun constrainListItems(items: List<Row>, maxItems: Int = MAX_LIST_ITEMS): List<Row> {
        return items.take(maxItems)
    }

    /**
     * Safely constructs a Row with truncated title and text fallbacks.
     */
    fun safeBuildRow(title: String?, text: String?): Row {
        return Row.Builder()
            .setTitle(truncateTitle(title))
            .addText(truncateRowText(text))
            .build()
    }
}
