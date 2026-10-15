package com.lauburu.androidauto.agi

import android.app.Application
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.util.Log
import com.lauburu.androidauto.agi.api.MeshApiClient
import com.lauburu.androidauto.agi.data.VoiceCodingRepository
import com.lauburu.androidauto.agi.voice.VoiceInputManager
import com.lauburu.androidauto.agi.voice.VoiceOutputManager
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob

/**
 * Primary Application class for Lauburu Voice Coder.
 * Hosts the global shared repository instance accessible across both
 * the standalone mobile UI (MainActivity) and the Android Auto head unit session (LauburuCarAppService).
 */
class VoiceCodingApp : Application() {

    lateinit var repository: VoiceCodingRepository
        private set

    lateinit var meshApiClient: MeshApiClient
        private set

    lateinit var voiceInputManager: VoiceInputManager
        private set

    lateinit var voiceOutputManager: VoiceOutputManager
        private set

    private val applicationScope = CoroutineScope(SupervisorJob() + Dispatchers.Main)


    override fun onCreate() {
        super.onCreate()
        instance = this

        meshApiClient = MeshApiClient()
        voiceInputManager = VoiceInputManager(this)
        voiceOutputManager = VoiceOutputManager(this)
        repository = VoiceCodingRepository(
            meshApiClient = meshApiClient,
            voiceInputManager = voiceInputManager,
            voiceOutputManager = voiceOutputManager,
            coroutineScope = applicationScope
        )

        // Debug/ADB Automation: Intercept simulated speech intents
        val filter = IntentFilter("com.lauburu.intent.action.SIMULATE_SPEECH")
        val receiver = object : BroadcastReceiver() {
            override fun onReceive(context: Context, intent: Intent) {
                val transcript = intent.getStringExtra("transcript") ?: return
                Log.d("VoiceCodingApp", "ADB Simulation Intent Received: $transcript")
                repository.handleVoiceTranscript(transcript)
            }
        }
        if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(receiver, filter, Context.RECEIVER_EXPORTED)
        } else {
            registerReceiver(receiver, filter)
        }
    }

    companion object {
        lateinit var instance: VoiceCodingApp
            private set
    }
}
