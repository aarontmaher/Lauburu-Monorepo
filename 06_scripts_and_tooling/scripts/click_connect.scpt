tell application "System Events"
    tell process "OpenClaw"
        set frontmost to true
        delay 0.5
        
        -- recursive search
        my clickElementNamed(window 1, "Connect")
    end tell
end tell

on clickElementNamed(uiElem, targetName)
    tell application "System Events"
        if name of uiElem is targetName or description of uiElem is targetName then
            click uiElem
            return true
        end if
        
        set elemChildren to UI elements of uiElem
        repeat with child in elemChildren
            if my clickElementNamed(child, targetName) then return true
        end repeat
        return false
    end tell
end clickElementNamed
