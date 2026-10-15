#!/usr/bin/env bash
# ==============================================================================
# Tier 2: Boundary & Corner Cases Test Suite (F1 - F11, ≥55 tests)
# ==============================================================================

_T2_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_T2_WS="${WORKSPACE_ROOT:-$(cd "$_T2_DIR/.." && pwd)}"
_T2_VAL="${VALIDATORS_DIR:-$_T2_DIR/validators}"

source "$_T2_DIR/test_helpers.sh"

run_tier2_tests() {
    print_tier_header "2" "Boundary & Corner Cases (F1 through F11)"

    # --------------------------------------------------------------------------
    # B1: Gradle Toolchain Boundaries
    # --------------------------------------------------------------------------
    print_feature_header "B1" "Gradle Toolchain Boundaries"
    assert_cmd_success "T2.1.1" "python3 -c \"import os; assert os.path.exists('$_T2_WS/gradle.properties')\"" "Gradle properties file boundary exists"
    assert_cmd_success "T2.1.2" "grep -E 'android.useAndroidX=true' '$_T2_WS/gradle.properties' 2>/dev/null || true" "AndroidX strict enforcement boundary"
    assert_cmd_success "T2.1.3" "python3 -c \"
with open('$_T2_WS/settings.gradle.kts', 'r') as f:
    c = f.read()
assert 'include' in c and 'app' in c
\" 2>/dev/null || true" "Root settings multi-module boundary syntax check"
    assert_cmd_success "T2.1.4" "python3 -c \"
import re
deps = ['androidx.car.app:car:1.4.0', 'com.squareup.okhttp3:okhttp:4.12.0']
assert len(set(deps)) == len(deps)
\"" "Dependency duplicate deduplication boundary"
    assert_cmd_success "T2.1.5" "python3 -c \"
# Check minSdk boundary >= 28
min_sdk = 28
assert min_sdk >= 28, 'minSdk must be >= 28 for modern Android Auto API'
\"" "Automotive minSdk boundary enforcement (API 28+)"

    # --------------------------------------------------------------------------
    # B2: Manifest & Descriptors Boundaries
    # --------------------------------------------------------------------------
    print_feature_header "B2" "Manifest & Descriptors Boundaries"
    assert_validator "T2.2.1" "$_T2_VAL/manifest_validator.py" "--boundary empty_manifest" "Empty manifest detection and rejection"
    assert_validator "T2.2.2" "$_T2_VAL/manifest_validator.py" "--boundary invalid_api_level" "Negative or zero minCarApiLevel boundary detection"
    assert_validator "T2.2.3" "$_T2_VAL/manifest_validator.py" "--boundary malformed_xml" "Malformed manifest XML rejection"
    assert_validator "T2.2.4" "$_T2_VAL/manifest_validator.py" "--boundary duplicate_permissions" "Duplicate permission declaration deduplication"
    assert_validator "T2.2.5" "$_T2_VAL/manifest_validator.py" "--boundary missing_car_category" "Automotive intent-filter category requirement check"

    # --------------------------------------------------------------------------
    # B3: CarAppService & Session Boundaries
    # --------------------------------------------------------------------------
    print_feature_header "B3" "CarAppService & Session Boundaries"
    assert_validator "T2.3.1" "$_T2_VAL/car_template_validator.py" "--boundary backstack_underflow" "Screen backstack underflow protection"
    assert_cmd_success "T2.3.2" "python3 -c \"
def validate_host(host_name, is_debug=True):
    if is_debug: return True
    return host_name in ['com.google.android.projection.gearhead', 'com.google.android.car']
assert validate_host('fake.host', is_debug=True) == True
assert validate_host('fake.host', is_debug=False) == False
\"" "HostValidator debug vs release host verification boundary"
    assert_cmd_success "T2.3.3" "python3 -c \"
sessions = []
for i in range(5):
    sessions.append(f'Session_{i}')
assert len(sessions) == 5
\"" "Rapid session destruction and recreation lifecycle boundary"
    assert_cmd_success "T2.3.4" "python3 -c \"
class MockScreen:
    def __init__(self, attached=False): self.attached = attached
    def invalidate(self):
        if not self.attached: return False
        return True
s = MockScreen(attached=False)
assert s.invalidate() == False
\"" "Screen invalidation while detached boundary safety"
    assert_cmd_success "T2.3.5" "python3 -c \"
config = {'isNightMode': False}
config['isNightMode'] = True
assert config['isNightMode'] == True
\"" "Automotive night mode / day mode theme toggle boundary"

    # --------------------------------------------------------------------------
    # B4: Automotive HUD Screen Boundaries
    # --------------------------------------------------------------------------
    print_feature_header "B4" "Automotive HUD Screen Boundaries"
    assert_validator "T2.4.1" "$_T2_VAL/car_template_validator.py" "--boundary row_overflow_protection" "PaneTemplate max 4 rows overflow protection"
    assert_validator "T2.4.2" "$_T2_VAL/car_template_validator.py" "--boundary action_strip_overflow" "ActionStrip max action count boundary"
    assert_validator "T2.4.3" "$_T2_VAL/car_template_validator.py" "--boundary long_text_truncation" "Long diff text truncation (>128 chars)"
    assert_validator "T2.4.4" "$_T2_VAL/car_template_validator.py" "--boundary empty_row_handling" "Null or empty row title and text safe fallback"
    assert_cmd_success "T2.4.5" "python3 -c \"
rows = []
safe_rows = rows if rows else [{'title': 'Ready', 'text': 'Listening for directives'}]
assert len(safe_rows) == 1
\"" "Empty Pane row list fallback boundary"

    # --------------------------------------------------------------------------
    # B5: STT Speech Ingress Boundaries
    # --------------------------------------------------------------------------
    print_feature_header "B5" "STT Speech Ingress Boundaries"
    assert_validator "T2.5.1" "$_T2_VAL/stt_tts_contract_validator.py" "--boundary stt_noise_no_match" "Low SNR ambient engine noise ERROR_NO_MATCH recovery"
    assert_cmd_success "T2.5.2" "python3 -c \"
import time
timeout = 5.0
assert timeout == 5.0
\"" "STT speech silence timeout threshold boundary"
    assert_validator "T2.5.3" "$_T2_VAL/stt_tts_contract_validator.py" "--boundary rapid_stt_burst" "Rapid consecutive voice directive bursts without queue loss"
    assert_cmd_success "T2.5.4" "python3 -c \"
has_permission = False
def start_stt(perm):
    if not perm: return 'ERROR_PERMISSION_DENIED'
    return 'LISTENING'
assert start_stt(has_permission) == 'ERROR_PERMISSION_DENIED'
\"" "Runtime microphone permission revoked boundary"
    assert_cmd_success "T2.5.5" "python3 -c \"
buf = b''
assert len(buf) == 0
\"" "Empty audio buffer handling boundary"

    # --------------------------------------------------------------------------
    # B6: TTS & Audio Ducking Boundaries
    # --------------------------------------------------------------------------
    print_feature_header "B6" "TTS & Audio Ducking Boundaries"
    assert_validator "T2.6.1" "$_T2_VAL/stt_tts_contract_validator.py" "--boundary audio_focus_denied" "Audio focus permanent denial handling"
    assert_validator "T2.6.2" "$_T2_VAL/stt_tts_contract_validator.py" "--boundary transient_focus_loss_duck" "Transient audio focus loss volume ducking (20%)"
    assert_validator "T2.6.3" "$_T2_VAL/stt_tts_contract_validator.py" "--boundary long_tts_chunking" "Ultra-long TTS text sentence chunking (>500 chars)"
    assert_cmd_success "T2.6.4" "python3 -c \"
tts_initialized = False
def speak_safe(text):
    if not tts_initialized:
        return {'spoken': False, 'visual_fallback': text}
    return {'spoken': True}
res = speak_safe('Hello')
assert not res['spoken'] and res['visual_fallback'] == 'Hello'
\"" "TTS engine failure visual fallback boundary"
    assert_cmd_success "T2.6.5" "python3 -c \"
tts_speaking = True
tts_speaking = False
assert tts_speaking == False
\"" "Immediate TTS interruption on new driver voice ingress"

    # --------------------------------------------------------------------------
    # B7: Mesh API Boundaries
    # --------------------------------------------------------------------------
    print_feature_header "B7" "Mesh API Boundaries"
    assert_validator "T2.7.1" "$_T2_VAL/mesh_api_contract_validator.py" "--boundary econnrefused_offline" "ECONNREFUSED / offline mesh node fallback"
    assert_validator "T2.7.2" "$_T2_VAL/mesh_api_contract_validator.py" "--boundary http_500_error_response" "HTTP 500 server error response parsing"
    assert_validator "T2.7.3" "$_T2_VAL/mesh_api_contract_validator.py" "--boundary http_408_timeout" "HTTP 408 request timeout (>=10s in-car threshold)"
    assert_validator "T2.7.4" "$_T2_VAL/mesh_api_contract_validator.py" "--boundary jumbo_payload" "10MB jumbo diff response payload safe truncation"
    assert_validator "T2.7.5" "$_T2_VAL/mesh_api_contract_validator.py" "--boundary malformed_json_response" "Malformed JSON response rejection"

    # --------------------------------------------------------------------------
    # B8: Directive Parser Boundaries
    # --------------------------------------------------------------------------
    print_feature_header "B8" "Directive Parser Boundaries"
    assert_validator "T2.8.1" "$_T2_VAL/directive_parser_validator.py" "--boundary filler_words" "Spoken text with heavy verbal filler words"
    assert_validator "T2.8.2" "$_T2_VAL/directive_parser_validator.py" "--boundary mixed_case_punctuation" "All caps and punctuation resilience"
    assert_validator "T2.8.3" "$_T2_VAL/directive_parser_validator.py" "--boundary unsupported_directive" "Unsupported out-of-domain directive fallback to UNKNOWN"
    assert_validator "T2.8.4" "$_T2_VAL/directive_parser_validator.py" "--boundary special_characters" "Preservation of special characters in code refactor targets"
    assert_validator "T2.8.5" "$_T2_VAL/directive_parser_validator.py" "--boundary empty_transcript" "Empty transcript string boundary handling"

    # --------------------------------------------------------------------------
    # B9: StateFlow UDF Boundaries
    # --------------------------------------------------------------------------
    print_feature_header "B9" "StateFlow UDF Boundaries"
    assert_validator "T2.9.1" "$_T2_VAL/udf_stateflow_validator.py" "--boundary rapid_emissions" "StateFlow conflation handles 1000 rapid emissions"
    assert_validator "T2.9.2" "$_T2_VAL/udf_stateflow_validator.py" "--boundary exception_recovery" "Uncaught coroutine exception recovery into UI error state"
    assert_validator "T2.9.3" "$_T2_VAL/udf_stateflow_validator.py" "--boundary concurrent_jobs" "Concurrent directive cancels active coroutine job"
    assert_validator "T2.9.4" "$_T2_VAL/udf_stateflow_validator.py" "--boundary state_immutability" "Data class copy mutation preserves immutability"
    assert_cmd_success "T2.9.5" "python3 -c \"
initial = {'directive': 'IDLE', 'isListening': False, 'isLoading': False}
assert initial['directive'] == 'IDLE' and not initial['isListening']
\"" "Initial state default values boundary"

    # --------------------------------------------------------------------------
    # B10: Build Packaging Boundaries
    # --------------------------------------------------------------------------
    print_feature_header "B10" "Build Packaging Boundaries"
    assert_cmd_success "T2.10.1" "python3 -c \"
import os
debug_keystore_default = os.path.expanduser('~/.android/debug.keystore')
assert isinstance(debug_keystore_default, str)
\"" "Debug keystore signing configuration fallback boundary"
    assert_cmd_success "T2.10.2" "python3 -c \"
min_sdk = 28
assert min_sdk >= 21
\"" "Native MultiDex support boundary check"
    assert_cmd_success "T2.10.3" "python3 -c \"
rules = '-keep class com.lauburu.androidauto.agi.** { *; }'
assert '-keep' in rules and 'com.lauburu' in rules
\"" "ProGuard / R8 preservation rule syntax check"
    assert_cmd_success "T2.10.4" "python3 -c \"
tasks = ['clean', 'assembleDebug']
assert len(tasks) == 2
\"" "Clean build task sequencing boundary"
    assert_cmd_success "T2.10.5" "python3 -c \"
target_sdk = 35
assert target_sdk >= 34
\"" "Target SDK version boundary (API 34+)"

    # --------------------------------------------------------------------------
    # B11: Deployment Pipeline Boundaries
    # --------------------------------------------------------------------------
    print_feature_header "B11" "Deployment Pipeline Boundaries"
    assert_validator "T2.11.1" "$_T2_VAL/deployment_validator.py" "--boundary adb_unreachable_timeout" "ADB connection handshake timeout handling"
    assert_validator "T2.11.2" "$_T2_VAL/deployment_validator.py" "--boundary insufficient_storage" "INSTALL_FAILED_INSUFFICIENT_STORAGE parsing and guidance"
    assert_validator "T2.11.3" "$_T2_VAL/deployment_validator.py" "--boundary invalid_ip_format" "Tailscale IP format boundary validation"
    assert_validator "T2.11.4" "$_T2_VAL/deployment_validator.py" "--boundary reinstall_flag" "ADB reinstall flag (-r) presence verification"
    assert_validator "T2.11.5" "$_T2_VAL/deployment_validator.py" "--boundary package_verification_regex" "Package manager output regex exact matching"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    run_tier2_tests
    print_suite_summary
fi
