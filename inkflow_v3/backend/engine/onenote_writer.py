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
    """Bring OneNote to foreground, maximize."""
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
        time.sleep(0.3)

        # User requested to remove the automated zoom typing as it interferes with textboxes.
        # We only keep the window activation.
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


def extract_stroke_paths(image_path: str, target_w: int, target_h: int) -> list[list[tuple[int, int]]]:
    """
    Extracts multiple strokes from a character image.
    Splits the path into separate strokes when a large gap is detected.
    """
    try:
        img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
        if img is None:
            return [_fallback_path(target_w, target_h)]

        if len(img.shape) == 3 and img.shape[2] == 4:
            mask = img[:, :, 3]
        else:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, mask = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)

        h, w = mask.shape
        raw_strokes = _skeleton_to_multi_strokes(_skeletonize((mask > 127).astype(np.uint8)))

        if not raw_strokes:
            return [_fallback_path(target_w, target_h)]

        # Map to target size
        final_strokes = []
        for stroke in raw_strokes:
            final_strokes.append([(int(x / w * target_w), int(y / h * target_h)) for x, y in stroke])

        return final_strokes
    except Exception:
        return [_fallback_path(target_w, target_h)]


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


def _skeleton_to_multi_strokes(skeleton):
    """
    Splits the skeleton into multiple strokes using a nearest-neighbor approach
    with a distance threshold.
    """
    pts = list(zip(*np.where(skeleton > 0)))
    if not pts: return []
    pts = [[c, r] for r, c in pts]

    strokes = []
    MAX_GAP = 12.0  # Pixels. If next point is further than this, start new stroke.

    while pts:
        # Start new stroke
        pts.sort(key=lambda p: (p[0], p[1]))
        current = pts.pop(0)
        current_stroke = [tuple(current)]

        while True:
            if not pts: break

            # Find nearest neighbor
            distances = [(p[0]-current[0])**2 + (p[1]-current[1])**2 for p in pts]
            idx = np.argmin(distances)
            dist = math.sqrt(distances[idx])

            if dist > MAX_GAP:
                # End of this stroke
                break

            current = pts.pop(idx)
            current_stroke.append(tuple(current))

        if len(current_stroke) > 1:
            # Downsample
            if len(current_stroke) > 100:
                step = len(current_stroke) // 100
                current_stroke = current_stroke[::step]
            strokes.append(current_stroke)

    return strokes


def _fallback_path(w, h):
    return [(w // 2, int(h * t)) for t in [i / 10 for i in range(11)]]


def _draw_strokes(
    job: WriteJob,
    strokes: list[list[tuple[int, int]]],
    speed: str,
    translator: CoordinateTranslator,
    origin_x: int,
    origin_y: int,
    point_delay_s: float,
):
    if not strokes: return

    speed_mul = {"slow": 1.7, "normal": 1.0, "fast": 0.65}.get(speed, 1.0)
    base_delay = max(0.0005, point_delay_s * speed_mul)
    vx, vy, vw, vh = _screen_metrics()

    def to_win(px, py):
        tx, ty = translator.to_windows_coordinates(px, py)
        return translator.normalize_to_win_abs(tx, ty, vx, vy, vw, vh)

    for stroke in strokes:
        if job.cancelled: break
        if not stroke: continue

        # Smoothing
        if len(stroke) >= 4:
            smoothed = stroke_proc.get_catmull_rom_spline(stroke, num_points=4)
        else:
            smoothed = stroke_proc.smooth_bezier(stroke, steps_per_segment=2)

        # Pen down
        fx, fy = to_win(origin_x + smoothed[0][0], origin_y + smoothed[0][1])
        input_mgr.down(fx, fy)
        time.sleep(base_delay)

        for i in range(1, len(smoothed)):
            if job.cancelled: break
            ax, ay = to_win(origin_x + smoothed[i][0], origin_y + smoothed[i][1])
            input_mgr.move_to(ax, ay)
            time.sleep(base_delay / 2.0)

        # Pen up
        lx, ly = to_win(origin_x + smoothed[-1][0], origin_y + smoothed[-1][1])
        input_mgr.up(lx, ly)
        time.sleep(base_delay * 1.5) # Small pause between strokes


DESCENDERS = set("gjpqyÖÄÜöäüß")

def _compute_baseline_offset(char: str, char_height: int, variant_baseline: int) -> int:
    if variant_baseline != 0:
        return variant_baseline
    if char in DESCENDERS:
        return -int(char_height * 0.25)
    return 0


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

        # Baseline and scaling fixes
        # Use calibration values to set the actual start position
        start_x = 0
        # Start at 0 relative to write_area_y (CoordinateTranslator handles write_area_y offset)
        start_y = 0
        area_w = calibration.write_area_width

        # Adjust scaling: The user reports it's 3x too large.
        # We also need to consider zoom_level.
        # Let's try a more conservative base scale and respect calibration.zoom_level
        effective_font_scale = (font_size_scale * 0.35) / max(0.1, calibration.zoom_level)

        line_h = int(calibration.line_height_px * font_size_scale)
        char_spacing = int(profile.char_spacing * calibration.zoom_level)
        word_sp = int(profile.word_spacing * effective_font_scale)

        cursor_x = start_x
        cursor_y = start_y
        job.current_line = 0
        job.message = "V3.2 Engine Ready. Writing..."

        if not prepare_onenote():
            job.status = "error"
            job.message = "OneNote window not found!"
            return
        
        time.sleep(0.3)

        for word in words:
            job.wait_if_paused()
            if job.cancelled: break

            # Word width estimate
            ww = 0
            for char in word:
                variants = profile.characters.get(char, [])
                if variants:
                    v = random.choice(variants)
                    ww += v.width * effective_font_scale + char_spacing
                else:
                    ww += profile.avg_char_width * effective_font_scale + char_spacing

            if cursor_x > start_x and cursor_x + ww > start_x + area_w:
                cursor_x = start_x
                cursor_y += line_h
                job.current_line += 1

            for char in word:
                job.wait_if_paused()
                if job.cancelled: break

                if char == " ":
                    cursor_x += int(profile.avg_char_width * effective_font_scale * 0.5)
                    job.chars_done += 1
                    continue

                variants = profile.characters.get(char, [])
                if not variants:
                    cursor_x += int(profile.avg_char_width * effective_font_scale)
                    job.chars_done += 1
                    continue

                variant = random.choice(variants)
                scale = effective_font_scale * random.uniform(1 - size_variation, 1 + size_variation)
                cw = int(variant.width * scale)
                ch = int(variant.height * scale)

                # Baseline logic
                baseline_y = cursor_y + line_h
                baseline_offset = _compute_baseline_offset(char, ch, variant.baseline_offset)
                y_pos = baseline_y - ch + baseline_offset

                char_v_jitter = int(random.uniform(-vertical_jitter, vertical_jitter))

                # Use pre-computed strokes if available for better movement reproduction
                if hasattr(variant, 'strokes') and variant.strokes:
                    # Scale strokes to target size
                    # variant.strokes are in pixels relative to the original variant image
                    sw, sh = variant.width, variant.height
                    strokes = []
                    for s in variant.strokes:
                        strokes.append([(int(x / sw * cw), int(y / sh * ch)) for x, y in s])
                else:
                    strokes = extract_stroke_paths(variant.image_path, cw, ch)

                _draw_strokes(
                    job=job,
                    strokes=strokes,
                    speed=speed,
                    translator=translator,
                    origin_x=cursor_x,
                    origin_y=y_pos + char_v_jitter,
                    point_delay_s=point_delay_s,
                )

                cursor_x += cw + char_spacing
                job.chars_done += 1
                job.progress = job.chars_done / max(job.chars_total, 1)

            cursor_x += word_sp
            time.sleep(max(0.001, point_delay_s))

        job.status = "done" if not job.cancelled else "cancelled"
        job.message = "Fertig!"
    except Exception as exc:
        job.status = "error"
        job.message = f"Error: {exc}"
