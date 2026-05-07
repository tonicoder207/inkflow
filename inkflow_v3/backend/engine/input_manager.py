import ctypes
from ctypes import wintypes
import time

# Constants
MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_ABSOLUTE = 0x8000
MOUSEEVENTF_VIRTUALDESK = 0x4000
INPUT_MOUSE = 0

# Pen Injection Constants
PT_PEN = 3
POINTER_FLAG_DOWN       = 0x00010000
POINTER_FLAG_UPDATE     = 0x00020000
POINTER_FLAG_UP         = 0x00040000
POINTER_FLAG_INRANGE    = 0x00000002
POINTER_FLAG_INCONTACT  = 0x00000004
POINTER_FLAG_CONFIDENCE = 0x00000400
POINTER_FLAG_PRIMARY    = 0x00002000
PEN_FLAG_NONE           = 0x00000000
PEN_MASK_PRESSURE       = 0x00000001

class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]

class INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT)]

class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", INPUT_UNION)]

# Pen Injection Structures
class POINTER_INFO(ctypes.Structure):
    _fields_ = [
        ("pointerType", wintypes.DWORD), ("pointerId", ctypes.c_uint32),
        ("frameId", ctypes.c_uint32), ("pointerFlags", wintypes.DWORD),
        ("sourceDevice", wintypes.HANDLE), ("hwndTarget", wintypes.HWND),
        ("ptPixelLocation", POINT), ("ptHimetricLocation", POINT),
        ("ptPixelLocationRaw", POINT), ("ptHimetricLocationRaw", POINT),
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

class InputManager:
    def __init__(self):
        self.use_pen_injection = False
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

        # Try to initialize pen injection
        if hasattr(ctypes, "windll"):
            try:
                # 10 devices, 1 contact, PT_PEN (3)
                if ctypes.windll.user32.InitializePointerDeviceInjection(10, 1, PT_PEN):
                    self.use_pen_injection = True
                    self.pointer_id = 1
                    self.frame_id = 0
            except Exception:
                pass

    def _send_mouse_input(self, flags, x, y):
        extra = ctypes.c_ulong(0)
        mi = MOUSEINPUT(x, y, 0, flags, 0, ctypes.pointer(extra))
        input_obj = INPUT(INPUT_MOUSE, INPUT_UNION(mi=mi))
        if hasattr(ctypes, "windll"):
            ctypes.windll.user32.SendInput(1, ctypes.byref(input_obj), ctypes.sizeof(input_obj))

    def _inject_pen(self, x, y, flags, pressure=512):
        info = POINTER_TYPE_INFO()
        info.type = PT_PEN
        p = info.penInfo
        p.pointerInfo.pointerType = PT_PEN
        p.pointerInfo.pointerId = self.pointer_id
        p.pointerInfo.frameId = self.frame_id
        # Note: InjectPointerInput uses screen pixels, NOT 0-65535
        p.pointerInfo.ptPixelLocation.x = int(x)
        p.pointerInfo.ptPixelLocation.y = int(y)
        p.pointerInfo.pointerFlags = flags
        p.pointerInfo.dwTime = 0 # System will timestamp
        p.penFlags = PEN_FLAG_NONE
        p.penMask = PEN_MASK_PRESSURE
        p.pressure = int(pressure)

        self.frame_id += 1
        return ctypes.windll.user32.InjectPointerInput(1, ctypes.byref(info))

    def move_to(self, x: int, y: int, is_absolute=True, pressure=512):
        if self.use_pen_injection:
            self._inject_pen(x, y, POINTER_FLAG_UPDATE | POINTER_FLAG_INRANGE | POINTER_FLAG_INCONTACT | POINTER_FLAG_CONFIDENCE | POINTER_FLAG_PRIMARY, pressure)
        else:
            flags = MOUSEEVENTF_MOVE | MOUSEEVENTF_VIRTUALDESK
            if is_absolute: flags |= MOUSEEVENTF_ABSOLUTE
            self._send_mouse_input(flags, x, y)

    def down(self, x: int, y: int, is_absolute=True, pressure=512):
        if self.use_pen_injection:
            self._inject_pen(x, y, POINTER_FLAG_DOWN | POINTER_FLAG_INRANGE | POINTER_FLAG_INCONTACT | POINTER_FLAG_CONFIDENCE | POINTER_FLAG_PRIMARY, pressure)
        else:
            flags = MOUSEEVENTF_MOVE | MOUSEEVENTF_VIRTUALDESK | MOUSEEVENTF_LEFTDOWN
            if is_absolute: flags |= MOUSEEVENTF_ABSOLUTE
            self._send_mouse_input(flags, x, y)

    def up(self, x: int, y: int, is_absolute=True):
        if self.use_pen_injection:
            self._inject_pen(x, y, POINTER_FLAG_UP | POINTER_FLAG_CONFIDENCE | POINTER_FLAG_PRIMARY, 0)
        else:
            flags = MOUSEEVENTF_MOVE | MOUSEEVENTF_VIRTUALDESK | MOUSEEVENTF_LEFTUP
            if is_absolute: flags |= MOUSEEVENTF_ABSOLUTE
            self._send_mouse_input(flags, x, y)

    def batch_inject(self, points):
        """Inject multiple points at once if supported by the underlying API."""
        # For simplicity, we loop, but with minimal overhead.
        # InjectPointerInput can take multiple points but we need historyCount which is complex.
        # So we just loop as fast as possible.
        for p in points:
            # p = (x, y, flags, pressure)
            self._inject_pen(p[0], p[1], p[2], p[3])
