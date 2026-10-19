import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk, ImageEnhance
import subprocess
import time
import pyautogui
import ctypes
import os
import sys
import uuid
import hashlib
import base64

from cryptography.fernet import Fernet
from numpy.random import geometric
from pyscreeze import center

# ==== НАСТРОЙКА AHK ====

def resource_path(relative_path):
    """Достаёт ресурс из exe или из папки при запуске в Python"""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("../../../Работы/Порт"), relative_path)

AHK_EXECUTABLE = resource_path("../../../Работы/Порт/AutoHotkeyU64.exe")
AHK_PATH = resource_path("../../../Работы/Порт/port.ahk")
ICON_PATH = resource_path("cda95f6b-1f50-49be-b6b9-77d54fa40350.ico")
LOGO_PNG_PATH = resource_path("cda95f6b-1f50-49be-b6b9-77d54fa40350.png")

APP_ACTIVATION_FOLDER = "PortAppHidden"      # папка для activation.dat
APP_SECRET_FOLDER = "PortAppSecretHidden"    # папка для secret.dat

PROGRAMDATA = os.environ.get("ProgramData", r"C:\ProgramData")

ACTIVATION_DIR = os.path.join(PROGRAMDATA, APP_ACTIVATION_FOLDER)
SECRET_DIR = os.path.join(PROGRAMDATA, APP_SECRET_FOLDER)

def _ensure_dir_hidden(path):
    try:
        os.makedirs(path, exist_ok=True)
        # Пометить скрытым атрибутом в Windows
        FILE_ATTRIBUTE_HIDDEN = 0x02
        ctypes.windll.kernel32.SetFileAttributesW(path, FILE_ATTRIBUTE_HIDDEN)
    except Exception:
        # Если не получилось установить атрибут — пропускаем, папка всё равно нужна
        pass

_ensure_dir_hidden(ACTIVATION_DIR)
_ensure_dir_hidden(SECRET_DIR)

ACTIVATION_FILE = os.path.join(ACTIVATION_DIR, "activation.dat")
SECRET_FILE = os.path.join(SECRET_DIR, "secret.dat")

DEFAULT_SECRET = "FUCKNIGGER"

# Функция получения HWID
def get_hwid():
    return str(uuid.getnode())  # простой вариант HWID

# ---- Помощники для детерминированного вывода Fernet-ключей ----
# Ключ для шифрования activation.dat будет получен из (loaded_secret + hwid)
# Ключ для шифрования secret.dat (при первом создании) будет получен из (hwid + соль_секрета)
def _derive_key_from_material(material_bytes: bytes, salt: bytes, iterations: int = 200_000) -> bytes:
    dk = hashlib.pbkdf2_hmac("sha256", material_bytes, salt, iterations, dklen=32)
    return base64.urlsafe_b64encode(dk)

# Соляные константы (должны быть фиксированными между запусками)
_SALT_SECRET_FILE = b"PortSecretSalt_v1"  # соль для хранения secret.dat
_SALT_ACTIVATION_KEY = b"PortActivationSalt_v1"  # соль для ключа шифрования activation.dat

# ==== Работа с секретом (secret.dat) ====
def _derive_key_for_secret(hwid: str) -> bytes:
    # Делаем материал: hwid + небольшой суффикс, чтобы ключ отличался от ключа для активации
    material = hwid.encode("utf-8") + b":secret-file"
    return _derive_key_from_material(material, _SALT_SECRET_FILE)

def _create_or_load_secret() -> str:
    """
    Если SECRET_FILE есть — расшифровывает и возвращает секрет.
    Если нет — шифрует DEFAULT_SECRET и сохраняет в SECRET_FILE, возвращает DEFAULT_SECRET.
    """
    hwid = get_hwid()
    key = _derive_key_for_secret(hwid)
    f = Fernet(key)
    if os.path.exists(SECRET_FILE):
        try:
            with open(SECRET_FILE, "rb") as fh:
                token = fh.read()
            secret = f.decrypt(token).decode("utf-8")
            return secret
        except Exception:
            # если файл повреждён или HWID изменился — перезапишем новым (безопаснее запросить новый)
            pass

    # создаём файл с DEFAULT_SECRET
    try:
        token = f.encrypt(DEFAULT_SECRET.encode("utf-8"))
        with open(SECRET_FILE, "wb") as fh:
            fh.write(token)
        # пометим файл скрытым (если нужно)
        try:
            ctypes.windll.kernel32.SetFileAttributesW(SECRET_FILE, 0x02)
        except Exception:
            pass
    except Exception:
        pass

    return DEFAULT_SECRET

# Загружаем секрет в память (используется далее при генерации ключей активации)
SECRET_KEY = _create_or_load_secret()


# ==== HWID / Активация ====
def generate_activation_code(hwid):
    combined = f"{hwid}-{SECRET_KEY}"
    code = hashlib.sha256(combined.encode()).hexdigest()
    return code[:20]

# Ключ для шифрования activation.dat детерминирован от (SECRET_KEY + HWID)
def _derive_fernet_key_for_activation(hwid: str) -> bytes:
    material = (SECRET_KEY + "|" + hwid).encode("utf-8")
    return _derive_key_from_material(material, _SALT_ACTIVATION_KEY)

def save_code_locally(code: str):
    """
    Сохраняет код активации в скрытой папке ACTIVATION_DIR, зашифрованным Fernet.
    Ключ для Fernet детерминирован от SECRET_KEY + HWID.
    """
    try:
        hwid = get_hwid()
        key = _derive_fernet_key_for_activation(hwid)
        f = Fernet(key)
        token = f.encrypt(code.encode("utf-8"))
        with open(ACTIVATION_FILE, "wb") as fh:
            fh.write(token)
        # пометить файл скрытым
        try:
            ctypes.windll.kernel32.SetFileAttributesW(ACTIVATION_FILE, 0x02)
        except Exception:
            pass
    except Exception as e:
        print("Ошибка сохранения кода:", e)

def load_local_code():
    """
    Считывает и расшифровывает код из скрытой папки ACTIVATION_DIR.
    Возвращает строку кода или None, если файла нет / дешифровка не удалась.
    """
    if not os.path.exists(ACTIVATION_FILE):
        return None
    try:
        hwid = get_hwid()
        key = _derive_fernet_key_for_activation(hwid)
        f = Fernet(key)
        with open(ACTIVATION_FILE, "rb") as fh:
            token = fh.read()
        code = f.decrypt(token).decode("utf-8")
        return code
    except Exception:
        return None

def verify_activation_code(user_code):
    hwid = get_hwid()
    correct_code = generate_activation_code(hwid)
    return user_code == correct_code

def check_activation():
    local_code = load_local_code()
    if local_code is None:
        return False
    return verify_activation_code(local_code)


# ==== AHK Контроллер ====
class AHKController:
    def __init__(self, status_label, animate_func):
        self.process = None
        self.status_label = status_label
        self.animate_buttons_appearance = animate_func

    def start_ahk(self):
        if self.process is None or self.process.poll() is not None:
            try:
                self.process = subprocess.Popen(
                    [AHK_EXECUTABLE, AHK_PATH],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                time.sleep(1)
                pyautogui.press('f5')
                self.status_label._full_text = "AHK - включен"
                self.animate_buttons_appearance()
            except Exception as e:
                self.status_label._full_text = f"Ошибка запуска AHK: {e}"
                self.animate_buttons_appearance()

    def stop_ahk(self):
        if self.process is None or self.process.poll() is not None:
            self.status_label._full_text = "AHK - выключен"
            self.animate_buttons_appearance()
            return

        pyautogui.keyDown('shift')
        time.sleep(0.5)
        pyautogui.press('f7')
        pyautogui.keyUp('shift')
        time.sleep(0.5)

        self.process.terminate()
        self.process = None
        self.status_label._full_text = "AHK - выключен"
        self.animate_buttons_appearance()
        release_shift()


def release_shift():
    INPUT_KEYBOARD = 1
    KEYEVENTF_KEYUP = 0x0002
    VK_SHIFT = 0x10

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", ctypes.c_ushort),
            ("wScan", ctypes.c_ushort),
            ("dwFlags", ctypes.c_ulong),
            ("time", ctypes.c_ulong),
            ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong))
        ]

    class INPUT(ctypes.Structure):
        class _INPUT(ctypes.Union):
            _fields_ = [("ki", KEYBDINPUT)]

        _anonymous_ = ("u",)
        _fields_ = [("type", ctypes.c_ulong), ("u", _INPUT)]

    inp = INPUT()
    inp.type = INPUT_KEYBOARD
    inp.ki = KEYBDINPUT(
        wVk=VK_SHIFT, wScan=0, dwFlags=KEYEVENTF_KEYUP, time=0, dwExtraInfo=None
    )

    ctypes.windll.user32.SendInput(1, ctypes.byref(inp), ctypes.sizeof(inp))


# ==== Интерфейс программы ====
def launch_ahk_interface():
    root = tk.Tk()
    root.title("Контроль AHK")
    if os.path.exists(ICON_PATH):
        try:
            root.iconbitmap(ICON_PATH)
        except Exception:
            # на некоторых системах может не сработать, но это не критично
            pass
    root.attributes("-fullscreen", True)
    root.configure(bg="black")

    status_label = tk.Label(
        root, text="", bg="black", fg="#00FF00", font=("Segoe UI", 20, "bold")
    )
    button_frame = tk.Frame(root, bg="black")

    btn_style = {
        "bg": "black",
        "fg": "#000000",
        "activebackground": "black",
        "activeforeground": "#ff0000",
        "font": ("Segoe UI", 24, "bold"),
        "relief": "flat",
        "bd": 0,
        "highlightthickness": 0,
        "takefocus": 0,
        "width": 20,
        "height": 2
    }

    def interpolate_color(start_color, end_color, factor):
        def hex_to_rgb(hex_color):
            hex_color = hex_color.lstrip("#")
            return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))

        start_rgb = hex_to_rgb(start_color)
        end_rgb = hex_to_rgb(end_color)
        interp_rgb = tuple(
            int(start + (end - start) * factor) for start, end in zip(start_rgb, end_rgb)
        )
        return "#%02x%02x%02x" % interp_rgb

    def add_hover_animation(btn):
        def animate_hover(event, reverse=False):
            steps = 20
            duration = 300

            def step(i=0):
                factor = i / steps if not reverse else 1 - i / steps
                color = interpolate_color("#ffffff", "#ff0000", factor)
                btn.config(fg=color)
                if i < steps:
                    btn.after(duration // steps, step, i + 1)

            step()

        btn.bind("<Enter>", lambda e: animate_hover(e, reverse=False))
        btn.bind("<Leave>", lambda e: animate_hover(e, reverse=True))

    start_btn = tk.Button(button_frame, text="Включить AHK", **btn_style)
    stop_btn = tk.Button(button_frame, text="Выключить AHK", **btn_style)

    start_btn.grid(row=0, column=0, padx=40)
    stop_btn.grid(row=0, column=1, padx=40)

    button_frame.place_forget()
    status_label.place_forget()

    # --- Логотип ---
    try:
        logo_img_orig = Image.open(resource_path("cda95f6b-1f50-49be-b6b9-77d54fa40350.png"))
        logo_img_orig = logo_img_orig.resize((600, 450), Image.Resampling.LANCZOS)
    except Exception as e:
        print("Не удалось загрузить логотип:", e)
        logo_img_orig = None

    logo_label = tk.Label(root, bg="black")
    logo_label.place(relx=0.5, rely=0.45, anchor="center")

    welcome_label = tk.Label(
        root, text="", bg="black", fg="white", font=("Segoe UI", 24, "normal")
    )
    welcome_label.place(relx=0.5, rely=0.7, anchor="center")

    def animate_buttons_appearance(step=0, steps=25):
        button_frame.place(relx=0.5, rely=1.0, anchor="s")
        status_label.place(relx=0.5, rely=0.8, anchor="center")

        factor = step / steps
        start_btn.config(fg="#ffffff")
        stop_btn.config(fg="#ffffff")

        full_text = getattr(status_label, "_full_text", "")
        status_label.config(text=full_text)

        if "включен" in full_text.lower():
            start_color = "#000000"
            end_color = "#00ff00"
        elif "выключен" in full_text.lower():
            start_color = "#000000"
            end_color = "#ff0000"
        else:
            start_color = "#000000"
            end_color = "#ffffff"

        current_color = interpolate_color(start_color, end_color, factor)
        status_label.config(fg=current_color)

        if step < steps:
            root.after(40, animate_buttons_appearance, step + 1, steps)
        else:
            status_label.config(fg=end_color)

    ahk_controller = AHKController(status_label, animate_buttons_appearance)
    start_btn.config(command=ahk_controller.start_ahk)
    stop_btn.config(command=ahk_controller.stop_ahk)

    for b in (start_btn, stop_btn):
        add_hover_animation(b)

    def fade_in_logo(step=0, steps=30):
        if logo_img_orig is None:
            type_text(welcome_label, "Добро пожаловать в систему!", delay=70,
                      after_typing_callback=wait_and_erase)
            return

        factor = step / steps
        enhancer = ImageEnhance.Brightness(logo_img_orig)
        img_enhanced = enhancer.enhance(factor)
        logo_photo = ImageTk.PhotoImage(img_enhanced)
        logo_label.img = logo_photo
        logo_label.config(image=logo_photo)

        if step < steps:
            root.after(40, fade_in_logo, step + 1, steps)
        else:
            type_text(welcome_label, "Добро пожаловать в систему!", delay=70,
                      after_typing_callback=wait_and_erase)

    def type_text(label, text, index=0, delay=70, after_typing_callback=None):
        if index <= len(text):
            label.config(text=text[:index])
            label.after(delay, type_text, label, text, index + 1, delay, after_typing_callback)
        else:
            if after_typing_callback:
                after_typing_callback()

    def wait_and_erase():
        root.after(1000, erase_text_and_show_buttons)

    def erase_text_and_show_buttons():
        def erasure_text(label, text, index=None, delay=50):
            if index is None:
                index = len(text)
            if index >= 0:
                label.config(text=text[:index])
                label.after(delay, erasure_text, label, text, index - 1, delay)
            else:
                label.config(text="")
                show_buttons()

        erasure_text(welcome_label, welcome_label.cget("text"))

    def show_buttons():
        if not hasattr(status_label, "_full_text"):
            status_label._full_text = "AHK - выключен"
        animate_buttons_appearance()

    fade_in_logo()
    root.mainloop()


# ==== Окно активации ====
def launch_activation_window():
    win = tk.Tk()
    win.title("Активация программы")
    if os.path.exists(ICON_PATH):
        try:
            win.iconbitmap(ICON_PATH)
        except Exception:
            pass
    win.attributes("-fullscreen", True)
    win.configure(bg="black")

    def interpolate_color(start_color, end_color, factor):
        def hex_to_rgb(hex_color):
            hex_color = hex_color.lstrip("#")
            return tuple(int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
        start_rgb = hex_to_rgb(start_color)
        end_rgb = hex_to_rgb(end_color)
        interp_rgb = tuple(
            int(start + (end - start) * factor) for start, end in zip(start_rgb, end_rgb)
        )
        return "#%02x%02x%02x" % interp_rgb

    def add_hover_animation(btn):
        def animate_hover(event, reverse=False):
            steps = 20
            duration = 300
            def step(i=0):
                factor = i / steps if not reverse else 1 - i / steps
                color = interpolate_color("#ffffff", "#ff0000", factor)
                btn.config(fg=color)
                if i < steps:
                    btn.after(duration // steps, step, i + 1)
            step()
        btn.bind("<Enter>", lambda e: animate_hover(e, reverse=False))
        btn.bind("<Leave>", lambda e: animate_hover(e, reverse=True))

    # --- логотип ---
    try:
        logo_img_orig = Image.open(resource_path("cda95f6b-1f50-49be-b6b9-77d54fa40350.png"))
        logo_img_orig = logo_img_orig.resize((600, 450), Image.Resampling.LANCZOS)
    except Exception as e:
        print("Не удалось загрузить логотип:", e)
        logo_img_orig = None

    logo_label = tk.Label(win, bg="black")
    logo_label.place(relx=0.5, rely=0.45, anchor="center")

    # --- подпись «Ваш код» ---
    title_label = tk.Label(win, text="Ваш код:", fg="black", bg="black", font=("Segoe UI", 30, "bold"))
    title_label.place(relx=0.5, rely=0.62, anchor="center")

    # --- поле ввода ---
    code_entry = tk.Entry(win, font=("Segoe UI", 12), width=35,
                          bg="black", fg="red", relief="flat", bd=0, highlightthickness=1, takefocus=0)
    code_entry.place_forget()  # <- спрятали изначально

    # --- кнопки ---
    def copy_hwid():
        win.clipboard_clear()
        win.clipboard_append(get_hwid())
        win.update()
        messagebox.showinfo("Скопировано", "HWID скопирован в буфер обмена")

    copy = tk.Button(win, text="Скопировать код", command=copy_hwid,bg="black", fg="black", font=("Segoe UI", 28, "bold"),activebackground="black", activeforeground="white",relief="flat", bd=0, highlightthickness=0, takefocus=0,width=20, height=2)
    copy.place_forget()
    add_hover_animation(copy)

    def activate_program():
        user_code = code_entry.get().strip()
        if verify_activation_code(user_code):
            save_code_locally(user_code)
            messagebox.showinfo("Успех", "Программа активирована!")
            win.destroy()
            launch_ahk_interface()
        else:
            messagebox.showerror("Ошибка", "Неверный код активации!")

    active = tk.Button(win, text="Активировать код", command=activate_program,bg="black", fg="black", font=("Segoe UI", 28, "bold"),activebackground="black", activeforeground="white",relief="flat", bd=0, highlightthickness=0, takefocus=0,width=20, height=2)
    active.place_forget()
    add_hover_animation(active)

    # --- HWID для печати ---
    hwid_label = tk.Label(win, text="", fg="white", bg="black", font=("Segoe UI", 26, "normal"))
    hwid_label.place(relx=0.5, rely=0.68, anchor="center")
    hwid_label.place_forget()

    # --- Анимации ---
    def fade_in_logo(step=0, steps=30):
        if logo_img_orig is None:
            fade_in_all_widgets()
            return

        factor = step / steps
        enhancer = ImageEnhance.Brightness(logo_img_orig)
        img_enhanced = enhancer.enhance(factor)
        logo_photo = ImageTk.PhotoImage(img_enhanced)
        logo_label.img = logo_photo
        logo_label.config(image=logo_photo)

        if step < steps:
            win.after(40, fade_in_logo, step + 1, steps)
        else:
            fade_in_all_widgets()

    def fade_in_widget(widget, step=0, steps=20, after=None):
        factor = step / steps
        gray = int(0 + 255 * factor)
        color = f"#{gray:02x}{gray:02x}{gray:02x}"
        widget.config(fg=color)
        widget.place()  # показываем виджет

        if step < steps:
            win.after(40, fade_in_widget, widget, step + 1, steps, after)
        else:
            widget.config(fg="white")
            if after:
                after()

    def fade_in_all_widgets():
        # Плавное появление подписи
        fade_in_widget(title_label)
        # Появление поля ввода
        code_entry.place(relx=0.5, rely=0.74, anchor="center")
        fade_in_widget(code_entry)
        # Появление кнопок
        copy.place(relx=0.3, rely=0.85, anchor="center")
        active.place(relx=0.7, rely=0.85, anchor="center")
        fade_in_widget(copy)
        fade_in_widget(active, after=type_hwid)  # после последней кнопки печатаем HWID

    def type_hwid():
        hwid_label.place(relx=0.5, rely=0.68, anchor="center")
        type_text(hwid_label, get_hwid(), delay=70)

    def type_text(label, text, index=0, delay=70):
        if index <= len(text):
            label.config(text=text[:index])
            label.after(delay, type_text, label, text, index + 1, delay)

    fade_in_logo()
    win.mainloop()

# ==== Основной запуск ====
if check_activation():
    launch_ahk_interface()
else:
    launch_activation_window()