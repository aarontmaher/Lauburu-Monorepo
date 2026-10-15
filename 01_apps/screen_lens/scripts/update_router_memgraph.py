import re

file_path = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/screen_lens/src/lens_omniscient_router.py"
with open(file_path, "r") as f:
    content = f.read()

# Add memgraph_cypher_executor
if "memgraph_cypher_executor" not in content:
    content = content.replace('"invoke_subagent": "genetic_swarm_router"', '"invoke_subagent": "genetic_swarm_router",\n            "query_graph": "memgraph_cypher_executor"')

with open(file_path, "w") as f:
    f.write(content)

print("Updated router to support query_graph -> memgraph_cypher_executor")
