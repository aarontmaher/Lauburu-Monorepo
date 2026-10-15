package com.lauburu.androidauto.agi.voice

import android.content.Context
import android.media.AudioAttributes
import android.media.AudioFocusRequest
import android.media.AudioManager

/**
 * AudioFocusController manages in-cabin audio focus ducking for Android Auto.
 * It requests transient audio focus with ducking (AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK)
 * with USAGE_ASSISTANT and CONTENT_TYPE_SPEECH so that background music or podcasts
 * are automatically ducked while the AGI assistant speaks to the driver.
 * Focus is immediately released via abandonAudioFocus() upon speech completion.
 */
class AudioFocusController(
    private val context: Context,
    private val onFocusLoss: (() -> Unit)? = null
) {
    private val audioManager: AudioManager =
        context.getSystemService(Context.AUDIO_SERVICE) as AudioManager

    private var audioFocusRequest: AudioFocusRequest? = null

    var isFocusHeld: Boolean = false
        private set

    /**
     * Request transient audio focus with ducking (AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK)
     * using USAGE_ASSISTANT and CONTENT_TYPE_SPEECH.
     * @return true if focus request was granted, false otherwise.
     */
    fun requestDuckFocus(): Boolean {
        val audioAttributes = AudioAttributes.Builder()
            .setUsage(AudioAttributes.USAGE_ASSISTANT)
            .setContentType(AudioAttributes.CONTENT_TYPE_SPEECH)
            .build()

        val request = AudioFocusRequest.Builder(AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK)
            .setAudioAttributes(audioAttributes)
            .setAcceptsDelayedFocusGain(false)
            .setOnAudioFocusChangeListener { focusChange ->
                when (focusChange) {
                    AudioManager.AUDIOFOCUS_LOSS,
                    AudioManager.AUDIOFOCUS_LOSS_TRANSIENT -> {
                        isFocusHeld = false
                        onFocusLoss?.invoke()
                    }
                    AudioManager.AUDIOFOCUS_LOSS_TRANSIENT_CAN_DUCK -> {
                        // Transient ducking allowed
                    }
                    AudioManager.AUDIOFOCUS_GAIN -> {
                        isFocusHeld = true
                    }
                }
            }
            .build()

        audioFocusRequest = request
        val result = audioManager.requestAudioFocus(request)
        isFocusHeld = (result == AudioManager.AUDIOFOCUS_REQUEST_GRANTED)
        return isFocusHeld
    }

    /**
     * Abandons the currently held audio focus request and restores cabin media volume.
     * @return true if focus was successfully abandoned or was not held.
     */
    fun abandonAudioFocus(): Boolean {
        val request = audioFocusRequest
        var success = true
        if (request != null) {
            val result = audioManager.abandonAudioFocusRequest(request)
            success = (result == AudioManager.AUDIOFOCUS_REQUEST_GRANTED)
            audioFocusRequest = null
        }
        isFocusHeld = false
        activePriority = AudioPriority.BACKGROUND_MEDIA
        return success
    }

    /**
     * Releases any held focus and cleans up resources.
     */
    fun release() {
        abandonAudioFocus()
    }

    var activePriority: AudioPriority = AudioPriority.BACKGROUND_MEDIA
        private set

    /**
     * Multi-level priority hierarchy for strict NHTSA driver safety.
     * Level 1 (Emergency Navigation) overrides Level 2 (Voice Coding IDE).
     */
    enum class AudioPriority(val level: Int) {
        EMERGENCY_NAVIGATION(1),
        VOICE_CODING_IDE(2),
        BACKGROUND_MEDIA(3);

        fun shouldYieldTo(other: AudioPriority): Boolean = other.level < this.level
    }

    /**
     * Checks whether the current audio focus should yield to an incoming audio event.
     * If true, immediately abandons audio focus to prevent driver distraction.
     */
    fun yieldIfLowerPriority(incoming: AudioPriority): Boolean {
        if (activePriority.shouldYieldTo(incoming)) {
            abandonAudioFocus()
            return true
        }
        return false
    }
}
