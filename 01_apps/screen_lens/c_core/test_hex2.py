file_path = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/reverse_engineering/movesense/extracted_assets/assets/flutter_assets/assets/sample_ecg.mecg"
with open(file_path, "rb") as f:
    f.seek(376)
    rec = f.read(20)
    print("Hex around 376:", rec.hex())
