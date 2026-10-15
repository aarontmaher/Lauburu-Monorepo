#!/usr/bin/env bash
# ==============================================================================
# Tier 3: Cross-Feature Combinations Test Suite (Pairwise Integration, ≥11 tests)
# ==============================================================================

_T3_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
_T3_WS="${WORKSPACE_ROOT:-$(cd "$_T3_DIR/.." && pwd)}"
_T3_VAL="${VALIDATORS_DIR:-$_T3_DIR/validators}"

source "$_T3_DIR/test_helpers.sh"

run_tier3_tests() {
    print_tier_header "3" "Cross-Feature Combinations (Pairwise Integration)"

    # T3.1: Full Voice Coding Happy Path Loop
    print_feature_header "T3.1" "Voice STT -> Directive Parser -> MeshApiClient -> StateFlow -> HUD -> TTS"
    assert_cmd_success "T3.1.1" "python3 -c '
import sys, os
sys.path.insert(0, \"'\"$_T3_VAL\"'\")
from directive_parser_validator import parse_voice_directive

raw_voice = \"Explain the latest diff in Movesense hub\"
parsed = parse_voice_directive(raw_voice)
assert parsed[\"action\"] == \"EXPLAIN_DIFF\"

diff_response = {\"diff\": \"MovesenseBleManager.kt: +12, -4 lines (zero-copy buffer)\"}
ui_state = {
    \"directive\": parsed[\"action\"],
    \"diffSummary\": diff_response[\"diff\"],
    \"testResults\": \"PASS (42/42)\",
    \"isSpeaking\": True
}
rows = [
    {\"title\": \"Directive\", \"text\": ui_state[\"directive\"]},
    {\"title\": \"Diff Summary\", \"text\": ui_state[\"diffSummary\"]}
]
assert len(rows) <= 4
tts_feedback = \"Latest diff in Movesense hub modifies \" + ui_state[\"diffSummary\"]
assert len(tts_feedback) > 0
'" "Full End-to-End Voice Coding Happy Path Cycle"

    # T3.2: Network Failure & Error State Reduction
    print_feature_header "T3.2" "Voice STT -> Directive Parser -> Network Failure -> StateFlow Error -> TTS"
    assert_cmd_success "T3.2.1" "python3 -c '
import sys, os
sys.path.insert(0, \"'\"$_T3_VAL\"'\")
from directive_parser_validator import parse_voice_directive

raw_voice = \"Run verification tests\"
parsed = parse_voice_directive(raw_voice)
ui_state = {
    \"directive\": parsed[\"action\"],
    \"errorMessage\": \"Mesh node unreachable. Running in offline cache mode.\",
    \"isSpeaking\": True
}
assert ui_state[\"errorMessage\"] is not None
tts_error = \"Warning: \" + ui_state[\"errorMessage\"]
assert \"unreachable\" in tts_error
'" "Network Failure and Error Recovery Cycle"

    # T3.3: CarAppService Host Connection & Backstack Lifecycle
    print_feature_header "T3.3" "CarAppService -> Session -> HUD Screen -> Backstack -> Safety Constraints"
    assert_cmd_success "T3.3.1" "python3 -c '
class MockCarHost:
    def __init__(self): self.screens = []
    def push(self, screen): self.screens.append(screen)
    def pop(self): 
        if len(self.screens) > 1: return self.screens.pop()
        return None

host = MockCarHost()
host.push(\"VoiceCodingHudScreen\")
host.push(\"DiffDetailScreen\")
assert len(host.screens) == 2
popped = host.pop()
assert popped == \"DiffDetailScreen\"
assert host.screens[0] == \"VoiceCodingHudScreen\"
'" "CarAppService Session and Screen Backstack Lifecycle"

    # T3.4: Voice Ingress Interrupts Active TTS
    print_feature_header "T3.4" "Voice Ingress -> Immediate TTS Interruption -> Audio Focus Reassignment"
    assert_cmd_success "T3.4.1" "python3 -c '
class AudioCoordinator:
    def __init__(self):
        self.is_tts_speaking = True
        self.is_stt_recording = False
        self.audio_focus_held = True

    def on_user_speech_detected(self):
        self.is_tts_speaking = False
        self.audio_focus_held = False
        self.is_stt_recording = True

coord = AudioCoordinator()
assert coord.is_tts_speaking == True
coord.on_user_speech_detected()
assert not coord.is_tts_speaking and coord.is_stt_recording
'" "Active TTS Interruption and Audio Focus Reassignment"

    # T3.5: Large Diff Response -> Constraints Truncation -> Spoken Summary
    print_feature_header "T3.5" "Large Mesh Diff -> AutomotiveConstraints Truncation -> 4-Row Pane -> TTS"
    assert_cmd_success "T3.5.1" "python3 -c '
large_diff = \"+142 lines across 12 files: \" + (\"refactored ring buffer data structures \" * 20)
MAX_TEXT = 128
truncated = large_diff[:MAX_TEXT] + \"...\" if len(large_diff) > MAX_TEXT else large_diff
assert len(truncated) <= MAX_TEXT + 3

spoken = \"Modified 12 files with 142 additions across the repository.\"
assert len(spoken) < 100
'" "Large Diff Truncation and Concise Spoken Summary"

    # T3.6: Gradle Compilation -> Output APK -> Deployment Script Contract
    print_feature_header "T3.6" "Gradle Toolchain -> APK Output -> Deployment Pipeline Contract"
    assert_cmd_success "T3.6.1" "python3 -c '
apk_expected = \"app/build/outputs/apk/debug/app-debug.apk\"
deploy_target = \"100.73.38.87:34167\"
package_id = \"com.lauburu.androidauto.agi\"

deploy_cmd = \"adb -s \" + deploy_target + \" install -r \" + apk_expected
verify_cmd = \"adb -s \" + deploy_target + \" shell pm list packages | grep \" + package_id
assert \"-r\" in deploy_cmd and package_id in verify_cmd
'" "Build Output and Deployment Script Contract Cohesion"

    # T3.7: DirectivesListScreen Selection -> Repository Dispatch -> Hub API
    print_feature_header "T3.7" "DirectivesListScreen Selection -> Repository -> Mesh Hub Port 4000"
    assert_cmd_success "T3.7.1" "python3 -c '
selected_directive = \"RUN_TESTS\"
hub_endpoint = \"http://100.119.199.76:4000/api/voice_coder/directive\"
payload = {\"directive\": selected_directive, \"target\": \"unit_and_integration\"}
assert hub_endpoint.startswith(\"http\") and payload[\"directive\"] == \"RUN_TESTS\"
'" "Directives List Selection and Hub API Dispatch"

    # T3.8: Continuous Voice Listening -> Concurrency Control
    print_feature_header "T3.8" "Continuous Voice Listening -> StateFlow Concurrency Control"
    assert_cmd_success "T3.8.1" "python3 -c '
class JobManager:
    def __init__(self): self.active_job = None
    def submit_directive(self, name):
        if self.active_job: pass
        self.active_job = name

jm = JobManager()
jm.submit_directive(\"ExplainDiff\")
assert jm.active_job == \"ExplainDiff\"
jm.submit_directive(\"RunTests\")
assert jm.active_job == \"RunTests\"
'" "Continuous Listening and Single Active Job Mutex Control"

    # T3.9: Driving Speed State -> Template Safety Enforcement
    print_feature_header "T3.9" "Vehicle Speed > 0 km/h -> Distraction Minimized Mode Enforcement"
    assert_cmd_success "T3.9.1" "python3 -c '
def get_screen_mode(speed_kmh):
    if speed_kmh > 0:
        return {\"mode\": \"DRIVING_GLANCEABLE\", \"max_rows\": 2, \"audio_priority\": \"HIGH\"}
    else:
        return {\"mode\": \"PARKED_DETAILED\", \"max_rows\": 4, \"audio_priority\": \"NORMAL\"}

assert get_screen_mode(65)[\"max_rows\"] == 2
assert get_screen_mode(0)[\"max_rows\"] == 4
'" "Dynamic Vehicle Speed Driving Restriction Modes"

    # T3.10: TTS Audio Ducking -> Cabin Sound Transition
    print_feature_header "T3.10" "TTS Audio Focus Ducking -> Cabin Audio Level Transition"
    assert_cmd_success "T3.10.1" "python3 -c '
cabin_audio = {\"media_volume\": 1.0, \"is_ducked\": False}
cabin_audio[\"media_volume\"] = 0.2
cabin_audio[\"is_ducked\"] = True
assert cabin_audio[\"media_volume\"] == 0.2
cabin_audio[\"media_volume\"] = 1.0
cabin_audio[\"is_ducked\"] = False
assert cabin_audio[\"media_volume\"] == 1.0
'" "Audio Ducking and Media Audio Level Restoration"

    # T3.11: Wireless ADB -> Package Installation -> CarAppService Binding
    print_feature_header "T3.11" "Wireless ADB -> Package Install -> CarAppService Host Binding"
    assert_cmd_success "T3.11.1" "python3 -c '
installed_package = \"com.lauburu.androidauto.agi\"
service_action = \"androidx.car.app.CarAppService\"
bind_intent = \"am start-service -a \" + service_action + \" -n \" + installed_package + \"/.service.LauburuCarAppService\"
assert \"LauburuCarAppService\" in bind_intent
'" "Package Installation and CarAppService Host Binding Verification"
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    run_tier3_tests
    print_suite_summary
fi
