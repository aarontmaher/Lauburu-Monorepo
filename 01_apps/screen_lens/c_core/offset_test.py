import zipfile, json

with zipfile.ZipFile("/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/reverse_engineering/movesense/extracted_assets/assets/flutter_assets/assets/sample_ecg.mecg.zip", "r") as z:
    with z.open("sample_ecg.mecg") as f:
        magic = f.read(4)
        raw_header = f.read(2048)
        start_json = raw_header.find(b"{\"path\"")
        end_json = raw_header.find(b"}}") + 2
        print(f"magic: {magic}")
        print(f"end_json relative to 4: {end_json}")
        abs_offset = 4 + end_json + 5
        print(f"python seek absolute: {abs_offset}")
        print(f"C seek absolute (4+end_json+3): {4 + end_json + 3}")
        
        # let's see what is at the python offset
        f.seek(abs_offset)
        print("Python offset first record:", f.read(7).hex())

        # let's see what is at the C offset
        f.seek(4 + end_json + 3)
        print("C offset first record:", f.read(7).hex())
