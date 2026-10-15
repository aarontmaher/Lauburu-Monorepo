-- ==============================================================================
-- 🚀 Lauburu Mesh - Zero-Token Native Chrome AppleScript Controller
-- Opens and navigates dashboards natively without pumping DOM into LLM context
-- ==============================================================================

on run argv
    set defaultURLs to {"https://cloud.cerebras.ai/", "https://cloud.sambanova.ai/apis"}
    
    tell application "Google Chrome"
        activate
        if (count of windows) is 0 then
            make new window
        end if
        
        set targetWindow to window 1
        
        repeat with targetURL in defaultURLs
            tell targetWindow
                make new tab with properties {URL:targetURL}
            end tell
        end repeat
    end tell
    
    return "Opened target tabs in Chrome via native Apple Events."
end run
