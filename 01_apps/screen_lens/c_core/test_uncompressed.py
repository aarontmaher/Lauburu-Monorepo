file_path = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/reverse_engineering/movesense/extracted_assets/assets/flutter_assets/assets/sample_ecg.mecg"
with open(file_path, "rb") as f:
    magic = f.read(4)
    raw_header = f.read(2048)
    start_json = raw_header.find(b"{\"path\"")
    end_json = raw_header.find(b"}}") + 2
    print(f"magic: {magic}")
    print(f"end_json relative to 4: {end_json}")
    
    # Let's print exactly what is at 381
    f.seek(381)
    for _ in range(5):
        rec = f.read(7)
        ts = int.from_bytes(rec[:4], "little", signed=False)
        amp = int.from_bytes(rec[4:], "little", signed=True)
        print(f"At 381: TS: {ts}, Amp: {amp}")
        
    # Let's print what is at 385
    f.seek(385)
    for _ in range(5):
        rec = f.read(7)
        ts = int.from_bytes(rec[:4], "little", signed=False)
        amp = int.from_bytes(rec[4:], "little", signed=True)
        print(f"At 385: TS: {ts}, Amp: {amp}")

