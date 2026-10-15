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
            if not record: break
            ts = int.from_bytes(record[:4], "little", signed=False)
            ecg_val = int.from_bytes(record[4:], "little", signed=True)
            samples.append(ecg_val)

mean_val = sum(samples) / len(samples)
centered = [s - mean_val for s in samples]
derived = [0.0] * len(centered)
for i in range(4, len(centered)):
    derived[i] = (2 * centered[i] + centered[i-1] - centered[i-3] - 2 * centered[i-4]) / 8.0

squared = [d * d for d in derived]
window_size = 30
integrated = [0.0] * len(squared)
running_sum = sum(squared[:window_size])
for i in range(len(squared)):
    if i >= window_size:
        running_sum += squared[i] - squared[i - window_size]
    integrated[i] = running_sum / window_size

threshold = sum(integrated) / len(integrated) * 2.5
print(f"Py threshold: {threshold}")
peak_count = 0
for i in range(1, len(integrated) - 1):
    if integrated[i] > threshold and integrated[i] > integrated[i-1] and integrated[i] >= integrated[i+1]:
        if peak_count < 5:
            print(f"Peak candidate at {i}, val {integrated[i]}")
        peak_count += 1
print(f"Total peak candidates: {peak_count}")
