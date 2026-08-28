---
title: "09_app_store_and_release — Production Packaging, App Store Delivery & OTA"
updated: "2026-08-27"
tags: [app_store, google_play, apple_app_store, release, apk_signing, ota, spec-09]
---

# 09_app_store_and_release — Production Packaging, App Store Delivery & OTA

## 📋 Scope & Release Pipeline
Governs production build verification, mobile app store packaging, cryptographic signing, memory leak elimination, and zero-crash release workflows.

## 🚀 Release Subsystems
1. **Android Google Play Release Pipeline:**
   - Automated AAB/APK compilation, keystore cryptographic signing, ProGuard/R8 obfuscation, and Play Console track deployment.
2. **Apple App Store & TestFlight Delivery:**
   - iOS Xcode build automation, Provisioning Profile management, and TestFlight beta distribution.
3. **Production Stability & Memory Leak Auditing:**
   - Automated memory profiling using Chrome DevTools MCP and Memlab to enforce 0 memory leaks prior to production signoff.
4. **Over-The-Air (OTA) Dynamic Updates:**
   - Incremental asset manifests and release tag management via GitHub Releases (`gh release`).

## 🤖 Assigned Subsystem Specialist AI
- **Specialist Agent:** `spec-09-app-store-production`
- **Focus Areas:** APK/AAB signing, iOS archive generation, memory leak auditing, App Store compliance review.

## 🔗 Knowledge Graph Connections
- **Master Index:** [[Index]]
- **Deep Architecture:** [[LAUBURU_MONOREPO_DEEP_ARCHITECTURE_INDEX]]
- **Connected Modules:** [[01_apps]], [[11_security_and_governance]]
