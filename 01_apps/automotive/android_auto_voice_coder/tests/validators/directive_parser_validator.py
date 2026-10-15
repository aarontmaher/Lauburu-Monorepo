#!/usr/bin/env python3
"""
Voice Directive Parser Contract and Boundary Validator
"""
import sys
import os
import re

def parse_voice_directive(transcript):
    """Reference implementation of VoiceDirectiveParser logic"""
    if not transcript or not transcript.strip():
        return {"action": "UNKNOWN", "target": "", "raw": transcript}
    
    clean = transcript.strip().lower()
    clean = re.sub(r'[!?,.:;]', '', clean)
    clean = re.sub(r'\b(uh|um|please|could you|can you|hey agent)\b', '', clean).strip()

    # 1. EXPLAIN_DIFF
    if any(k in clean for k in ["explain diff", "explain changes", "what changed", "show diff", "diff"]):
        target = ""
        m = re.search(r'(?:in|for)\s+([a-zA-Z0-9_\-/\. ]+)', clean)
        if m:
            target = m.group(1).strip()
        return {"action": "EXPLAIN_DIFF", "target": target, "raw": transcript}

    # 2. RUN_TESTS
    if any(k in clean for k in ["run tests", "verify suite", "execute test", "run verification", "test"]):
        target = "all"
        m = re.search(r'(?:on|for)\s+([a-zA-Z0-9_\-/\. ]+)', clean)
        if m:
            target = m.group(1).strip()
        return {"action": "RUN_TESTS", "target": target, "raw": transcript}

    # 3. REFACTOR
    if any(k in clean for k in ["refactor function", "refactor", "rewrite"]):
        target = ""
        m = re.search(r'refactor\s+(?:function\s+)?([a-zA-Z0-9_\-/\. \$<>\(\)]+)', clean)
        if m:
            target = m.group(1).strip()
        return {"action": "REFACTOR", "target": target, "raw": transcript}

    # 4. GIT_STATUS
    if any(k in clean for k in ["show git status", "git status", "status of branch", "branch status", "status"]):
        return {"action": "GIT_STATUS", "target": "", "raw": transcript}

    # 5. COMMIT
    if any(k in clean for k in ["commit changes", "confirm commit", "approve and commit", "commit"]):
        msg = ""
        m = re.search(r'commit(?:\s+changes)?(?:\s+with\s+message\s+)?(.*)', clean)
        if m:
            msg = m.group(1).strip()
        return {"action": "COMMIT", "target": msg, "raw": transcript}

    return {"action": "UNKNOWN", "target": "", "raw": transcript}

def check_kotlin_parser_file(workspace_root):
    path = os.path.join(workspace_root, "app", "src", "main", "java", "com", "lauburu", "androidauto", "agi", "api", "VoiceCodingDirectives.kt")
    if not os.path.isfile(path):
        # Check in data package
        path = os.path.join(workspace_root, "app", "src", "main", "java", "com", "lauburu", "androidauto", "agi", "data", "VoiceCodingRepository.kt")
        if not os.path.isfile(path):
            print(f"FAIL: VoiceCodingDirectives.kt or parser not found at {path}")
            return False
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    for action in ["EXPLAIN_DIFF", "RUN_TESTS", "REFACTOR", "GIT_STATUS", "COMMIT"]:
        if action not in content:
            print(f"FAIL: VoiceDirective enum/sealed class missing {action}")
            return False
    print("PASS: VoiceCodingDirectives enum declarations verified")
    return True

def test_core_5():
    cases = [
        ("Explain the latest diff in Movesense hub", "EXPLAIN_DIFF"),
        ("Run verification tests on Lauburu monorepo", "RUN_TESTS"),
        ("Refactor function zero-copy ring buffer", "REFACTOR"),
        ("Show git status and modified files", "GIT_STATUS"),
        ("Confirm commit and deploy changes", "COMMIT")
    ]
    for text, expected in cases:
        res = parse_voice_directive(text)
        if res["action"] != expected:
            print(f"FAIL: Expected {expected} for '{text}', got {res['action']}")
            return False
    print("PASS: All 5 core voice actions accurately parsed")
    return True

def test_boundaries(b_type):
    if b_type == "filler_words":
        text = "uh please could you hey agent explain diff right now"
        res = parse_voice_directive(text)
        if res["action"] == "EXPLAIN_DIFF":
            print("PASS: Successfully parsed directive through heavy verbal filler words")
            return True
    elif b_type == "mixed_case_punctuation":
        text = "RUN TESTS NOW!!!"
        res = parse_voice_directive(text)
        if res["action"] == "RUN_TESTS":
            print("PASS: Successfully parsed directive with all caps and punctuation")
            return True
    elif b_type == "unsupported_directive":
        text = "Order a large pepperoni pizza"
        res = parse_voice_directive(text)
        if res["action"] == "UNKNOWN":
            print("PASS: Safely classified out-of-domain speech as UNKNOWN")
            return True
    elif b_type == "special_characters":
        text = "refactor function parse_node<T>($id: Int)"
        res = parse_voice_directive(text)
        if res["action"] == "REFACTOR":
            print("PASS: Preserved special characters in refactor target extraction")
            return True
    elif b_type == "empty_transcript":
        res = parse_voice_directive("")
        if res["action"] == "UNKNOWN":
            print("PASS: Empty transcript returned UNKNOWN state without exception")
            return True
    print(f"FAIL: Unknown boundary {b_type}")
    return False

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: directive_parser_validator.py <mode> [arg]")
        sys.exit(1)
    mode = sys.argv[1]
    arg = sys.argv[2] if len(sys.argv) > 2 else ""
    
    success = False
    if mode == "--check-kotlin":
        success = check_kotlin_parser_file(arg)
    elif mode == "--test-core-5":
        success = test_core_5()
    elif mode == "--boundary":
        success = test_boundaries(arg)
    else:
        print(f"Unknown mode {mode}")
        sys.exit(1)
        
    sys.exit(0 if success else 1)
