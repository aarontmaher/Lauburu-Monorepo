file_path = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/reverse_engineering/movesense/extracted_assets/assets/flutter_assets/assets/sample_ecg.mecg"
with open(file_path, "rb") as f:
    f.seek(710)
    rec = f.read(40)
    print("Hex around 710:", rec.hex())
