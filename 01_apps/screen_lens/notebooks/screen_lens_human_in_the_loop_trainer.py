# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "marimo",
#     "numpy",
#     "sqlite3",
# ]
# ///

import marimo

__generated_with = "0.10.0"
app = marimo.App(width="medium")


@app.cell
def __():
    import sys, os
    from pathlib import Path
    import json
    import sqlite3

    workspace = "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo"
    if workspace not in sys.path:
        sys.path.insert(0, workspace)
    sys.path.insert(0, f"{workspace}/01_apps/screen_lens/src")

    from lens_human_evaluator import HumanPerspectiveEvaluator
    from lens_speculative_draft_engine import SmolSpeculativeDraftEngine
    from lens_continuous_training_engine import ScreenLensContinuousTrainingEngine

    print("✅ Screen Lens Human-in-the-Loop Environment Initialized!")
    return (
        HumanPerspectiveEvaluator,
        Path,
        ScreenLensContinuousTrainingEngine,
        SmolSpeculativeDraftEngine,
        json,
        os,
        sqlite3,
        sys,
        workspace,
    )


@app.cell
def __(HumanPerspectiveEvaluator):
    evaluator = HumanPerspectiveEvaluator()
    sample_eval = evaluator.evaluate_screen(
        app_name="Active Workspace / Screen Lens",
        target_type="app",
        ocr_text="Screen Lens Perception Engine active. Clean minimal UI layout, 60-30-10 palette."
    )
    print("📊 Current Screen Human Perception Evaluation:")
    print(f"   ► ELO Rating: {sample_eval['elo_rating']} ({sample_eval['tier']})")
    print(f"   ► UI Visual:  {sample_eval['scores']['ui_visual_polish']}/100")
    print(f"   ► UX Ergonomics: {sample_eval['scores']['ux_heuristics']}/100")
    print(f"   ► Sellability:   {sample_eval['scores']['sellability_commercial']}/100")
    return evaluator, sample_eval


@app.cell
def __(SmolSpeculativeDraftEngine):
    spec_engine = SmolSpeculativeDraftEngine()
    test_raw_context = "CRITICAL: Connection dropped on port 8081. Traceback: connection timeout in network.py. Re-routing to local fallback." * 10
    comp_result = spec_engine.compress_prompt_context(test_raw_context)
    print("⚡ Speculative Draft Pre-Compression Metrics:")
    print(f"   ► Original Size: {comp_result['original_length_chars']} chars")
    print(f"   ► Compressed Size: {comp_result['compressed_length_chars']} chars")
    print(f"   ► Compression Ratio: {comp_result['compression_ratio']}")
    print(f"   ► Estimated Cloud Tokens Saved: {comp_result['estimated_tokens_saved']}")
    return comp_result, spec_engine, test_raw_context


@app.cell
def __(ScreenLensContinuousTrainingEngine):
    training_engine = ScreenLensContinuousTrainingEngine()
    cycle = training_engine.run_training_cycle()
    print("🔄 24/7 Multi-Modal Training Step Status:")
    print(f"   ► Status: {cycle['status']}")
    print(f"   ► Total Samples Indexed: {cycle['total_samples_indexed']}")
    print(f"   ► Current Model Loss: {cycle['current_loss']}")
    print(f"   ► Hardware Accelerator: {cycle['hardware_accelerator']}")
    return cycle, training_engine


if __name__ == "__main__":
    app.run()
