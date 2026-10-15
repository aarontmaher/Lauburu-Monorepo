import zipfile

with zipfile.ZipFile("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/reverse_engineering/movesense/extracted_assets/assets/flutter_assets/assets/sample_ecg.mecg.zip", "r") as z:
    with z.open("sample_ecg.mecg") as f:
        f.seek(381)
        prev = -1
        for i in range(100):
            rec = f.read(7)
            ts = int.from_bytes(rec[:4], "little", signed=False)
            amp = int.from_bytes(rec[4:], "little", signed=True)
            if ts < prev:
                print(f"Non-monotonic at {i}: TS={ts}, prev={prev}")
            prev = ts
