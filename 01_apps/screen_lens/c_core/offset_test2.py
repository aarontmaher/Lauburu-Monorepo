import zipfile
import struct

with zipfile.ZipFile("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/reverse_engineering/movesense/extracted_assets/assets/flutter_assets/assets/sample_ecg.mecg.zip", "r") as z:
    with z.open("sample_ecg.mecg") as f:
        f.seek(385)
        print("Python offset:")
        for _ in range(5):
            rec = f.read(7)
            ts = int.from_bytes(rec[:4], "little", signed=False)
            amp = int.from_bytes(rec[4:], "little", signed=True)
            print(f"TS: {ts}, Amp: {amp}")

        f.seek(383)
        print("\nC offset:")
        for _ in range(5):
            rec = f.read(7)
            ts = int.from_bytes(rec[:4], "little", signed=False)
            amp = int.from_bytes(rec[4:], "little", signed=True)
            print(f"TS: {ts}, Amp: {amp}")

        f.seek(381)
        print("\nOriginal C offset (381):")
        for _ in range(5):
            rec = f.read(7)
            ts = int.from_bytes(rec[:4], "little", signed=False)
            amp = int.from_bytes(rec[4:], "little", signed=True)
            print(f"TS: {ts}, Amp: {amp}")
