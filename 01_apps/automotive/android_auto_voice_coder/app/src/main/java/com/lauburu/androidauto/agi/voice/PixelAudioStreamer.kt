package com.lauburu.androidauto.agi.voice

import android.content.Context
import android.content.pm.PackageManager
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import androidx.core.content.ContextCompat
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.OutputStream
import java.net.InetSocketAddress
import java.net.Socket
import kotlin.math.sqrt

/**
 * PixelAudioStreamer captures raw, uncompressed 16kHz 16-bit mono PCM audio from the Pixel's
 * hardware microphone and streams it in real-time over TCP to the Mac Mini on Port 19999.
 *
 * This turns the Pixel 10 Pro XL into a dedicated studio microphone for the Mac Mini
 * over USB-C (adb reverse tunnel, <0.5ms latency), local Wi-Fi 7, or Tailscale WireGuard.
 */
class PixelAudioStreamer(
    private val context: Context,
    private val onStateChange: ((Boolean, String) -> Unit)? = null,
    private val onAudioLevel: ((Float) -> Unit)? = null
) {
    companion object {
        const val SAMPLE_RATE = 16000
        const val CHANNEL_CONFIG = AudioFormat.CHANNEL_IN_MONO
        const val AUDIO_FORMAT = AudioFormat.ENCODING_PCM_16BIT
        const val DEFAULT_PORT = 19999

        // Target Endpoints in priority order
        const val USB_REVERSE_HOST = "127.0.0.1"      // USB-C ADB reverse (<0.5ms)
        const val LOCAL_WIFI_HOST = "192.168.8.230"   // Wi-Fi 7 LAN
        const val TAILSCALE_HOST = "100.119.199.76"   // Tailscale L3 overlay
    }

    private var audioRecord: AudioRecord? = null
    private var streamingJob: Job? = null
    private var activeSocket: Socket? = null

    var isStreaming: Boolean = false
        private set

    fun hasRecordPermission(): Boolean {
        return ContextCompat.checkSelfPermission(
            context,
            android.Manifest.permission.RECORD_AUDIO
        ) == PackageManager.PERMISSION_GRANTED
    }

    /**
     * Starts audio streaming to the Mac Mini.
     * Tries USB-C reverse first, then local Wi-Fi, then Tailscale.
     */
    fun startStreaming(scope: CoroutineScope, customHost: String? = null) {
        if (isStreaming) return
        if (!hasRecordPermission()) {
            onStateChange?.invoke(false, "Microphone permission required")
            return
        }

        streamingJob = scope.launch(Dispatchers.IO) {
            val candidateHosts = if (!customHost.isNullOrBlank()) {
                listOf(customHost)
            } else {
                listOf(USB_REVERSE_HOST, LOCAL_WIFI_HOST, TAILSCALE_HOST)
            }

            var connectedSocket: Socket? = null
            var connectedHost = ""

            // Attempt connection across available transport layers
            for (host in candidateHosts) {
                try {
                    val socket = Socket()
                    val connectTimeout = if (host == TAILSCALE_HOST) 2500 else 400
                    socket.connect(InetSocketAddress(host, DEFAULT_PORT), connectTimeout)
                    socket.tcpNoDelay = true
                    socket.sendBufferSize = 4096
                    connectedSocket = socket
                    connectedHost = host
                    break
                } catch (_: Exception) {
                    // Try next candidate host
                }
            }

            if (connectedSocket == null) {
                withContext(Dispatchers.Main) {
                    onStateChange?.invoke(false, "Mac Mini receiver offline on Port 19999")
                }
                return@launch
            }

            activeSocket = connectedSocket
            val transportLabel = when (connectedHost) {
                USB_REVERSE_HOST -> "USB-C Bus (<0.5ms)"
                LOCAL_WIFI_HOST -> "Wi-Fi 7 LAN"
                TAILSCALE_HOST -> "Tailscale Mesh"
                else -> connectedHost
            }

            // Initialize AudioRecord
            val minBufferSize = AudioRecord.getMinBufferSize(SAMPLE_RATE, CHANNEL_CONFIG, AUDIO_FORMAT)
            val bufferSize = (minBufferSize * 2).coerceAtLeast(4096)

            try {
                val record = AudioRecord(
                    MediaRecorder.AudioSource.VOICE_RECOGNITION,
                    SAMPLE_RATE,
                    CHANNEL_CONFIG,
                    AUDIO_FORMAT,
                    bufferSize
                )

                if (record.state != AudioRecord.STATE_INITIALIZED) {
                    withContext(Dispatchers.Main) {
                        onStateChange?.invoke(false, "Failed to initialize AudioRecord")
                    }
                    connectedSocket.close()
                    return@launch
                }

                audioRecord = record
                record.startRecording()
                isStreaming = true

                withContext(Dispatchers.Main) {
                    onStateChange?.invoke(true, "🟢 Streaming to Mac Mini via $transportLabel")
                }

                val buffer = ByteArray(2048)
                val outputStream: OutputStream = connectedSocket.getOutputStream()

                while (isActive && isStreaming) {
                    val bytesRead = record.read(buffer, 0, buffer.size)
                    if (bytesRead > 0) {
                        outputStream.write(buffer, 0, bytesRead)
                        outputStream.flush()

                        // Calculate RMS amplitude for real-time VU meter
                        val rms = calculateRms(buffer, bytesRead)
                        withContext(Dispatchers.Main) {
                            onAudioLevel?.invoke(rms)
                        }
                    }
                }
            } catch (e: Exception) {
                withContext(Dispatchers.Main) {
                    onStateChange?.invoke(false, "Stream ended: ${e.message}")
                }
            } finally {
                cleanup()
            }
        }
    }

    /**
     * Stops the audio stream and closes the network socket.
     */
    fun stopStreaming() {
        isStreaming = false
        streamingJob?.cancel()
        streamingJob = null
        cleanup()
        onStateChange?.invoke(false, "Disconnected from Mac Mini")
    }

    private fun cleanup() {
        try {
            audioRecord?.stop()
            audioRecord?.release()
        } catch (_: Exception) {}
        audioRecord = null

        try {
            activeSocket?.close()
        } catch (_: Exception) {}
        activeSocket = null
        isStreaming = false
    }

    private fun calculateRms(buffer: ByteArray, length: Int): Float {
        var sum = 0.0
        val sampleCount = length / 2
        if (sampleCount == 0) return 0f

        var i = 0
        while (i < length - 1) {
            val sample = (buffer[i].toInt() and 0xFF) or (buffer[i + 1].toInt() shl 8)
            val normalized = sample.toShort().toFloat() / 32768.0f
            sum += normalized * normalized
            i += 2
        }

        val rms = sqrt(sum / sampleCount).toFloat()
        return (rms * 100f).coerceIn(0f, 100f)
    }
}
