# E2E Test Infra: Android Auto AGI Hands-Free Coding Agent

## Test Philosophy
- Opaque-box, requirement-driven. No dependency on implementation internals.
- Methodology: Category-Partition + Boundary Value Analysis (BVA) + Pairwise Combinatorial Testing + Real-World Driving Workload Testing.
- Target: Verify all features from `PROJECT.md § Feature Inventory` with empirical zero-mock verification.

## Feature Inventory & Test Mapping
| # | Feature | Requirement Source | Tier 1 | Tier 2 | Tier 3 |
|---|---|---|:---:|:---:|:---:|
| F1 | Gradle Toolchain & Dependencies | ORIGINAL_REQUEST §2 | 5 | 5 | ✓ |
| F2 | Android Manifest & Descriptors | ORIGINAL_REQUEST §1 | 5 | 5 | ✓ |
| F3 | CarAppService & Session Lifecycle | ORIGINAL_REQUEST §1 | 5 | 5 | ✓ |
| F4 | Automotive HUD Screen Templates | ORIGINAL_REQUEST §1 | 5 | 5 | ✓ |
| F5 | STT Voice Ingress | ORIGINAL_REQUEST §1 | 5 | 5 | ✓ |
| F6 | TTS Audio Feedback & Ducking | ORIGINAL_REQUEST §1 | 5 | 5 | ✓ |
| F7 | Mesh AGI Client & Endpoints | ORIGINAL_REQUEST §1 | 5 | 5 | ✓ |
| F8 | 5 Core Voice Directives | ORIGINAL_REQUEST §1 | 5 | 5 | ✓ |
| F9 | Coroutines & StateFlow UDF | ORIGINAL_REQUEST §1 | 5 | 5 | ✓ |
| F10 | Gradle assembleDebug Compilation | ORIGINAL_REQUEST §2 | 5 | 5 | ✓ |
| F11 | Wireless ADB Deployment to Pixel | ORIGINAL_REQUEST §2 | 5 | 5 | ✓ |

## Test Architecture
- **E2E Test Runner**: `test_e2e_suite.sh` at workspace root.
- **Unit & Verification Runner**: `./gradlew testDebugUnitTest` and direct verification scripts.
- **Pass/Fail Semantics**: All test tiers must exit with status 0, 0 assertion errors, 0 compilation errors.

## Test Tiers Breakdown
### Tier 1 - Feature Coverage (≥5 per feature)
- T1.1: Gradle build script syntax and repository definitions.
- T1.2: Manifest declarations (CarAppService filter, categories, permissions, metadata).
- T1.3: CarAppService and Session class hierarchy and initialization.
- T1.4: Screen template generation (PaneTemplate, Row, ActionStrip).
- T1.5: SpeechRecognizer configuration and error handling.
- T1.6: TextToSpeech initialization and AudioFocusRequestCompat ducking request.
- T1.7: MeshApiClient endpoint URL building and timeout settings.
- T1.8: Voice directive parsing for each of the 5 core commands.
- T1.9: StateFlow emissions and UI state reduction.
- T1.10: `./gradlew assembleDebug` produces valid unsigned/debug APK.
- T1.11: `adb install` / `pm list packages` deployment command verification.

### Tier 2 - Boundary & Corner Cases (≥5 per feature)
- T2.1: Long diff summary text truncation (complying with 2-line row limit).
- T2.2: Excessive action counts (>2 actions on Pane, >2 on ActionStrip) safely constrained.
- T2.3: Network timeout / mesh offline handling with graceful offline error state.
- T2.4: Audio focus collision / transient loss while TTS is actively speaking.
- T2.5: Rapid consecutive voice directives without race conditions or memory leaks.

### Tier 3 - Cross-Feature Combinations (Pairwise Coverage)
- T3.1: Voice STT input -> Mesh API query -> StateFlow update -> Screen invalidate() -> TTS audio response.
- T3.2: Network error -> Error Screen presentation -> Audio error notification -> Auto-recovery.
- T3.3: Automotive driving speed state change -> Template restriction check -> Safe UI rendering.

### Tier 4 - Real-World Application Scenarios
- T4.1: Scenario 1: Developer asks "Explain the latest diff in Movesense hub" -> HUD displays diff cards (+12/-4) -> TTS speaks concise summary.
- T4.2: Scenario 2: Developer asks "Run verification tests" -> Mesh API executes test suite -> HUD displays Pass (42/42) -> Audio confirms all green.
- T4.3: Scenario 3: Developer asks "Show git status" -> HUD displays branch `main` and 3 modified files -> Action allows "Approve & Deploy".
- T4.4: Scenario 4: Full APK build and installation to Pixel 10 Pro XL over Tailscale ADB wireless debugging.

## Coverage Thresholds
- Tier 1: ≥ 55 test cases
- Tier 2: ≥ 55 boundary cases
- Tier 3: ≥ 11 pairwise interaction cases
- Tier 4: ≥ 5 realistic application scenarios
- Total: ≥ 126 test cases
