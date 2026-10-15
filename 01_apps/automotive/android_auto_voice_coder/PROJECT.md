# Project: Android Auto AGI Hands-Free Coding Agent (`com.lauburu.androidauto.agi`)

## Architecture
The Android Auto AGI Hands-Free Coding Agent provides a distraction-free, voice-first developer HUD on vehicle head units connected to the Lauburu 7-layer physical mesh. It enables developers to query repository status, inspect diffs, trigger verification test runs, and approve refactors while driving.

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                       ANDROID AUTO HEAD UNIT (CAR)                          │
├─────────────────────────────────────────────────────────────────────────────┤
│  androidx.car.app Templates (PaneTemplate, ActionStrip, ListTemplate)       │
│  • VoiceCodingHudScreen (4 glanceable rows: Directive, Status, Diff, Test)  │
│  • DiffDetailScreen / TestResultScreen / DirectivesListScreen               │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ (CarAppService IPC / Session)
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                  PIXEL 10 PRO XL (Android 17 / API 37)                      │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. CarAppService (LauburuCarAppService) & HostValidator (ALLOW_ALL in debug)│
│ 2. Voice Subsystem:                                                         │
│    • STT: Android SpeechRecognizer (Tensor G5 NPU) + Whisper fallback       │
│    • TTS: Android TextToSpeech + AudioFocusRequestCompat (Cabin Ducking)    │
│ 3. State & Repository:                                                      │
│    • VoiceCodingRepository (Unidirectional Data Flow via StateFlow)         │
│ 4. Mesh Client:                                                             │
│    • MeshApiClient (OkHttp/Coroutines -> llama.cpp:8081, Hub:4000, WoL:18802)│
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │ (Tailscale / 10GbE / Wi-Fi Mesh)
┌──────────────────────────────────────▼──────────────────────────────────────┐
│                    LAUBURU MESH COMPUTE ECOSYSTEM                           │
├─────────────────────────────────────────────────────────────────────────────┤
│  • Host Mac Mini M4: llama-server:8081, Port 4000 Hub, WoL Port 18802       │
│  • Local Scripts: in_car_voice_coder.py, LoRA action recorder               │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---|---|---|---|
| 1 | Gradle Toolchain & Dependencies | Setup root & app Gradle build with AGP 8.6.0, Kotlin 2.0.21, `androidx.car.app:1.4.0`, OkHttp, Coroutines | M1 | Survey |
| 2 | Android Manifest & Automotive Descriptors | Service intent-filter `androidx.car.app.CarAppService`, `@xml/car_app_desc`, `minCarApiLevel`, permissions | M1 | Survey |
| 3 | CarAppService & Session Lifecycle | `LauburuCarAppService`, `VoiceCodingSession`, and `HostValidator` initialization | M2 | Survey |
| 4 | Automotive Safety HUD Screens | `VoiceCodingHudScreen` (`PaneTemplate` max 4 rows), `DiffDetailScreen`, `TestResultScreen`, `DirectivesListScreen` | M2 | Survey |
| 5 | Hands-Free STT Speech Recognition | In-cabin voice capture via `SpeechRecognizer` + fallback Whisper 16kHz PCM transcription | M3 | Survey |
| 6 | TTS Voice Synthesis & Audio Ducking | Automotive TTS with transient audio focus ducking (`AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK`) | M3 | Survey |
| 7 | Mesh AGI Client & Endpoints | Async client connecting to Port 8081 (`/v1/chat/completions`), Port 4000 Hub API, and Port 18802 | M4 | Survey |
| 8 | 5 Core Voice Directives | Support "explain diff", "run tests", "refactor function", "show git status", "commit changes" | M4 | Survey |
| 9 | Coroutine StateFlow UDF Architecture | Zero UI-thread blocking, reactive screen invalidation on `VoiceCodingUiState` updates | M4 | Survey |
| 10 | Gradle Assemble & APK Generation | `./gradlew assembleDebug` compiling clean debug APK to `app/build/outputs/apk/debug/app-debug.apk` | M5 | Survey |
| 11 | Wireless ADB Deployment to Pixel Target | Automated deployment script to `100.73.38.87:34167` (Pixel 10 Pro XL) and package verification | M5 | Survey |
| 12 | E2E Test Suite & Adversarial Hardening | Comprehensive 4-Tier test suite + Tier 5 Challenger white-box hardening & Forensic Audit | M6 / E2E Track | Survey |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|---|---|---|---|
| M1 | Toolchain, Gradle Scaffolding & Manifest Setup | Gradle project files, wrapper, dependencies, AndroidManifest.xml, car_app_desc.xml | none | DONE |
| M2 | CarAppService, Session & Automotive HUD Screens | `LauburuCarAppService`, `VoiceCodingSession`, `VoiceCodingHudScreen`, `DiffDetailScreen`, `TestResultScreen` | M1 | DONE |
| M3 | Voice STT/TTS Engine & In-Cabin Audio Ducking | `VoiceInputManager`, `VoiceOutputManager`, audio focus ducking lifecycle | M1 | DONE |
| M4 | Mesh AGI Coding Client & State Repository | `MeshApiClient`, `VoiceCodingRepository`, directive models, 5 core voice actions | M2, M3 | DONE |
| M5 | Build Packaging & ADB Wireless Deployment Pipeline | Compilation check `./gradlew assembleDebug`, deployment scripts to Pixel 10 Pro XL (`100.73.38.87:34167`) | M1, M2, M3, M4 | DONE |
| M6 | Final Milestone: 100% E2E Pass & Adversarial Hardening | Pass Tiers 1-4 E2E tests, Tier 5 Challenger stress testing & Forensic Integrity Audit | M5, E2E-Ready | DONE |
| E2E | E2E Testing Track | Independent 4-Tier requirement-driven test suite publishing `TEST_READY.md` | M1 | DONE |

## Code Layout
```
/Users/aaron/teamwork_projects/android_auto_agi/
├── settings.gradle.kts
├── build.gradle.kts
├── gradle.properties
├── local.properties
├── gradlew
├── gradlew.bat
├── gradle/wrapper/
│   ├── gradle-wrapper.jar
│   └── gradle-wrapper.properties
├── app/
│   ├── build.gradle.kts
│   └── src/
│       ├── main/
│       │   ├── AndroidManifest.xml
│       │   ├── res/
│       │   │   ├── values/
│       │   │   │   └── strings.xml
│       │   │   └── xml/
│       │   │       └── car_app_desc.xml
│       │   └── java/com/lauburu/androidauto/agi/
│       │       ├── service/
│       │       │   ├── LauburuCarAppService.kt
│       │       │   └── VoiceCodingSession.kt
│       │       ├── ui/
│       │       │   ├── VoiceCodingHudScreen.kt
│       │       │   ├── DiffDetailScreen.kt
│       │       │   ├── TestResultScreen.kt
│       │       │   └── DirectivesListScreen.kt
│       │       ├── voice/
│       │       │   ├── VoiceInputManager.kt
│       │       │   ├── VoiceOutputManager.kt
│       │       │   └── AudioFocusController.kt
│       │       ├── api/
│       │       │   ├── MeshApiClient.kt
│       │       │   ├── MeshEndpoints.kt
│       │       │   └── VoiceCodingDirectives.kt
│       │       ├── data/
│       │       │   ├── VoiceCodingRepository.kt
│       │       │   ├── VoiceCodingUiState.kt
│       │       │   └── Models.kt
│       │       └── util/
│       │           └── AutomotiveConstraints.kt
│       └── test/java/com/lauburu/androidauto/agi/
│           ├── ScreenTemplatesUnitTest.kt
│           ├── DirectivesParserUnitTest.kt
│           ├── MeshApiClientUnitTest.kt
│           └── StateFlowUdfUnitTest.kt
├── deploy_to_pixel.sh
├── test_e2e_suite.sh
└── ORIGINAL_REQUEST.md
```

## Interface Contracts
### `LauburuCarAppService` ↔ Android Auto Host
- `createHostValidator()`: Returns `HostValidator.ALLOW_ALL_HOSTS_VALIDATOR` for development / sideloading.
- `onCreateSession()`: Instantiates `VoiceCodingSession`.

### `VoiceCodingSession` ↔ Screens
- `onCreateScreen(intent: Intent)`: Returns initial `VoiceCodingHudScreen`.

### `VoiceCodingRepository` ↔ UI Screens
- `val uiState: StateFlow<VoiceCodingUiState>`
- `fun executeDirective(directive: VoiceDirective, payload: Map<String, Any> = emptyMap())`
- `fun startVoiceListening()`
- `fun stopVoiceListening()`
- `fun speakFeedback(text: String, onDone: () -> Unit = {})`

### `MeshApiClient` ↔ Local Mesh Endpoints
- `POST http://100.119.199.76:8081/v1/chat/completions`: llama-server coding completion
- `POST http://100.119.199.76:4000/api/voice_coder/directive`: Port 4000 Hub directive dispatch
- `GET http://100.119.199.76:4000/health`: Health status
