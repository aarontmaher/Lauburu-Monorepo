import sys

file_path = "/Volumes/Lauburu-Monorepo/01_apps/screen_lens/screen_life_companion/screen_life_companion.py"
with open(file_path, "r") as f:
    content = f.read()

# Fix broken strings with literal newlines
fixed_content = content.replace("background tasks). \n", 'background tasks). \\n" \\\n                    "')
fixed_content = fixed_content.replace('AI swarm.\n', 'AI swarm.\\n" \\\n                    ')
fixed_content = fixed_content.replace('Data:\n', 'Data:\\n" \\\n                    f"')

with open(file_path, "w") as f:
    f.write(fixed_content)
