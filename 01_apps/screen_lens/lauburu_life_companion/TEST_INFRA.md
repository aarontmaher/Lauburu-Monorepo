# Test Infrastructure Architecture: Lauburu Life Companion E2E Testing Track

## 1. Overview & Testing Philosophy
The Lauburu Life Companion E2E test suite provides rigorous, requirement-driven, opaque-box verification across all four core functional pillars (R1: Silent Boot Persistence, R2: Shopify Customer Authentication, R3: Cloud-Based Cross-Device Session Syncing, R4: Sovereign Local AI E-Commerce Models Integration).

In accordance with Cardinal Rule 1 (**Zero-Mock & Truth Verification**) and Rule 15 (**Sovereign Local AI Hierarchy**), tests do not inject synthetic or fabricated hardware telemetry. All external and local service interactions are evaluated against authentic protocols, live system daemons, POSIX/Darwin kernel state, Android XML schemas, and resilient developer fallback contracts.

---

## 2. 4-Tier Test Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                   4-TIER OPAQUE-BOX TEST ARCHITECTURE                       │
├─────────────────────────────────────────────────────────────────────────────┤
│ TIER 1: FEATURE COVERAGE (>=5 test cases per feature for R1, R2, R3, R4)    │
│ • Verifies primary behaviors, interface contracts, and foundational flows.   │
│ • Total Cases: 22                                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│ TIER 2: BOUNDARY & CORNER CASES (>=5 test cases per feature)                 │
│ • Verifies malformed inputs, timeouts, offline fallbacks, revoked sessions. │
│ • Total Cases: 20                                                           │
├─────────────────────────────────────────────────────────────────────────────┤
│ TIER 3: CROSS-FEATURE COMBINATIONS (Pairwise Interactions)                  │
│ • Verifies state handoffs across subsystem boundaries.                     │
│ • Total Cases: 5                                                            │
├─────────────────────────────────────────────────────────────────────────────┤
│ TIER 4: REAL-WORLD SCENARIOS (End-to-End User Journeys)                     │
│ • Verifies full user lifecycles from device boot to ad copy generation.     │
│ • Total Cases: 3                                                            │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Tier 1: Feature Coverage
- **R1: Silent Boot Persistence (macOS LaunchAgent & Android Receiver)**
  1. `test_macos_launchagent_plist_structure_and_syntax`: Validates plist XML structure, labels, target paths, and keys (`RunAtLoad`, `KeepAlive`, `ProcessType=Background`).
  2. `test_macos_launchagent_silent_execution`: Validates non-forking execution parameters preventing restart loops.
  3. `test_macos_daemon_port_responsiveness`: Verifies that daemon ports (`127.0.0.1:3036`, `127.0.0.1:5555`) respond to socket probes.
  4. `test_android_manifest_boot_permission`: Verifies `RECEIVE_BOOT_COMPLETED` permission declaration in `AndroidManifest.xml`.
  5. `test_android_boot_receiver_intent_filter`: Verifies `.BootReceiver` declaration with `BOOT_COMPLETED` and `QUICKBOOT_POWERON` intent filters.
  6. `test_android_boot_receiver_silent_contract`: Verifies BootReceiver does not invoke foreground `startActivity`.

- **R2: Shopify Customer Authentication**
  1. `test_shopify_graphql_login_endpoint_structure`: Validates GraphQL mutation payload, headers, and endpoint mapping.
  2. `test_shopify_dev_token_authentication`: Validates developer token fast-path (`tok_dev_*`, `dev_aaron`) for zero-mock local testing.
  3. `test_shopify_customer_profile_tier_parsing_pro`: Verifies customer tag `lauburu_pro` maps to `CustomerTier.pro`.
  4. `test_shopify_customer_profile_tier_parsing_elite`: Verifies customer tag `lauburu_elite` maps to `CustomerTier.elite`.
  5. `test_shopify_customer_profile_tier_parsing_free`: Verifies un-tagged customer maps to `CustomerTier.free`.
  6. `test_shopify_token_renewal_mutation`: Verifies `customerAccessTokenRenew` mutation generation and contract.

- **R3: Cloud-Based Cross-Device Syncing & Session Persistence**
  1. `test_session_storage_serialization_and_restore`: Verifies persistent storage serialization of tokens and profiles.
  2. `test_cloud_sync_refreshes_local_customer_tags`: Verifies local session updates when remote tags change.
  3. `test_session_token_expiration_validation`: Verifies near-expiry tokens trigger automatic renewal.
  4. `test_session_clear_on_logout`: Verifies complete wipe of auth tokens and cached profiles upon logout.
  5. `test_concurrent_device_session_reconciliation`: Verifies multi-device session token coexistence and consistency.

- **R4: Local E-Commerce Models Integration**
  1. `test_local_ai_dual_port_routing_hierarchy`: Verifies primary routing to Port 8082 with fallback to Port 8083.
  2. `test_local_ai_live_inference_port_8083`: Verifies live OpenAI-compatible `/v1/chat/completions` query to Port 8083.
  3. `test_canonical_catalog_integrity`: Verifies canonical 18-item catalog schema, prices in AUD, and categories.
  4. `test_ad_copy_generation_prompt_contract`: Verifies copywriting prompt structure and parameters for catalog items.
  5. `test_strict_timeout_boundaries_enforced`: Verifies probe timeout <= 1.5s and inference timeout <= 15s.

---

### Tier 2: Boundary & Corner Cases
- **R1 Boundary & Corner Cases**
  1. `test_plist_file_missing_or_corrupt_handling`: Verifies graceful failure reporting when plist is missing or invalid XML.
  2. `test_launchctl_unloaded_state_handling`: Verifies detection of daemon in unloaded state.
  3. `test_android_manifest_missing_permission_detection`: Verifies test detects when permission is omitted or misspelled.
  4. `test_daemon_port_conflict_detection`: Verifies port binding check handles unavailable ports gracefully.
  5. `test_repeated_launchd_load_idempotency`: Verifies re-loading plist does not cause duplicate processes or crashes.

- **R2 Boundary & Corner Cases**
  1. `test_login_invalid_email_format`: Verifies rejection of malformed emails (missing `@`, empty string).
  2. `test_login_incorrect_password`: Verifies handling of `customerUserErrors` from Shopify API without crashing.
  3. `test_login_empty_or_null_credentials`: Verifies client-side validation rejects empty inputs before network call.
  4. `test_expired_access_token_renew_failure`: Verifies invalid token renewal returns appropriate error.
  5. `test_malformed_dev_token_rejected`: Verifies dev token parser rejects invalid token prefixes.

- **R3 Boundary & Corner Cases**
  1. `test_corrupted_session_storage_recovery`: Verifies app handles corrupted JSON session storage gracefully.
  2. `test_network_offline_during_cloud_sync`: Verifies offline sync attempt preserves cached session rather than crashing.
  3. `test_token_revoked_remotely_triggers_logout`: Verifies 401/unauthenticated response triggers local session wipe.
  4. `test_storage_near_expiration_boundary`: Verifies token with 1 second remaining triggers renewal instead of failing.
  5. `test_missing_required_profile_fields`: Verifies profile deserialization handles null firstName/lastName gracefully.

- **R4 Boundary & Corner Cases**
  1. `test_both_ai_ports_offline_fallback`: Verifies fallback to clean waiting state (`--`) when ports are unavailable.
  2. `test_ai_inference_http_503_recovery`: Verifies handling of Port 8082 HTTP 503 (model offline / Rule 3 RAM protection) by routing to Port 8083.
  3. `test_ai_inference_empty_prompt_rejection`: Verifies validation rejects empty prompt string.
  4. `test_ai_inference_timeout_cutoff`: Verifies client aborts request if server exceeds 15.0s without hanging UI.
  5. `test_canonical_catalog_invalid_item_lookup`: Verifies querying non-existent catalog ID returns null/error cleanly.

---

### Tier 3: Cross-Feature Combinations (Pairwise)
1. `test_boot_persistence_to_auth_session_restore`: Native boot -> Launch app -> Validate persisted session restored without user re-entry.
2. `test_auth_sync_to_ecommerce_tier_entitlement`: Shopify Login with Pro tier -> Sync tags -> Verify Pro tier discount / entitlement applies to canonical catalog.
3. `test_session_restore_to_ai_model_query`: Persisted session -> App start -> Query e-commerce AI model for catalog ad copy.
4. `test_ai_inference_failure_during_active_session`: Logged-in session -> AI port offline -> Verify app remains authenticated and displays clean waiting state (`--`).
5. `test_token_revocation_during_ai_catalog_browsing`: Active catalog browsing -> Session revoked -> Verify UI prompts re-auth while preserving catalog view.

---

### Tier 4: Real-World Scenarios (End-to-End User Journeys)
1. `test_user_journey_cold_boot_login_sync_and_ad_generation`: Complete journey: Device boots -> Background daemon starts -> Flutter app opens -> User logs in via Shopify -> Profile tags sync tier -> User views 18-item catalog -> User queries Local AI for product ad copy -> App terminates and restarts -> Session persists without re-login.
2. `test_user_journey_offline_start_reconnect_and_sync`: Complete journey: User opens app with network offline -> Cached session loaded -> Offline badge displayed -> Network restored -> Background cloud sync reconciles profile tags -> E-commerce AI queried with fallback.
3. `test_user_journey_cross_device_tier_upgrade`: Complete journey: User logs in on Device A as Free user -> Tier upgraded in Shopify -> User opens Device B -> Device B syncs updated tier (`lauburu_pro`) -> E-commerce hub displays Pro badge and unlocked features.

---

## 3. Test Matrix & Acceptance Criteria Mapping

| Deliverable | Acceptance Criteria | Covered In | Test Cases |
| :--- | :--- | :--- | :--- |
| **R1: Boot Persistence** | macOS plist valid, installed, and loaded | Tier 1, Tier 2, Tier 3, Tier 4 | 6 (T1) + 5 (T2) = 11 cases |
| **R1: Boot Persistence** | Android `RECEIVE_BOOT_COMPLETED` permission & receiver | Tier 1, Tier 2, Tier 4 | 3 (T1) + 2 (T2) = 5 cases |
| **R2: Shopify Auth** | Login captures and stores Auth Token | Tier 1, Tier 2, Tier 3, Tier 4 | 6 (T1) + 5 (T2) = 11 cases |
| **R3: Cross-Device Sync** | Session survives app restarts; syncs cloud tags | Tier 1, Tier 2, Tier 3, Tier 4 | 5 (T1) + 5 (T2) = 10 cases |
| **R4: E-Commerce AI** | Connects to & queries models without timeouts | Tier 1, Tier 2, Tier 3, Tier 4 | 5 (T1) + 5 (T2) = 10 cases |
| **Cross-Feature** | Pairwise subsystem interactions | Tier 3 | 5 cases |
| **User Journeys** | End-to-end multi-step realistic lifecycles | Tier 4 | 3 cases |
| **Total** | **All Acceptance Criteria Fully Covered** | **Tiers 1–4** | **50 Test Cases** |

---

## 4. Execution Commands

### Executing the Entire E2E Test Suite
```bash
# Using Shell script runner
bash test/e2e/run_all_e2e_tests.sh

# Or directly via Python runner
python3 test/e2e/run_all_e2e_tests.py
```

### Running Specific Tiers
```bash
# Run only Tier 1 Feature Coverage
python3 test/e2e/run_all_e2e_tests.py --tier 1

# Run only Tier 2 Boundary & Corner Cases
python3 test/e2e/run_all_e2e_tests.py --tier 2

# Run only Tier 3 Cross-Feature Combinations
python3 test/e2e/run_all_e2e_tests.py --tier 3

# Run only Tier 4 Real-World Scenarios
python3 test/e2e/run_all_e2e_tests.py --tier 4
```

### Additional Flags
- `--verbose`: Output detailed logs and tracebacks for every test.
- `--report-json <path>`: Emit machine-readable JSON execution summary.
- `--fail-fast`: Stop immediately on the first test failure.

---

## 5. Directory Layout & Artifacts
```
test/e2e/
├── e2e_harness.py                     # Shared opaque-box testing harness & contracts
├── test_tier1_feature_coverage.py     # Tier 1 (22 tests)
├── test_tier2_boundary_corner.py      # Tier 2 (20 tests)
├── test_tier3_cross_feature.py        # Tier 3 (5 tests)
├── test_tier4_real_world_scenarios.py # Tier 4 (3 tests)
├── run_all_e2e_tests.py               # Master Python test runner
└── run_all_e2e_tests.sh               # Executable shell runner wrapper
```
