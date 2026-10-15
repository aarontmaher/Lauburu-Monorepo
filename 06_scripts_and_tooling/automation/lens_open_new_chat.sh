#!/usr/bin/env bash
# lens_open_new_chat.sh
# Screen Lens Sovereign - Automate opening a new conversation in Antigravity

TRACK="${1:-1}"
DOSSIER=""

case "$TRACK" in
  1)
    DOSSIER="/Volumes/Lauburu-Monorepo/obsidian_vault/APPS_AND_FEATURES/TRACK_1_OMNI_INBOX_MESSAGING.md"
    TITLE="Track 1: Omni Inbox (All-in-One Multi-Account Messaging App)"
    ;;
  2)
    DOSSIER="/Volumes/Lauburu-Monorepo/obsidian_vault/APPS_AND_FEATURES/TRACK_2_LIFE_COMPANION_CORE_APP.md"
    TITLE="Track 2: Life Companion Core App (macOS & Android)"
    ;;
  3)
    DOSSIER="/Volumes/Lauburu-Monorepo/obsidian_vault/APPS_AND_FEATURES/TRACK_3_COMMERCE_AND_BLUETOOTH_TERMINAL.md"
    TITLE="Track 3: Commerce & Bluetooth Serial Terminal"
    ;;
  *)
    echo "Usage: $0 [1|2|3]"
    exit 1
    ;;
esac

echo "[👁️ Screen Lens] Loading Dossier for $TITLE..."
PROMPT="Execute $TITLE.
Please thoroughly review the parent conversation history:
[Conversation History d161e75c-1d12-4715-8ca2-2eb3cab65eed](conversation://d161e75c-1d12-4715-8ca2-2eb3cab65eed)
and the line-by-line dossier at:
$DOSSIER

Begin execution of the top 5 priorities immediately."

# Copy to macOS clipboard
echo "$PROMPT" | pbcopy
echo "[👁️ Screen Lens] Kickoff prompt copied to macOS clipboard."

# Actuate Antigravity to click '+ New Conversation'
osascript << 'APPLESCRIPT'
tell application "System Events"
    tell process "Antigravity"
        set frontmost to true
        set allUI to entire contents of window 1
        repeat with uiElem in allUI
            try
                set elemPos to position of uiElem
                if (item 1 of elemPos) is 8 and (item 2 of elemPos) is 82 then
                    perform action "AXPress" of uiElem
                    delay 0.5
                    -- Paste clipboard
                    keystroke "v" using command down
                    delay 0.2
                    return "Successfully opened new conversation and pasted kickoff prompt."
                end if
            end try
        end repeat
    end tell
end tell
return "Could not find New Conversation button at 8,82."
APPLESCRIPT

