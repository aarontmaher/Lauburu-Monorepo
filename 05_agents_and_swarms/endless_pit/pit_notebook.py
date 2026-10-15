import marimo

__generated_with = "0.8.0"
app = marimo.App(width="full")


@app.cell
def __():
    import marimo as mo
    import json
    import pandas as pd
    import altair as alt
    from pathlib import Path
    return alt, json, mo, pd, Path


@app.cell
def __(Path, json, pd):
    LORA_PATH = Path("/Users/aaron/DFS_UNIFIED/lora_datasets/continuous_lora_dataset.jsonl")
    
    data = []
    if LORA_PATH.exists():
        with open(LORA_PATH, "r") as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    if "endless_pit" in rec.get("domain", ""):
                        data.append(rec)
                except Exception:
                    pass
    
    df = pd.DataFrame(data)
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return LORA_PATH, data, df


@app.cell
def __(df, pd):
    # Calculate ELO drift over time
    std_elo = 1200
    abl_elo = 1200
    
    elo_history = []
    for idx, row in df.iterrows():
        winner = row.get("winner")
        if winner == "STANDARD":
            std_elo += 15
            abl_elo -= 10
        elif winner == "ABLITERATED":
            abl_elo += 15
            std_elo -= 10
            
        elo_history.append({
            "timestamp": row["timestamp"],
            "Standard (Qwen 3.8 Max)": std_elo,
            "Abliterated (Qwen 27B)": abl_elo
        })
        
    elo_df = pd.DataFrame(elo_history)
    if not elo_df.empty:
        elo_long = elo_df.melt(id_vars=["timestamp"], value_vars=["Standard (Qwen 3.8 Max)", "Abliterated (Qwen 27B)"], var_name="Agent", value_name="ELO")
    else:
        elo_long = pd.DataFrame()
    return abl_elo, elo_df, elo_history, elo_long, idx, row, std_elo, winner


@app.cell
def __(alt, elo_long, mo):
    if not elo_long.empty:
        chart = alt.Chart(elo_long).mark_line(point=True).encode(
            x='timestamp:T',
            y=alt.Y('ELO:Q', scale=alt.Scale(zero=False)),
            color=alt.Color('Agent:N', scale=alt.Scale(domain=["Standard (Qwen 3.8 Max)", "Abliterated (Qwen 27B)"], range=["cyan", "red"]))
        ).properties(
            title="Adversarial ELO Drift Over Time",
            width=800,
            height=400
        ).interactive()
        mo.ui.altair_chart(chart)
    else:
        mo.md("No battle data found yet.")
    return chart,


@app.cell
def __(df, pd):
    # Extract TinyML Footprint sizes
    sizes = []
    for idx, row in df.iterrows():
        # Standard
        std_res = row.get("standard", {}).get("result", {})
        if "compiled_size_kb" in std_res:
            sizes.append({
                "Agent": "Standard",
                "Domain": std_res.get("domain", "Unknown"),
                "Size (KB)": std_res["compiled_size_kb"]
            })
            
        # Abliterated
        abl_res = row.get("abliterated", {}).get("result", {})
        if "compiled_size_kb" in abl_res:
            sizes.append({
                "Agent": "Abliterated",
                "Domain": abl_res.get("domain", "Unknown"),
                "Size (KB)": abl_res["compiled_size_kb"]
            })
            
    size_df = pd.DataFrame(sizes)
    return abl_res, idx, row, size_df, sizes, std_res


@app.cell
def __(alt, mo, size_df):
    if not size_df.empty:
        size_chart = alt.Chart(size_df).mark_boxplot().encode(
            x='Agent:N',
            y='Size (KB):Q',
            color='Agent:N'
        ).properties(
            title="TinyML Compilation Footprint Distribution",
            width=400,
            height=400
        )
        mo.ui.altair_chart(size_chart)
    else:
        mo.md("No Edge TinyML data found yet.")
    return size_chart,


if __name__ == "__main__":
    app.run()
