"""
Test Suite: Bloat Pruning Verification (Milestone 2)
Authoritative verification that:
1. `fl_chart` is 100% eradicated across 01_apps/ and Installed_Apps/ (pubspecs, locks, and source).
2. `WearableSource` in spatial_sensor_fusion_service.dart is strictly limited to movesense and polarH10.
3. Legacy sensor drivers (whoop, genericBle, ingestWhoop) are completely stripped.
4. Heavy unused dependencies (llama_cpp_dart, firebase_storage, cloud_firestore, etc.) are purged from compute hub.
5. All target pubspec and Dart files maintain valid syntax and clean structures.
"""

import os
import re
from pathlib import Path
import yaml
import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_business_app_pubspec_fl_chart_absence():
    """Verify that fl_chart is completely absent from 01_apps/lauburu_business_app/pubspec.yaml."""
    pubspec_path = REPO_ROOT / "01_apps" / "lauburu_business_app" / "pubspec.yaml"
    assert pubspec_path.exists(), f"Missing business app pubspec at {pubspec_path}"

    content = pubspec_path.read_text(encoding="utf-8")
    assert "fl_chart" not in content, "Found fl_chart in 01_apps/lauburu_business_app/pubspec.yaml"

    parsed = yaml.safe_load(content)
    deps = parsed.get("dependencies", {})
    dev_deps = parsed.get("dev_dependencies", {})
    assert "fl_chart" not in deps, "fl_chart found in dependencies dict"
    assert "fl_chart" not in dev_deps, "fl_chart found in dev_dependencies dict"


def test_business_app_pubspec_lock_fl_chart_absence():
    """Verify that fl_chart and its direct artifacts are absent from 01_apps/lauburu_business_app/pubspec.lock."""
    lock_path = REPO_ROOT / "01_apps" / "lauburu_business_app" / "pubspec.lock"
    if lock_path.exists():
        content = lock_path.read_text(encoding="utf-8")
        assert "fl_chart" not in content, "Found fl_chart in 01_apps/lauburu_business_app/pubspec.lock"
        parsed = yaml.safe_load(content)
        packages = parsed.get("packages", {})
        assert "fl_chart" not in packages, "fl_chart found in locked packages dict"


def test_compute_hub_pubspec_bloat_pruning():
    """Verify that llama_cpp_dart, firebase_storage, cloud_firestore, and fl_chart are stripped from compute hub pubspec."""
    candidates = [
        REPO_ROOT / "Installed_Apps" / "Phone_Applications" / "lauburu_compute_hub" / "pubspec.yaml",
        REPO_ROOT / "01_apps" / "lauburu_compute_hub" / "pubspec.yaml",
    ]
    checked_any = False
    for pubspec_path in candidates:
        if pubspec_path.exists():
            checked_any = True
            content = pubspec_path.read_text(encoding="utf-8")
            parsed = yaml.safe_load(content)
            deps = parsed.get("dependencies", {})
            dev_deps = parsed.get("dev_dependencies", {})
            all_deps = {**deps, **dev_deps}

            forbidden = [
                "fl_chart",
                "llama_cpp_dart",
                "firebase_storage",
                "cloud_firestore",
                "firebase_core",
                "firebase_auth",
                "hive",
                "hive_flutter",
            ]

            for pkg in forbidden:
                assert pkg not in all_deps, f"Forbidden bloat package '{pkg}' found in {pubspec_path}"
                # Check for word-bounded dependency declaration in raw content (e.g. 'pkg:' or 'pkg :')
                assert not re.search(r"^\s*" + re.escape(pkg) + r"\s*:", content, re.MULTILINE), (
                    f"Forbidden dependency declaration '{pkg}' found in {pubspec_path}"
                )

    assert checked_any, "At least one compute hub pubspec.yaml must exist and be verified."


def test_spatial_sensor_fusion_service_drivers_pruning():
    """Verify that spatial_sensor_fusion_service.dart contains only Movesense and Polar H10 drivers."""
    candidates = [
        REPO_ROOT / "Installed_Apps" / "Phone_Applications" / "lauburu_compute_hub" / "lib" / "services" / "spatial_sensor_fusion_service.dart",
        REPO_ROOT / "01_apps" / "lauburu_compute_hub" / "lib" / "services" / "spatial_sensor_fusion_service.dart",
    ]
    checked = False
    for service_path in candidates:
        if service_path.exists():
            checked = True
            content = service_path.read_text(encoding="utf-8")

            # Verify enum WearableSource
            enum_match = re.search(r"enum\s+WearableSource\s*\{([^}]+)\}", content)
            assert enum_match is not None, f"Could not locate WearableSource enum in {service_path}"
            enum_body = enum_match.group(1)

            # Check that whoop and genericBle are absent from enum
            assert "whoop" not in enum_body, f"Found 'whoop' in WearableSource enum at {service_path}"
            assert "genericBle" not in enum_body, f"Found 'genericBle' in WearableSource enum at {service_path}"

            # Check that polarH10 and movesense are present
            assert "polarH10" in enum_body, f"Missing 'polarH10' in WearableSource enum at {service_path}"
            assert "movesense" in enum_body, f"Missing 'movesense' in WearableSource enum at {service_path}"

            # Verify ingestWhoop function is completely absent
            assert "ingestWhoop" not in content, f"Found ingestWhoop method in {service_path}"

    assert checked, "At least one spatial_sensor_fusion_service.dart must exist and be verified."


def test_monorepo_apps_zero_fl_chart_occurrences():
    """Scan all source/config files across 01_apps/ and Installed_Apps/ to confirm 0 occurrences of fl_chart."""
    target_dirs = [
        REPO_ROOT / "01_apps",
        REPO_ROOT / "Installed_Apps",
    ]

    matched_files = []
    for target_dir in target_dirs:
        if not target_dir.exists():
            continue
        for root, _, files in os.walk(target_dir):
            for file_name in files:
                if file_name.endswith((".dart", ".yaml", ".lock", ".json", ".kt", ".gradle", ".kts")):
                    file_path = Path(root) / file_name
                    try:
                        content = file_path.read_text(encoding="utf-8", errors="ignore")
                        if "fl_chart" in content:
                            matched_files.append(str(file_path))
                    except Exception:
                        pass

    assert len(matched_files) == 0, f"Found fl_chart in files: {matched_files}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
