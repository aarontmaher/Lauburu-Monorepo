#!/usr/bin/env python3
import json
import os
import sys

def test_jsonl_file(path, expected_min_records=1):
    print(f"Testing {path} ...")
    assert os.path.exists(path), f"File not found: {path}"
    assert os.path.getsize(path) > 0, f"File is empty: {path}"
    
    records = []
    with open(path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line_str = line.strip()
            if not line_str:
                continue
            try:
                data = json.loads(line_str)
            except Exception as e:
                print(f"SYNTAX ERROR on line {line_num} in {path}: {e}")
                sys.exit(1)
            
            # Schema assertions
            required_keys = ["instruction", "input", "output", "metadata"]
            for k in required_keys:
                assert k in data, f"Missing required key '{k}' on line {line_num} in {path}"
                assert data[k] is not None, f"Key '{k}' is None on line {line_num} in {path}"
            
            assert isinstance(data["instruction"], str) and len(data["instruction"]) >= 10, f"Invalid instruction length on line {line_num}"
            assert isinstance(data["input"], str) and len(data["input"]) >= 5, f"Invalid input length on line {line_num}"
            assert isinstance(data["output"], str) and len(data["output"]) >= 20, f"Invalid output length on line {line_num}"
            assert isinstance(data["metadata"], dict), f"Metadata must be a dictionary on line {line_num}"
            
            records.append(data)
    
    assert len(records) >= expected_min_records, f"Record count {len(records)} is less than expected minimum {expected_min_records}"
    print(f"PASSED: {len(records)} records successfully validated in {path}\n")
    return records

if __name__ == "__main__":
    f1 = "/Users/aaron/DFS_UNIFIED/lora_datasets/truth_audit_shizuku_debate.jsonl"
    f2 = "/Users/aaron/DFS_UNIFIED/lora_datasets/truth_audit_pixel_diagnostics.jsonl"
    
    r1 = test_jsonl_file(f1, expected_min_records=5)
    r2 = test_jsonl_file(f2, expected_min_records=5)
    
    # Also verify mirrors
    m1 = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/lora_datasets/truth_audit_shizuku_debate.jsonl"
    m2 = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/04_data_and_memory/lora_datasets/truth_audit_pixel_diagnostics.jsonl"
    
    rm1 = test_jsonl_file(m1, expected_min_records=5)
    rm2 = test_jsonl_file(m2, expected_min_records=5)
    
    print("==================================================")
    print("ALL 4 DATASET TARGETS CERTIFIED 100% VALID JSONL!")
    print(f"Total Shizuku Debate instruction pairs: {len(r1)}")
    print(f"Total Pixel Diagnostics instruction pairs: {len(r2)}")
    print("==================================================")
