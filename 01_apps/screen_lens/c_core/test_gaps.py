import zipfile
import sys

with zipfile.ZipFile("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/reverse_engineering/movesense/extracted_assets/assets/flutter_assets/assets/sample_ecg.mecg.zip", "r") as z:
    with z.open("sample_ecg.mecg") as f:
        f.seek(381)
        prev = 0
        for i in range(5000):
            record = f.read(7)
            if not record: break
            ts = int.from_bytes(record[:4], "little", signed=False)
            if i > 0 and ts < prev:
                print(f"Timestamp went backwards at index {i}: prev={prev}, curr={ts}")
            elif i > 0 and ts - prev > 1000:
                print(f"Huge gap at index {i}: prev={prev}, curr={ts}, gap={ts - prev}")
            prev = ts
