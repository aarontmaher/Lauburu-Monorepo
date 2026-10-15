-- ===============================================================================
-- Lauburu Local AI Quick Prompt (AppleScript)
-- ===============================================================================
-- Subsystem: 06_scripts_and_tooling/automation/applescript/Local_AI_Quick_Prompt.applescript
-- Strict Local-AI-Only Invariant: 100% Loopback Inference (Port 8081 / Port 8083)
-- ===============================================================================

property bridgePath : "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/automation/applescript/local_ai_apple_bridge.py"
property pythonBin : "/Users/aaron/.venv/bin/python3"

on run
    my promptAndExecute()
end run

on promptAndExecute()
    set clipContent to ""
    try
        set clipContent to the clipboard as text
    end try
    
    set defaultInstruction to "Explain this code and suggest optimizations"
    if clipContent is "" then
        set defaultInstruction to "What is the status of the local AI mesh?"
    end if
    
    set userDialog to display dialog "Local AI Prompt (Zero-Cloud Loopback):" ¬
        default answer defaultInstruction ¬
        buttons {"Cancel", "Use Clipboard", "Execute"} ¬
        default button "Execute" ¬
        with title "⚡ Local AI Quick Prompt"
    
    if button returned of userDialog is "Cancel" then return
    
    set userInstruction to text returned of userDialog
    set clipFlag to ""
    if button returned of userDialog is "Use Clipboard" then
        set clipFlag to " --clipboard"
    end if
    
    display notification "Processing on local Metal GPU..." with title "⚡ Local AI Running" subtitle "Qwen 2.5 Coder 7B (:8081)"
    
    set escapedPrompt to quoted form of userInstruction
    set cmd to pythonBin & " " & bridgePath & " --mode coder --prompt " & escapedPrompt & clipFlag & " --set-clipboard"
    
    try
        set aiOutput to do shell script cmd
        display notification "Result copied to clipboard!" with title "✅ Local AI Finished" subtitle "Output Ready"
        
        -- Optional preview
        set previewText to aiOutput
        if (length of previewText) > 1200 then
            set previewText to (text 1 thru 1200 of previewText) & "\n\n...[Full response on clipboard]..."
        end if
        
        display dialog previewText buttons {"OK", "Open in TextEdit"} default button "OK" with title "⚡ Local AI Response"
        if button returned of result is "Open in TextEdit" then
            tell application "TextEdit"
                activate
                make new document with properties {text:aiOutput}
            end tell
        end if
    on error errMsg
        display alert "Local AI Execution Failed" message errMsg as critical
    end try
end promptAndExecute
