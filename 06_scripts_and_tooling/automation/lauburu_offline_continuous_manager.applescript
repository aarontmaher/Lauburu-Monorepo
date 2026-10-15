-- ==============================================================================
-- Lauburu Mesh — Native AppleScript 24/7 Offline Continuous Swarm Manager
-- Subsystem: 06_scripts_and_tooling/automation/lauburu_offline_continuous_manager.applescript
-- Version: 1.0.0-APPLESCRIPT-OFFLINE-247
-- ==============================================================================

on run argv
    set daemonScript to "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/automation/lauburu_offline_continuous_daemon.sh"
    
    -- Command-line execution mode (e.g., osascript ... start)
    if (count of argv) > 0 then
        set userAction to item 1 of argv
        if userAction is "start" then
            set res to do shell script daemonScript & " start"
            display notification "10M Drafter & Swarm Loop running offline with caffeinate." with title "Lauburu 24/7 Mesh" subtitle "Swarm Online"
            return res
        else if userAction is "stop" then
            set res to do shell script daemonScript & " stop"
            display notification "All 24/7 continuous daemons stopped." with title "Lauburu 24/7 Mesh" subtitle "Swarm Paused"
            return res
        else if userAction is "restart" then
            set res to do shell script daemonScript & " restart"
            return res
        else if userAction is "status" then
            set res to do shell script daemonScript & " status"
            return res
        end if
    end if

    -- Interactive GUI mode (when launched from Finder, Dock, or Shortcuts)
    try
        set chosenAction to button returned of (display dialog "Lauburu Mesh — 24/7 Offline Continuous Swarm Control" buttons {"Stop All", "Status", "Start 24/7 Swarm"} default button "Start 24/7 Swarm" with title "Lauburu AI Mesh Governor" with icon note)
        
        if chosenAction is "Start 24/7 Swarm" then
            set res to do shell script daemonScript & " start"
            display notification "Continuous 10M Drafter & Swarm Loop active with caffeinate." with title "Lauburu 24/7 Mesh" subtitle "Continuous Offline Loop Engaged"
            display dialog res buttons {"OK"} default button "OK" with title "Lauburu 24/7 Status"
        else if chosenAction is "Status" then
            set res to do shell script daemonScript & " status"
            display dialog res buttons {"OK"} default button "OK" with title "Lauburu 24/7 Status"
        else if chosenAction is "Stop All" then
            set res to do shell script daemonScript & " stop"
            display notification "All continuous daemons stopped cleanly." with title "Lauburu 24/7 Mesh" subtitle "Swarm Disengaged"
            display dialog res buttons {"OK"} default button "OK" with title "Lauburu 24/7 Status"
        end if
    on error errMsg number errNum
        if errNum is not -128 then -- Ignore user cancel
            display alert "Error running Lauburu Swarm Manager: " & errMsg
        end if
    end try
end run
