package com.lauburu.androidauto.agi.voice

import android.content.Context
import android.media.AudioManager
import android.os.Bundle
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import java.util.Locale
import java.util.UUID
import java.util.concurrent.ConcurrentHashMap

/**
 * VoiceOutputManager handles Text-To-Speech (TTS) voice synthesis for Android Auto.
 * It integrates with AudioFocusController to request transient in-cabin ducking before
 * speaking, sets up an UtteranceProgressListener to release audio focus upon speech
 * completion, and supports sentence chunking for long code summaries.
 */
class VoiceOutputManager(
    private val context: Context,
    private val audioFocusController: AudioFocusController = AudioFocusController(context),
    private val onInitResult: ((Boolean) -> Unit)? = null
) {
    private var textToSpeech: TextToSpeech? = null
    private var isInitialized: Boolean = false
    private val completionCallbacks = ConcurrentHashMap<String, () -> Unit>()
    private val chunkToParentMap = ConcurrentHashMap<String, String>()
    private val parentTotalChunks = ConcurrentHashMap<String, Int>()
    private val parentCompletedChunks = ConcurrentHashMap<String, Int>()
    private val pendingUtterances = java.util.concurrent.ConcurrentLinkedQueue<Pair<String, () -> Unit>>()

    var isSpeaking: Boolean = false
        private set

    init {
        textToSpeech = TextToSpeech(context) { status ->
            if (status == TextToSpeech.SUCCESS) {
                val result = textToSpeech?.setLanguage(Locale.US)
                if (result == TextToSpeech.LANG_MISSING_DATA || result == TextToSpeech.LANG_NOT_SUPPORTED) {
                    textToSpeech?.language = Locale.getDefault()
                }
                textToSpeech?.setSpeechRate(1.05f)
                textToSpeech?.setPitch(1.0f)
                setupUtteranceListener()
                isInitialized = true
                onInitResult?.invoke(true)
                drainPendingUtterances()
            } else {
                isInitialized = false
                onInitResult?.invoke(false)
            }
        }
    }

    private fun drainPendingUtterances() {
        while (pendingUtterances.isNotEmpty()) {
            val next = pendingUtterances.poll() ?: break
            speak(next.first, next.second)
        }
    }

    private fun cleanUpUtterance(parentId: String) {
        parentTotalChunks.remove(parentId)
        parentCompletedChunks.remove(parentId)
        chunkToParentMap.entries.removeIf { it.value == parentId }
    }

    private fun setupUtteranceListener() {
        textToSpeech?.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
            override fun onStart(utteranceId: String?) {
                isSpeaking = true
            }

            override fun onDone(utteranceId: String?) {
                if (utteranceId != null) {
                    val parentId = chunkToParentMap[utteranceId] ?: utteranceId
                    val total = parentTotalChunks[parentId] ?: 1
                    val completed = (parentCompletedChunks[parentId] ?: 0) + 1
                    parentCompletedChunks[parentId] = completed

                    if (completed >= total) {
                        isSpeaking = false
                        audioFocusController.abandonAudioFocus()
                        cleanUpUtterance(parentId)
                        completionCallbacks.remove(parentId)?.invoke()
                    }
                } else {
                    isSpeaking = false
                    audioFocusController.abandonAudioFocus()
                }
            }

            @Deprecated("Deprecated in Java")
            override fun onError(utteranceId: String?) {
                handleUtteranceError(utteranceId)
            }

            override fun onError(utteranceId: String?, errorCode: Int) {
                handleUtteranceError(utteranceId)
            }

            private fun handleUtteranceError(utteranceId: String?) {
                isSpeaking = false
                audioFocusController.abandonAudioFocus()
                if (utteranceId != null) {
                    val parentId = chunkToParentMap[utteranceId] ?: utteranceId
                    cleanUpUtterance(parentId)
                    completionCallbacks.remove(parentId)?.invoke()
                }
            }
        })
    }

    /**
     * Synthesizes text to speech with in-cabin audio ducking.
     * @param text The message string to speak.
     * @param onCompletion Callback invoked when TTS has completed or encountered an error.
     * @return true if speech was enqueued, false otherwise.
     */
    fun speak(text: String, onCompletion: () -> Unit = {}): Boolean {
        if (text.isBlank()) {
            onCompletion()
            return false
        }

        val tts = textToSpeech
        if (!isInitialized || tts == null) {
            pendingUtterances.add(text to onCompletion)
            return true
        }

        // Request transient audio ducking before outputting sound.
        // If focus ducking is unavailable (e.g. phone speaker mode), still speak so user hears feedback.
        audioFocusController.requestDuckFocus()

        val utteranceId = "utterance_${UUID.randomUUID()}"
        completionCallbacks[utteranceId] = onCompletion

        val params = Bundle().apply {
            putInt(TextToSpeech.Engine.KEY_PARAM_STREAM, AudioManager.STREAM_MUSIC)
            putFloat(TextToSpeech.Engine.KEY_PARAM_VOLUME, 1.0f)
        }

        // Check if text is long and chunk if necessary (>400 chars)
        val chunks = chunkTextForAutomotive(text)
        parentTotalChunks[utteranceId] = chunks.size
        parentCompletedChunks[utteranceId] = 0

        if (chunks.size <= 1) {
            chunkToParentMap[utteranceId] = utteranceId
            val result = tts.speak(text, TextToSpeech.QUEUE_FLUSH, params, utteranceId)
            if (result != TextToSpeech.SUCCESS) {
                isSpeaking = false
                audioFocusController.abandonAudioFocus()
                cleanUpUtterance(utteranceId)
                completionCallbacks.remove(utteranceId)?.invoke()
                return false
            }
        } else {
            // Queue first chunk with FLUSH, subsequent chunks with ADD
            for (i in chunks.indices) {
                val chunkUtteranceId = "${utteranceId}_chunk_$i"
                chunkToParentMap[chunkUtteranceId] = utteranceId
                val queueMode = if (i == 0) TextToSpeech.QUEUE_FLUSH else TextToSpeech.QUEUE_ADD
                val result = tts.speak(chunks[i], queueMode, params, chunkUtteranceId)
                if (result != TextToSpeech.SUCCESS) {
                    isSpeaking = false
                    audioFocusController.abandonAudioFocus()
                    cleanUpUtterance(utteranceId)
                    completionCallbacks.remove(utteranceId)?.invoke()
                    return false
                }
            }
        }

        isSpeaking = true
        return true
    }

    /**
     * Splits long text into concise sentence chunks (<300 characters each) for driving safety.
     */
    fun chunkTextForAutomotive(text: String, maxChunkSize: Int = 300): List<String> {
        if (text.length <= maxChunkSize) {
            return listOf(text)
        }
        val sentences = text.split(Regex("(?<=[.!?])\\s+"))
        val result = mutableListOf<String>()
        val currentChunk = StringBuilder()

        for (sentence in sentences) {
            if (currentChunk.isNotEmpty() && currentChunk.length + sentence.length + 1 > maxChunkSize) {
                result.add(currentChunk.toString().trim())
                currentChunk.clear()
            }
            if (sentence.length > maxChunkSize) {
                // If a single sentence exceeds maxChunkSize, split by commas or words
                val words = sentence.split(" ")
                for (word in words) {
                    if (currentChunk.isNotEmpty() && currentChunk.length + word.length + 1 > maxChunkSize) {
                        result.add(currentChunk.toString().trim())
                        currentChunk.clear()
                    }
                    if (currentChunk.isNotEmpty()) currentChunk.append(" ")
                    currentChunk.append(word)
                }
            } else {
                if (currentChunk.isNotEmpty()) currentChunk.append(" ")
                currentChunk.append(sentence)
            }
        }

        if (currentChunk.isNotEmpty()) {
            result.add(currentChunk.toString().trim())
        }

        return if (result.isEmpty()) listOf(text) else result
    }

    /**
     * Immediately stops active speech and abandons audio focus.
     */
    fun stop() {
        try {
            textToSpeech?.stop()
        } catch (_: Exception) {}
        isSpeaking = false
        audioFocusController.abandonAudioFocus()
        chunkToParentMap.clear()
        parentTotalChunks.clear()
        parentCompletedChunks.clear()
        val pending = completionCallbacks.values.toList()
        completionCallbacks.clear()
        pending.forEach { it.invoke() }
    }

    /**
     * Shuts down TextToSpeech engine and cleans up audio focus.
     */
    fun shutdown() {
        stop()
        try {
            textToSpeech?.shutdown()
        } catch (_: Exception) {}
        textToSpeech = null
        isInitialized = false
        audioFocusController.release()
    }

    /**
     * Alias for shutdown() to comply with resource lifecycle conventions.
     */
    fun release() {
        shutdown()
    }
}
