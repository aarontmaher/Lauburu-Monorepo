import os
import sqlite3
import tempfile

num_nodes = 2500
unique_edges = set()
for src in range(num_nodes):
    for offset in [1, 7, 13, 29]:
        tgt = (src * 3 + offset) % num_nodes
        if src != tgt:
            unique_edges.add((src, tgt))
edges = list(unique_edges)[:10000]

with tempfile.NamedTemporaryFile(suffix="_chk.db", delete=False) as f:
    db_path = f.name

conn = sqlite3.connect(db_path)
cur = conn.cursor()
cur.execute("PRAGMA journal_mode = WAL")
cur.execute("PRAGMA synchronous = NORMAL")
cur.execute("PRAGMA temp_store = MEMORY")
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

# Checkpoint WAL back into the main database file
cur.execute("PRAGMA wal_checkpoint(TRUNCATE);")
conn.commit()
conn.close()

db_size = os.path.getsize(db_path) / 1024
wal_path = db_path + "-wal"
wal_size = os.path.getsize(wal_path) / 1024 if os.path.exists(wal_path) else 0.0

print(f"Verified Checkpointed DB Size: {db_size:.2f} KB")
print(f"Verified WAL Size: {wal_size:.2f} KB")
print(f"Total Disk Footprint: {db_size + wal_size:.2f} KB")
print(f"Physical Bytes Per Edge: {(db_size + wal_size) * 1024 / len(edges):.2f} bytes/edge")
os.remove(db_path)
if os.path.exists(wal_path):
    os.remove(wal_path)
