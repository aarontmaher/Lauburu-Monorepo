#!/usr/bin/env python3
"""
Physical Zero-Mock Benchmark: Baseline SQLite vs Tuned WITHOUT ROWID SQLite
"""
import os
import time
import sqlite3
import tempfile

unique_edges = set()
for src in range(2500):
    for offset in [1, 7, 13, 29]:
        tgt = (src * 3 + offset) % 2500
        if src != tgt:
            unique_edges.add((src, tgt))
edges = list(unique_edges)[:10000]

# 1. Baseline SQLite
with tempfile.NamedTemporaryFile(suffix="_base.db", delete=False) as f:
    base_path = f.name
conn = sqlite3.connect(base_path)
cur = conn.cursor()
cur.execute("CREATE TABLE edges (src INT, tgt INT)")
cur.executemany("INSERT INTO edges VALUES (?, ?)", edges)
cur.execute("CREATE INDEX idx_src ON edges(src)")
cur.execute("CREATE INDEX idx_tgt ON edges(tgt)")
conn.commit()

t0 = time.perf_counter()
for _ in range(50):
    cur.execute("""
        WITH RECURSIVE traverse(node, depth) AS (
            SELECT tgt, 1 FROM edges WHERE src = 0
            UNION
            SELECT e.tgt, t.depth + 1
            FROM edges e JOIN traverse t ON e.src = t.node
            WHERE t.depth < 3
        )
        SELECT count(DISTINCT node) FROM traverse;
    """)
    res_base = cur.fetchone()[0]
t_base = (time.perf_counter() - t0) / 50 * 1000
size_base = os.path.getsize(base_path) / 1024
conn.close()
os.remove(base_path)

# 2. Tuned SQLite (WITHOUT ROWID + WAL + mmap + temp_store=MEMORY)
with tempfile.NamedTemporaryFile(suffix="_tuned.db", delete=False) as f:
    tuned_path = f.name
conn = sqlite3.connect(tuned_path)
cur = conn.cursor()
cur.execute("PRAGMA journal_mode = WAL")
cur.execute("PRAGMA synchronous = NORMAL")
cur.execute("PRAGMA temp_store = MEMORY")
cur.execute("PRAGMA mmap_size = 268435456") # 256MB mmap
cur.execute("""
    CREATE TABLE edges (
        src INT NOT NULL,
        tgt INT NOT NULL,
        PRIMARY KEY (src, tgt)
    ) WITHOUT ROWID;
""")
cur.execute("CREATE INDEX idx_rev ON edges(tgt, src);")
cur.executemany("INSERT INTO edges VALUES (?, ?)", edges)
conn.commit()

t0 = time.perf_counter()
for _ in range(50):
    cur.execute("""
        WITH RECURSIVE traverse(node, depth) AS (
            SELECT tgt, 1 FROM edges WHERE src = 0
            UNION
            SELECT e.tgt, t.depth + 1
            FROM edges e JOIN traverse t ON e.src = t.node
            WHERE t.depth < 3
        )
        SELECT count(DISTINCT node) FROM traverse;
    """)
    res_tuned = cur.fetchone()[0]
t_tuned = (time.perf_counter() - t0) / 50 * 1000
size_tuned = os.path.getsize(tuned_path) / 1024
conn.close()
os.remove(tuned_path)

print("================================================================================")
print(f"{'Configuration':<30} | {'3-Hop Latency (ms)':<20} | {'Disk Size (KB)':<15} | {'Bytes/Edge'}")
print("-" * 80)
print(f"{'Baseline SQLite':<30} | {t_base:<20.3f} | {size_base:<15.1f} | {size_base*1024/len(edges):.2f}")
print(f"{'Tuned (WITHOUT ROWID + mmap)':<30} | {t_tuned:<20.3f} | {size_tuned:<15.1f} | {size_tuned*1024/len(edges):.2f}")
print("================================================================================")
print(f"Speedup: {t_base/t_tuned:.2f}x faster | Size Reduction: {(1 - size_tuned/size_base)*100:.1f}% smaller")
