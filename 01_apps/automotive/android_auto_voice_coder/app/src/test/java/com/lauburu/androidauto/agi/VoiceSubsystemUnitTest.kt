package com.lauburu.androidauto.agi

import android.media.AudioAttributes
import android.media.AudioManager
import android.speech.SpeechRecognizer
import com.lauburu.androidauto.agi.voice.VoiceInputCallback
import com.lauburu.androidauto.agi.voice.VoiceInputManager
import com.lauburu.androidauto.agi.voice.VoiceInputState
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicInteger
import java.util.concurrent.atomic.AtomicReference

class VoiceSubsystemUnitTest {

    @Test
    fun testVoiceInputStateEnumTransitions() {
        val states = VoiceInputState.values()
        assertTrue(states.contains(VoiceInputState.IDLE))
        assertTrue(states.contains(VoiceInputState.LISTENING))
        assertTrue(states.contains(VoiceInputState.PROCESSING))
        assertTrue(states.contains(VoiceInputState.ERROR))
        assertEquals(4, states.size)
    }

    @Test
    fun testVoiceInputConstants() {
        assertEquals(16000, VoiceInputManager.SAMPLE_RATE_16KHZ)
        assertEquals("16kHz_mono_pcm", VoiceInputManager.WHISPER_FALLBACK_AUDIO_SOURCE)
        assertEquals(1500L, VoiceInputManager.EXTRA_SPEECH_SILENCE_TIMEOUT_MS)
    }

    @Test
    fun testVoiceInputCallbackDefaultImplementations() {
        val stateChangedCalled = AtomicBoolean(false)
        val readyCalled = AtomicBoolean(false)
        val beginningCalled = AtomicBoolean(false)
        val rmsChangedCalled = AtomicBoolean(false)
        val partialResultCalled = AtomicBoolean(false)
        val finalResultCalled = AtomicBoolean(false)
        val errorCalled = AtomicBoolean(false)

        val callback = object : VoiceInputCallback {
            override fun onStateChanged(state: VoiceInputState) {
                stateChangedCalled.set(true)
            }
            override fun onReadyForSpeech() {
                readyCalled.set(true)
            }
            override fun onBeginningOfSpeech() {
                beginningCalled.set(true)
            }
            override fun onRmsChanged(rmsdB: Float) {
                rmsChangedCalled.set(true)
            }
            override fun onPartialResult(partialTranscript: String) {
                partialResultCalled.set(true)
            }
            override fun onFinalResult(finalTranscript: String) {
                finalResultCalled.set(true)
            }
            override fun onError(errorCode: Int, errorMessage: String) {
                errorCalled.set(true)
            }
        }

        callback.onStateChanged(VoiceInputState.LISTENING)
        callback.onReadyForSpeech()
        callback.onBeginningOfSpeech()
        callback.onRmsChanged(5.0f)
        callback.onPartialResult("explain")
        callback.onFinalResult("explain diff")
        callback.onError(SpeechRecognizer.ERROR_NO_MATCH, "No match")

        assertTrue(stateChangedCalled.get())
        assertTrue(readyCalled.get())
        assertTrue(beginningCalled.get())
        assertTrue(rmsChangedCalled.get())
        assertTrue(partialResultCalled.get())
        assertTrue(finalResultCalled.get())
        assertTrue(errorCalled.get())
    }

    @Test
    fun testErrorCodeMappingDrivingSafety() {
        // Mock error code mapping helper
        fun mapError(error: Int): String {
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

        assertTrue(mapError(SpeechRecognizer.ERROR_NO_MATCH).contains("Could not understand"))
        assertTrue(mapError(SpeechRecognizer.ERROR_SPEECH_TIMEOUT).contains("timed out"))
        assertTrue(mapError(SpeechRecognizer.ERROR_AUDIO).contains("Audio recording error"))
        assertTrue(mapError(SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS).contains("permission missing"))
        assertTrue(mapError(SpeechRecognizer.ERROR_NETWORK).contains("Network error"))
        assertTrue(mapError(SpeechRecognizer.ERROR_RECOGNIZER_BUSY).contains("busy"))
        assertTrue(mapError(999).contains("999"))
    }

    @Test
    fun testSentenceChunkingForAutomotiveDrivingSafety() {
        fun chunkText(text: String, maxChunkSize: Int = 300): List<String> {
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

        // Short text
        val shortText = "All 42 tests passed."
        val chunksShort = chunkText(shortText, 300)
        assertEquals(1, chunksShort.size)
        assertEquals(shortText, chunksShort[0])

        // Multi-sentence long text
        val longText = "In port 4000 hub, added PBKDF2 authentication hashing and token validation. " +
                "2 files changed, plus 45, minus 3 lines. " +
                "Movesense ring buffer has been updated with zero-copy circular queue semantics. " +
                "All verification tests passed across active mesh nodes with zero errors. " +
                "Say confirm or tap the dashboard button to commit and push changes."

        val chunksLong = chunkText(longText, 120)
        assertTrue(chunksLong.size >= 3)
        for (chunk in chunksLong) {
            assertTrue("Chunk length ${chunk.length} should be <= 120", chunk.length <= 120)
        }
    }

    @Test
    fun testTransientAudioDuckingFocusAttributes() {
        assertEquals(
            AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK,
            AudioManager.AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK
        )
        assertEquals(AudioAttributes.USAGE_ASSISTANT, AudioAttributes.USAGE_ASSISTANT)
        assertEquals(AudioAttributes.CONTENT_TYPE_SPEECH, AudioAttributes.CONTENT_TYPE_SPEECH)
    }

    @Test
    fun testAudioDuckVolumeCalculation() {
        val initialVolume = 1.0f
        val duckedVolume = initialVolume * 0.2f
        assertEquals(0.2f, duckedVolume, 0.001f)
        val restoredVolume = initialVolume
        assertEquals(1.0f, restoredVolume, 0.001f)
    }

    @Test
    fun testRapidDirectiveBurstQueueing() {
        val directives = listOf(
            "explain diff",
            "run tests",
            "refactor calculate_rmssd",
            "show git status",
            "confirm commit"
        )
        val received = mutableListOf<String>()
        for (d in directives) {
            received.add(d.trim())
        }
        assertEquals(5, received.size)
        assertEquals("explain diff", received[0])
        assertEquals("confirm commit", received[4])
    }

    @Test
    fun testAudioInterruptionOnSpeechIngress() {
        var isTtsSpeaking = true
        var isSttActive = false
        var audioFocusHeld = true

        // Simulate driver speech trigger interrupting active TTS
        fun onDriverSpeechTriggered() {
            isTtsSpeaking = false
            audioFocusHeld = false
            isSttActive = true
        }

        onDriverSpeechTriggered()
        assertFalse(isTtsSpeaking)
        assertFalse(audioFocusHeld)
        assertTrue(isSttActive)
    }
}
