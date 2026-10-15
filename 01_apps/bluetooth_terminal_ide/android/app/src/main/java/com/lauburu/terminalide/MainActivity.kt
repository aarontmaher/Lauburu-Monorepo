package com.lauburu.terminalide

import android.Manifest
import android.annotation.SuppressLint
import android.content.pm.PackageManager
import android.os.Build
import android.os.Bundle
import android.util.Log
import android.view.WindowManager
import android.webkit.*
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat

class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        // Screen Sanctuary: Keep screen awake for continuous terminal & AI debate monitoring
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)

        requestPermissionsIfNecessary()

        WebView.setWebContentsDebuggingEnabled(true)

        webView = WebView(this).apply {
            settings.javaScriptEnabled = true
            settings.domStorageEnabled = true
            settings.databaseEnabled = true
            settings.allowFileAccess = true
            settings.allowContentAccess = true
            settings.mediaPlaybackRequiresUserGesture = false
            settings.cacheMode = WebSettings.LOAD_DEFAULT

            webChromeClient = object : WebChromeClient() {
                override fun onPermissionRequest(request: PermissionRequest) {
                    runOnUiThread {
                        Log.d("LauburuTerminal", "Granting WebChromeClient permissions: ${request.resources.joinToString()}")
                        request.grant(request.resources)
                    }
                }

                override fun onConsoleMessage(consoleMessage: ConsoleMessage?): Boolean {
                    Log.d(
                        "LauburuTerminalConsole",
                        "[${consoleMessage?.messageLevel()}] ${consoleMessage?.message()} (${consoleMessage?.sourceId()}:${consoleMessage?.lineNumber()})"
                    )
                    return true
                }
            }

            webViewClient = object : WebViewClient() {
                override fun onReceivedError(
                    view: WebView?,
                    request: WebResourceRequest?,
                    error: WebResourceError?
                ) {
                    if (request?.isForMainFrame == true) {
                        val failingUrl = request.url?.toString() ?: ""
                        Log.w("LauburuTerminal", "Main frame load failure on $failingUrl: ${error?.description}")
                        if (failingUrl.startsWith("http://127.0.0.1:4050")) {
                            view?.loadUrl("http://100.119.199.76:4050")
                        } else if (failingUrl.startsWith("http://100.119.199.76:4050")) {
                            view?.loadUrl("http://192.168.8.230:4050")
                        } else if (!failingUrl.startsWith("file:///android_asset/")) {
                            view?.loadUrl("file:///android_asset/index.html")
                        }
                    }
                }

                @Deprecated("Deprecated in Java")
                override fun onReceivedError(
                    view: WebView?,
                    errorCode: Int,
                    description: String?,
                    failingUrl: String?
                ) {
                    Log.w("LauburuTerminal", "Legacy error on $failingUrl: $description")
                    if (failingUrl != null && failingUrl.startsWith("http://127.0.0.1:4050")) {
                        view?.loadUrl("http://100.119.199.76:4050")
                    } else if (failingUrl != null && failingUrl.startsWith("http://100.119.199.76:4050")) {
                        view?.loadUrl("http://192.168.8.230:4050")
                    } else if (failingUrl != null && !failingUrl.startsWith("file:///android_asset/")) {
                        view?.loadUrl("file:///android_asset/index.html")
                    }
                }
            }
        }

        setContentView(webView)

        // Primary: Secure Context 127.0.0.1:4050 via adb reverse, falling back to LAN or bundled assets
        val primaryEndpoint = "http://127.0.0.1:4050"
        webView.loadUrl(primaryEndpoint)
    }

    private fun requestPermissionsIfNecessary() {
        val permissions = mutableListOf<String>()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.BLUETOOTH_SCAN) != PackageManager.PERMISSION_GRANTED) {
                permissions.add(Manifest.permission.BLUETOOTH_SCAN)
            }
            if (ContextCompat.checkSelfPermission(this, Manifest.permission.BLUETOOTH_CONNECT) != PackageManager.PERMISSION_GRANTED) {
                permissions.add(Manifest.permission.BLUETOOTH_CONNECT)
            }
        }
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            permissions.add(Manifest.permission.ACCESS_FINE_LOCATION)
        }
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
            permissions.add(Manifest.permission.CAMERA)
        }

        if (permissions.isNotEmpty()) {
            ActivityCompat.requestPermissions(this, permissions.toTypedArray(), 1002)
        }
    }

    @Deprecated("Deprecated in Java")
    override fun onBackPressed() {
        if (this::webView.isInitialized && webView.canGoBack()) {
            webView.goBack()
        } else {
            @Suppress("DEPRECATION")
            super.onBackPressed()
        }
    }
}
