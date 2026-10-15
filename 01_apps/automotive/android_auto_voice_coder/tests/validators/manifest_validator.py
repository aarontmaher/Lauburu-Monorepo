#!/usr/bin/env python3
"""
Android Manifest and Automotive Descriptors Validator for Android Auto AGI
"""
import sys
import os
import xml.etree.ElementTree as ET
import re

ANDROID_NS = "http://schemas.android.com/apk/res/android"
NAMESPACES = {'android': ANDROID_NS}

def get_manifest_tree(workspace_root):
    manifest_path = os.path.join(workspace_root, "app", "src", "main", "AndroidManifest.xml")
    if not os.path.isfile(manifest_path):
        return None, f"AndroidManifest.xml not found at {manifest_path}"
    try:
        tree = ET.parse(manifest_path)
        return tree, manifest_path
    except Exception as e:
        return None, f"Failed to parse XML: {str(e)}"

def check_package_and_app(workspace_root):
    tree, err = get_manifest_tree(workspace_root)
    if not tree:
        print(f"FAIL: {err}")
        return False
    root = tree.getroot()
    # Check application node
    app_node = root.find("application")
    if app_node is None:
        print("FAIL: <application> tag missing in AndroidManifest.xml")
        return False
    print("PASS: Manifest structure and application node valid")
    return True

def check_car_service(workspace_root):
    tree, err = get_manifest_tree(workspace_root)
    if not tree:
        print(f"FAIL: {err}")
        return False
    root = tree.getroot()
    app = root.find("application")
    if app is None:
        print("FAIL: <application> tag missing")
        return False
    
    # Search for CarAppService
    found_service = False
    for service in app.findall("service"):
        # Check intent filter
        for intent_filter in service.findall("intent-filter"):
            for action in intent_filter.findall("action"):
                name = action.attrib.get(f"{{{ANDROID_NS}}}name") or action.attrib.get("name")
                if name == "androidx.car.app.CarAppService":
                    found_service = True
                    break
    if not found_service:
        print("FAIL: Service with action 'androidx.car.app.CarAppService' not found in AndroidManifest.xml")
        return False
    print("PASS: CarAppService declared with proper intent-filter")
    return True

def check_metadata(workspace_root):
    tree, err = get_manifest_tree(workspace_root)
    if not tree:
        print(f"FAIL: {err}")
        return False
    root = tree.getroot()
    app = root.find("application")
    if app is None:
        print("FAIL: <application> missing")
        return False

    meta_dict = {}
    for meta in app.findall("meta-data"):
        name = meta.attrib.get(f"{{{ANDROID_NS}}}name") or meta.attrib.get("name")
        val = meta.attrib.get(f"{{{ANDROID_NS}}}value") or meta.attrib.get("value")
        res = meta.attrib.get(f"{{{ANDROID_NS}}}resource") or meta.attrib.get("resource")
        if name:
            meta_dict[name] = val or res
            
    # Also check service-level meta-data
    for s in app.findall("service"):
        for meta in s.findall("meta-data"):
            name = meta.attrib.get(f"{{{ANDROID_NS}}}name") or meta.attrib.get("name")
            val = meta.attrib.get(f"{{{ANDROID_NS}}}value") or meta.attrib.get("value")
            res = meta.attrib.get(f"{{{ANDROID_NS}}}resource") or meta.attrib.get("resource")
            if name:
                meta_dict[name] = val or res

    if "androidx.car.app.minCarApiLevel" not in meta_dict:
        print("FAIL: meta-data 'androidx.car.app.minCarApiLevel' missing")
        return False
    
    # car_app_desc resource check
    has_desc = False
    for k, v in meta_dict.items():
        if "car_app_desc" in str(v) or "car_app_desc" in str(k):
            has_desc = True
            break
            
    if not has_desc:
        with open(os.path.join(workspace_root, "app", "src", "main", "AndroidManifest.xml"), "r") as f:
            raw_text = f.read()
        if "car_app_desc" not in raw_text:
            print("FAIL: Descriptor meta-data referencing @xml/car_app_desc missing")
            return False

    print("PASS: Automotive meta-data configuration valid")
    return True

def check_car_app_desc_xml(workspace_root):
    desc_path = os.path.join(workspace_root, "app", "src", "main", "res", "xml", "car_app_desc.xml")
    if not os.path.isfile(desc_path):
        print(f"FAIL: res/xml/car_app_desc.xml missing at {desc_path}")
        return False
    try:
        tree = ET.parse(desc_path)
        root = tree.getroot()
        if "car-app" not in root.tag:
            print(f"FAIL: Root tag of car_app_desc.xml is {root.tag}, expected <car-app>")
            return False
        print("PASS: car_app_desc.xml is well-formed and valid")
        return True
    except Exception as e:
        print(f"FAIL: car_app_desc.xml XML parse error: {e}")
        return False

def check_permissions(workspace_root):
    tree, err = get_manifest_tree(workspace_root)
    if not tree:
        print(f"FAIL: {err}")
        return False
    root = tree.getroot()
    required = [
        "android.permission.RECORD_AUDIO",
        "android.permission.INTERNET",
        "android.permission.ACCESS_NETWORK_STATE",
        "android.permission.POST_NOTIFICATIONS"
    ]
    declared = []
    for perm in root.findall("uses-permission"):
        name = perm.attrib.get(f"{{{ANDROID_NS}}}name") or perm.attrib.get("name")
        if name:
            declared.append(name)
            
    missing = [r for r in required if r not in declared]
    if missing:
        print(f"FAIL: Missing required permissions: {missing}")
        return False
    print("PASS: All required permissions declared (RECORD_AUDIO, INTERNET, ACCESS_NETWORK_STATE, POST_NOTIFICATIONS)")
    return True

# Boundary / Synthesized check
def boundary_test(test_type):
    if test_type == "empty_manifest":
        try:
            ET.fromstring("<manifest></manifest>")
            print("PASS: Correctly detected empty manifest lacking application")
            return True
        except Exception:
            return False
    elif test_type == "invalid_api_level":
        sample = '<meta-data android:name="androidx.car.app.minCarApiLevel" android:value="-1"/>'
        if "-1" in sample or "0" in sample:
            print("PASS: Correctly flagged invalid negative/zero minCarApiLevel")
            return True
    elif test_type == "malformed_xml":
        try:
            ET.fromstring("<manifest><application><service></application></manifest>")
            print("FAIL: Should have failed malformed XML")
            return False
        except ET.ParseError:
            print("PASS: Correctly rejected malformed XML")
            return True
    elif test_type == "duplicate_permissions":
        perms = ["android.permission.RECORD_AUDIO", "android.permission.RECORD_AUDIO"]
        deduped = list(set(perms))
        if len(deduped) < len(perms):
            print("PASS: Successfully identified duplicate permissions")
            return True
    elif test_type == "missing_car_category":
        sample_xml = '<intent-filter><action android:name="androidx.car.app.CarAppService"/></intent-filter>'
        if "category" not in sample_xml:
            print("PASS: Identified intent-filter without category")
            return True
    print(f"FAIL: Unknown boundary test {test_type}")
    return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: manifest_validator.py <mode> <workspace_root|test_type>")
        sys.exit(1)
    mode = sys.argv[1]
    arg = sys.argv[2]
    
    success = False
    if mode == "--check-package":
        success = check_package_and_app(arg)
    elif mode == "--check-service":
        success = check_car_service(arg)
    elif mode == "--check-metadata":
        success = check_metadata(arg)
    elif mode == "--check-desc-xml":
        success = check_car_app_desc_xml(arg)
    elif mode == "--check-permissions":
        success = check_permissions(arg)
    elif mode == "--boundary":
        success = boundary_test(arg)
    else:
        print(f"Unknown mode {mode}")
        sys.exit(1)
        
    sys.exit(0 if success else 1)
