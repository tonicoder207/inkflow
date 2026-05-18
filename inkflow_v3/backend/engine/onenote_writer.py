"""
InkFlow v3 — OneNote Writing Engine
Rewritten stroke engine: pen stays DOWN for the entire stroke,
moves smoothly between points — produces real lines, not dots.
"""
import math
import platform
import random
import threading
import time
from typing import Optional

import cv2
import numpy as np

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


# ── Job management ─────────────────────────────────────────────────────────────

class WriteJob:
    def __init__(self, job_id: str):
        self.job_id      = job_id
        self.status      = "idle"
        self.progress    = 0.0
        self.chars_done  = 0
        self.chars_total = 0
        self.current_line = 0
        self.message     = ""
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

input_mgr  = InputManager()
stroke_proc = StrokeProcessor()

pen_injector      = input_mgr
HAS_PEN_INJECTION = input_mgr.use_pen_injection

_stroke_cache: dict = {}


def create_job(job_id: str) -> WriteJob:
    job = WriteJob(job_id)
    _jobs[job_id] = job
    return job


def get_job(job_id: str) -> Optional[WriteJob]:
    return _jobs.get(job_id)


def clear_engine_cache():
    global _stroke_cache
    _stroke_cache = {}


# ── Helpers ────────────────────────────────────────────────────────────────────

def _precise_sleep(duration: float):
    if duration <= 0:
        return
    end = time.perf_counter() + duration
    while time.perf_counter() < end:
        if duration > 0.002:
            time.sleep(0)


def scroll_onenote(amount: int):
    if not HAS_NATIVE_EVENTS:
        return
    win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, amount, 0)


def prepare_onenote() -> bool:
    if not HAS_NATIVE_EVENTS or win32gui is None:
        return False
    target_hwnd = None

    def _enum(hwnd, _):
        nonlocal target_hwnd
        title = win32gui.GetWindowText(hwnd) or ""
        if win32gui.IsWindowVisible(hwnd) and "onenote" in title.lower():
            target_hwnd = hwnd
            return False
        return True

    win32gui.EnumWindows(_enum, None)
    if not target_hwnd:
        return False
    try:
        placement = win32gui.GetWindowPlacement(target_hwnd)
        if placement[1] == win32con.SW_SHOWMINIMIZED:
            win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
        win32gui.ShowWindow(target_hwnd, win32con.SW_SHOW)
        try:
            win32gui.SetForegroundWindow(target_hwnd)
        except Exception:
            pass
        time.sleep(0.3)
    except Exception:
        return False
    return True


def _screen_metrics():
    if not HAS_NATIVE_EVENTS:
        return 0, 0, 1920, 1080
    vx = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN)
    vy = win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN)
    vw = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
    vh = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)
    return vx, vy, max(1, vw), max(1, vh)


# ── Stroke extraction ──────────────────────────────────────────────────────────

def _skeletonize(binary_img):
    img = binary_img.copy()
    skeleton = np.zeros_like(img)
    kernel = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
    while True:
        eroded  = cv2.erode(img, kernel)
        dilated = cv2.dilate(eroded, kernel)
        skeleton = cv2.bitwise_or(skeleton, cv2.subtract(img, dilated))
        img = eroded.copy()
        if cv2.countNonZero(img) == 0:
            break
    return skeleton


def _skeleton_to_multi_strokes(skeleton):
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(
        skeleton, connectivity=8
    )
    all_strokes = []
    for label in range(1, num_labels):
        comp_mask = (labels == label).astype(np.uint8)
        pts = np.argwhere(comp_mask > 0)
        if pts.size == 0:
            continue
        pts = pts[:, [1, 0]].tolist()  # (x, y)
        MAX_GAP = 5.0
        while pts:
            pts.sort(key=lambda p: (p[1], p[0]))
            current = pts.pop(0)
            stroke  = [tuple(current)]
            while True:
                if not pts:
                    break
                arr   = np.array(pts)
                diffs = arr - current
                sqdst = np.sum(diffs ** 2, axis=1)
                idx   = int(np.argmin(sqdst))
                if sqdst[idx] > MAX_GAP ** 2:
                    break
                current = pts.pop(idx)
                stroke.append(tuple(current))
            if stroke:
                all_strokes.append(stroke)
    all_strokes.sort(key=lambda s: s[0][0])
    return all_strokes


def extract_stroke_paths(
    image_path: str, target_w: int, target_h: int
) -> list[list[tuple[float, float]]]:
    cache_key = (image_path, target_w, target_h)
    if cache_key in _stroke_cache:
        return _stroke_cache[cache_key]

    try:
        img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
        if img is None:
            return [[(target_w / 2, target_h * t) for t in (0.1, 0.5, 0.9)]]

        if len(img.shape) == 3 and img.shape[2] == 4:
            mask = img[:, :, 3]
        else:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, mask = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)

        h, w = mask.shape
        raw_strokes = _skeleton_to_multi_strokes(
            _skeletonize((mask > 127).astype(np.uint8))
        )

        final_strokes = []
        for stroke in raw_strokes:
            mapped   = [(x / w * target_w, y / h * target_h) for x, y in stroke]
            smoothed = stroke_proc.smooth_stroke_v2(mapped, density=1.5)
            final_strokes.append(smoothed)

        _stroke_cache[cache_key] = final_strokes
        return final_strokes

    except Exception:
        return [[(target_w / 2, target_h * t) for t in (0.1, 0.5, 0.9)]]


# ── Core drawing: ONE continuous stroke per path ───────────────────────────────

def _lerp_points(
    p1: tuple[float, float],
    p2: tuple[float, float],
    max_step_px: float = 2.0,
) -> list[tuple[float, float]]:
    """
    Return intermediate points between p1 and p2 so that no gap is larger
    than max_step_px pixels.  This is what turns dots into solid lines.
    """
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    dist = math.hypot(dx, dy)
    if dist <= max_step_px:
        return [p2]
    steps = max(1, int(math.ceil(dist / max_step_px)))
    result = []
    for i in range(1, steps + 1):
        t = i / steps
        result.append((p1[0] + dx * t, p1[1] + dy * t))
    return result


def _draw_strokes(
    job: WriteJob,
    strokes: list[list[tuple[float, float]]],
    words_per_second: float,
    translator: CoordinateTranslator,
    origin_x: float,
    origin_y: float,
    pressure_base: int = 700,
):
    """
    Draw every stroke as a CONTINUOUS pen movement:
      pen_down → move → move → … → pen_up

    The pen NEVER lifts between points inside a stroke.
    Inter-point gaps are filled by linear interpolation so OneNote
    sees a smooth line, not individual dots.
    """
    if not strokes:
        return

    vx, vy, vw, vh = _screen_metrics()

    def to_screen(px: float, py: float):
        tx, ty = translator.to_windows_coordinates(
            origin_x + px, origin_y + py
        )
        if input_mgr.use_pen_injection:
            return int(tx), int(ty)
        return translator.normalize_to_win_abs(tx, ty, vx, vy, vw, vh)

    # Delay between individual move events (keeps CPU reasonable, still smooth)
    # At 3 w/s this is ~1 ms; at 1 w/s ~3 ms — fast enough for OneNote.
    move_delay   = max(0.0, 0.003 / max(words_per_second, 0.1))
    stroke_gap   = max(0.005, 0.015 / max(words_per_second, 0.1))

    for stroke in strokes:
        if job.cancelled:
            break
        if len(stroke) < 1:
            continue

        # ── Pen DOWN at first point ────────────────────────────────────────
        sx, sy = to_screen(stroke[0][0], stroke[0][1])
        input_mgr.down(sx, sy, pressure=pressure_base)

        prev = stroke[0]

        # ── Move through all remaining points, interpolating gaps ──────────
        for point in stroke[1:]:
            if job.cancelled:
                break

            # Fill in any gap between prev and point
            interp = _lerp_points(prev, point, max_step_px=1.5)
            for ip in interp:
                if job.cancelled:
                    break
                ix, iy = to_screen(ip[0], ip[1])
                input_mgr.move_to(ix, iy, pressure=pressure_base)
                if move_delay > 0.0005:
                    _precise_sleep(move_delay)

            prev = point

        # ── Pen UP at last point ───────────────────────────────────────────
        ex, ey = to_screen(prev[0], prev[1])
        input_mgr.up(ex, ey)

        # Brief pause between separate strokes (e.g. dot of an 'i')
        if stroke_gap > 0.0005:
            _precise_sleep(stroke_gap)


# ── Baseline helpers ───────────────────────────────────────────────────────────

DESCENDERS = set("gjpqyßÖÄÜöäü")


def _compute_baseline_offset(char: str, char_height: int, variant_baseline: int) -> int:
    if variant_baseline != 0:
        return variant_baseline
    if char in DESCENDERS:
        return int(char_height * 0.25)
    return 0


# ── Main writing function ──────────────────────────────────────────────────────

def write_text_to_screen(
    job: WriteJob,
    profile,
    calibration,
    text: str,
    words_per_second: float = 1.5,
    font_size_scale: float  = 1.0,
    size_variation: float   = 0.08,
    rotation_variation: float = 2.0,
    vertical_jitter: float  = 1.5,
    pressure: float         = 0.7,
    scaling_factor: float   = 1.0,
    **kwargs,
):
    if not HAS_NATIVE_EVENTS:
        job.status  = "error"
        job.message = "Native Win32 events not available."
        return

    try:
        job.status = "running"
        clear_engine_cache()

        words            = text.split()
        job.chars_total  = sum(len(w) for w in words) + len(words) - 1

        translator = CoordinateTranslator(calibration)
        translator.scaling_factor = scaling_factor

        area_w = calibration.write_area_width
        area_h = calibration.write_area_height

        effective_font_scale = (font_size_scale * 0.38) / max(0.1, calibration.zoom_level)
        line_h = int(calibration.line_height_px * font_size_scale)
        if line_h <= 0:
            line_h = 35

        char_spacing_base = int(profile.char_spacing * calibration.zoom_level)
        word_sp = int(
            max(profile.word_spacing, profile.avg_char_width * 1.2) * effective_font_scale
        )

        first_line_y = getattr(calibration, "first_line_y", 0)
        rel_start_y  = max(0, first_line_y - calibration.write_area_y) if first_line_y > 0 else 0

        cursor_x = 0.0
        cursor_y = float(rel_start_y - line_h)
        job.current_line = 0
        job.message      = "InkFlow Engine — smooth line mode"

        if not prepare_onenote():
            job.status  = "error"
            job.message = "OneNote window not found!"
            return

        # Pre-warm stroke cache for all unique characters
        job.message = "Preparing ink data..."
        for char in set(text):
            if job.cancelled:
                break
            if char.strip() and char in profile.characters:
                variants = profile.characters[char]
                v = random.choice(variants)
                cw = int(v.width  * effective_font_scale)
                ch = int(v.height * effective_font_scale)
                extract_stroke_paths(v.image_path, cw, ch)

        time.sleep(0.1)
        scroll_threshold_y = area_h * 0.80
        last_focus_check   = time.time()

        for word in words:
            job.wait_if_paused()
            if job.cancelled:
                break

            # Focus failsafe
            if time.time() - last_focus_check > 4.0:
                curr_hwnd = win32gui.GetForegroundWindow()
                if "onenote" not in win32gui.GetWindowText(curr_hwnd).lower():
                    job.message = "Focus lost! Pausing..."
                    job.pause()
                last_focus_check = time.time()

            # Word-wrap prediction
            ww = sum(
                (
                    (
                        sum(v.width for v in profile.characters.get(c, [])) /
                        max(len(profile.characters.get(c, [])), 1)
                        if profile.characters.get(c) else profile.avg_char_width
                    ) * effective_font_scale + char_spacing_base
                )
                for c in word
            )

            if cursor_x > 0 and cursor_x + ww > area_w:
                cursor_x  = 0.0
                cursor_y += line_h
                job.current_line += 1

                if cursor_y > scroll_threshold_y:
                    job.message = "Scrolling OneNote..."
                    scroll_onenote(-600)
                    time.sleep(0.4)
                    cursor_y -= line_h * 4
                    job.message = "Writing..."

            # Draw each character
            for char in word:
                job.wait_if_paused()
                if job.cancelled:
                    break

                variants = profile.characters.get(char, [])
                if not variants:
                    cursor_x += profile.avg_char_width * effective_font_scale
                    job.chars_done += 1
                    continue

                variant = random.choice(variants)
                scale   = effective_font_scale * random.uniform(
                    1 - size_variation, 1 + size_variation
                )
                cw = max(4, int(variant.width  * scale))
                ch = max(4, int(variant.height * scale))

                baseline_y = cursor_y + line_h
                baseline_offset = _compute_baseline_offset(
                    char, ch, variant.baseline_offset
                )
                y_pos = baseline_y - ch + baseline_offset
                y_pos += random.uniform(-vertical_jitter, vertical_jitter)

                strokes = extract_stroke_paths(variant.image_path, cw, ch)

                _draw_strokes(
                    job=job,
                    strokes=strokes,
                    words_per_second=words_per_second,
                    translator=translator,
                    origin_x=cursor_x,
                    origin_y=y_pos,
                    pressure_base=int(pressure * 1024),
                )

                cursor_x += cw + char_spacing_base
                job.chars_done += 1
                job.progress    = job.chars_done / max(job.chars_total, 1)

            cursor_x += word_sp

        job.status  = "done" if not job.cancelled else "cancelled"
        job.message = "Finished! ✍️"

    except Exception as exc:
        job.status  = "error"
        job.message = f"Engine Error: {exc}"
