-- ===============================================================================
-- Lauburu Sovereign Local AI Command Center (AppleScript)
-- ===============================================================================
-- Subsystem: 06_scripts_and_tooling/automation/applescript/Local_AI_Command_Center.applescript
-- Strict Local-AI-Only Invariant: Zero Cloud Calls, 100% Private Loopback AI
-- ===============================================================================

property bridgePath : "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/automation/applescript/local_ai_apple_bridge.py"
property pythonBin : "/Users/aaron/.venv/bin/python3"
property arenaScript : "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/01_apps/screen_lens/sandbox_evolution/bluetooth_terminal_arena/run_sovereign_bluetooth_npu_ide.sh"

on run
    my mainWorkflow()
end run

on mainWorkflow()
    set menuOptions to {¬
        "⚡ 1. Code Refactor / Fix (Qwen 2.5 Coder 7B :8081)", ¬
        "👑 2. Sovereign Architecture Reasoner (Qwen 3.8 Max :8082)", ¬
        "🔥 3. Red Team Adversarial Audit (Qwen 3.8 Abliterated :8083)", ¬
        "⚔️ 4. Local AI Adversarial Debate (Sovereign vs Red Team)", ¬
        "💬 5. Quick Local AI Chat", ¬
        "🛡️ 6. Check Local Mesh Health & Auto-Heal", ¬
        "🚀 7. Open Sovereign Bluetooth Terminal IDE Arena"}
    
    set chosenItem to choose from list menuOptions ¬
        with title "🧠 Lauburu Local AI Command Center" ¬
        with prompt "Select a 100% Local AI Action (Zero-Cloud Enforced):" ¬
        default items {item 1 of menuOptions} ¬
        OK button name "Run Action" ¬
        cancel button name "Cancel"
    
    if chosenItem is false then return
    set action to item 1 of chosenItem
    
    if action starts with "⚡ 1." then
        my handleLocalInference("coder", "Code Refactor / Fix")
    else if action starts with "👑 2." then
        my handleLocalInference("sovereign", "Sovereign Architecture Reasoning")
    else if action starts with "🔥 3." then
        my handleLocalInference("red_team", "Red Team Adversarial Audit")
    else if action starts with "⚔️ 4." then
        my handleLocalDebate()
    else if action starts with "💬 5." then
        my handleFreeformChat()
    else if action starts with "🛡️ 6." then
        my handleMeshHealth()
    else if action starts with "🚀 7." then
        my launchArenaIDE()
    end if
end mainWorkflow

on handleLocalInference(modeName, titleName)
    set currentClip to ""
    try
        set currentClip to the clipboard as text
    end try
    
    set userPrompt to ""
    set defaultText to ""
    if currentClip is not "" and (length of currentClip) < 2000 then
        set defaultText to currentClip
    end if
    
    set promptDialog to display dialog "Enter instruction or code for " & titleName & ":" ¬
        default answer defaultText ¬
        buttons {"Cancel", "Use Clipboard Context", "Execute"} ¬
        default button "Execute" ¬
        with title "🧠 Local AI: " & titleName
    
    if button returned of promptDialog is "Cancel" then return
    
    set enteredText to text returned of promptDialog
    set clipFlag to ""
    if button returned of promptDialog is "Use Clipboard Context" then
        set clipFlag to " --clipboard"
    end if
    
    display notification "Dispatching query to Local AI..." with title "🧠 Lauburu Local AI" subtitle titleName
    
    -- Execute bridge
    set escapedPrompt to quoted form of enteredText
    set cmd to pythonBin & " " & bridgePath & " --mode " & modeName & " --prompt " & escapedPrompt & clipFlag
    
    try
        set aiResponse to do shell script cmd
        my displayAiResult(titleName, aiResponse)
    on error errMsg
        display alert "Local AI Error" message errMsg as critical
    end try
end handleLocalInference

on handleLocalDebate()
    set promptDialog to display dialog "Enter proposal, architecture design, or code to debate locally:" ¬
        default answer "Should we shard KV cache over 10Gbps Thunderbolt 4 DMA or keep it localized to Apple Silicon M4 Pro unified RAM?" ¬
        buttons {"Cancel", "Debate Locally"} ¬
        default button "Debate Locally" ¬
        with title "⚔️ Local AI Adversarial Debate"
    
    if button returned of promptDialog is "Cancel" then return
    set topicText to text returned of promptDialog
    
    display notification "Running 2-Turn Debate (:8082 vs :8083)..." with title "⚔️ Local AI Debate" subtitle "Sovereign vs Red Team"
    
    set escapedTopic to quoted form of topicText
    set cmd to pythonBin & " " & bridgePath & " --mode debate --prompt " & escapedTopic
    
    try
        set debateResult to do shell script cmd
        my displayAiResult("Adversarial Debate Consensus", debateResult)
    on error errMsg
        display alert "Debate Error" message errMsg as critical
    end try
end handleLocalDebate

on handleFreeformChat()
    set promptDialog to display dialog "Ask Local AI anything (Zero Cloud):" ¬
        default answer "" ¬
        buttons {"Cancel", "Ask Local AI"} ¬
        default button "Ask Local AI" ¬
        with title "💬 Local AI Chat"
    
    if button returned of promptDialog is "Cancel" then return
    set queryText to text returned of promptDialog
    
    display notification "Generating local response..." with title "💬 Local AI Chat"
    
    set escapedQuery to quoted form of queryText
    set cmd to pythonBin & " " & bridgePath & " --mode coder --prompt " & escapedQuery
    
    try
        set aiResponse to do shell script cmd
        my displayAiResult("Local AI Chat Response", aiResponse)
    on error errMsg
        display alert "Local AI Chat Error" message errMsg as critical
    end try
end handleFreeformChat

on handleMeshHealth()
    set cmd to pythonBin & " " & bridgePath & " --mode health"
    try
        set healthOutput to do shell script cmd
        set healthDialog to display dialog healthOutput ¬
            buttons {"Close", "Run Auto-Heal"} ¬
            default button "Close" ¬
            with title "🛡️ Local AI Mesh Health Status"
        
        if button returned of healthDialog is "Run Auto-Heal" then
            display notification "Executing Self-Healing Ladder..." with title "🛡️ Mesh Self-Healing"
            set healCmd to pythonBin & " " & bridgePath & " --mode auto_heal"
            set healResult to do shell script healCmd
            display dialog healResult buttons {"OK"} default button "OK" with title "🛡️ Auto-Heal Result"
        end if
    on error errMsg
        display alert "Health Probe Error" message errMsg as critical
    end try
end handleMeshHealth

on launchArenaIDE()
    tell application "Terminal"
        activate
        do script arenaScript & " --dev"
    end tell
    display notification "Launched Bluetooth Arena IDE in Terminal." with title "🚀 Sovereign IDE"
end launchArenaIDE

on displayAiResult(titleStr, resultText)
    set the clipboard to resultText
    display notification "Result copied to clipboard!" with title "✅ Local AI Complete" subtitle titleStr
    
    -- Display preview dialog
    set previewText to resultText
    if (length of previewText) > 1500 then
        set previewText to (text 1 thru 1500 of previewText) & "\n\n...[Full response copied to system clipboard]..."
    end if
    
    set resDialog to display dialog previewText ¬
        buttons {"Done", "Open In TextEdit", "Copy Again"} ¬
        default button "Done" ¬
        with title "🧠 Local AI Output (" & titleStr & ")"
    
    if button returned of resDialog is "Open In TextEdit" then
        tell application "TextEdit"
            activate
            make new document with properties {text:resultText}
        end tell
    else if button returned of resDialog is "Copy Again" then
        set the clipboard to resultText
    end if
end displayAiResult
