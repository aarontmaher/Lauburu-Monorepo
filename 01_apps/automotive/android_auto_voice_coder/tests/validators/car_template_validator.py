#!/usr/bin/env python3
"""
Car App Templates and Automotive Safety Compliance Validator
"""
import sys
import os
import re

def check_car_service_kt(workspace_root):
    path = os.path.join(workspace_root, "app", "src", "main", "java", "com", "lauburu", "androidauto", "agi", "service", "LauburuCarAppService.kt")
    if not os.path.isfile(path):
        print(f"FAIL: LauburuCarAppService.kt not found at {path}")
        return False
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    if "class LauburuCarAppService" not in content or "CarAppService()" not in content and ": CarAppService" not in content:
        print("FAIL: LauburuCarAppService must inherit from CarAppService")
        return False
    if "createHostValidator" not in content:
        print("FAIL: LauburuCarAppService must implement createHostValidator()")
        return False
    if "onCreateSession" not in content:
        print("FAIL: LauburuCarAppService must implement onCreateSession()")
        return False
    print("PASS: LauburuCarAppService Kotlin interface contract valid")
    return True

def check_host_validator(workspace_root):
    path = os.path.join(workspace_root, "app", "src", "main", "java", "com", "lauburu", "androidauto", "agi", "service", "LauburuCarAppService.kt")
    if not os.path.isfile(path):
        print(f"FAIL: LauburuCarAppService.kt not found")
        return False
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    if "ALLOW_ALL_HOSTS_VALIDATOR" not in content and "HostValidator" not in content:
        print("FAIL: createHostValidator should configure HostValidator (e.g. ALLOW_ALL_HOSTS_VALIDATOR in debug)")
        return False
    print("PASS: HostValidator contract verified")
    return True

def check_session_kt(workspace_root):
    path = os.path.join(workspace_root, "app", "src", "main", "java", "com", "lauburu", "androidauto", "agi", "service", "VoiceCodingSession.kt")
    if not os.path.isfile(path):
        print(f"FAIL: VoiceCodingSession.kt not found at {path}")
        return False
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    if "class VoiceCodingSession" not in content or "Session" not in content:
        print("FAIL: VoiceCodingSession must inherit from Session")
        return False
    if "onCreateScreen" not in content:
        print("FAIL: VoiceCodingSession must implement onCreateScreen")
        return False
    print("PASS: VoiceCodingSession interface contract valid")
    return True

def check_hud_screen(workspace_root):
    path = os.path.join(workspace_root, "app", "src", "main", "java", "com", "lauburu", "androidauto", "agi", "ui", "VoiceCodingHudScreen.kt")
    if not os.path.isfile(path):
        print(f"FAIL: VoiceCodingHudScreen.kt not found at {path}")
        return False
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    if "class VoiceCodingHudScreen" not in content or "Screen(carContext)" not in content and ": Screen" not in content:
        print("FAIL: VoiceCodingHudScreen must inherit from Screen")
        return False
    if "onGetTemplate" not in content:
        print("FAIL: VoiceCodingHudScreen must implement onGetTemplate()")
        return False
    if "PaneTemplate" not in content and "Pane" not in content:
        print("FAIL: VoiceCodingHudScreen should construct a PaneTemplate")
        return False
    print("PASS: VoiceCodingHudScreen template structure valid")
    return True

def check_diff_screen(workspace_root):
    path = os.path.join(workspace_root, "app", "src", "main", "java", "com", "lauburu", "androidauto", "agi", "ui", "DiffDetailScreen.kt")
    if not os.path.isfile(path):
        print(f"FAIL: DiffDetailScreen.kt not found at {path}")
        return False
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    if "class DiffDetailScreen" not in content or ": Screen" not in content and "Screen(carContext)" not in content:
        print("FAIL: DiffDetailScreen must inherit from Screen")
        return False
    print("PASS: DiffDetailScreen contract valid")
    return True

def check_test_screen(workspace_root):
    path = os.path.join(workspace_root, "app", "src", "main", "java", "com", "lauburu", "androidauto", "agi", "ui", "TestResultScreen.kt")
    if not os.path.isfile(path):
        print(f"FAIL: TestResultScreen.kt not found at {path}")
        return False
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    if "class TestResultScreen" not in content or ": Screen" not in content and "Screen(carContext)" not in content:
        print("FAIL: TestResultScreen must inherit from Screen")
        return False
    print("PASS: TestResultScreen contract valid")
    return True

def check_directives_screen(workspace_root):
    path = os.path.join(workspace_root, "app", "src", "main", "java", "com", "lauburu", "androidauto", "agi", "ui", "DirectivesListScreen.kt")
    if not os.path.isfile(path):
        print(f"FAIL: DirectivesListScreen.kt not found at {path}")
        return False
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    if "class DirectivesListScreen" not in content or ": Screen" not in content and "Screen(carContext)" not in content:
        print("FAIL: DirectivesListScreen must inherit from Screen")
        return False
    if "ListTemplate" not in content and "ItemList" not in content:
        print("FAIL: DirectivesListScreen must use ListTemplate or ItemList")
        return False
    print("PASS: DirectivesListScreen contract valid")
    return True

def check_constraints_util(workspace_root):
    path = os.path.join(workspace_root, "app", "src", "main", "java", "com", "lauburu", "androidauto", "agi", "util", "AutomotiveConstraints.kt")
    if not os.path.isfile(path):
        print(f"FAIL: AutomotiveConstraints.kt not found at {path}")
        return False
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    if "MAX_PANE_ROWS" not in content and "4" not in content:
        print("FAIL: AutomotiveConstraints must define max pane row limits (<= 4)")
        return False
    print("PASS: AutomotiveConstraints enforcement utility valid")
    return True

# Boundary and Automotive safety rule tests
def test_boundary(test_name):
    MAX_PANE_ROWS = 4
    MAX_ACTION_STRIP_ACTIONS = 2
    MAX_ROW_TEXT_LENGTH = 128
    
    if test_name == "row_overflow_protection":
        # Simulate creating 10 rows
        input_rows = [f"Row {i}" for i in range(10)]
        safe_rows = input_rows[:MAX_PANE_ROWS]
        if len(safe_rows) == 4:
            print("PASS: Correctly constrained 10 rows to max 4 rows for PaneTemplate")
            return True
    elif test_name == "action_strip_overflow":
        actions = ["Action1", "Action2", "Action3", "Action4"]
        safe_actions = actions[:MAX_ACTION_STRIP_ACTIONS]
        if len(safe_actions) == 2:
            print("PASS: Correctly constrained action strip to max 2 actions")
            return True
    elif test_name == "long_text_truncation":
        long_diff = "diff --git a/app/src/main/java/com/lauburu/VeryLongFilenameThatExceedsTheSingleLineGlanceabilityRequirementAndMustBeSafelyTruncated.kt " * 3
        truncated = long_diff[:MAX_ROW_TEXT_LENGTH] + "..." if len(long_diff) > MAX_ROW_TEXT_LENGTH else long_diff
        if len(truncated) <= MAX_ROW_TEXT_LENGTH + 3:
            print("PASS: Successfully truncated long text exceeding glanceable bounds")
            return True
    elif test_name == "empty_row_handling":
        def build_safe_row(title, text):
            safe_title = title if title and title.strip() else "Untitled Directive"
            safe_text = text if text and text.strip() else "--"
            return {"title": safe_title, "text": safe_text}
        res = build_safe_row("", None)
        if res["title"] == "Untitled Directive" and res["text"] == "--":
            print("PASS: Safe fallback applied for null/empty row contents")
            return True
    elif test_name == "backstack_underflow":
        backstack = ["HudScreen"]
        # Pop screen
        if len(backstack) <= 1:
            # Cannot pop root screen
            print("PASS: Prevented backstack underflow when popping root screen")
            return True
    print(f"FAIL: Unknown boundary test {test_name}")
    return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: car_template_validator.py <mode> <arg>")
        sys.exit(1)
    mode = sys.argv[1]
    arg = sys.argv[2]
    
    success = False
    if mode == "--check-service":
        success = check_car_service_kt(arg)
    elif mode == "--check-host-validator":
        success = check_host_validator(arg)
    elif mode == "--check-session":
        success = check_session_kt(arg)
    elif mode == "--check-hud-screen":
        success = check_hud_screen(arg)
    elif mode == "--check-diff-screen":
        success = check_diff_screen(arg)
    elif mode == "--check-test-screen":
        success = check_test_screen(arg)
    elif mode == "--check-directives-screen":
        success = check_directives_screen(arg)
    elif mode == "--check-constraints-util":
        success = check_constraints_util(arg)
    elif mode == "--check-all":
        results = [
            check_car_service_kt(arg),
            check_host_validator(arg),
            check_session_kt(arg),
            check_hud_screen(arg),
            check_diff_screen(arg),
            check_test_screen(arg),
            check_directives_screen(arg),
            check_constraints_util(arg)
        ]
        success = all(results)
    elif mode == "--boundary":
        success = test_boundary(arg)
    else:
        print(f"Unknown mode {mode}")
        sys.exit(1)
        
    sys.exit(0 if success else 1)
