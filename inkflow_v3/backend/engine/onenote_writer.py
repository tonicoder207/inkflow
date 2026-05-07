"""InkFlow v3 — OneNote Writer Engine (Native Win32 Event Rebuild)."""

import math
import platform
import random
import threading
import time
from typing import Optional

import cv2
import numpy as np

HAS_PEN_INJECTION = False
HAS_NATIVE_EVENTS = False

try:
    import win32api
    import win32con
    import win32gui

    HAS_NATIVE_EVENTS = True
    HAS_PEN_INJECTION = True
except Exception:
    win32api = None
    win32con = None
    win32gui = None
    if platform.system() == "Windows":
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32

            class _Win32Con:
                SW_RESTORE = 9
                SW_MAXIMIZE = 3
                VK_MENU = 0x12
                VK_RETURN = 0x0D
                KEYEVENTF_KEYUP = 0x0002
                MOUSEEVENTF_MOVE = 0x0001
                MOUSEEVENTF_LEFTDOWN = 0x0002
                MOUSEEVENTF_LEFTUP = 0x0004
                MOUSEEVENTF_ABSOLUTE = 0x8000
                MOUSEEVENTF_VIRTUALDESK = 0x4000
                SM_XVIRTUALSCREEN = 76
                SM_YVIRTUALSCREEN = 77
                SM_CXVIRTUALSCREEN = 78
                SM_CYVIRTUALSCREEN = 79

            class _Point(ctypes.Structure):
                _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

            class _Win32Api:
                @staticmethod
                def keybd_event(key, scan, flags, extra):
                    user32.keybd_event(key, scan, flags, extra)

                @staticmethod
                def mouse_event(flags, x, y, data, extra):
                    user32.mouse_event(flags, x, y, data, extra)

                @staticmethod
                def GetSystemMetrics(index):
                    return user32.GetSystemMetrics(index)

                @staticmethod
                def SetCursorPos(pos):
                    x, y = pos
                    user32.SetCursorPos(int(x), int(y))

                @staticmethod
                def GetCursorPos():
                    pt = _Point()
                    user32.GetCursorPos(ctypes.byref(pt))
                    return pt.x, pt.y

            win32api = _Win32Api()
            win32con = _Win32Con()
            win32gui = None
            HAS_NATIVE_EVENTS = True
            HAS_PEN_INJECTION = True
            
            # ── Pen Injection Constants & Structures ───────────────────────────
            PT_PEN = 3
            PT_TOUCH = 2
            POINTER_FLAG_DOWN       = 0x00010000
            POINTER_FLAG_UPDATE     = 0x00020000
            POINTER_FLAG_UP         = 0x00040000
            POINTER_FLAG_INRANGE    = 0x00000002
            POINTER_FLAG_INCONTACT  = 0x00000004
            POINTER_FLAG_CONFIDENCE = 0x00000400
            POINTER_FLAG_PRIMARY    = 0x00002000
            PEN_FLAG_NONE           = 0x00000000
            PEN_MASK_PRESSURE       = 0x00000001

            class POINTER_INFO(ctypes.Structure):
                _fields_ = [
                    ("pointerType", wintypes.DWORD), ("pointerId", ctypes.c_uint32),
                    ("frameId", ctypes.c_uint32), ("pointerFlags", wintypes.DWORD),
                    ("sourceDevice", wintypes.HANDLE), ("hwndTarget", wintypes.HWND),
                    ("ptPixelLocation", _Point), ("ptHimetricLocation", _Point),
                    ("ptPixelLocationRaw", _Point), ("ptHimetricLocationRaw", _Point),
                    ("dwTime", wintypes.DWORD), ("historyCount", ctypes.c_uint32),
                    ("InputData", ctypes.c_int32), ("dwKeyStates", wintypes.DWORD),
                    ("PerformanceCount", ctypes.c_uint64), ("ButtonChangeType", ctypes.c_int32),
                ]

            class POINTER_PEN_INFO(ctypes.Structure):
                _fields_ = [
                    ("pointerInfo", POINTER_INFO), ("penFlags", wintypes.DWORD),
                    ("penMask", wintypes.DWORD), ("pressure", ctypes.c_uint32),
                    ("rotation", ctypes.c_uint32), ("tiltX", ctypes.c_int32), ("tiltY", ctypes.c_int32),
                ]

            class POINTER_TYPE_INFO(ctypes.Structure):
                _fields_ = [("type", wintypes.DWORD), ("penInfo", POINTER_PEN_INFO)]

            _InitializePointerDeviceInjection = user32.InitializePointerDeviceInjection
            _InitializePointerDeviceInjection.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32]
            _InitializePointerDeviceInjection.restype = wintypes.BOOL

            _InjectPointerInput = user32.InjectPointerInput
            _InjectPointerInput.argtypes = [ctypes.c_uint32, ctypes.POINTER(POINTER_TYPE_INFO)]
            _InjectPointerInput.restype = wintypes.BOOL
            
            try: ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except: pass
        except Exception:
            pass

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

        # User-verified OneNote flow (pen already selected):
        # 1) Alt+F, 1, O, 100, Enter
        _send_hotkey([win32con.VK_MENU], ord("F"))
        time.sleep(0.06)
        _send_key(ord("1"))
        time.sleep(0.06)
        _send_key(ord("O"))
        time.sleep(0.06)
        _type_text("100")
        time.sleep(0.04)
        _send_key(win32con.VK_RETURN)
        # Small wait so the zoom/menu transition can settle.
        time.sleep(0.35)

        # 2) Additional sequence requested by user: Alt+H, F, 1
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
    vx = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN)
    vy = win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN)
    vw = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
    vh = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)
    return vx, vy, max(1, vw), max(1, vh)


def _to_absolute(x: int, y: int) -> tuple[int, int]:
    vx, vy, vw, vh = _screen_metrics()
    ax = int((x - vx) * 65535 / (vw - 1))
    ay = int((y - vy) * 65535 / (vh - 1))
    return max(0, min(65535, ax)), max(0, min(65535, ay))


def _mouse_move_abs(x: int, y: int):
    # Prefer direct pixel positioning (most robust across DPI/multi-monitor setups).
    try:
        win32api.SetCursorPos((int(x), int(y)))
        return
    except Exception:
        pass

    # Fallback to normalized absolute events if SetCursorPos is unavailable.
    ax, ay = _to_absolute(x, y)
    win32api.mouse_event(
        win32con.MOUSEEVENTF_MOVE | win32con.MOUSEEVENTF_ABSOLUTE | win32con.MOUSEEVENTF_VIRTUALDESK,
        ax,
        ay,
        0,
        0,
    )


def _mouse_down():
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)


def _mouse_up():
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


class PenDevice:
    def __init__(self):
        self.pointer_id = 1
        self.frame_id = 0
        self.initialized = False
        self.mode = "pen"
        
        if HAS_PEN_INJECTION:
            if _InitializePointerDeviceInjection(10, 1, 3):
                self.initialized = True
                self.mode = "pen"
            elif _InitializePointerDeviceInjection(11, 1, 2):
                self.initialized = True
                self.mode = "touch"

    def _inject(self, x: int, y: int, flags: int, pressure: int = 512):
        if not self.initialized:
            _mouse_move_abs(x, y)
            if flags & POINTER_FLAG_DOWN: _mouse_down()
            elif flags & POINTER_FLAG_UP: _mouse_up()
            return True
        
        info = POINTER_TYPE_INFO()
        info.type = 3 if self.mode == "pen" else 2
        p = info.penInfo
        p.pointerInfo.pointerType = info.type
        p.pointerInfo.pointerId = self.pointer_id
        p.pointerInfo.frameId = self.frame_id
        p.pointerInfo.ptPixelLocation.x = int(x)
        p.pointerInfo.ptPixelLocation.y = int(y)
        p.pointerInfo.pointerFlags = flags
        p.pointerInfo.dwTime = int(time.time() * 1000) & 0xFFFFFFFF
        p.penFlags = PEN_FLAG_NONE
        p.penMask = PEN_MASK_PRESSURE
        p.pressure = int(pressure)
        
        self.frame_id += 1
        return _InjectPointerInput(1, ctypes.byref(info))

    def down(self, x: int, y: int, pressure: int = 512):
        return self._inject(x, y, POINTER_FLAG_DOWN | POINTER_FLAG_INRANGE | POINTER_FLAG_INCONTACT | POINTER_FLAG_CONFIDENCE | POINTER_FLAG_PRIMARY, pressure)

    def move(self, x: int, y: int, pressure: int = 512):
        return self._inject(x, y, POINTER_FLAG_UPDATE | POINTER_FLAG_INRANGE | POINTER_FLAG_INCONTACT | POINTER_FLAG_CONFIDENCE | POINTER_FLAG_PRIMARY, pressure)

    def up(self, x: int, y: int):
        return self._inject(x, y, POINTER_FLAG_UP | POINTER_FLAG_CONFIDENCE | POINTER_FLAG_PRIMARY, 0)

pen_injector = PenDevice()


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
    pts.sort(key=lambda p: (p[0], p[1]))
    if len(pts) > 100:
        step = max(1, len(pts) // 100)
        pts = pts[::step]
    return pts


def _fallback_path(w, h):
    return [(w // 2, int(h * t)) for t in [i / 10 for i in range(11)]]


def _apply_transform(calibration, x: float, y: float, scaling_factor: float = 1.0) -> tuple[int, int]:
    matrix = getattr(calibration, "transform_matrix", None) or []
    if matrix and len(matrix) == 3 and len(matrix[0]) == 3:
        m = np.array(matrix, dtype=np.float64)
        vec = np.array([x, y, 1.0], dtype=np.float64)
        tx, ty, tw = m @ vec
        if abs(tw) > 1e-9:
            final_x, final_y = tx / tw, ty / tw
        else:
            final_x, final_y = calibration.write_area_x + x, calibration.write_area_y + y
    else:
        final_x, final_y = calibration.write_area_x + x, calibration.write_area_y + y
        
    return int(final_x * scaling_factor), int(final_y * scaling_factor)


def _draw_stroke(
    job: WriteJob,
    points: list[tuple[int, int]],
    speed: str,
    calibration,
    origin_x: int,
    origin_y: int,
    point_delay_s: float,
    pressure_base: float,
    scaling_factor: float,
):
    if not HAS_NATIVE_EVENTS or not points:
        return

    speed_mul = {"slow": 1.7, "normal": 1.0, "fast": 0.65}.get(speed, 1.0)
    base_delay = max(0.001, point_delay_s * speed_mul)

    sx, sy = _apply_transform(calibration, origin_x + points[0][0], origin_y + points[0][1], scaling_factor)
    pen_injector.down(sx, sy, int(pressure_base * 1024))
    time.sleep(base_delay)

    for i in range(1, len(points)):
        if job.cancelled:
            break
        px, py = points[i]
        ppx, ppy = points[i - 1]
        dist = math.sqrt((px - ppx) ** 2 + (py - ppy) ** 2)
        segments = max(1, int(dist / 2.5))
        for s in range(1, segments + 1):
            if job.cancelled:
                break
            t = s / segments
            ix = int(ppx + (px - ppx) * t)
            iy = int(ppy + (py - ppy) * t)
            ax, ay = _apply_transform(calibration, origin_x + ix, origin_y + iy, scaling_factor)
            
            # Simple sinusoid pressure variation
            p_val = pressure_base * (0.8 + 0.4 * math.sin(t * math.pi))
            pen_injector.move(ax, ay, int(p_val * 1024))
            time.sleep(base_delay / segments)

    ex, ey = _apply_transform(calibration, origin_x + points[-1][0], origin_y + points[-1][1], scaling_factor)
    pen_injector.up(ex, ey)
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
    _ = rotation_variation
    if not HAS_NATIVE_EVENTS:
        job.status = "error"
        job.message = "Native Win32 events not available."
        return

    try:
        job.status = "running"
        words = text.split()
        all_chars = [c for w in words for c in (list(w) + [" "])]
        job.chars_total = len(all_chars)

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
                vy = int(random.uniform(-vertical_jitter, vertical_jitter))

                points = extract_stroke_path(variant.image_path, cw, ch)
                _draw_stroke(
                    job=job,
                    points=points,
                    speed=speed,
                    calibration=calibration,
                    origin_x=cursor_x,
                    origin_y=cursor_y + vy,
                    point_delay_s=point_delay_s,
                    pressure_base=pressure,
                    scaling_factor=getattr(calibration, "scaling_factor", 1.0),
                )
                cursor_x += cw + int(profile.char_spacing * calibration.zoom_level)
                job.chars_done += 1
                job.progress = job.chars_done / max(job.chars_total, 1)

            cursor_x += word_sp
            time.sleep(max(0.002, point_delay_s * 3))

        job.status = "done" if not job.cancelled else "cancelled"
        job.message = "Fertig!" if not job.cancelled else "Abgebrochen"
    except Exception as exc:
        job.status = "error"
        job.message = f"Fehler: {exc}"
