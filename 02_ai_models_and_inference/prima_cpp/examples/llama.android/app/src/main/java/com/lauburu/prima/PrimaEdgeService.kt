package com.lauburu.prima

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.os.Binder
import android.os.IBinder
import android.os.PowerManager
import android.util.Log

/**
 * PrimaEdgeService — Android Foreground Service for 3B MoE & prima.cpp Client
 *
 * Runs a persistent, battery-optimized foreground service (WakeLock + Foreground Notification)
 * that bypasses Android Doze mode and prevents Low-Memory Killer (LMK) termination.
 * Complies with Gate 9 Customer Mobile RAM Envelope (<= 1,500 MB).
 */
class PrimaEdgeService : Service() {

    private val binder = LocalBinder()
    private var nativeClientPtr: Long = 0
    private var wakeLock: PowerManager.WakeLock? = null

    companion object {
        private const val TAG = "PrimaEdgeService"
        private const val CHANNEL_ID = "prima_edge_channel"
        private const val NOTIFICATION_ID = 4004

        init {
            System.loadLibrary("prima_edge_jni")
        }
    }

    inner class LocalBinder : Binder() {
        fun getService(): PrimaEdgeService = this@PrimaEdgeService
    }

    override fun onCreate() {
        super.onCreate()
        Log.i(TAG, "Starting PrimaEdgeService on Android...")

        // Acquire partial wake lock to prevent CPU throttling
        val powerManager = getSystemService(POWER_SERVICE) as PowerManager
        wakeLock = powerManager.newWakeLock(
            PowerManager.PARTIAL_WAKE_LOCK,
            "LauburuMesh::PrimaEdgeWakeLock"
        ).apply {
            setReferenceCounted(false)
            acquire(24 * 60 * 60 * 1000L) // 24h safety limit
        }

        startForegroundNotification()
    }

    fun initClient(modelPath: String, meshUrl: String = "http://100.119.199.76:8082", timeoutMs: Float = 150f): Boolean {
        nativeClientPtr = nativeInitClient(modelPath, meshUrl, timeoutMs)
        val margin = FloatArray(1)
        val compliant = nativeCheckEnvelope(nativeClientPtr, margin)
        Log.i(TAG, "Device Envelope Checked: compliant=$compliant, marginMb=${margin[0]}")
        return compliant
    }

    fun chat(prompt: String, forceLocal: Boolean = false): String {
        if (nativeClientPtr == 0L) {
            return "Error: Native prima client uninitialized"
        }
        return nativeGenerateChat(nativeClientPtr, prompt, forceLocal)
    }

    private fun startForegroundNotification() {
        val channel = NotificationChannel(
            CHANNEL_ID,
            "Lauburu prima.cpp Edge Daemon",
            NotificationManager.IMPORTANCE_LOW
        ).apply {
            description = "Active 3B MoE Local Chat & Pipelined Ring Mesh Link"
        }
        val manager = getSystemService(NotificationManager::class.java)
        manager?.createNotificationChannel(channel)

        val notification: Notification = Notification.Builder(this, CHANNEL_ID)
            .setContentTitle("Lauburu prima.cpp Edge Client Active")
            .setContentText("On-device 3B MoE ready | 150ms mesh coupling active")
            .setOngoing(true)
            .build()

        startForeground(NOTIFICATION_ID, notification)
    }

    override fun onDestroy() {
        super.onDestroy()
        if (nativeClientPtr != 0L) {
            nativeDestroyClient(nativeClientPtr)
            nativeClientPtr = 0L
        }
        wakeLock?.let {
            if (it.isHeld) it.release()
        }
        Log.i(TAG, "PrimaEdgeService stopped.")
    }

    override fun onBind(intent: Intent?): IBinder = binder

    // Native JNI functions
    private external fun nativeInitClient(modelPath: String, meshUrl: String, timeoutMs: Float): Long
    private external fun nativeDestroyClient(clientPtr: Long)
    private external fun nativeCheckEnvelope(clientPtr: Long, marginOut: FloatArray): Boolean
    private external fun nativeGenerateChat(clientPtr: Long, prompt: String, forceLocal: Boolean): String
}
