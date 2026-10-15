package com.lauburu.androidauto.agi.service

import android.content.Intent
import android.content.res.Configuration
import androidx.car.app.Screen
import androidx.car.app.Session
import androidx.lifecycle.DefaultLifecycleObserver
import androidx.lifecycle.LifecycleOwner
import com.lauburu.androidauto.agi.ui.VoiceCodingHudScreen

/**
 * Android Auto Session managing the in-vehicle UI lifecycle, configuration changes,
 * and root Screen stack navigation.
 */
class VoiceCodingSession : Session(), DefaultLifecycleObserver {

    private var rootHudScreen: VoiceCodingHudScreen? = null

    override fun onCreateScreen(intent: Intent): Screen = VoiceCodingHudScreen(carContext).also {
        lifecycle.addObserver(this)
        rootHudScreen = it
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        // Handle voice shortcut intents, notification deep links or directive payloads
        intent.getStringExtra("directive")?.let { directiveText ->
            rootHudScreen?.updateState(
                directive = directiveText,
                status = "Processing Spoken Directive..."
            )
        }
    }

    override fun onCarConfigurationChanged(newConfiguration: Configuration) {
        super.onCarConfigurationChanged(newConfiguration)
        // Invalidate screen on configuration changes (e.g. Day/Night mode switch)
        rootHudScreen?.invalidate()
    }

    override fun onDestroy(owner: LifecycleOwner) {
        super.onDestroy(owner)
        rootHudScreen = null
    }
}
