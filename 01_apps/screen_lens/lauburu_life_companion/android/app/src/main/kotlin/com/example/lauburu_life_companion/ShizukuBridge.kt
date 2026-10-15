package com.example.lauburu_life_companion

import android.content.Context
import android.content.pm.PackageManager
import android.util.Log
import rikka.shizuku.Shizuku
import java.io.BufferedReader
import java.io.InputStreamReader
import java.util.concurrent.TimeUnit

/**
 * ShizukuBridge: Native Kotlin bridge providing privileged Binder IPC interaction
 * with Shizuku server (moe.shizuku.privileged.api) on Android.
 */
class ShizukuBridge(private val context: Context) {
    companion object {
        private const val TAG = "LifeCompanionShizuku"
        const val SHIZUKU_PERMISSION_REQUEST_CODE = 4001
    }

    private var hasBinder: Boolean = false
    private var isPermissionGranted: Boolean = false

    private val binderReceivedListener = Shizuku.OnBinderReceivedListener {
        val version = try { Shizuku.getVersion() } catch (_: Throwable) { -1 }
        val uid = try { Shizuku.getUid() } catch (_: Throwable) { -1 }
        Log.i(TAG, "Shizuku Binder received. Version: $version, UID: $uid")
        hasBinder = true
        checkPermission()
    }

    private val binderDeadListener = Shizuku.OnBinderDeadListener {
        Log.w(TAG, "Shizuku Binder died.")
        hasBinder = false
        isPermissionGranted = false
    }

    private val requestPermissionResultListener = Shizuku.OnRequestPermissionResultListener { requestCode, grantResult ->
        if (requestCode == SHIZUKU_PERMISSION_REQUEST_CODE) {
            isPermissionGranted = (grantResult == PackageManager.PERMISSION_GRANTED)
            Log.i(TAG, "Shizuku permission request result: granted=$isPermissionGranted")
        }
    }

    fun init() {
        try {
            Shizuku.addBinderReceivedListenerSticky(binderReceivedListener)
            Shizuku.addBinderDeadListener(binderDeadListener)
            Shizuku.addRequestPermissionResultListener(requestPermissionResultListener)
            if (Shizuku.pingBinder()) {
                hasBinder = true
                checkPermission()
            }
        } catch (t: Throwable) {
            Log.e(TAG, "Error initializing Shizuku listeners: ${t.message}", t)
        }
    }

    fun destroy() {
        try {
            Shizuku.removeBinderReceivedListener(binderReceivedListener)
            Shizuku.removeBinderDeadListener(binderDeadListener)
            Shizuku.removeRequestPermissionResultListener(requestPermissionResultListener)
        } catch (t: Throwable) {
            Log.e(TAG, "Error destroying Shizuku listeners: ${t.message}", t)
        }
    }

    fun checkPermission(): Boolean {
        if (!Shizuku.pingBinder()) {
            isPermissionGranted = false
            return false
        }
        if (Shizuku.isPreV11()) {
            isPermissionGranted = false
            return false
        }
        isPermissionGranted = try {
            Shizuku.checkSelfPermission() == PackageManager.PERMISSION_GRANTED
        } catch (t: Throwable) {
            false
        }
        return isPermissionGranted
    }

    fun requestPermission(): Boolean {
        if (!Shizuku.pingBinder()) {
            return false
        }
        if (checkPermission()) {
            return true
        }
        return try {
            Shizuku.requestPermission(SHIZUKU_PERMISSION_REQUEST_CODE)
            true
        } catch (t: Throwable) {
            Log.e(TAG, "Error requesting Shizuku permission: ${t.message}", t)
            false
        }
    }

    fun isAvailable(): Boolean = try {
        Shizuku.pingBinder()
    } catch (t: Throwable) {
        false
    }

    fun getUid(): Int? = try {
        if (Shizuku.pingBinder()) Shizuku.getUid() else null
    } catch (t: Throwable) {
        null
    }

    fun getVersion(): Int? = try {
        if (Shizuku.pingBinder()) Shizuku.getVersion() else null
    } catch (t: Throwable) {
        null
    }

    fun executeShellCommand(command: String, timeoutMs: Long = 10000): Map<String, Any> {
        val startTime = System.currentTimeMillis()
        if (!Shizuku.pingBinder()) {
            return mapOf(
                "exitCode" to -1,
                "stdout" to "",
                "stderr" to "Shizuku Binder is not available",
                "durationMs" to 0L
            )
        }
        if (!checkPermission()) {
            return mapOf(
                "exitCode" to -2,
                "stdout" to "",
                "stderr" to "Shizuku permission not granted",
                "durationMs" to 0L
            )
        }

        return try {
            val process = Shizuku.newProcess(arrayOf("sh", "-c", command), null, null)

            // Read stdout and stderr in separate threads to avoid deadlocks with large outputs
            var stdoutStr = ""
            var stderrStr = ""
            val stdoutThread = Thread {
                try {
                    stdoutStr = BufferedReader(InputStreamReader(process.inputStream)).readText()
                } catch (e: Exception) {
                    Log.e(TAG, "Error reading process stdout: ${e.message}")
                }
            }
            val stderrThread = Thread {
                try {
                    stderrStr = BufferedReader(InputStreamReader(process.errorStream)).readText()
                } catch (e: Exception) {
                    Log.e(TAG, "Error reading process stderr: ${e.message}")
                }
            }
            stdoutThread.start()
            stderrThread.start()

            val completed = process.waitFor(timeoutMs, TimeUnit.MILLISECONDS)
            stdoutThread.join(1000)
            stderrThread.join(1000)

            val durationMs = System.currentTimeMillis() - startTime
            if (completed) {
                mapOf(
                    "exitCode" to process.exitValue(),
                    "stdout" to stdoutStr,
                    "stderr" to stderrStr,
                    "durationMs" to durationMs
                )
            } else {
                process.destroyForcibly()
                mapOf(
                    "exitCode" to -4,
                    "stdout" to stdoutStr,
                    "stderr" to "Execution timed out after ${timeoutMs}ms",
                    "durationMs" to durationMs
                )
            }
        } catch (e: Exception) {
            val durationMs = System.currentTimeMillis() - startTime
            Log.e(TAG, "Process execution error: ${e.message}", e)
            mapOf(
                "exitCode" to -3,
                "stdout" to "",
                "stderr" to (e.message ?: "Execution error"),
                "durationMs" to durationMs
            )
        }
    }
}
