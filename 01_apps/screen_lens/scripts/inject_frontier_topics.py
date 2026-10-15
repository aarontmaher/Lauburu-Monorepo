import re

file_path = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/screen_lens/src/lens_continuous_deep_research_daemon.py"
with open(file_path, "r") as f:
    content = f.read()

new_topics = [
    '"Speculative Multimodal Telemetry Pre-Fetch (SMTP) via /screen-lens-sovereign and /deep-research"',
    '"Asynchronous Deep-Tree MoE Fact-Verification (ADTF) via /frontier-swarm-consensus"',
    '"Genetic LoRA Adversarial Distillation (GLAD) via /loop and /ai-debate"',
    '"Autonomous Visual-Actuation Consensus (AVAC) via /screen-lens-sovereign on Android UI"'
]

# Find the end of the RESEARCH_TOPICS list and inject
injection = ",\n    " + ",\n    ".join(new_topics) + "\n]"
content = re.sub(r'\]\s*$', injection, content, flags=re.MULTILINE)

with open(file_path, "w") as f:
    f.write(content)
print("Injected Frontier Swarm topics.")
