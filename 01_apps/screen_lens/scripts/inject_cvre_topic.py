import re

file_path = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/screen_lens/src/lens_continuous_deep_research_daemon.py"
with open(file_path, "r") as f:
    content = f.read()

new_topics = [
    '"Continuous Visual Reverse Engineering (CVRE): Autonomous VLA cloning of third-party UI/UX paradigms and feature recreation across the mesh via /screen-lens-sovereign, /ai-debate, and /frontier-swarm-consensus"'
]

# Find the end of the RESEARCH_TOPICS list and inject
injection = ",\n    " + ",\n    ".join(new_topics) + "\n]"
content = re.sub(r'\]\s*$', injection, content, flags=re.MULTILINE)

with open(file_path, "w") as f:
    f.write(content)
print("Injected CVRE Swarm topic.")
