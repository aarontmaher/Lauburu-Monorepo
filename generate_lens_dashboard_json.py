import json

with open('/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/notebooks/09_sovereign_screen_lens_dashboard.ipynb', 'r') as f:
    nb = json.load(f)

# Insert OCR telemetry cell before master_tab assembly
cells = nb['cells']

ocr_cell = {
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "# ==============================================================================\n",
        "# OCR Capture Engine Telemetry (Port 3035)\n",
        "# ==============================================================================\n",
        "out_ocr = widgets.Output()\n",
        "with out_ocr:\n",
        "    display(HTML(\"<h3 style='color: #f43f5e;'>OCR Engine Status (Port 3035)</h3>\"))\n",
        "    try:\n",
        "        response = requests.get('http://127.0.0.1:3035/api/status', timeout=2)\n",
        "        import json\n",
        "        display(HTML(f\"<pre style='color: #fbbf24; font-size: 14px;'>{json.dumps(response.json(), indent=2)}</pre>\"))\n",
        "    except Exception as e:\n",
        "        display(HTML(f\"<p style='color: #ef4444;'>OCR Engine unreachable: {e}</p>\"))"
    ]
}

master_tab_cell = {
    "cell_type": "code",
    "execution_count": None,
    "metadata": {},
    "outputs": [],
    "source": [
        "# ==============================================================================\n",
        "# Global Orchestrator Master Tab Assembly\n",
        "# ==============================================================================\n",
        "master_tab = widgets.Tab(children=[\n",
        "    out_telemetry,\n",
        "    out_ocr,\n",
        "    tab_life_companion,\n",
        "    tab_mjpeg_hud,\n",
        "])\n",
        "\n",
        "master_tab.set_title(0, \"🧠 Global Orchestrator\")\n",
        "master_tab.set_title(1, \"👁️ OCR Engine\")\n",
        "master_tab.set_title(2, \"📓 Life Companion\")\n",
        "master_tab.set_title(3, \"📡 MJPEG HUD\")\n",
        "\n",
        "display(master_tab)"
    ]
}

# Replace the last cell (which was master_tab assembly)
nb['cells'].pop()
nb['cells'].append(ocr_cell)
nb['cells'].append(master_tab_cell)

with open('/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/notebooks/09_sovereign_screen_lens_dashboard.ipynb', 'w') as f:
    json.dump(nb, f, indent=1)

print("Notebook updated with OCR Engine.")
