"""InkFlow v3 — OneNote Writer Engine (Native Win32 Event Rebuild)."""

import math
import platform
import random
import threading
import time
from typing import Optional

import cv2
import numpy as np

# Import our new modular components
from .input_manager import InputManager
from .coordinate_translator import CoordinateTranslator
from .stroke_processor import StrokeProcessor

HAS_NATIVE_EVENTS = False

try:
    import win32api
    import win32con
    import win32gui
    HAS_NATIVE_EVENTS = True
except Exception:
    win32api = None
    win32con = None
    win32gui = None

try:
    from pynput import keyboard
    HAS_KEYBOARD_FAILSAFE = True
except Exception:
    keyboard = None
    HAS_KEYBOARD_FAILSAFE = False


class WriteJob:
    def __init__(self, job_id: str):
        self.job_id = job_id
        self.status = "idle"
        self.progress = 0.0
        self.chars_done = 0
        self.chars_total = 0
        self.current_line = 0
        self.message = ""
        self._pause_event = threading.Event()
        self._pause_event.set()
        self._cancel = False

    def pause(self):
        self._pause_event.clear()
        self.status = "paused"

    def resume(self):
        self._pause_event.set()
        self.status = "running"

    def cancel(self):
        self._cancel = True
        self._pause_event.set()

    def wait_if_paused(self):
        self._pause_event.wait()

    @property
    def cancelled(self):
        return self._cancel


_jobs: dict[str, WriteJob] = {}
_failsafe_listener = None
_failsafe_lock = threading.Lock()

# Global instances
input_mgr = InputManager()
stroke_proc = StrokeProcessor()


# Backward Compatibility Layer for API
class LegacyPenInjector:
    def down(self, x: int, y: int, pressure: int = 512):
        vx, vy, vw, vh = _screen_metrics()
        ax, ay = CoordinateTranslator.normalize_to_win_abs(x, y, vx, vy, vw, vh)
        input_mgr.down(ax, ay)

    def move(self, x: int, y: int, pressure: int = 512):
        vx, vy, vw, vh = _screen_metrics()
        ax, ay = CoordinateTranslator.normalize_to_win_abs(x, y, vx, vy, vw, vh)
        input_mgr.move_to(ax, ay)

    def up(self, x: int, y: int):
        vx, vy, vw, vh = _screen_metrics()
        ax, ay = CoordinateTranslator.normalize_to_win_abs(x, y, vx, vy, vw, vh)
        input_mgr.up(ax, ay)


pen_injector = LegacyPenInjector()
HAS_PEN_INJECTION = True


def get_job(job_id: str) -> Optional[WriteJob]:
    return _jobs.get(job_id)


def create_job(job_id: str) -> WriteJob:
    job = WriteJob(job_id)
    _jobs[job_id] = job
    _ensure_failsafe_listener()
    return job


def _ensure_failsafe_listener():
    global _failsafe_listener
    if not HAS_KEYBOARD_FAILSAFE:
        return
    with _failsafe_lock:
        if _failsafe_listener is not None:
            return

        def on_press(key):
            if key == keyboard.Key.esc:
                for running in list(_jobs.values()):
                    running.cancel()

        _failsafe_listener = keyboard.Listener(on_press=on_press)
        _failsafe_listener.daemon = True
        _failsafe_listener.start()


def prepare_onenote() -> bool:
    """Bring OneNote to foreground, maximize and apply known zoom sequence."""
    if not HAS_NATIVE_EVENTS or win32gui is None:
        return False

    target_hwnd = None

    def _enum_handler(hwnd, _):
        nonlocal target_hwnd
        title = win32gui.GetWindowText(hwnd) or ""
        if win32gui.IsWindowVisible(hwnd) and "onenote" in title.lower():
            target_hwnd = hwnd

    win32gui.EnumWindows(_enum_handler, None)
    if not target_hwnd:
        return False

    try:
        win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
        win32gui.ShowWindow(target_hwnd, win32con.SW_MAXIMIZE)
        win32gui.SetForegroundWindow(target_hwnd)
        time.sleep(0.25)

        # OneNote Zoom/Reset Sequence
        _send_hotkey([win32con.VK_MENU], ord("F"))
        time.sleep(0.06)
        _send_key(ord("1"))
        time.sleep(0.06)
        _send_key(ord("O"))
        time.sleep(0.06)
        _type_text("100")
        time.sleep(0.04)
        _send_key(win32con.VK_RETURN)
        time.sleep(0.35)

        _send_hotkey([win32con.VK_MENU], ord("H"))
        time.sleep(0.06)
        _send_key(ord("F"))
        time.sleep(0.06)
        _send_key(ord("1"))
        time.sleep(0.2)
    except Exception:
        return False
    return True


def _send_hotkey(modifiers: list[int], key: int):
    for mod in modifiers:
        win32api.keybd_event(mod, 0, 0, 0)
    win32api.keybd_event(key, 0, 0, 0)
    win32api.keybd_event(key, 0, win32con.KEYEVENTF_KEYUP, 0)
    for mod in reversed(modifiers):
        win32api.keybd_event(mod, 0, win32con.KEYEVENTF_KEYUP, 0)


def _send_key(key: int):
    win32api.keybd_event(key, 0, 0, 0)
    win32api.keybd_event(key, 0, win32con.KEYEVENTF_KEYUP, 0)


def _type_text(text: str):
    for ch in text:
        _send_key(ord(ch.upper()))


def _screen_metrics():
    if not HAS_NATIVE_EVENTS:
        return 0, 0, 1920, 1080
    vx = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN)
    vy = win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN)
    vw = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
    vh = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)
    return vx, vy, max(1, vw), max(1, vh)


def extract_stroke_path(image_path: str, target_w: int, target_h: int) -> list[tuple[int, int]]:
    try:
        img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
        if img is None:
            return _fallback_path(target_w, target_h)
        if len(img.shape) == 3 and img.shape[2] == 4:
            mask = img[:, :, 3]
        else:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, mask = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)

        points = _skeleton_to_path(_skeletonize((mask > 127).astype(np.uint8)))
        if len(points) < 2:
            return _fallback_path(target_w, target_h)

        h, w = mask.shape
        return [(int(x / w * target_w), int(y / h * target_h)) for x, y in points]
    except Exception:
        return _fallback_path(target_w, target_h)


def _skeletonize(binary_img):
    img = binary_img.copy()
    skeleton = np.zeros_like(img)
    kernel = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
    while True:
        eroded = cv2.erode(img, kernel)
        dilated = cv2.dilate(eroded, kernel)
        skeleton = cv2.bitwise_or(skeleton, cv2.subtract(img, dilated))
        img = eroded.copy()
        if cv2.countNonZero(img) == 0:
            break
    return skeleton


def _skeleton_to_path(skeleton):
    pts = [(c, r) for r, c in zip(*np.where(skeleton > 0))]
    # Basic sorting to keep stroke order somewhat sane
    pts.sort(key=lambda p: (p[0], p[1]))
    if len(pts) > 150:
        step = max(1, len(pts) // 150)
        pts = pts[::step]
    return pts


def _fallback_path(w, h):
    return [(w // 2, int(h * t)) for t in [i / 10 for i in range(11)]]


def _draw_stroke(
    job: WriteJob,
    points: list[tuple[int, int]],
    speed: str,
    translator: CoordinateTranslator,
    origin_x: int,
    origin_y: int,
    point_delay_s: float,
):
    if not points:
        return

    speed_mul = {"slow": 1.7, "normal": 1.0, "fast": 0.65}.get(speed, 1.0)
    base_delay = max(0.0005, point_delay_s * speed_mul)

    vx, vy, vw, vh = _screen_metrics()

    # Apply smoothing
    if len(points) >= 4:
        # Use Catmull-Rom for natural curvature
        smoothed_points = stroke_proc.get_catmull_rom_spline(points, num_points=5)
    else:
        # Simple subdivision for short strokes
        smoothed_points = stroke_proc.smooth_bezier(points, steps_per_segment=3)

    def to_win(px, py):
        tx, ty = translator.to_windows_coordinates(px, py)
        return translator.normalize_to_win_abs(tx, ty, vx, vy, vw, vh)

    # First point
    fx, fy = to_win(origin_x + smoothed_points[0][0], origin_y + smoothed_points[0][1])
    input_mgr.down(fx, fy)
    time.sleep(base_delay)

    for i in range(1, len(smoothed_points)):
        if job.cancelled:
            break
        px, py = smoothed_points[i]
        ax, ay = to_win(origin_x + px, origin_y + py)
        input_mgr.move_to(ax, ay)
        time.sleep(base_delay / 2.0)

    # Last point
    lx, ly = to_win(origin_x + smoothed_points[-1][0], origin_y + smoothed_points[-1][1])
    input_mgr.up(lx, ly)
    time.sleep(base_delay)


def write_text_to_screen(
    job: WriteJob,
    profile,
    calibration,
    text: str,
    speed: str = "normal",
    font_size_scale: float = 1.0,
    size_variation: float = 0.10,
    rotation_variation: float = 3.0,
    vertical_jitter: float = 2.0,
    point_delay_s: float = 0.005,
    pressure: float = 0.7,
):
    if not HAS_NATIVE_EVENTS:
        job.status = "error"
        job.message = "Native Win32 events not available."
        return

    try:
        job.status = "running"
        words = text.split()
        all_chars = [c for w in words for c in (list(w) + [" "])]
        job.chars_total = len(all_chars)

        translator = CoordinateTranslator(calibration)

        start_x = 0
        start_y = 0
        area_w = calibration.write_area_width
        line_h = int(calibration.line_height_px * font_size_scale)
        char_w = int(profile.avg_char_width * font_size_scale * calibration.zoom_level)
        space_w = int(char_w * 0.55)
        word_sp = int(profile.word_spacing * font_size_scale)

        cursor_x = start_x
        cursor_y = start_y
        job.current_line = 0
        job.message = "OneNote wird vorbereitet..."

        if not prepare_onenote():
            job.status = "error"
            job.message = "Fehler: OneNote-Fenster wurde nicht gefunden. Bitte OneNote öffnen!"
            return
        
        job.message = "OneNote bereit. Schreibe..."
        time.sleep(0.3)

        for word in words:
            job.wait_if_paused()
            if job.cancelled:
                break

            # Word width estimation
            ww = sum(
                (
                    (sum(v.width for v in profile.characters.get(c, [])) / max(len(profile.characters.get(c, [])), 1))
                    if profile.characters.get(c)
                    else profile.avg_char_width
                )
                * font_size_scale
                for c in word
            )

            if cursor_x > start_x and cursor_x + ww > start_x + area_w:
                cursor_x = start_x
                cursor_y += line_h
                job.current_line += 1

            for char in word:
                job.wait_if_paused()
                if job.cancelled:
                    break
                if char == " ":
                    cursor_x += space_w
                    job.chars_done += 1
                    continue

                variants = profile.characters.get(char, [])
                if not variants:
                    cursor_x += char_w
                    job.chars_done += 1
                    continue

                variant = random.choice(variants)
                scale = font_size_scale * random.uniform(1 - size_variation, 1 + size_variation)
                cw = int(variant.width * scale * calibration.zoom_level)
                ch = int(variant.height * scale * calibration.zoom_level)

                # Correctly define vy within the scope of the character processing
                char_v_jitter = int(random.uniform(-vertical_jitter, vertical_jitter))

                points = extract_stroke_path(variant.image_path, cw, ch)
                _draw_stroke(
                    job=job,
                    points=points,
                    speed=speed,
                    translator=translator,
                    origin_x=cursor_x,
                    origin_y=cursor_y + char_v_jitter,
                    point_delay_s=point_delay_s,
                )
                cursor_x += cw + int(profile.char_spacing * calibration.zoom_level)
                job.chars_done += 1
                job.progress = job.chars_done / max(job.chars_total, 1)

            cursor_x += word_sp
            time.sleep(max(0.001, point_delay_s * 2))

        job.status = "done" if not job.cancelled else "cancelled"
        job.message = "Fertig!" if not job.cancelled else "Abgebrochen"
    except Exception as exc:
        job.status = "error"
        job.message = f"Fehler: {exc}"
