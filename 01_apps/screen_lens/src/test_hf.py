from lens_huggingface_hub_manager import LensHuggingFaceManager
manager = LensHuggingFaceManager()
print(manager.list_benchmark_datasets())
print(manager.get_dataset_leaderboard("SWE-bench/SWE-bench_Verified", 3))
