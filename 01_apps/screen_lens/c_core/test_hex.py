file_path = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/reverse_engineering/movesense/extracted_assets/assets/flutter_assets/assets/sample_ecg.mecg"
with open(file_path, "rb") as f:
    f.seek(381)
    for i in range(55):
        rec = f.read(7)
        ts = int.from_bytes(rec[:4], "little", signed=False)
        amp = int.from_bytes(rec[4:], "little", signed=True)
        print(f"Index {i}: Hex {rec.hex()} -> TS: {ts}, Amp: {amp}")
