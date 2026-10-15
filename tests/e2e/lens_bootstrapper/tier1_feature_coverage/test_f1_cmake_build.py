#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tier 1: Feature F1 - CMake Build Configuration E2E Test Suite.
Validates zero-dependency CMakeLists.txt configuration, compiler flags (-O2, -fno-rtti, -fno-exceptions),
target generation, out-of-source builds, and binary artifacts.
"""

import os
import sys
import shutil
import subprocess
import unittest
from pathlib import Path

# Setup paths via test_helpers
SUITE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SUITE_ROOT))
from test_helpers import PROJECT_ROOT, BOOTSTRAPPER_DIR

CMAKELISTS_PATH = BOOTSTRAPPER_DIR / "CMakeLists.txt"


class TestF1CMakeBuildConfiguration(unittest.TestCase):
    """E2E Verification for Feature F1: CMake Build Configuration."""

    def setUp(self):
        self.cmake_path = CMAKELISTS_PATH
        self.build_dir = BOOTSTRAPPER_DIR / "build"

    def test_f1_01_cmake_file_exists(self):
        """F1.1: Verify CMakeLists.txt exists in lens_bootstrapper directory."""
        self.assertTrue(
            self.cmake_path.exists(),
            f"CMakeLists.txt missing at {self.cmake_path}"
        )
        content = self.cmake_path.read_text(encoding="utf-8")
        self.assertGreater(len(content), 100, "CMakeLists.txt is unexpectedly empty")

    def test_f1_02_cmake_minimum_version_and_standard(self):
        """F1.2: Verify C++17 standard, cmake_minimum_required, and project declaration."""
        content = self.cmake_path.read_text(encoding="utf-8")
        self.assertIn("cmake_minimum_required", content.lower())
        self.assertIn("project", content.lower())
        has_cxx17 = ("17" in content and "CXX_STANDARD" in content) or "-std=c++17" in content
        self.assertTrue(has_cxx17, "CMakeLists.txt must mandate C++17 standard")

    def test_f1_03_compiler_flags_strict_specification(self):
        """F1.3: Verify -O2, -fno-rtti, and -fno-exceptions flags are configured."""
        content = self.cmake_path.read_text(encoding="utf-8")
        self.assertIn("-O2", content, "CMakeLists.txt must specify -O2 optimization")
        self.assertIn("-fno-rtti", content, "CMakeLists.txt must disable RTTI (-fno-rtti)")
        self.assertIn("-fno-exceptions", content, "CMakeLists.txt must disable C++ exceptions (-fno-exceptions)")

    def test_f1_04_target_declarations(self):
        """F1.4: Verify static library lens_telemetry, lens_bootstrapper, and lens_bootstrapper_ctl."""
        content = self.cmake_path.read_text(encoding="utf-8")
        self.assertIn("lens_telemetry", content, "Target lens_telemetry must be declared")
        self.assertIn("lens_bootstrapper", content, "Target lens_bootstrapper must be declared")
        self.assertIn("lens_bootstrapper_ctl", content, "Target lens_bootstrapper_ctl must be declared")

    def test_f1_05_cmake_configure_and_build_execution(self):
        """F1.5: Execute live CMake configuration and build, verifying Exit Code 0."""
        self.build_dir.mkdir(parents=True, exist_ok=True)
        
        # Configure step
        config_cmd = ["cmake", "-B", str(self.build_dir), "-S", str(BOOTSTRAPPER_DIR), "-DCMAKE_BUILD_TYPE=Release"]
        config_proc = subprocess.run(
            config_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=60
        )
        self.assertEqual(
            config_proc.returncode, 0,
            f"CMake configuration failed: {config_proc.stderr}\n{config_proc.stdout}"
        )

        # Build step
        build_cmd = ["cmake", "--build", str(self.build_dir), "-j", "4"]
        build_proc = subprocess.run(
            build_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=120
        )
        self.assertEqual(
            build_proc.returncode, 0,
            f"CMake build failed: {build_proc.stderr}\n{build_proc.stdout}"
        )

    def test_f1_06_build_artifacts_binary_validation(self):
        """F1.6: Verify produced binaries exist, are executable, and have valid headers."""
        daemon_bin = self.build_dir / "lens_bootstrapper"
        ctl_bin = self.build_dir / "lens_bootstrapper_ctl"

        self.assertTrue(daemon_bin.exists(), f"Daemon binary missing at {daemon_bin}")
        self.assertTrue(os.access(str(daemon_bin), os.X_OK), "Daemon binary is not executable")

        self.assertTrue(ctl_bin.exists(), f"Control CLI binary missing at {ctl_bin}")
        self.assertTrue(os.access(str(ctl_bin), os.X_OK), "Control CLI binary is not executable")

        if sys.platform == "darwin":
            file_proc = subprocess.run(["file", str(daemon_bin)], stdout=subprocess.PIPE, text=True)
            self.assertIn("Mach-O", file_proc.stdout, "Compiled daemon must be a valid Mach-O binary")


if __name__ == "__main__":
    unittest.main()
