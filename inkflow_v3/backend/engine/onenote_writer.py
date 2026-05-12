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

# Aliases for API compatibility
pen_injector = input_mgr
HAS_PEN_INJECTION = input_mgr.use_pen_injection

def create_job(job_id: str) -> WriteJob:
    job = WriteJob(job_id)
    _jobs[job_id] = job
    return job

def get_job(job_id: str) -> Optional[WriteJob]:
    return _jobs.get(job_id)

# Memory Cache for strokes to avoid repeated skeletonization/smoothing
_stroke_cache = {}

def clear_engine_cache():
    global _stroke_cache
    _stroke_cache = {}

def _precise_sleep(duration):
    """High-resolution sleep."""
    if duration <= 0: return
    end_time = time.perf_counter() + duration
    while time.perf_counter() < end_time:
        if duration > 0.001:
            time.sleep(0) # Yield for OS efficiency if delay is long
        pass


def scroll_onenote(amount: int):
    """Scroll OneNote using the mouse wheel. amount in notches (-120 = one notch down)"""
    if not HAS_NATIVE_EVENTS: return
    # Send wheel event
    win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, amount, 0)


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
            return False # Stop searching
        return True

    win32gui.EnumWindows(_enum_handler, None)
    if not target_hwnd:
        return False

    try:
        # Restore if minimized
        placement = win32gui.GetWindowPlacement(target_hwnd)
        if placement[1] == win32con.SW_SHOWMINIMIZED:
            win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
        
        win32gui.ShowWindow(target_hwnd, win32con.SW_SHOW)
        
        try:
            win32gui.SetForegroundWindow(target_hwnd)
        except Exception:
            # If foregrounding fails, we still continue since we have the handle
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


def _skeleton_to_multi_strokes(skeleton):
    num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(skeleton, connectivity=8)
    all_strokes = []
    for label in range(1, num_labels):
        comp_mask = (labels == label).astype(np.uint8)
        pts = np.argwhere(comp_mask > 0)
        if pts.size == 0: continue
        pts = pts[:, [1, 0]].tolist()
        MAX_GAP = 5.0
        while pts:
            pts.sort(key=lambda p: (p[1], p[0]))
            current = pts.pop(0)
            current_stroke = [tuple(current)]
            while True:
                if not pts: break
                pts_arr = np.array(pts)
                diffs = pts_arr - current
                sq_dists = np.sum(diffs**2, axis=1)
                idx = np.argmin(sq_dists)
                if sq_dists[idx] > MAX_GAP**2: break
                current = pts.pop(idx)
                current_stroke.append(tuple(current))
            if len(current_stroke) >= 1:
                all_strokes.append(current_stroke)
    all_strokes.sort(key=lambda s: s[0][0])
    return all_strokes


def _skeletonize(binary_img):
    img = binary_img.copy()
    skeleton = np.zeros_like(img)
    kernel = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3))
    while True:
        eroded = cv2.erode(img, kernel)
        dilated = cv2.dilate(eroded, kernel)
        skeleton = cv2.bitwise_or(skeleton, cv2.subtract(img, dilated))
        img = eroded.copy()
        if cv2.countNonZero(img) == 0: break
    return skeleton


def extract_stroke_paths(image_path: str, target_w: int, target_h: int) -> list[list[tuple[int, int]]]:
    cache_key = (image_path, target_w, target_h)
    if cache_key in _stroke_cache: return _stroke_cache[cache_key]

    try:
        img = cv2.imread(image_path, cv2.IMREAD_UNCHANGED)
        if img is None: return [[(target_w // 2, int(target_h * t)) for t in [0.1, 0.5, 0.9]]]
        if len(img.shape) == 3 and img.shape[2] == 4: mask = img[:, :, 3]
        else:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            _, mask = cv2.threshold(gray, 127, 255, cv2.THRESH_BINARY_INV)
        
        h, w = mask.shape
        raw_strokes = _skeleton_to_multi_strokes(_skeletonize((mask > 127).astype(np.uint8)))
        
        final_strokes = []
        for stroke in raw_strokes:
            mapped = [(int(x / w * target_w), int(y / h * target_h)) for x, y in stroke]
            # LIQUID INK SMOOTHING
            smoothed = stroke_proc.smooth_stroke_v2(mapped, density=0.8)
            final_strokes.append(smoothed)

        _stroke_cache[cache_key] = final_strokes
        return final_strokes
    except Exception:
        return [[(target_w // 2, int(target_h * t)) for t in [0.1, 0.5, 0.9]]]


def _draw_strokes(
    job: WriteJob,
    strokes: list[list[tuple[int, int]]],
    words_per_second: float,
    translator: CoordinateTranslator,
    origin_x: int,
    origin_y: int,
    pressure_base: int = 700,
):
    if not strokes: return
    vx, vy, vw, vh = _screen_metrics()

    def get_coords(px, py):
        tx, ty = translator.to_windows_coordinates(px, py)
        if input_mgr.use_pen_injection: return int(tx), int(ty)
        return translator.normalize_to_win_abs(tx, ty, vx, vy, vw, vh)

    # V3.1 DYNAMIC TIMING
    is_ultra = words_per_second >= 3.5
    
    # Calculate base delays
    # Normal mode needs some delay for "feel", Ultra mode needs minimal delay
    move_delay = 0 if is_ultra else (0.005 / words_per_second)
    stroke_gap = 0.002 if is_ultra else (0.012 / words_per_second)

    for stroke in strokes:
        if job.cancelled: break
        if not stroke: continue

        # Pen down
        fx, fy = get_coords(origin_x + stroke[0][0], origin_y + stroke[0][1])
        input_mgr.down(fx, fy, pressure=pressure_base)
        
        # Draw points
        for i in range(1, len(stroke)):
            if job.cancelled: break
            ax, ay = get_coords(origin_x + stroke[i][0], origin_y + stroke[i][1])
            input_mgr.move_to(ax, ay, pressure=pressure_base)
            
            # Smart skipping for Ultra Mode: avoid too many tiny moves
            if not is_ultra:
                if move_delay > 0.0001: _precise_sleep(move_delay)

        # Pen up
        lx, ly = get_coords(origin_x + stroke[-1][0], origin_y + stroke[-1][1])
        input_mgr.up(lx, ly)
        if stroke_gap > 0.0001: _precise_sleep(stroke_gap)


DESCENDERS = set("gjpqyßÖÄÜöäü")

def _compute_baseline_offset(char: str, char_height: int, variant_baseline: int) -> int:
    if variant_baseline != 0: return variant_baseline
    if char in DESCENDERS: return int(char_height * 0.25)
    return 0


def write_text_to_screen(
    job: WriteJob,
    profile,
    calibration,
    text: str,
    words_per_second: float = 1.5,
    font_size_scale: float = 1.0,
    size_variation: float = 0.08,
    rotation_variation: float = 2.0,
    vertical_jitter: float = 1.5,
    pressure: float = 0.7,
    scaling_factor: float = 1.0,
    **kwargs
):
    if not HAS_NATIVE_EVENTS:
        job.status = "error"
        job.message = "Native Win32 events not available."
        return

    try:
        job.status = "running"
        clear_engine_cache() # Fresh start for the job
        
        words = text.split()
        job.chars_total = sum(len(w) for w in words) + len(words) - 1
        
        translator = CoordinateTranslator(calibration)
        translator.scaling_factor = scaling_factor # DPI FIX
        
        area_w = calibration.write_area_width
        area_h = calibration.write_area_height
        
        # V3.1 SMART SPACING
        effective_font_scale = (font_size_scale * 0.38) / max(0.1, calibration.zoom_level)
        line_h = int(calibration.line_height_px * font_size_scale)
        if line_h <= 0: line_h = 35
        
        char_spacing_base = int(profile.char_spacing * calibration.zoom_level)
        # Increase word spacing for better readability
        word_sp = int(max(profile.word_spacing, profile.avg_char_width * 1.2) * effective_font_scale)

        first_line_y = getattr(calibration, "first_line_y", 0)
        rel_start_y = max(0, first_line_y - calibration.write_area_y) if first_line_y > 0 else 0
        
        cursor_x = 0
        cursor_y = rel_start_y - line_h
        job.current_line = 0
        job.message = f"V3.1 Liquid Ink Engine — {words_per_second} w/s"

        if not prepare_onenote():
            job.status = "error"
            job.message = "OneNote window not found!"
            return
        
        # V3.1 WARM-UP PHASE: Pre-calculate all unique characters in the text
        job.message = "Preparing ink data..."
        unique_chars = set(text)
        for char in unique_chars:
            if job.cancelled: break
            if char.strip() and char in profile.characters:
                variants = profile.characters[char]
                v = random.choice(variants)
                extract_stroke_paths(v.image_path, int(v.width * effective_font_scale), int(v.height * effective_font_scale))
        
        time.sleep(0.1)
        # Scroll threshold: reached bottom 20%
        scroll_threshold_y = area_h * 0.80
        last_focus_check = time.time()

        for word_idx, word in enumerate(words):
            job.wait_if_paused()
            if job.cancelled: break

            # Focus failsafe
            if time.time() - last_focus_check > 4.0:
                curr_hwnd = win32gui.GetForegroundWindow()
                if "onenote" not in win32gui.GetWindowText(curr_hwnd).lower():
                    job.message = "Focus lost! Pausing..."
                    job.pause()
                last_focus_check = time.time()

            # Word wrap prediction
            ww = 0
            for char in word:
                variants = profile.characters.get(char, [])
                if variants:
                    ww += variants[0].width * effective_font_scale + char_spacing_base
                else:
                    ww += profile.avg_char_width * effective_font_scale + char_spacing_base

            if cursor_x > 0 and cursor_x + ww > area_w:
                cursor_x = 0
                cursor_y += line_h
                job.current_line += 1

                if cursor_y > scroll_threshold_y:
                    # V3.1 INTELLIGENT SCROLLING
                    job.message = "Scrolling OneNote..."
                    # Scroll 5 notches (approx 5-6 lines)
                    scroll_amount = -600
                    scroll_onenote(scroll_amount)
                    
                    # Pause to allow OneNote to finish scroll animation
                    time.sleep(0.4) 
                    
                    # Recalculate Y. 120 notches is roughly 1-2 lines in OneNote.
                    # This is an estimate, but with 5 notches we stay safe in the middle.
                    # We assume 1 notch = 1 line height.
                    cursor_y -= (line_h * 4) 
                    job.message = "Writing..."

            # Write individual characters
            for char_idx, char in enumerate(word):
                job.wait_if_paused()
                if job.cancelled: break

                variants = profile.characters.get(char, [])
                if not variants:
                    cursor_x += int(profile.avg_char_width * effective_font_scale)
                    job.chars_done += 1
                    continue

                variant = random.choice(variants)
                scale = effective_font_scale * random.uniform(1 - size_variation, 1 + size_variation)
                cw, ch = int(variant.width * scale), int(variant.height * scale)

                baseline_y = cursor_y + line_h
                baseline_offset = _compute_baseline_offset(char, ch, variant.baseline_offset)
                y_pos = baseline_y - ch + baseline_offset
                
                # Apply vertical jitter
                y_pos += int(random.uniform(-vertical_jitter, vertical_jitter))

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
                job.progress = job.chars_done / max(job.chars_total, 1)

            # End of word: Add word space
            cursor_x += word_sp

        job.status = "done" if not job.cancelled else "cancelled"
        job.message = "Finished! ✍️"
    except Exception as exc:
        job.status = "error"
        job.message = f"Engine Error: {exc}"
