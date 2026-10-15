-- ===============================================================================
-- Lauburu Local AI Mesh Health & Auto-Heal (AppleScript)
-- ===============================================================================
-- Subsystem: 06_scripts_and_tooling/automation/applescript/Local_AI_Mesh_Health.applescript
-- Strict Local-AI-Only Invariant: Zero Cloud Calls
-- ===============================================================================

property bridgePath : "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/automation/applescript/local_ai_apple_bridge.py"
property pythonBin : "/Users/aaron/.venv/bin/python3"

on run
    my checkMeshHealth()
end run

on checkMeshHealth()
    set cmd to pythonBin & " " & bridgePath & " --mode health"
    try
        set healthOutput to do shell script cmd
        display notification healthOutput with title "🛡️ Local AI Mesh Health" subtitle "Ports 8081 | 8082 | 8083"
        
        set dialogResult to display dialog healthOutput ¬
            buttons {"Dismiss", "Auto-Heal Network & Models"} ¬
            default button "Dismiss" ¬
            giving up after 3 ¬
            with title "🛡️ Local AI Mesh Status"
        
        if button returned of dialogResult is "Auto-Heal Network & Models" then
            display notification "Initiating 4-Tier Auto-Healing Protocol..." with title "🛡️ Mesh Auto-Heal"
            set healCmd to pythonBin & " " & bridgePath & " --mode auto_heal"
            set healResult to do shell script healCmd
            display notification "Self-healing cycle finished." with title "✅ Auto-Heal Complete"
            display dialog healResult buttons {"OK"} default button "OK" with title "✅ Auto-Heal Summary"
        end if
        return healthOutput
    on error errMsg
        display notification "Mesh Health Check Failed: " & errMsg with title "⚠️ Local AI Error"
        return "ERROR: " & errMsg
    end try
end checkMeshHealth
