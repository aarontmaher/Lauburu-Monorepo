-- mesh_sentinel.applescript
-- Constant background AppleScript monitor for Lauburu Mesh Network Health & Native Notifications
-- Invokes mesh_unhealable_notifier_daemon.py and displays system alerts for unhealable hardware

on run
    set pythonPath to "/usr/bin/python3"
    set scriptPath to "/Users/aaron/DFS_UNIFIED/Lauburu-Monorepo/06_scripts_and_tooling/network/mesh_unhealable_notifier_daemon.py"
    
    try
        set auditResult to do shell script pythonPath & " " & scriptPath & " --once"
        return auditResult
    on error errMsg
        display notification "Mesh Sentinel execution error: " & errMsg with title "🚨 Mesh Monitor Error" subtitle "Execution Halted" sound name "Basso"
        return errMsg
    end try
end run
