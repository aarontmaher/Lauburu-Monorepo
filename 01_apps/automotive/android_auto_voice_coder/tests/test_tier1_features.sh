#!/usr/bin/env bash
# ==============================================================================
# Tier 1: Feature Coverage Test Suite (F1 - F11, ≥55 tests)
# ==============================================================================

_T1_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_T1_WS="${WORKSPACE_ROOT:-$(cd "$_T1_DIR/.." && pwd)}"
_T1_VAL="${VALIDATORS_DIR:-$_T1_DIR/validators}"

source "$_T1_DIR/test_helpers.sh"

run_tier1_tests() {
    print_tier_header "1" "Feature Coverage (F1 through F11)"

    # --------------------------------------------------------------------------
    # F1: Gradle Toolchain & Dependencies
    # --------------------------------------------------------------------------
    print_feature_header "F1" "Gradle Toolchain & Dependencies"
    assert_validator "T1.1.1" "$_T1_VAL/gradle_validator.py" "--check-root-settings $_T1_WS" "Verify settings.gradle.kts and app module inclusion"
    assert_validator "T1.1.2" "$_T1_VAL/gradle_validator.py" "--check-root-build $_T1_WS" "Verify root build.gradle.kts plugin definitions"
    assert_validator "T1.1.3" "$_T1_VAL/gradle_validator.py" "--check-app-build $_T1_WS" "Verify app/build.gradle.kts dependencies (Car App, OkHttp, Coroutines)"
    assert_validator "T1.1.4" "$_T1_VAL/gradle_validator.py" "--check-properties $_T1_WS" "Verify gradle.properties AndroidX configuration"
    assert_validator "T1.1.5" "$_T1_VAL/gradle_validator.py" "--check-wrapper $_T1_WS" "Verify Gradle wrapper executable and distribution"

    # --------------------------------------------------------------------------
    # F2: Android Manifest & Automotive Descriptors
    # --------------------------------------------------------------------------
    print_feature_header "F2" "Android Manifest & Automotive Descriptors"
    assert_validator "T1.2.1" "$_T1_VAL/manifest_validator.py" "--check-package $_T1_WS" "Verify AndroidManifest.xml package and application structure"
    assert_validator "T1.2.2" "$_T1_VAL/manifest_validator.py" "--check-service $_T1_WS" "Verify CarAppService declaration with intent filter action"
    assert_validator "T1.2.3" "$_T1_VAL/manifest_validator.py" "--check-metadata $_T1_WS" "Verify minCarApiLevel and descriptor metadata"
    assert_validator "T1.2.4" "$_T1_VAL/manifest_validator.py" "--check-desc-xml $_T1_WS" "Verify res/xml/car_app_desc.xml schema and root tag"
    assert_validator "T1.2.5" "$_T1_VAL/manifest_validator.py" "--check-permissions $_T1_WS" "Verify RECORD_AUDIO, INTERNET, and required permissions"

    # --------------------------------------------------------------------------
    # F3: CarAppService & Session Lifecycle
    # --------------------------------------------------------------------------
    print_feature_header "F3" "CarAppService & Session Lifecycle"
    assert_validator "T1.3.1" "$_T1_VAL/car_template_validator.py" "--check-service $_T1_WS" "Verify LauburuCarAppService inherits from CarAppService"
    assert_validator "T1.3.2" "$_T1_VAL/car_template_validator.py" "--check-host-validator $_T1_WS" "Verify createHostValidator returns HostValidator"
    assert_validator "T1.3.3" "$_T1_VAL/car_template_validator.py" "--check-session $_T1_WS" "Verify onCreateSession returns VoiceCodingSession"
    assert_file_contains "T1.3.4" "$_T1_WS/app/src/main/java/com/lauburu/androidauto/agi/service/VoiceCodingSession.kt" "class VoiceCodingSession.*: Session" "Verify VoiceCodingSession inherits from Session"
    assert_file_contains "T1.3.5" "$_T1_WS/app/src/main/java/com/lauburu/androidauto/agi/service/VoiceCodingSession.kt" "override fun onCreateScreen.*VoiceCodingHudScreen" "Verify onCreateScreen returns initial VoiceCodingHudScreen"

    # --------------------------------------------------------------------------
    # F4: Automotive HUD Screen Templates
    # --------------------------------------------------------------------------
    print_feature_header "F4" "Automotive HUD Screen Templates"
    assert_validator "T1.4.1" "$_T1_VAL/car_template_validator.py" "--check-hud-screen $_T1_WS" "Verify VoiceCodingHudScreen builds PaneTemplate"
    assert_validator "T1.4.2" "$_T1_VAL/car_template_validator.py" "--check-diff-screen $_T1_WS" "Verify DiffDetailScreen Screen implementation"
    assert_validator "T1.4.3" "$_T1_VAL/car_template_validator.py" "--check-test-screen $_T1_WS" "Verify TestResultScreen Screen implementation"
    assert_validator "T1.4.4" "$_T1_VAL/car_template_validator.py" "--check-directives-screen $_T1_WS" "Verify DirectivesListScreen ListTemplate implementation"
    assert_validator "T1.4.5" "$_T1_VAL/car_template_validator.py" "--check-constraints-util $_T1_WS" "Verify AutomotiveConstraints limits <= 4 rows"

    # --------------------------------------------------------------------------
    # F5: Hands-Free STT Speech Recognition
    # --------------------------------------------------------------------------
    print_feature_header "F5" "Hands-Free STT Speech Recognition"
    assert_validator "T1.5.1" "$_T1_VAL/stt_tts_contract_validator.py" "--check-stt $_T1_WS" "Verify VoiceInputManager and SpeechRecognizer contract"
    assert_file_contains "T1.5.2" "$_T1_WS/app/src/main/java/com/lauburu/androidauto/agi/voice/VoiceInputManager.kt" "RecognitionListener" "Verify RecognitionListener implementation"
    assert_file_contains "T1.5.3" "$_T1_WS/app/src/main/java/com/lauburu/androidauto/agi/voice/VoiceInputManager.kt" "onError" "Verify STT onError error handling"
    assert_file_contains "T1.5.4" "$_T1_WS/app/src/main/java/com/lauburu/androidauto/agi/voice/VoiceInputManager.kt" "startListening|stopListening" "Verify voice listening lifecycle control"
    assert_validator "T1.5.5" "$_T1_VAL/stt_tts_contract_validator.py" "--check-whisper $_T1_WS" "Verify 16kHz audio buffer & Whisper fallback architecture"

    # --------------------------------------------------------------------------
    # F6: TTS Voice Synthesis & Audio Ducking
    # --------------------------------------------------------------------------
    print_feature_header "F6" "TTS Voice Synthesis & Audio Ducking"
    assert_validator "T1.6.1" "$_T1_VAL/stt_tts_contract_validator.py" "--check-tts $_T1_WS" "Verify VoiceOutputManager TextToSpeech engine contract"
    assert_validator "T1.6.2" "$_T1_VAL/stt_tts_contract_validator.py" "--check-audio-focus $_T1_WS" "Verify AUDIOFOCUS_GAIN_TRANSIENT_MAY_DUCK ducking request"
    assert_file_contains "T1.6.3" "$_T1_WS/app/src/main/java/com/lauburu/androidauto/agi/voice/VoiceOutputManager.kt" "speak" "Verify VoiceOutputManager expose speak() method"
    assert_file_contains "T1.6.4" "$_T1_WS/app/src/main/java/com/lauburu/androidauto/agi/voice/VoiceOutputManager.kt" "stop|shutdown" "Verify TTS audio cancellation & shutdown"
    assert_file_contains "T1.6.5" "$_T1_WS/app/src/main/java/com/lauburu/androidauto/agi/voice/AudioFocusController.kt" "abandonAudioFocus|release" "Verify audio focus abandon on utterance completion"

    # --------------------------------------------------------------------------
    # F7: Mesh AGI Client & Endpoints
    # --------------------------------------------------------------------------
    print_feature_header "F7" "Mesh AGI Client & Endpoints"
    assert_validator "T1.7.1" "$_T1_VAL/mesh_api_contract_validator.py" "--check-endpoints $_T1_WS" "Verify MeshEndpoints Port 8081 and Port 4000 constants"
    assert_validator "T1.7.2" "$_T1_VAL/mesh_api_contract_validator.py" "--check-client $_T1_WS" "Verify MeshApiClient OkHttp network client implementation"
    assert_validator "T1.7.3" "$_T1_VAL/mesh_api_contract_validator.py" "--check-serialization" "Verify /v1/chat/completions LLM payload serialization"
    assert_validator "T1.7.4" "$_T1_VAL/mesh_api_contract_validator.py" "--check-directive-payload" "Verify /api/voice_coder/directive Hub payload serialization"
    assert_file_contains "T1.7.5" "$_T1_WS/app/src/main/java/com/lauburu/androidauto/agi/api/MeshApiClient.kt" "timeout|connectTimeout|readTimeout" "Verify OkHttp timeout configurations"

    # --------------------------------------------------------------------------
    # F8: 5 Core Voice Directives
    # --------------------------------------------------------------------------
    print_feature_header "F8" "5 Core Voice Directives"
    assert_validator "T1.8.1" "$_T1_VAL/directive_parser_validator.py" "--check-kotlin $_T1_WS" "Verify VoiceDirective sealed class / enum definition"
    assert_validator "T1.8.2" "$_T1_VAL/directive_parser_validator.py" "--test-core-5" "Verify parser accuracy across all 5 core voice directives"
    assert_file_contains "T1.8.3" "$_T1_WS/app/src/main/java/com/lauburu/androidauto/agi/api/VoiceCodingDirectives.kt" "EXPLAIN_DIFF|RUN_TESTS|REFACTOR|GIT_STATUS|COMMIT" "Verify core directive tokens in Kotlin AST"
    assert_file_contains "T1.8.4" "$_T1_WS/app/src/main/java/com/lauburu/androidauto/agi/data/VoiceCodingRepository.kt" "executeDirective" "Verify repository executeDirective interface"
    assert_file_contains "T1.8.5" "$_T1_WS/app/src/main/java/com/lauburu/androidauto/agi/ui/DirectivesListScreen.kt" "VoiceDirective" "Verify DirectivesListScreen references directives"

    # --------------------------------------------------------------------------
    # F9: Coroutine StateFlow UDF Architecture
    # --------------------------------------------------------------------------
    print_feature_header "F9" "Coroutine StateFlow UDF Architecture"
    assert_validator "T1.9.1" "$_T1_VAL/udf_stateflow_validator.py" "--check-uistate $_T1_WS" "Verify VoiceCodingUiState immutable data class"
    assert_validator "T1.9.2" "$_T1_VAL/udf_stateflow_validator.py" "--check-repo $_T1_WS" "Verify VoiceCodingRepository StateFlow exposure"
    assert_validator "T1.9.3" "$_T1_VAL/udf_stateflow_validator.py" "--simulate" "Verify full UDF state transition cycle simulation"
    assert_file_contains "T1.9.4" "$_T1_WS/app/src/main/java/com/lauburu/androidauto/agi/ui/VoiceCodingHudScreen.kt" "invalidate" "Verify Screen reactive invalidate() on state change"
    assert_file_contains "T1.9.5" "$_T1_WS/app/src/main/java/com/lauburu/androidauto/agi/data/VoiceCodingRepository.kt" "Dispatchers|coroutineScope|launch" "Verify Coroutines dispatcher threading separation"

    # --------------------------------------------------------------------------
    # F10: Gradle Assemble & APK Generation
    # --------------------------------------------------------------------------
    print_feature_header "F10" "Gradle Assemble & APK Generation"
    assert_file_exists "T1.10.1" "$_T1_WS/gradlew" "Verify gradlew entrypoint exists"
    assert_file_contains "T1.10.2" "$_T1_WS/app/build.gradle.kts" "com.android.application" "Verify Android application plugin for APK assembly"
    assert_file_contains "T1.10.3" "$_T1_WS/app/build.gradle.kts" "buildTypes" "Verify debug build type configured in app/build.gradle.kts"
    assert_file_contains "T1.10.4" "$_T1_WS/app/src/main/res/values/strings.xml" "app_name" "Verify strings.xml contains app_name resource"
    assert_validator "T1.10.5" "$_T1_VAL/deployment_validator.py" "--check-apk $_T1_WS" "Verify output debug APK artifact availability"

    # --------------------------------------------------------------------------
    # F11: Wireless ADB Deployment to Pixel Target
    # --------------------------------------------------------------------------
    print_feature_header "F11" "Wireless ADB Deployment to Pixel Target"
    assert_file_exists "T1.11.1" "$_T1_WS/deploy_to_pixel.sh" "Verify deploy_to_pixel.sh script exists"
    assert_executable "T1.11.2" "$_T1_WS/deploy_to_pixel.sh" "Verify deploy_to_pixel.sh is executable (+x)"
    assert_validator "T1.11.3" "$_T1_VAL/deployment_validator.py" "--check-script $_T1_WS" "Verify deploy_to_pixel.sh parameters (100.73.38.87:34167)"
    assert_file_contains "T1.11.4" "$_T1_WS/deploy_to_pixel.sh" "pm list packages" "Verify post-deployment package verification command"
    assert_file_contains "T1.11.5" "$_T1_WS/deploy_to_pixel.sh" "adb connect" "Verify wireless ADB connection initiation"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    run_tier1_tests
    print_suite_summary
fi
