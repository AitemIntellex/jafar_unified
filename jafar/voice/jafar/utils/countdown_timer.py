import tkinter as tk
import sys

def start_countdown_timer(duration):
    root = tk.Tk()
    root.overrideredirect(True)  # Remove window decorations (title bar, borders)
    root.attributes("-topmost", True) # Always on top
    root.geometry("+700+50") # Position the window (e.g., near top center)
    root.wm_attributes("-transparent", True) # Make background transparent
    root.config(bg='systemTransparent') # For macOS transparency

    label = tk.Label(root, text=str(duration), font=("Helvetica Neue", 48, "bold"), fg="red", bg="systemTransparent")
    label.pack(padx=20, pady=10)

    def update_countdown(current_time):
        if current_time > 0:
            label.config(text=str(current_time))
            root.after(1000, update_countdown, current_time - 1)
        else:
            label.config(text="0")
            root.destroy()

    update_countdown(duration)
    root.mainloop()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        duration = int(sys.argv[1])
        start_countdown_timer(duration)
    else:
        print("Usage: python countdown_timer.py <duration_in_seconds>")
