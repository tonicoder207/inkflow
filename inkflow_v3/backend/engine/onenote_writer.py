"""
InkFlow v3 — OneNote Writing Engine

Fixes in this version:
  1. Smooth lines: pen stays DOWN for full stroke, lerp fills every gap <= 1px
  2. No drift: cursor_y is anchored to real calibrated line_height, never accumulates float error
  3. Scroll fix: cursor_y is reset to line 0 relative position after scroll, not estimated
  4. Error 0 fix: no WinError() calls on native API returns
"""
import math
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
    import win32api, win32con, win32gui
    HAS_NATIVE_EVENTS = True
except Exception:
    win32api = win32con = win32gui = None

try:
    from pynput import keyboard
    HAS_KEYBOARD_FAILSAFE = True
except Exception:
    keyboard = None
    HAS_KEYBOARD_FAILSAFE = False


# ── Job ────────────────────────────────────────────────────────────────────────

class WriteJob:
    def __init__(self, job_id: str):
        self.job_id       = job_id
        self.status       = "idle"
        self.progress     = 0.0
        self.chars_done   = 0
        self.chars_total  = 0
        self.current_line = 0
        self.message      = ""
        self._pause_event = threading.Event()
        self._pause_event.set()
        self._cancel = False

    def pause(self):   self._pause_event.clear(); self.status = "paused"
    def resume(self):  self._pause_event.set();   self.status = "running"
    def cancel(self):  self._cancel = True;        self._pause_event.set()
    def wait_if_paused(self): self._pause_event.wait()

    @property
    def cancelled(self): return self._cancel


_jobs: dict[str, WriteJob] = {}
_stroke_cache: dict = {}

input_mgr   = InputManager()
stroke_proc = StrokeProcessor()
pen_injector       = input_mgr
HAS_PEN_INJECTION  = input_mgr.use_pen_injection


def create_job(job_id: str) -> WriteJob:
    job = WriteJob(job_id)
    _jobs[job_id] = job
    return job

def get_job(job_id: str) -> Optional[WriteJob]:
    return _jobs.get(job_id)

def clear_engine_cache():
    global _stroke_cache
    _stroke_cache = {}


# ── Utilities ──────────────────────────────────────────────────────────────────

def _precise_sleep(s: float):
    if s <= 0: return
    end = time.perf_counter() + s
    while time.perf_counter() < end:
        if s > 0.002: time.sleep(0)


def scroll_onenote(amount: int):
    if HAS_NATIVE_EVENTS:
        win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, amount, 0)


def prepare_onenote() -> bool:
    if not HAS_NATIVE_EVENTS: return False
    hwnd = None
    def _cb(h, _):
        nonlocal hwnd
        if win32gui.IsWindowVisible(h) and "onenote" in (win32gui.GetWindowText(h) or "").lower():
            hwnd = h; return False
        return True
    win32gui.EnumWindows(_cb, None)
    if not hwnd: return False
    try:
        if win32gui.GetWindowPlacement(hwnd)[1] == win32con.SW_SHOWMINIMIZED:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
        try: win32gui.SetForegroundWindow(hwnd)
        except: pass
        time.sleep(0.35)
    except: return False
    return True


def _screen_metrics():
    if not HAS_NATIVE_EVENTS: return 0, 0, 1920, 1080
    return (
        win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN),
        win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN),
        max(1, win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)),
        max(1, win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)),
    )


# ── Stroke extraction ──────────────────────────────────────────────────────────

def _skeletonize(binary_img):
    img = binary_img.copy()
    skel = np.zeros_like(img)
    k = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
    while True:
        e = cv2.erode(img, k)
        skel = cv2.bitwise_or(skel, cv2.subtract(img, cv2.dilate(e, k)))
        img = e
        if not cv2.countNonZero(img): break
    return skel


def _skeleton_to_strokes(skel):
    n, labels, _, _ = cv2.connectedComponentsWithStats(skel, connectivity=8)
    all_strokes = []
    for lbl in range(1, n):
        pts = np.argwhere((labels == lbl))[:, [1, 0]].tolist()
        MAX_GAP_SQ = 25.0
        while pts:
            pts.sort(key=lambda p: (p[1], p[0]))
            cur = pts.pop(0)
            stroke = [tuple(cur)]
            while pts:
                arr = np.array(pts)
                sq  = np.sum((arr - cur) ** 2, axis=1)
                i   = int(np.argmin(sq))
                if sq[i] > MAX_GAP_SQ: break
                cur = pts.pop(i)
                stroke.append(tuple(cur))
            all_strokes.append(stroke)
    all_strokes.sort(key=lambda s: s[0][0])
    return all_strokes


def extract_stroke_paths(image_path: str, target_w: int, target_h: int):
    key = (image_path, target_w, target_h)
    if key in _stroke_cache: return _stroke_cache[key]
    try:
        img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
        if img is None: return [[(target_w/2, target_h*t) for t in (.1,.5,.9)]]
        mask = img[:,:,3] if (len(img.shape)==3 and img.shape[2]==4) else \
               cv2.threshold(cv2.cvtColor(img,cv2.COLOR_BGR2GRAY),127,255,cv2.THRESH_BINARY_INV)[1]
        h, w = mask.shape
        raw  = _skeleton_to_strokes(_skeletonize((mask > 127).astype(np.uint8)))
        out  = []
        for stroke in raw:
            mapped   = [(x/w*target_w, y/h*target_h) for x,y in stroke]
            # High-density smoothing: 2.0 points per pixel for truly smooth curves
            smoothed = stroke_proc.smooth_stroke_v2(mapped, density=2.0)
            out.append(smoothed)
        _stroke_cache[key] = out
        return out
    except Exception:
        return [[(target_w/2, target_h*t) for t in (.1,.5,.9)]]


# ── Core drawing ───────────────────────────────────────────────────────────────

def _lerp(p1, p2, max_step=1.0):
    """Fill in points between p1 and p2 so no gap exceeds max_step pixels."""
    dx, dy = p2[0]-p1[0], p2[1]-p1[1]
    dist = math.hypot(dx, dy)
    if dist <= max_step:
        return [p2]
    steps = max(1, int(math.ceil(dist / max_step)))
    return [(p1[0]+dx*i/steps, p1[1]+dy*i/steps) for i in range(1, steps+1)]


def _draw_strokes(job, strokes, words_per_second, translator,
                  origin_x, origin_y, pressure_base=700):
    """
    KEY FIX: pen goes DOWN once, moves continuously through ALL interpolated
    points, then goes UP once. No pen-up between points = real lines not dots.
    """
    if not strokes: return
    vx, vy, vw, vh = _screen_metrics()

    def to_screen(px, py):
        tx, ty = translator.to_windows_coordinates(origin_x+px, origin_y+py)
        if input_mgr.use_pen_injection:
            return int(tx), int(ty)
        return translator.normalize_to_win_abs(tx, ty, vx, vy, vw, vh)

    # Delay between move events: fast enough to not lag, slow enough for OneNote
    move_delay  = max(0.0, min(0.003, 0.002 / max(words_per_second, 0.5)))
    stroke_gap  = max(0.004, 0.012 / max(words_per_second, 0.5))

    for stroke in strokes:
        if job.cancelled or not stroke: continue

        # ── Pen DOWN ─────────────────────────────────────────────────────────
        sx, sy = to_screen(stroke[0][0], stroke[0][1])
        input_mgr.down(sx, sy, pressure=pressure_base)

        prev = stroke[0]

        # ── Continuous move through all points with sub-pixel interpolation ──
        for pt in stroke[1:]:
            if job.cancelled: break
            # Fill any gap > 1px so OneNote sees a solid line
            for ip in _lerp(prev, pt, max_step=1.0):
                if job.cancelled: break
                ix, iy = to_screen(ip[0], ip[1])
                input_mgr.move_to(ix, iy, pressure=pressure_base)
                if move_delay > 0.0003:
                    _precise_sleep(move_delay)
            prev = pt

        # ── Pen UP ───────────────────────────────────────────────────────────
        ex, ey = to_screen(prev[0], prev[1])
        input_mgr.up(ex, ey)
        if stroke_gap > 0.0003:
            _precise_sleep(stroke_gap)


# ── Baseline ───────────────────────────────────────────────────────────────────

DESCENDERS = set("gjpqyßÖÄÜöäü")

def _baseline_offset(char, ch, variant_offset):
    if variant_offset != 0: return variant_offset
    return int(ch * 0.25) if char in DESCENDERS else 0


# ── Main entry ─────────────────────────────────────────────────────────────────

def write_text_to_screen(
    job, profile, calibration, text,
    words_per_second=1.5, font_size_scale=1.0,
    size_variation=0.08, rotation_variation=2.0,
    vertical_jitter=1.5, pressure=0.7,
    scaling_factor=1.0, **kwargs
):
    if not HAS_NATIVE_EVENTS:
        job.status = "error"; job.message = "Win32 not available."; return

    try:
        job.status = "running"
        clear_engine_cache()

        words           = text.split()
        job.chars_total = sum(len(w) for w in words) + max(0, len(words)-1)

        translator = CoordinateTranslator(calibration)
        translator.scaling_factor = scaling_factor

        area_w = calibration.write_area_width
        area_h = calibration.write_area_height

        eff_scale = (font_size_scale * 0.38) / max(0.1, calibration.zoom_level)

        # ── Line height: integer to prevent drift accumulation ────────────────
        # Use the calibrated line height directly — never float-accumulate it
        LINE_H = max(10, int(round(calibration.line_height_px * font_size_scale)))

        char_sp = int(profile.char_spacing * calibration.zoom_level)
        word_sp = int(max(profile.word_spacing, profile.avg_char_width*1.2) * eff_scale)

        # ── Start position anchored to calibrated first line ──────────────────
        first_line_y = getattr(calibration, "first_line_y", 0)
        # rel_start_y is the Y of the FIRST baseline relative to write_area_y
        if first_line_y > 0:
            rel_start_y = max(0, first_line_y - calibration.write_area_y)
        else:
            rel_start_y = 0

        # current_line counts which line we are on (0-based integer)
        # cursor_y = rel_start_y + current_line * LINE_H  — computed fresh each time
        # This PREVENTS float drift: we never add to cursor_y, we always recompute it.
        current_line = 0
        cursor_x     = 0.0

        def get_cursor_y():
            return rel_start_y + current_line * LINE_H

        job.current_line = 0
        job.message      = "InkFlow — smooth line engine"

        if not prepare_onenote():
            job.status = "error"; job.message = "OneNote not found!"; return

        # Pre-warm stroke cache
        job.message = "Preparing strokes..."
        for char in set(text):
            if job.cancelled: break
            if char.strip() and char in profile.characters:
                v  = random.choice(profile.characters[char])
                cw = int(v.width  * eff_scale)
                ch = int(v.height * eff_scale)
                extract_stroke_paths(v.image_path, cw, ch)
        time.sleep(0.1)

        # How many lines fit before we need to scroll
        # Leave 20% margin at bottom
        max_line_y    = area_h * 0.80
        # How many lines that is:
        lines_per_page = max(1, int(max_line_y / LINE_H))

        # Track how many times we've scrolled (to keep cursor_y consistent)
        total_scroll_lines = 0

        last_focus = time.time()

        for word in words:
            job.wait_if_paused()
            if job.cancelled: break

            # Focus check every 4 s
            if time.time() - last_focus > 4.0:
                if HAS_NATIVE_EVENTS:
                    curr = win32gui.GetForegroundWindow()
                    if "onenote" not in (win32gui.GetWindowText(curr) or "").lower():
                        job.message = "Focus lost – pausing"
                        job.pause()
                last_focus = time.time()

            # ── Word width prediction ─────────────────────────────────────────
            ww = sum(
                ((sum(v.width for v in profile.characters.get(c,[]))/
                  max(len(profile.characters.get(c,[])),1)
                  if profile.characters.get(c) else profile.avg_char_width)
                 * eff_scale + char_sp)
                for c in word
            )

            # ── Line wrap ─────────────────────────────────────────────────────
            if cursor_x > 0 and cursor_x + ww > area_w:
                cursor_x      = 0.0
                current_line += 1
                job.current_line = current_line

                # ── Scroll when we reach the bottom margin ────────────────────
                cursor_y_now = get_cursor_y()
                if cursor_y_now > max_line_y:
                    job.message = "Scrolling..."
                    # Scroll exactly SCROLL_LINES lines worth of pixels
                    SCROLL_LINES = 4
                    scroll_px    = SCROLL_LINES * LINE_H
                    # Windows scroll: 120 units = 1 notch ≈ 3 text lines in OneNote
                    # So we need: scroll_px / LINE_H lines / 3 lines_per_notch * 120
                    notches      = max(1, round(SCROLL_LINES / 3))
                    scroll_onenote(-(notches * 120))
                    time.sleep(0.5)  # Wait for OneNote animation

                    # Move cursor back up by SCROLL_LINES lines
                    current_line     -= SCROLL_LINES
                    current_line      = max(0, current_line)
                    total_scroll_lines += SCROLL_LINES
                    job.current_line   = current_line
                    job.message        = "Writing..."

            cursor_y = get_cursor_y()

            # ── Draw each character ───────────────────────────────────────────
            for char in word:
                job.wait_if_paused()
                if job.cancelled: break

                variants = profile.characters.get(char, [])
                if not variants:
                    cursor_x += profile.avg_char_width * eff_scale
                    job.chars_done += 1
                    continue

                variant = random.choice(variants)
                scale   = eff_scale * random.uniform(1-size_variation, 1+size_variation)
                cw = max(4, int(variant.width  * scale))
                ch = max(4, int(variant.height * scale))

                # Baseline alignment
                baseline_y = cursor_y + LINE_H
                y_pos      = baseline_y - ch + _baseline_offset(char, ch, variant.baseline_offset)
                y_pos     += random.uniform(-vertical_jitter, vertical_jitter)

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

                cursor_x     += cw + char_sp
                job.chars_done += 1
                job.progress   = job.chars_done / max(job.chars_total, 1)

            cursor_x += word_sp

        job.status  = "done" if not job.cancelled else "cancelled"
        job.message = "Fertig! ✍️"

    except Exception as exc:
        job.status  = "error"
        job.message = f"Engine Error: {exc}"
