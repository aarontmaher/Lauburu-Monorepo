import sys
sys.path.insert(0, "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo")
from importlib.machinery import SourceFileLoader
mod = SourceFileLoader("movesense_dsp_mecg_parser", "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/biometrics/movesense_dsp_mecg_parser.py").load_module()

parser = mod.MovesenseMecgParser()
import zipfile
with zipfile.ZipFile(parser.zip_path, "r") as z:
    with z.open("sample_ecg.mecg") as f:
        f.seek(381)
        samples = []
        for _ in range(5000):
            record = f.read(7)
            ts = int.from_bytes(record[:4], "little", signed=False)
            ecg_val = int.from_bytes(record[4:], "little", signed=True)
            samples.append(ecg_val)

mean_val = sum(samples) / len(samples)
centered = [s - mean_val for s in samples]
derived = [0.0] * len(centered)
for i in range(4, 10):
    derived[i] = (2 * centered[i] + centered[i-1] - centered[i-3] - 2 * centered[i-4]) / 8.0
    print(f"Py derived[{i}] = {derived[i] * derived[i]:.6f}")
