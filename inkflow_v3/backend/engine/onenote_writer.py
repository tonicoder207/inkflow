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
        if input_mgr.use_pen_injection:
            input_mgr.down(x, y, pressure=pressure)
        else:
            ax, ay = CoordinateTranslator.normalize_to_win_abs(x, y, vx, vy, vw, vh)
            input_mgr.down(ax, ay, pressure=pressure)

    def move(self, x: int, y: int, pressure: int = 512):
        vx, vy, vw, vh = _screen_metrics()
        if input_mgr.use_pen_injection:
            input_mgr.move_to(x, y, pressure=pressure)
        else:
            ax, ay = CoordinateTranslator.normalize_to_win_abs(x, y, vx, vy, vw, vh)
            input_mgr.move_to(ax, ay, pressure=pressure)

    def up(self, x: int, y: int):
        vx, vy, vw, vh = _screen_metrics()
        if input_mgr.use_pen_injection:
            input_mgr.up(x, y)
        else:
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
        time.sleep(0.2)
    except Exception:
        return False
    return True


def scroll_onenote(amount: int):
    """Scroll OneNote down using the mouse wheel."""
    if not HAS_NATIVE_EVENTS: return
    # MOUSEEVENTF_WHEEL takes dwData as the amount to scroll.
    # A positive value scrolls away from the user (up), negative scrolls towards (down).
    # OneNote typically needs -120 per notch.
    win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, amount, 0)


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
    with a distance threshold. Optimized for German dots and fine details.
    """
    pts = list(zip(*np.where(skeleton > 0)))
    if not pts: return []
    pts = [[c, r] for r, c in pts]

    strokes = []
    MAX_GAP = 8.0

    while pts:
        pts.sort(key=lambda p: (p[0], p[1]))
        current = pts.pop(0)
        current_stroke = [tuple(current)]

        while True:
            if not pts: break
            sq_distances = [(p[0]-current[0])**2 + (p[1]-current[1])**2 for p in pts]
            idx = np.argmin(sq_distances)
            dist = math.sqrt(sq_distances[idx])
            if dist > MAX_GAP: break
            current = pts.pop(idx)
            current_stroke.append(tuple(current))

        if len(current_stroke) >= 1:
            if len(current_stroke) > 80:
                step = len(current_stroke) // 80
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
    pressure_base: int = 512,
):
    if not strokes: return

    # Ultra-Turbo speed multipliers: almost no delay
    speed_mul = {"slow": 0.5, "normal": 0.1, "fast": 0.001}.get(speed, 1.0)
    base_delay = point_delay_s * speed_mul
    vx, vy, vw, vh = _screen_metrics()

    def get_coords(px, py):
        tx, ty = translator.to_windows_coordinates(px, py)
        if input_mgr.use_pen_injection:
            return int(tx), int(ty)
        return translator.normalize_to_win_abs(tx, ty, vx, vy, vw, vh)

    for stroke in strokes:
        if job.cancelled: break
        if not stroke: continue

        # Human-like smoothing but with minimal points for speed
        if len(stroke) >= 4:
            smoothed = stroke_proc.get_catmull_rom_spline(stroke, num_points=3)
        else:
            smoothed = stroke_proc.smooth_bezier(stroke, steps_per_segment=2)

        # Pen down
        fx, fy = get_coords(origin_x + smoothed[0][0], origin_y + smoothed[0][1])
        input_mgr.down(fx, fy, pressure=int(pressure_base * 0.7))
        if base_delay > 0.001: time.sleep(base_delay)

        for i in range(1, len(smoothed)):
            if job.cancelled: break
            ax, ay = get_coords(origin_x + smoothed[i][0], origin_y + smoothed[i][1])

            # Simple pressure variation without expensive math
            curr_p = pressure_base if i % 2 == 0 else int(pressure_base * 1.1)
            input_mgr.move_to(ax, ay, pressure=curr_p)

            # Ultra-low delay
            if base_delay > 0.0001: time.sleep(base_delay / 4.0)

        # Pen up
        lx, ly = get_coords(origin_x + smoothed[-1][0], origin_y + smoothed[-1][1])
        input_mgr.up(lx, ly)
        if base_delay > 0.001: time.sleep(base_delay)


# Characters that extend BELOW the baseline
DESCENDERS = set("gjpqyß")

def _compute_baseline_offset(char: str, char_height: int, variant_baseline: int) -> int:
    """
    Returns the vertical pixel adjustment to align characters.
    - variant_baseline: stored offset from manual calibration (if any)
    - descenders: move DOWN (positive Y)
    """
    if variant_baseline != 0:
        return variant_baseline
    if char in DESCENDERS:
        # Move down by ~22% of height to place the descender below the baseline
        return int(char_height * 0.22)
    return 0


def write_text_to_screen(
    job: WriteJob,
    profile,
    calibration,
    text: str,
    speed: str = "normal",
    font_size_scale: float = 1.0,
    size_variation: float = 0.05,
    rotation_variation: float = 1.0,
    vertical_jitter: float = 0.5,
    point_delay_s: float = 0.001,
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

        # Alignment logic
        line_top = getattr(calibration, "line_top_offset", 0)
        start_x = 0
        start_y = line_top
        area_w = calibration.write_area_width
        area_h = calibration.write_area_height

        # Scaling adjustment
        effective_font_scale = (font_size_scale * 0.32) / max(0.1, calibration.zoom_level)
        line_h = int(calibration.line_height_px * font_size_scale)

        # Spacing
        char_spacing_base = int(profile.char_spacing * calibration.zoom_level)
        word_sp = int(profile.word_spacing * effective_font_scale)

        cursor_x = start_x
        cursor_y = start_y
        job.current_line = 0
        job.message = "Engine V4.2 (Turbo-Fluid) - Writing..."

        if not prepare_onenote():
            job.status = "error"
            job.message = "OneNote window not found!"
            return
        
        time.sleep(0.1)

        # Scroll threshold: vorvorletzte Zeile (e.g., around 75-80% of area height)
        scroll_threshold_y = area_h * 0.75

        last_focus_check = time.time()

        for word in words:
            job.wait_if_paused()
            if job.cancelled: break

            # Slipping Prevention: Periodic Focus Check
            if time.time() - last_focus_check > 2.0:
                curr_hwnd = win32gui.GetForegroundWindow()
                title = win32gui.GetWindowText(curr_hwnd).lower()
                if "onenote" not in title:
                    job.message = "Focus lost! Pausing..."
                    job.pause()
                    # User will need to resume after focusing OneNote
                last_focus_check = time.time()

            # Word width estimate
            ww = 0
            for char in word:
                variants = profile.characters.get(char, [])
                if variants:
                    v = random.choice(variants)
                    ww += v.width * effective_font_scale + char_spacing_base
                else:
                    ww += profile.avg_char_width * effective_font_scale + char_spacing_base

            if cursor_x > start_x and cursor_x + ww > start_x + area_w:
                cursor_x = start_x
                cursor_y += line_h
                job.current_line += 1

                # Check for auto-scroll
                if cursor_y > scroll_threshold_y:
                    job.message = "Auto-Scrolling..."
                    # Scroll down by roughly one line height in pixels (negative value)
                    scroll_onenote(-120)
                    time.sleep(0.2)
                    # Adjust cursor_y back up to stay on the same "relative" line on screen
                    cursor_y -= line_h
                    job.message = "Engine V4.2 (Turbo-Fluid) - Writing..."

            for char in word:
                job.wait_if_paused()
                if job.cancelled: break

                if char == " ":
                    cursor_x += int(profile.avg_char_width * effective_font_scale * 0.6)
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

                # Use pre-computed strokes
                if hasattr(variant, 'strokes') and variant.strokes:
                    sw, sh = variant.width, variant.height
                    strokes = [[(int(x / sw * cw), int(y / sh * ch)) for x, y in s] for s in variant.strokes]
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
                    pressure_base=int(pressure * 1024),
                )

                cursor_x += cw + char_spacing_base + int(random.uniform(0, 1))
                job.chars_done += 1
                job.progress = job.chars_done / max(job.chars_total, 1)

            cursor_x += word_sp

        job.status = "done" if not job.cancelled else "cancelled"
        job.message = "Turbo-Finish!"
    except Exception as exc:
        job.status = "error"
        job.message = f"Error: {exc}"
