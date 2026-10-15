import zipfile

with zipfile.ZipFile("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/reverse_engineering/movesense/extracted_assets/assets/flutter_assets/assets/sample_ecg.mecg.zip", "r") as z:
    with z.open("sample_ecg.mecg") as f:
        f.seek(381 + 88 * 7)
        rec = f.read(7)
        print("Hex:", rec.hex())
        ts_py = int.from_bytes(rec[:4], "little", signed=False)
        print("Python TS:", ts_py)
