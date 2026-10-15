#!/usr/bin/env python3
"""
Gradle build configuration validator for Android Auto AGI
"""
import sys
import os
import re

def check_root_settings(workspace_root):
    path = os.path.join(workspace_root, "settings.gradle.kts")
    if not os.path.isfile(path):
        # Fallback to groovy if kts not present
        path = os.path.join(workspace_root, "settings.gradle")
        if not os.path.isfile(path):
            print(f"FAIL: Neither settings.gradle.kts nor settings.gradle found in {workspace_root}")
            return False
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    if 'rootProject.name' not in content and 'rootProject.setName' not in content:
        print("FAIL: rootProject.name missing from settings")
        return False
    if 'include(":app")' not in content and 'include(\":app\")' not in content and "include ':app'" not in content and 'include("app")' not in content:
        print("FAIL: app module not included in settings")
        return False
    print("PASS: Root settings valid")
    return True

def check_root_build(workspace_root):
    path = os.path.join(workspace_root, "build.gradle.kts")
    if not os.path.isfile(path):
        path = os.path.join(workspace_root, "build.gradle")
        if not os.path.isfile(path):
            print(f"FAIL: Root build.gradle(.kts) not found")
            return False
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    # Check plugins or buildscript
    has_android_plugin = "com.android.application" in content or "android" in content
    has_kotlin_plugin = "kotlin" in content or "org.jetbrains.kotlin" in content
    if not (has_android_plugin and has_kotlin_plugin):
        print("FAIL: Missing Android or Kotlin plugin definition in root build.gradle(.kts)")
        return False
    print("PASS: Root build configuration valid")
    return True

def check_app_build(workspace_root):
    path = os.path.join(workspace_root, "app", "build.gradle.kts")
    if not os.path.isfile(path):
        path = os.path.join(workspace_root, "app", "build.gradle")
        if not os.path.isfile(path):
            print(f"FAIL: app/build.gradle(.kts) not found")
            return False
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    # Check essential requirements
    checks = [
        ("namespace", r'namespace\s*=\s*"com\.lauburu\.androidauto\.agi"|applicationId\s*["\']com\.lauburu\.androidauto\.agi["\']'),
        ("androidx.car.app dependency", r'androidx\.car\.app:app|androidx\.car\.app:app-automotive|androidx\.car\.app:app-projected|androidx\.car\.app'),
        ("okhttp dependency", r'okhttp3|okhttp'),
        ("coroutines dependency", r'kotlinx-coroutines|coroutines'),
    ]
    for name, pattern in checks:
        if not re.search(pattern, content):
            print(f"FAIL: Missing {name} in app/build.gradle(.kts)")
            return False
    print("PASS: app/build.gradle dependencies and namespace valid")
    return True

def check_properties(workspace_root):
    prop_path = os.path.join(workspace_root, "gradle.properties")
    if not os.path.isfile(prop_path):
        print(f"FAIL: gradle.properties missing")
        return False
    with open(prop_path, "r", encoding="utf-8") as f:
        content = f.read()
    if "android.useAndroidX=true" not in content.replace(" ", ""):
        print("FAIL: android.useAndroidX=true missing from gradle.properties")
        return False
    print("PASS: gradle.properties contains valid AndroidX flags")
    return True

def check_wrapper(workspace_root):
    wrapper_props = os.path.join(workspace_root, "gradle", "wrapper", "gradle-wrapper.properties")
    gradlew = os.path.join(workspace_root, "gradlew")
    if not os.path.isfile(gradlew):
        print("FAIL: gradlew script missing")
        return False
    if not os.path.isfile(wrapper_props):
        print("FAIL: gradle-wrapper.properties missing")
        return False
    with open(wrapper_props, "r", encoding="utf-8") as f:
        content = f.read()
    if "gradle-" not in content or "distributionUrl" not in content:
        print("FAIL: gradle-wrapper distributionUrl missing")
        return False
    print("PASS: Gradle wrapper files present and configured")
    return True

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: gradle_validator.py <mode> <workspace_root>")
        sys.exit(1)
    mode = sys.argv[1]
    ws = sys.argv[2]
    
    success = False
    if mode == "--check-root-settings":
        success = check_root_settings(ws)
    elif mode == "--check-root-build":
        success = check_root_build(ws)
    elif mode == "--check-app-build":
        success = check_app_build(ws)
    elif mode == "--check-properties":
        success = check_properties(ws)
    elif mode == "--check-wrapper":
        success = check_wrapper(ws)
    elif mode == "--check-all":
        success = (check_root_settings(ws) and 
                   check_root_build(ws) and 
                   check_app_build(ws) and 
                   check_properties(ws) and 
                   check_wrapper(ws))
    else:
        print(f"Unknown mode: {mode}")
        sys.exit(1)
    
    sys.exit(0 if success else 1)
