package com.lauburu.androidauto.agi.voice

import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import androidx.core.content.ContextCompat

/**
 * State enum representing the active lifecycle of the in-cabin voice input engine.
 */
enum class VoiceInputState {
    IDLE,
    LISTENING,
    PROCESSING,
    ERROR
}

/**
 * Callback interface for receiving speech recognition events, partial transcripts,
 * final results, and driving-optimized error notifications.
 */
interface VoiceInputCallback {
    fun onStateChanged(state: VoiceInputState) {}
    fun onReadyForSpeech() {}
    fun onBeginningOfSpeech() {}
    fun onRmsChanged(rmsdB: Float) {}
    fun onPartialResult(partialTranscript: String) {}
    fun onFinalResult(finalTranscript: String) {}
    fun onError(errorCode: Int, errorMessage: String) {}
}

/**
 * VoiceInputManager coordinates hands-free speech recognition for Android Auto.
 * It encapsulates Android's SpeechRecognizer, implements RecognitionListener,
 * exposes structured callbacks via VoiceInputCallback, and provides a 16kHz PCM
 * audio buffer contract for Whisper fallback when offline or recognizing complex code AST tokens.
 */
class VoiceInputManager(
    private val context: Context,
    private var callback: VoiceInputCallback? = null
) {
    companion object {
        const val SAMPLE_RATE_16KHZ: Int = 16000
        const val WHISPER_FALLBACK_AUDIO_SOURCE: String = "16kHz_mono_pcm"
        const val EXTRA_SPEECH_SILENCE_TIMEOUT_MS: Long = 1500L
    }

    private val mainHandler = Handler(Looper.getMainLooper())
    private var speechRecognizer: SpeechRecognizer? = null

    var currentState: VoiceInputState = VoiceInputState.IDLE
        private set

    fun setCallback(callback: VoiceInputCallback?) {
        this.callback = callback
    }

    /**
     * Checks if speech recognition is available on the host device.
     */
    fun isRecognitionAvailable(): Boolean {
        return SpeechRecognizer.isRecognitionAvailable(context)
    }

    /**
     * Checks if RECORD_AUDIO permission has been granted.
     */
    fun hasRecordAudioPermission(): Boolean {
        return ContextCompat.checkSelfPermission(
            context,
            android.Manifest.permission.RECORD_AUDIO
        ) == PackageManager.PERMISSION_GRANTED
    }

    private fun runOnMainThread(block: () -> Unit) {
        if (Looper.myLooper() == Looper.getMainLooper()) {
            block()
        } else {
            mainHandler.post(block)
        }
    }

    private fun internalTeardown(cancelRecognition: Boolean = false) {
        try {
            if (cancelRecognition) {
                speechRecognizer?.cancel()
            } else {
                speechRecognizer?.stopListening()
            }
            speechRecognizer?.destroy()
        } catch (_: Exception) {}
        speechRecognizer = null
        if (currentState == VoiceInputState.LISTENING || currentState == VoiceInputState.PROCESSING) {
            updateState(VoiceInputState.IDLE)
        }
    }

    /**
     * Begins listening for hands-free voice commands.
     * Must be called on or dispatched to the Main thread as required by SpeechRecognizer.
     */
    fun startListening() {
        if (!hasRecordAudioPermission()) {
            updateState(VoiceInputState.ERROR)
            callback?.onError(
                SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS,
                "RECORD_AUDIO permission missing or revoked."
            )
            return
        }

        if (!isRecognitionAvailable()) {
            updateState(VoiceInputState.ERROR)
            callback?.onError(
                SpeechRecognizer.ERROR_CLIENT,
                "Speech recognition is not available on this device. Fallback to Whisper recommended."
            )
            return
        }

        runOnMainThread {
            try {
                internalTeardown(cancelRecognition = false) // Immediate synchronous teardown of previous instance

                val recognizer = try {
                    if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.S &&
                        SpeechRecognizer.isOnDeviceRecognitionAvailable(context)) {
                        SpeechRecognizer.createOnDeviceSpeechRecognizer(context)
                    } else {
                        SpeechRecognizer.createSpeechRecognizer(context)
                    }
                } catch (_: Exception) {
                    SpeechRecognizer.createSpeechRecognizer(context)
                }.apply {
                    setRecognitionListener(createRecognitionListener())
                }
                speechRecognizer = recognizer

                val recognizerIntent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
                    putExtra(RecognizerIntent.EXTRA_CALLING_PACKAGE, context.packageName)
                    putExtra(
                        RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                        RecognizerIntent.LANGUAGE_MODEL_FREE_FORM
                    )
                    putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, true)
                    putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
                    putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 3)
                    putExtra(
                        RecognizerIntent.EXTRA_SPEECH_INPUT_MINIMUM_LENGTH_MILLIS,
                        1000L
                    )
                    putExtra(
                        RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS,
                        EXTRA_SPEECH_SILENCE_TIMEOUT_MS
                    )
                    putExtra(
                        RecognizerIntent.EXTRA_SPEECH_INPUT_POSSIBLY_COMPLETE_SILENCE_LENGTH_MILLIS,
                        1000L
                    )
                }

                updateState(VoiceInputState.LISTENING)
                recognizer.startListening(recognizerIntent)
            } catch (e: Exception) {
                updateState(VoiceInputState.ERROR)
                callback?.onError(
                    SpeechRecognizer.ERROR_CLIENT,
                    "Failed to initialize SpeechRecognizer: ${e.message}"
                )
            }
        }
    }

    /**
     * Stops listening and allows processing of pending speech.
     */
    fun stopListening() {
        runOnMainThread {
            internalTeardown(cancelRecognition = false)
        }
    }

    /**
     * Cancels active recognition immediately.
     */
    fun cancel() {
        runOnMainThread {
            internalTeardown(cancelRecognition = true)
        }
    }

    /**
     * Destroys recognizer and cleans up all resources.
     */
    fun destroy() {
        cancel()
    }

    private fun updateState(newState: VoiceInputState) {
        currentState = newState
        callback?.onStateChanged(newState)
    }

    private fun createRecognitionListener(): RecognitionListener {
        return object : RecognitionListener {
            override fun onReadyForSpeech(params: Bundle?) {
                updateState(VoiceInputState.LISTENING)
                callback?.onReadyForSpeech()
            }

            override fun onBeginningOfSpeech() {
                callback?.onBeginningOfSpeech()
            }

            override fun onRmsChanged(rmsdB: Float) {
                callback?.onRmsChanged(rmsdB)
            }

            override fun onBufferReceived(buffer: ByteArray?) {
                // Audio buffer stream callback (16kHz PCM buffer contract for Whisper fallback)
            }

            override fun onEndOfSpeech() {
                updateState(VoiceInputState.PROCESSING)
            }

            override fun onError(error: Int) {
                updateState(VoiceInputState.ERROR)
                val errorMessage = mapErrorCodeToMessage(error)
                callback?.onError(error, errorMessage)
            }

            override fun onResults(results: Bundle?) {
                updateState(VoiceInputState.IDLE)
                val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                val primaryMatch = matches?.firstOrNull() ?: ""
                callback?.onFinalResult(primaryMatch)
            }

            override fun onPartialResults(partialResults: Bundle?) {
                val matches = partialResults?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                val partialMatch = matches?.firstOrNull() ?: ""
                if (partialMatch.isNotBlank()) {
                    callback?.onPartialResult(partialMatch)
                }
            }

            override fun onEvent(eventType: Int, params: Bundle?) {}
        }
    }

    /**
     * Maps Android SpeechRecognizer error codes to driving-safe, glanceable explanations.
     */
    fun mapErrorCodeToMessage(error: Int): String {
        return when (error) {
            SpeechRecognizer.ERROR_AUDIO -> "Audio recording error. Please check microphone."
            SpeechRecognizer.ERROR_CLIENT -> "Client speech recognition error."
            SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS -> "RECORD_AUDIO permission missing."
            SpeechRecognizer.ERROR_NETWORK -> "Network error during speech recognition."
            SpeechRecognizer.ERROR_NETWORK_TIMEOUT -> "Network timed out during speech processing."
            SpeechRecognizer.ERROR_NO_MATCH -> "Could not understand voice. Please repeat."
            SpeechRecognizer.ERROR_RECOGNIZER_BUSY -> "Speech recognizer is busy. Retrying..."
            SpeechRecognizer.ERROR_SERVER -> "Speech recognition server error."
            SpeechRecognizer.ERROR_SPEECH_TIMEOUT -> "Speech input timed out. No speech detected."
            else -> "Speech recognition error ($error)."
        }
    }
}
