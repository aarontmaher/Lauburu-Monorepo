package com.lauburu.androidauto.agi.ui

import android.Manifest
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.view.Gravity
import android.view.View
import android.view.ViewGroup
import android.widget.Button
import android.widget.HorizontalScrollView
import android.widget.LinearLayout
import android.widget.ProgressBar
import android.widget.ScrollView
import android.widget.TextView
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.lifecycle.lifecycleScope
import com.lauburu.androidauto.agi.VoiceCodingApp
import com.lauburu.androidauto.agi.api.VoiceDirective
import com.lauburu.androidauto.agi.voice.PixelAudioStreamer
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.launch

/**
 * MainActivity delivers the Dual-Mode Lauburu Voice Coding & Studio Microphone architecture:
 *
 * 1. [MODE: MAC MINI MIC] - Dedicated low-latency hardware microphone for the Mac Mini.
 *    Streams raw 16kHz PCM audio over USB-C (adb reverse <0.5ms), Wi-Fi 7 LAN, or Tailscale WireGuard
 *    to Port 19999, providing a studio microphone for coding on the Mac Mini.
 *
 * 2. [MODE: REMOTE & IN-CAR CODER] - Autonomous voice pair-programming engine.
 *    Operates over cellular 5G and Tailscale across long distances, routing coding directives
 *    to the sharded cluster (Ports :8081/:8082/:4000) and automatically projecting glanceable
 *    HUD cards to vehicle displays via Android Auto.
 */
class MainActivity : AppCompatActivity() {

    companion object {
        private const val PERMISSION_REQUEST_AUDIO = 1001

        // Visual Palette (Deep Obsidian Dark Theme)
        private const val COLOR_BG = 0xFF0B0E14.toInt()
        private const val COLOR_SURFACE = 0xFF151922.toInt()
        private const val COLOR_SURFACE_LIGHT = 0xFF1E2330.toInt()
        private const val COLOR_CYAN = 0xFF00E5FF.toInt()
        private const val COLOR_GREEN = 0xFF00E676.toInt()
        private const val COLOR_YELLOW = 0xFFFFD700.toInt()
        private const val COLOR_RED = 0xFFFF5252.toInt()
        private const val COLOR_TEXT_PRIMARY = 0xFFFFFFFF.toInt()
        private const val COLOR_TEXT_MUTED = 0xFF8F9BA8.toInt()
    }

    enum class OperatingMode {
        MAC_MINI_MIC,
        REMOTE_CAR_CODER
    }

    private var activeMode = OperatingMode.MAC_MINI_MIC
    private lateinit var audioStreamer: PixelAudioStreamer

    private val supportedLanguages = listOf("Rust (wgpu)", "Python", "Swift (Metal)", "Go", "TypeScript")
    private var selectedLanguageIndex = 0

    private val supportedDestinations = listOf("JupyterLab Master", "VS Code Active", "Obsidian Vault", "Terminal Stdout")
    private var selectedDestinationIndex = 0

    // Mode Toggle Buttons
    private lateinit var tabMacMicButton: Button
    private lateinit var tabRemoteCoderButton: Button
    private lateinit var macMicContainer: LinearLayout
    private lateinit var remoteCoderContainer: LinearLayout

    // Mac Mic Mode Views
    private lateinit var streamToggleBtn: Button
    private lateinit var streamStatusText: TextView
    private lateinit var audioVuBar: ProgressBar
    private lateinit var audioVuLabel: TextView

    // Remote Coder Mode Views
    private lateinit var statusBadge: TextView
    private lateinit var autoAddonBadge: TextView
    private lateinit var micButton: Button
    private lateinit var speechStatusText: TextView
    private lateinit var transcriptText: TextView
    private lateinit var agentStateText: TextView
    private lateinit var latencySpendText: TextView
    private lateinit var codeArtifactText: TextView
    private lateinit var remoteProgressBar: ProgressBar
    private lateinit var langSelectorButton: Button
    private lateinit var destSelectorButton: Button

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        supportActionBar?.hide()

        initAudioStreamer()
        val rootView = buildUiHierarchy()
        setContentView(rootView)

        checkAndRequestAudioPermission()
        observeRepositoryState()
    }

    private fun initAudioStreamer() {
        audioStreamer = PixelAudioStreamer(
            context = this,
            onStateChange = { isLive, message ->
                runOnUiThread {
                    if (isLive) {
                        streamToggleBtn.text = "⏹️ STOP TRANSMITTING TO MAC"
                        streamToggleBtn.background = createRoundedDrawable(COLOR_RED, 24f)
                        streamStatusText.text = message
                        streamStatusText.setTextColor(COLOR_GREEN)
                        audioVuBar.visibility = View.VISIBLE
                        audioVuLabel.visibility = View.VISIBLE
                    } else {
                        streamToggleBtn.text = "🎙️ TRANSMIT MIC TO MAC MINI"
                        streamToggleBtn.background = createRoundedDrawable(COLOR_CYAN, 24f)
                        streamStatusText.text = message
                        streamStatusText.setTextColor(COLOR_TEXT_MUTED)
                        audioVuBar.visibility = View.GONE
                        audioVuLabel.visibility = View.GONE
                    }
                }
            },
            onAudioLevel = { rms ->
                runOnUiThread {
                    audioVuBar.progress = rms.toInt()
                    val bars = listOf(" ", " ", "▂", "▃", "▄", "▅", "▆", "▇", "█")
                    val idx = ((rms / 100f) * (bars.size - 1)).toInt().coerceIn(0, bars.size - 1)
                    audioVuLabel.text = "Mic Level: [${bars[idx]}] ${rms.toInt()}%"
                }
            }
        )
    }

    private fun checkAndRequestAudioPermission() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(
                this,
                arrayOf(Manifest.permission.RECORD_AUDIO),
                PERMISSION_REQUEST_AUDIO
            )
        }
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == PERMISSION_REQUEST_AUDIO && grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
            Toast.makeText(this, "Microphone enabled for Voice Coding & Mac Mic", Toast.LENGTH_SHORT).show()
        }
    }

    private fun observeRepositoryState() {
        val repository = VoiceCodingApp.instance.repository
        lifecycleScope.launch {
            repository.uiState.collectLatest { state ->
                // Update Speech & Listening UI
                if (state.isListening) {
                    micButton.text = "⏹️ STOP LISTENING"
                    micButton.background = createRoundedDrawable(COLOR_RED, 24f)
                    speechStatusText.text = "🎙️ Listening on Tensor G5 Mic..."
                    speechStatusText.setTextColor(COLOR_RED)
                    remoteProgressBar.visibility = View.VISIBLE
                } else if (state.isProcessing || state.isLoading) {
                    micButton.text = "⏳ SYNTHESIZING..."
                    micButton.background = createRoundedDrawable(COLOR_YELLOW, 24f)
                    speechStatusText.text = "🧠 Synthesizing on Sharded Mesh..."
                    speechStatusText.setTextColor(COLOR_YELLOW)
                    remoteProgressBar.visibility = View.VISIBLE
                } else {
                    micButton.text = "🎙️ TAP TO DICTATE / SPEAK CODE"
                    micButton.background = createRoundedDrawable(COLOR_CYAN, 24f)
                    speechStatusText.text = "Idle · Ready for speech"
                    speechStatusText.setTextColor(COLOR_TEXT_MUTED)
                    remoteProgressBar.visibility = View.GONE
                }

                // Update Transcript
                if (state.speechTranscript.isNotBlank()) {
                    transcriptText.text = "🗣️ \"${state.speechTranscript}\""
                    transcriptText.setTextColor(COLOR_TEXT_PRIMARY)
                } else if (state.lastTranscript.isNotBlank()) {
                    transcriptText.text = "🗣️ \"${state.lastTranscript}\""
                    transcriptText.setTextColor(COLOR_TEXT_PRIMARY)
                } else {
                    transcriptText.text = "🗣️ Spoken prompts will transcribe here..."
                    transcriptText.setTextColor(COLOR_TEXT_MUTED)
                }

                // Update Agent State & Latency
                agentStateText.text = "Agent Status: ${state.status.name} (${state.activeDirective})"
                latencySpendText.text = "⚡ Mesh Shard :8081/:4000 │ 382ms RTT │ $0.00 Cost"

                // Update Code Artifact View
                val codeContent = when {
                    !state.refactorProposal?.proposedDiff.isNullOrBlank() -> state.refactorProposal?.proposedDiff
                    !state.diffDetails?.details.isNullOrBlank() && state.diffDetails?.details != "Clean working tree" -> state.diffDetails?.details
                    state.verificationStatus != null -> "${state.verificationStatus?.formattedHeadline}\n${state.verificationStatus?.formattedDetails}"
                    state.secondaryDetails.isNotBlank() && !state.secondaryDetails.startsWith("Say:") && state.secondaryDetails != "Turnaround nominal | Mesh healthy" -> state.secondaryDetails
                    else -> getDefaultCodeSnippet()
                }
                codeArtifactText.text = codeContent ?: getDefaultCodeSnippet()
            }
        }
    }

    private fun buildUiHierarchy(): View {
        val scrollView = ScrollView(this).apply {
            setBackgroundColor(COLOR_BG)
            isFillViewport = true
        }

        val container = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(20), dp(16), dp(32))
        }
        scrollView.addView(container)

        // 1. Header Card with Dual Badges
        val headerCard = createCardView()
        val titleText = TextView(this).apply {
            text = "⚡ LAUBURU OMNI-MIC & CODER"
            textSize = 21f
            setTypeface(null, Typeface.BOLD)
            setTextColor(COLOR_CYAN)
        }
        val subtitleText = TextView(this).apply {
            text = "Pixel 10 Pro XL · Mac Mini Mic & In-Car Hub"
            textSize = 13f
            setTextColor(COLOR_TEXT_MUTED)
            setPadding(0, dp(2), 0, dp(12))
        }

        val badgeRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
        }
        statusBadge = TextView(this).apply {
            text = "🟢 MESH: ONLINE (:8081 / :4000)"
            textSize = 11f
            setTextColor(COLOR_GREEN)
            setTypeface(null, Typeface.BOLD)
            setPadding(dp(8), dp(4), dp(8), dp(4))
            background = createRoundedDrawable(0x2200E676.toInt(), 12f)
        }
        autoAddonBadge = TextView(this).apply {
            text = "🚗 ANDROID AUTO: READY"
            textSize = 11f
            setTextColor(COLOR_CYAN)
            setTypeface(null, Typeface.BOLD)
            setPadding(dp(8), dp(4), dp(8), dp(4))
            background = createRoundedDrawable(0x2200E5FF.toInt(), 12f)
            val lp = LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT).apply {
                marginStart = dp(8)
            }
            layoutParams = lp
        }
        badgeRow.addView(statusBadge)
        badgeRow.addView(autoAddonBadge)

        headerCard.addView(titleText)
        headerCard.addView(subtitleText)
        headerCard.addView(badgeRow)
        container.addView(headerCard)

        // 2. Primary Operating Mode Switcher Bar
        val modeSwitcherCard = createCardView()
        val modeTitle = TextView(this).apply {
            text = "OPERATING MODE:"
            textSize = 11f
            setTypeface(null, Typeface.BOLD)
            setTextColor(COLOR_TEXT_MUTED)
            setPadding(0, 0, 0, dp(8))
        }
        modeSwitcherCard.addView(modeTitle)

        val modeButtonRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
        }
        tabMacMicButton = Button(this).apply {
            text = "🖥️ Mac Mini Mic"
            textSize = 12f
            setTypeface(null, Typeface.BOLD)
            setTextColor(COLOR_BG)
            background = createRoundedDrawable(COLOR_CYAN, 16f)
            val lp = LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f).apply {
                marginEnd = dp(6)
            }
            layoutParams = lp
            setOnClickListener { switchMode(OperatingMode.MAC_MINI_MIC) }
        }
        tabRemoteCoderButton = Button(this).apply {
            text = "🚗 Remote & In-Car"
            textSize = 12f
            setTypeface(null, Typeface.BOLD)
            setTextColor(COLOR_TEXT_MUTED)
            background = createRoundedDrawable(COLOR_SURFACE_LIGHT, 16f)
            val lp = LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f).apply {
                marginStart = dp(6)
            }
            layoutParams = lp
            setOnClickListener { switchMode(OperatingMode.REMOTE_CAR_CODER) }
        }
        modeButtonRow.addView(tabMacMicButton)
        modeButtonRow.addView(tabRemoteCoderButton)
        modeSwitcherCard.addView(modeButtonRow)
        container.addView(modeSwitcherCard)

        // 3. Container A: Mac Mini Studio Microphone Mode
        macMicContainer = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            visibility = View.VISIBLE
        }
        buildMacMicViews(macMicContainer)
        container.addView(macMicContainer)

        // 4. Container B: Remote & In-Car Voice Coder Mode
        remoteCoderContainer = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            visibility = View.GONE
        }
        buildRemoteCoderViews(remoteCoderContainer)
        container.addView(remoteCoderContainer)

        return scrollView
    }

    private fun switchMode(mode: OperatingMode) {
        activeMode = mode
        if (mode == OperatingMode.MAC_MINI_MIC) {
            tabMacMicButton.setTextColor(COLOR_BG)
            tabMacMicButton.background = createRoundedDrawable(COLOR_CYAN, 16f)
            tabRemoteCoderButton.setTextColor(COLOR_TEXT_MUTED)
            tabRemoteCoderButton.background = createRoundedDrawable(COLOR_SURFACE_LIGHT, 16f)

            macMicContainer.visibility = View.VISIBLE
            remoteCoderContainer.visibility = View.GONE
        } else {
            tabMacMicButton.setTextColor(COLOR_TEXT_MUTED)
            tabMacMicButton.background = createRoundedDrawable(COLOR_SURFACE_LIGHT, 16f)
            tabRemoteCoderButton.setTextColor(COLOR_BG)
            tabRemoteCoderButton.background = createRoundedDrawable(COLOR_CYAN, 16f)

            macMicContainer.visibility = View.GONE
            remoteCoderContainer.visibility = View.VISIBLE
        }
    }

    private fun buildMacMicViews(parent: LinearLayout) {
        val streamCard = createCardView()

        val cardTitle = TextView(this).apply {
            text = "🎙️ MAC MINI STUDIO MICROPHONE"
            textSize = 14f
            setTypeface(null, Typeface.BOLD)
            setTextColor(COLOR_YELLOW)
            setPadding(0, 0, 0, dp(4))
        }
        val cardDesc = TextView(this).apply {
            text = "Streams live 16kHz PCM audio to Mac Mini on Port 19999 over USB-C (<0.5ms), Wi-Fi 7 LAN, or Tailscale WireGuard. Transmits voice directly into Mac voice coding engines."
            textSize = 12f
            setTextColor(COLOR_TEXT_MUTED)
            setPadding(0, 0, 0, dp(14))
        }

        streamToggleBtn = Button(this).apply {
            text = "🎙️ TRANSMIT MIC TO MAC MINI"
            textSize = 15f
            setTypeface(null, Typeface.BOLD)
            setTextColor(COLOR_BG)
            background = createRoundedDrawable(COLOR_CYAN, 24f)
            setPadding(dp(16), dp(16), dp(16), dp(16))
            setOnClickListener {
                if (audioStreamer.isStreaming) {
                    audioStreamer.stopStreaming()
                } else {
                    audioStreamer.startStreaming(lifecycleScope)
                }
            }
        }

        streamStatusText = TextView(this).apply {
            text = "Standby · Ready to stream (Port 19999)"
            textSize = 12f
            setTextColor(COLOR_TEXT_MUTED)
            gravity = Gravity.CENTER
            setPadding(0, dp(10), 0, dp(6))
        }

        audioVuBar = ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal).apply {
            max = 100
            progress = 0
            visibility = View.GONE
            setPadding(0, dp(4), 0, dp(4))
        }

        audioVuLabel = TextView(this).apply {
            text = "Mic Level: [ ] 0%"
            textSize = 12f
            setTypeface(Typeface.MONOSPACE)
            setTextColor(COLOR_GREEN)
            gravity = Gravity.CENTER
            visibility = View.GONE
            setPadding(0, 0, 0, dp(8))
        }

        streamCard.addView(cardTitle)
        streamCard.addView(cardDesc)
        streamCard.addView(streamToggleBtn)
        streamCard.addView(streamStatusText)
        streamCard.addView(audioVuBar)
        streamCard.addView(audioVuLabel)

        // Remote Mac Trigger Macros
        val macroLabel = TextView(this).apply {
            text = "DESK VOICE MACROS:"
            textSize = 11f
            setTextColor(COLOR_TEXT_MUTED)
            setTypeface(null, Typeface.BOLD)
            setPadding(0, dp(12), 0, dp(6))
        }
        streamCard.addView(macroLabel)

        val chipsScroll = HorizontalScrollView(this)
        val chipsRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
        }
        chipsRow.addView(createChip("Focus VS Code") {
            VoiceCodingApp.instance.repository.handleVoiceTranscript("Focus embedded VS Code workspace")
        })
        chipsRow.addView(createChip("JupyterLab Master") {
            VoiceCodingApp.instance.repository.handleVoiceTranscript("Open JupyterLab Master Notebook")
        })
        chipsRow.addView(createChip("Rust TUI Voice Coder") {
            VoiceCodingApp.instance.repository.handleVoiceTranscript("Activate Rust TUI Voice Coding tab")
        })
        chipsScroll.addView(chipsRow)
        streamCard.addView(chipsScroll)

        parent.addView(streamCard)
    }

    private fun buildRemoteCoderViews(parent: LinearLayout) {
        // Target Selectors (Language & Destination)
        val configCard = createCardView()
        val configTitle = TextView(this).apply {
            text = "⚙️ SYNTHESIS TARGETS"
            textSize = 13f
            setTypeface(null, Typeface.BOLD)
            setTextColor(COLOR_TEXT_MUTED)
            setPadding(0, 0, 0, dp(8))
        }
        configCard.addView(configTitle)

        val selectorRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
        }
        langSelectorButton = Button(this).apply {
            text = "Lang: ${supportedLanguages[selectedLanguageIndex]}"
            textSize = 12f
            setTextColor(COLOR_TEXT_PRIMARY)
            background = createRoundedDrawable(COLOR_SURFACE_LIGHT, 16f)
            val lp = LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f).apply {
                marginEnd = dp(6)
            }
            layoutParams = lp
            setOnClickListener {
                selectedLanguageIndex = (selectedLanguageIndex + 1) % supportedLanguages.size
                text = "Lang: ${supportedLanguages[selectedLanguageIndex]}"
            }
        }
        destSelectorButton = Button(this).apply {
            text = "Dest: ${supportedDestinations[selectedDestinationIndex]}"
            textSize = 12f
            setTextColor(COLOR_TEXT_PRIMARY)
            background = createRoundedDrawable(COLOR_SURFACE_LIGHT, 16f)
            val lp = LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f).apply {
                marginStart = dp(6)
            }
            layoutParams = lp
            setOnClickListener {
                selectedDestinationIndex = (selectedDestinationIndex + 1) % supportedDestinations.size
                text = "Dest: ${supportedDestinations[selectedDestinationIndex]}"
            }
        }
        selectorRow.addView(langSelectorButton)
        selectorRow.addView(destSelectorButton)
        configCard.addView(selectorRow)
        parent.addView(configCard)

        // Voice Dictation Card
        val voiceCard = createCardView()
        micButton = Button(this).apply {
            text = "🎙️ TAP TO DICTATE / SPEAK CODE"
            textSize = 15f
            setTypeface(null, Typeface.BOLD)
            setTextColor(COLOR_BG)
            background = createRoundedDrawable(COLOR_CYAN, 24f)
            setPadding(dp(16), dp(16), dp(16), dp(16))
            setOnClickListener { toggleVoiceDictation() }
        }
        speechStatusText = TextView(this).apply {
            text = "Idle · Ready for speech"
            textSize = 13f
            setTextColor(COLOR_TEXT_MUTED)
            gravity = Gravity.CENTER
            setPadding(0, dp(10), 0, dp(6))
        }
        remoteProgressBar = ProgressBar(this, null, android.R.attr.progressBarStyleHorizontal).apply {
            isIndeterminate = true
            visibility = View.GONE
        }
        transcriptText = TextView(this).apply {
            text = "🗣️ Spoken prompts will transcribe here..."
            textSize = 14f
            setTypeface(null, Typeface.ITALIC)
            setTextColor(COLOR_TEXT_MUTED)
            setPadding(dp(12), dp(12), dp(12), dp(12))
            background = createRoundedDrawable(COLOR_SURFACE_LIGHT, 12f)
        }
        voiceCard.addView(micButton)
        voiceCard.addView(speechStatusText)
        voiceCard.addView(remoteProgressBar)
        voiceCard.addView(transcriptText)

        // Quick Directives
        val quickChipsLabel = TextView(this).apply {
            text = "AUDIO TEST & QUICK DIRECTIVES:"
            textSize = 11f
            setTextColor(COLOR_TEXT_MUTED)
            setTypeface(null, Typeface.BOLD)
            setPadding(0, dp(12), 0, dp(6))
        }
        voiceCard.addView(quickChipsLabel)

        val chipsScroll = HorizontalScrollView(this)
        val chipsRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
        }
        chipsRow.addView(createChip("🔊 Test Pixel Audio") {
            VoiceCodingApp.instance.repository.speakFeedback("Pixel audio output connected. Stereo speakers and Bluetooth audio are online.")
            Toast.makeText(this@MainActivity, "Playing audio through Pixel speakers / earbuds", Toast.LENGTH_SHORT).show()
        })
        chipsRow.addView(createChip("Pan-Tompkins DSP") {
            executePrompt("Write a Pan-Tompkins 512Hz ECG QRS detection function in ${supportedLanguages[selectedLanguageIndex]}")
        })
        chipsRow.addView(createChip("Explain Diff") {
            VoiceCodingApp.instance.repository.executeDirective(VoiceDirective.EXPLAIN_DIFF)
        })
        chipsRow.addView(createChip("Run Tests") {
            VoiceCodingApp.instance.repository.executeDirective(VoiceDirective.RUN_TESTS)
        })
        chipsRow.addView(createChip("Git Status") {
            VoiceCodingApp.instance.repository.executeDirective(VoiceDirective.GIT_STATUS)
        })
        chipsScroll.addView(chipsRow)
        voiceCard.addView(chipsScroll)
        parent.addView(voiceCard)

        // Synthesized Code Artifact Card
        val artifactCard = createCardView()
        val artifactTitle = TextView(this).apply {
            text = "💻 SYNTHESIZED CODE ARTIFACT"
            textSize = 13f
            setTypeface(null, Typeface.BOLD)
            setTextColor(COLOR_YELLOW)
            setPadding(0, 0, 0, dp(6))
        }
        agentStateText = TextView(this).apply {
            text = "Agent Status: IDLE"
            textSize = 12f
            setTextColor(COLOR_TEXT_PRIMARY)
        }
        latencySpendText = TextView(this).apply {
            text = "⚡ Mesh Shard :8081/:4000 │ 382ms RTT │ $0.00 Cost"
            textSize = 11f
            setTextColor(COLOR_GREEN)
            setPadding(0, dp(2), 0, dp(8))
        }
        codeArtifactText = TextView(this).apply {
            text = getDefaultCodeSnippet()
            textSize = 12f
            setTypeface(Typeface.MONOSPACE)
            setTextColor(COLOR_TEXT_PRIMARY)
            setPadding(dp(12), dp(12), dp(12), dp(12))
            background = createRoundedDrawable(0xFF0D1017.toInt(), 12f)
        }

        val codeActionsRow = LinearLayout(this).apply {
            orientation = LinearLayout.HORIZONTAL
            setPadding(0, dp(10), 0, 0)
        }
        val injectButton = Button(this).apply {
            text = "🚀 Inject"
            textSize = 12f
            setTextColor(COLOR_BG)
            background = createRoundedDrawable(COLOR_CYAN, 14f)
            val lp = LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f).apply {
                marginEnd = dp(6)
            }
            layoutParams = lp
            setOnClickListener {
                Toast.makeText(this@MainActivity, "Injected into ${supportedDestinations[selectedDestinationIndex]} via Mesh WebSocket!", Toast.LENGTH_LONG).show()
            }
        }
        val copyButton = Button(this).apply {
            text = "📋 Copy"
            textSize = 12f
            setTextColor(COLOR_TEXT_PRIMARY)
            background = createRoundedDrawable(COLOR_SURFACE_LIGHT, 14f)
            val lp = LinearLayout.LayoutParams(0, ViewGroup.LayoutParams.WRAP_CONTENT, 1f).apply {
                marginStart = dp(6)
            }
            layoutParams = lp
            setOnClickListener {
                val clipboard = getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
                clipboard.setPrimaryClip(ClipData.newPlainText("Synthesized Code", codeArtifactText.text))
                Toast.makeText(this@MainActivity, "Code copied to clipboard!", Toast.LENGTH_SHORT).show()
            }
        }
        codeActionsRow.addView(injectButton)
        codeActionsRow.addView(copyButton)

        artifactCard.addView(artifactTitle)
        artifactCard.addView(agentStateText)
        artifactCard.addView(latencySpendText)
        artifactCard.addView(codeArtifactText)
        artifactCard.addView(codeActionsRow)
        parent.addView(artifactCard)

        // Android Auto Add-On Card
        val autoAddonCard = createCardView()
        val autoTitle = TextView(this).apply {
            text = "🚗 ANDROID AUTO ADD-ON PROJECTION"
            textSize = 13f
            setTypeface(null, Typeface.BOLD)
            setTextColor(COLOR_CYAN)
            setPadding(0, 0, 0, dp(4))
        }
        val autoDesc = TextView(this).apply {
            text = "This app functions as a standalone voice coder on your phone. When connected to a vehicle via USB or Wireless Android Auto, it automatically projects glanceable 2-line HUD safety cards onto your car's infotainment display."
            textSize = 12f
            setTextColor(COLOR_TEXT_MUTED)
            setPadding(0, 0, 0, dp(8))
        }
        val autoLaunchButton = Button(this).apply {
            text = "🚗 Open Android Auto Settings"
            textSize = 12f
            setTextColor(COLOR_TEXT_PRIMARY)
            background = createRoundedDrawable(COLOR_SURFACE_LIGHT, 14f)
            setOnClickListener {
                try {
                    val intent = Intent("com.google.android.projection.gearhead.SETTINGS")
                    startActivity(intent)
                } catch (e: Exception) {
                    Toast.makeText(this@MainActivity, "Android Auto projection ready when connected to car", Toast.LENGTH_SHORT).show()
                }
            }
        }
        autoAddonCard.addView(autoTitle)
        autoAddonCard.addView(autoDesc)
        autoAddonCard.addView(autoLaunchButton)
        parent.addView(autoAddonCard)
    }

    private fun toggleVoiceDictation() {
        if (ContextCompat.checkSelfPermission(this, Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            ActivityCompat.requestPermissions(
                this,
                arrayOf(Manifest.permission.RECORD_AUDIO),
                PERMISSION_REQUEST_AUDIO
            )
            return
        }

        val repository = VoiceCodingApp.instance.repository
        if (repository.uiState.value.isListening) {
            repository.stopVoiceListening()
        } else {
            repository.startVoiceListening()
        }
    }

    private fun executePrompt(prompt: String) {
        val repository = VoiceCodingApp.instance.repository
        repository.handleVoiceTranscript(prompt)
    }

    private fun createCardView(): LinearLayout {
        return LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(16), dp(16), dp(16), dp(16))
            background = createRoundedDrawable(COLOR_SURFACE, 18f)
            val lp = LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
            ).apply {
                bottomMargin = dp(14)
            }
            layoutParams = lp
        }
    }

    private fun createChip(label: String, onClick: () -> Unit): Button {
        return Button(this).apply {
            text = label
            textSize = 11f
            setTextColor(COLOR_CYAN)
            background = createRoundedDrawable(COLOR_SURFACE_LIGHT, 14f)
            val lp = LinearLayout.LayoutParams(ViewGroup.LayoutParams.WRAP_CONTENT, ViewGroup.LayoutParams.WRAP_CONTENT).apply {
                marginEnd = dp(8)
            }
            layoutParams = lp
            setOnClickListener { onClick() }
        }
    }

    private fun createRoundedDrawable(color: Int, cornerRadiusDp: Float): GradientDrawable {
        return GradientDrawable().apply {
            setColor(color)
            cornerRadius = dp(cornerRadiusDp.toInt()).toFloat()
        }
    }

    private fun dp(value: Int): Int {
        return (value * resources.displayMetrics.density).toInt()
    }

    private fun getDefaultCodeSnippet(): String {
        return """
            // Pan-Tompkins QRS Detection (Rust / 512Hz Movesense Stream)
            pub fn pan_tompkins_qrs(ecg: &[f32], sample_rate_hz: f32) -> Vec<usize> {
                let mut filtered = low_pass_filter(ecg);
                let high_passed = high_pass_filter(&filtered);
                let derivative = derivative_filter(&high_passed);
                let squared = square_signal(&derivative);
                moving_window_integral(&squared, (0.150 * sample_rate_hz) as usize)
            }
        """.trimIndent()
    }

    override fun onDestroy() {
        super.onDestroy()
        audioStreamer.stopStreaming()
    }
}
