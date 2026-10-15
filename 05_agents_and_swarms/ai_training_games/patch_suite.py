import sys

file_path = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/05_agents_and_swarms/ai_training_games/sovereign_ai_training_games_suite.py"
with open(file_path, "r") as f:
    content = f.read()

# 1. Update the docstring
content = content.replace(
    "4. Track 4: Terminal to Production & Commercial Sellability Game\n5. Meta-Evolutionary Analysis",
    "4. Track 4: Terminal to Production & Commercial Sellability Game\n5. Track 5: Capture The Flag (CTF) CyberGym Arena\n6. Meta-Evolutionary Analysis"
)

# 2. Add the import
if "from track5_capture_the_flag_cybergym import run_track5_evaluation" not in content:
    content = content.replace(
        "from track4_terminal_to_production_commerce import run_track4_evaluation",
        "from track4_terminal_to_production_commerce import run_track4_evaluation\nfrom track5_capture_the_flag_cybergym import run_track5_evaluation"
    )

# 3. Add to the run_full_tournament function
if "local_track5_results = run_track5_evaluation(is_cloud_agent=False)" not in content:
    # Find the place where track 4 results are printed and append track 5
    track4_local = "local_track4_results = run_track4_evaluation(is_cloud_agent=False)"
    track4_cloud = "cloud_track4_results = run_track4_evaluation(is_cloud_agent=True)"
    
    content = content.replace(track4_local, track4_local + "\n    local_track5_results = run_track5_evaluation(is_cloud_agent=False)")
    content = content.replace(track4_cloud, track4_cloud + "\n    cloud_track5_results = run_track5_evaluation(is_cloud_agent=True)")

    # Update the results array being collected
    content = content.replace(
        "local_track4_results\n        ],",
        "local_track4_results,\n            local_track5_results\n        ],"
    )
    content = content.replace(
        "cloud_track4_results\n        ]",
        "cloud_track4_results,\n            cloud_track5_results\n        ]"
    )

with open(file_path, "w") as f:
    f.write(content)

print("Patched successfully!")
