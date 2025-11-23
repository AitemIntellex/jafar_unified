tell application "TopstepX"
    activate
    tell application "System Events"
        tell process "TopstepX"
            click button "Snapshot" of window 1
        end tell
    end tell
end tell