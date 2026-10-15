file_path = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/screen_lens/src/lens_omniscient_router.py"
with open(file_path, "r") as f:
    content = f.read()

if "mmap_csr_graph_executor" not in content:
    content = content.replace(
        '"query_graph": "ephemeral_graph_engine"',
        '"query_graph": "mmap_csr_graph_executor",\n            "query_graph_sql": "sqlite_tuned_executor"'
    )

with open(file_path, "w") as f:
    f.write(content)

print("Updated router to support mmap_csr_graph_executor and sqlite_tuned_executor")
