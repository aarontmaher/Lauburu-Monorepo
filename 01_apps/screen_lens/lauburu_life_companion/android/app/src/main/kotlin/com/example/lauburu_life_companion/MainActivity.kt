package com.example.lauburu_life_companion

import android.os.Bundle
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    private val CHANNEL = "ai.lauburu.companion/shizuku"
    private lateinit var shizukuBridge: ShizukuBridge

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        shizukuBridge = ShizukuBridge(this)
        shizukuBridge.init()
    }

    override fun onDestroy() {
        super.onDestroy()
        if (::shizukuBridge.isInitialized) {
            shizukuBridge.destroy()
        }
    }

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        if (!::shizukuBridge.isInitialized) {
            shizukuBridge = ShizukuBridge(this)
            shizukuBridge.init()
        }

        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, CHANNEL).setMethodCallHandler { call, result ->
            when (call.method) {
                "isAvailable" -> {
                    result.success(shizukuBridge.isAvailable())
                }
                "hasPermission" -> {
                    result.success(shizukuBridge.checkPermission())
                }
                "requestPermission" -> {
                    val requested = shizukuBridge.requestPermission()
                    result.success(requested)
                }
                "getUid" -> {
                    result.success(shizukuBridge.getUid())
                }
                "getVersion" -> {
                    result.success(shizukuBridge.getVersion())
                }
                "executeCommand" -> {
                    val command = call.argument<String>("command") ?: ""
                    val timeoutMs = call.argument<Number>("timeoutMs")?.toLong() ?: 10000L
                    val res = shizukuBridge.executeShellCommand(command, timeoutMs)
                    result.success(res)
                }
                "injectTap" -> {
                    val x = call.argument<Int>("x") ?: 0
                    val y = call.argument<Int>("y") ?: 0
                    val res = shizukuBridge.executeShellCommand("input tap $x $y")
                    val success = (res["exitCode"] as? Int ?: -1) == 0
                    result.success(success)
                }
                "injectKey" -> {
                    val keyCode = call.argument<Int>("keyCode") ?: 0
                    val res = shizukuBridge.executeShellCommand("input keyevent $keyCode")
                    val success = (res["exitCode"] as? Int ?: -1) == 0
                    result.success(success)
                }
                "injectSwipe" -> {
                    val x1 = call.argument<Int>("x1") ?: 0
                    val y1 = call.argument<Int>("y1") ?: 0
                    val x2 = call.argument<Int>("x2") ?: 0
                    val y2 = call.argument<Int>("y2") ?: 0
                    val durationMs = call.argument<Int>("durationMs") ?: 300
                    val res = shizukuBridge.executeShellCommand("input swipe $x1 $y1 $x2 $y2 $durationMs")
                    val success = (res["exitCode"] as? Int ?: -1) == 0
                    result.success(success)
                }
                "injectText" -> {
                    val text = call.argument<String>("text") ?: ""
                    // Escape single quotes for shell safety
                    val escapedText = text.replace("'", "'\\''")
                    val res = shizukuBridge.executeShellCommand("input text '$escapedText'")
                    val success = (res["exitCode"] as? Int ?: -1) == 0
                    result.success(success)
                }
                else -> {
                    result.notImplemented()
                }
            }
        }
    }
}
