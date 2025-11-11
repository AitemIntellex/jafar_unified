import subprocess

session = "tmux_test"
window = "tmux_win"
command = "echo Hello from tmux && sleep 10"

subprocess.run(["tmux", "new-session", "-d", "-s", session, "-n", window])
subprocess.run(["tmux", "send-keys", "-t", f"{session}:{window}", command, "C-m"])
print("OK! Запусти: tmux attach -t tmux_test")
