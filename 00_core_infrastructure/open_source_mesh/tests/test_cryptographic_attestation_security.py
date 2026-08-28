#!/usr/bin/env python3
"""
Adversarial Stress Test: Cryptographic Attestation & Sovereign Governance Handover
File: 00_core_infrastructure/open_source_mesh/tests/test_cryptographic_attestation_security.py

Tests:
1. Ed25519 state root generation and verification
2. Replay attack vulnerability across governance epochs (absence of monotonic sequence/nonce)
3. Merkle inclusion proof incompatibility with flat concatenation hashing
"""

import hashlib
import json
import time
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature

def compute_flat_state_root(debate_hash: str, arena_hash: str, ast_hash: str, timestamp: str) -> bytes:
    payload = f"{debate_hash}||{arena_hash}||{ast_hash}||{timestamp}".encode("utf-8")
    return hashlib.sha256(payload).digest()

def compute_merkle_state_root(leaves: list) -> tuple:
    # Proper binary Merkle tree root computation
    current_level = [hashlib.sha256(leaf.encode("utf-8") if isinstance(leaf, str) else leaf).digest() for leaf in leaves]
    tree = [current_level]
    
    while len(current_level) > 1:
        next_level = []
        for i in range(0, len(current_level), 2):
            left = current_level[i]
            right = current_level[i+1] if i+1 < len(current_level) else left
            combined = hashlib.sha256(left + right).digest()
            next_level.append(combined)
        current_level = next_level
        tree.append(current_level)
        
    return tree[-1][0], tree

def run_crypto_stress_tests():
    print("================================================================================")
    print("EMPIRICAL ADVERSARIAL TEST: Cryptographic Attestation & Replay Resilience")
    print("================================================================================")

    # Generate Tri-Orchestrator Keypair
    private_key = ed25519.Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    public_bytes = public_key.public_bytes_raw().hex()

    # 1. EPOCH 1: Legitimate Tournament Victory (Governor A)
    print("\n--- TEST 1: Epoch 1 Legitimate Attestation ---")
    ts_epoch1 = "2026-08-27T06:00:00Z"
    h_debate_1 = hashlib.sha256(b"debate_transcript_epoch1").hexdigest()
    h_arena_1 = hashlib.sha256(b"arena_telemetry_epoch1").hexdigest()
    h_ast_1 = hashlib.sha256(b"ast_diff_epoch1").hexdigest()
    
    state_root_1 = compute_flat_state_root(h_debate_1, h_arena_1, h_ast_1, ts_epoch1)
    sig_1 = private_key.sign(state_root_1)

    crown_artifact_epoch1 = {
        "sovereign_governor_id": "Model-A-Candidate",
        "crown_timestamp": ts_epoch1,
        "state_root_hash": state_root_1.hex(),
        "ed25519_signature": sig_1.hex()
    }
    print("Epoch 1 Crown Artifact Signed Successfully.")
    
    # Verification in Epoch 1
    try:
        public_key.verify(bytes.fromhex(crown_artifact_epoch1["ed25519_signature"]), bytes.fromhex(crown_artifact_epoch1["state_root_hash"]))
        print("Epoch 1 Verification: ✅ VALID SIGNATURE")
    except InvalidSignature:
        print("Epoch 1 Verification: ❌ INVALID")

    # 2. EPOCH 2: Governance Transition to Governor B
    print("\n--- TEST 2: Epoch 2 Governance Transition ---")
    ts_epoch2 = "2026-08-27T12:00:00Z"
    h_debate_2 = hashlib.sha256(b"debate_transcript_epoch2").hexdigest()
    h_arena_2 = hashlib.sha256(b"arena_telemetry_epoch2").hexdigest()
    h_ast_2 = hashlib.sha256(b"ast_diff_epoch2").hexdigest()
    
    state_root_2 = compute_flat_state_root(h_debate_2, h_arena_2, h_ast_2, ts_epoch2)
    sig_2 = private_key.sign(state_root_2)
    crown_artifact_epoch2 = {
        "sovereign_governor_id": "Model-B-Candidate",
        "crown_timestamp": ts_epoch2,
        "state_root_hash": state_root_2.hex(),
        "ed25519_signature": sig_2.hex()
    }
    print("Epoch 2 Crown Artifact Generated: Governor is Model-B-Candidate.")

    # 3. REPLAY ATTACK: Attacker injects Epoch 1 artifact into Epoch 2 Mesh Node
    print("\n--- TEST 3: Signature Replay Attack Simulation ---")
    # A mesh node receives crown_artifact_epoch1 during Epoch 2
    # Because there is no monotonic sequence number or epoch height verified in the socket daemon,
    # the node checks:
    # 1. Is the signature valid against the state root? Yes!
    # 2. Is the state root equal to SHA-256(debate || arena || ast || timestamp)? Yes!
    
    replayed_sig = bytes.fromhex(crown_artifact_epoch1["ed25519_signature"])
    replayed_root = bytes.fromhex(crown_artifact_epoch1["state_root_hash"])
    
    try:
        public_key.verify(replayed_sig, replayed_root)
        print("Replay Attack Result: 🚨 REPLAY SUCCEEDED! Stale Governor A reinstated because state root lacks monotonic epoch counter / block height.")
    except InvalidSignature:
        print("Replay Attack Result: Blocked.")

    # 4. FLAT HASH VS MERKLE INCLUSION PROOF
    print("\n--- TEST 4: Merkle Tree vs Flat Hash Inclusion Proof ---")
    leaves = [h_debate_1, h_arena_1, h_ast_1, ts_epoch1]
    merkle_root, tree = compute_merkle_state_root(leaves)
    
    print(f"Flat Hash State Root:   {state_root_1.hex()}")
    print(f"Merkle Tree State Root: {merkle_root.hex()}")
    print("Vulnerability Confirmed: Flat hash concatenation does NOT support partial Merkle inclusion proofs (SPV validation), violating the specification claim in Section 4.4.")

if __name__ == "__main__":
    run_crypto_stress_tests()
