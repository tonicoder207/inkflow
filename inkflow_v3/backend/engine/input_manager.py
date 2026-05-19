"""
InkFlow v3 — Input Manager
Pen injection (preferred) with automatic mouse fallback.
All native signatures explicitly declared for 64-bit correctness.
Never raises on native return values — 0 from GetLastError == ERROR_SUCCESS.
"""
import ctypes
from ctypes import wintypes

# ── Mouse flags ────────────────────────────────────────────────────────────────
MOUSEEVENTF_MOVE        = 0x0001
MOUSEEVENTF_LEFTDOWN    = 0x0002
MOUSEEVENTF_LEFTUP      = 0x0004
MOUSEEVENTF_ABSOLUTE    = 0x8000
MOUSEEVENTF_VIRTUALDESK = 0x4000
INPUT_MOUSE             = 0

# ── Pen injection constants ────────────────────────────────────────────────────
PT_PEN               = 3
POINTER_FLAG_DOWN    = 0x00010000
POINTER_FLAG_UPDATE  = 0x00020000
POINTER_FLAG_UP      = 0x00040000
POINTER_FLAG_INRANGE    = 0x00000002
POINTER_FLAG_INCONTACT  = 0x00000004
POINTER_FLAG_CONFIDENCE = 0x00000400
POINTER_FLAG_PRIMARY    = 0x00002000
PEN_FLAG_NONE        = 0x00000000
PEN_MASK_PRESSURE    = 0x00000001


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx",          wintypes.LONG),
        ("dy",          wintypes.LONG),
        ("mouseData",   wintypes.DWORD),
        ("dwFlags",     wintypes.DWORD),
        ("time",        wintypes.DWORD),
        ("dwExtraInfo", ctypes.POINTER(ctypes.c_ulong)),
    ]


class INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", INPUT_UNION)]


class POINTER_INFO(ctypes.Structure):
    _fields_ = [
        ("pointerType",           wintypes.DWORD),
        ("pointerId",             ctypes.c_uint32),
        ("frameId",               ctypes.c_uint32),
        ("pointerFlags",          wintypes.DWORD),
        ("sourceDevice",          wintypes.HANDLE),
        ("hwndTarget",            wintypes.HWND),
        ("ptPixelLocation",       POINT),
        ("ptHimetricLocation",    POINT),
        ("ptPixelLocationRaw",    POINT),
        ("ptHimetricLocationRaw", POINT),
        ("dwTime",                wintypes.DWORD),
        ("historyCount",          ctypes.c_uint32),
        ("InputData",             ctypes.c_int32),
        ("dwKeyStates",           wintypes.DWORD),
        ("PerformanceCount",      ctypes.c_uint64),
        ("ButtonChangeType",      ctypes.c_int32),
    ]


class POINTER_PEN_INFO(ctypes.Structure):
    _fields_ = [
        ("pointerInfo", POINTER_INFO),
        ("penFlags",    wintypes.DWORD),
        ("penMask",     wintypes.DWORD),
        ("pressure",    ctypes.c_uint32),
        ("rotation",    ctypes.c_uint32),
        ("tiltX",       ctypes.c_int32),
        ("tiltY",       ctypes.c_int32),
    ]


class POINTER_TYPE_INFO(ctypes.Structure):
    _fields_ = [
        ("type",    wintypes.DWORD),
        ("penInfo", POINTER_PEN_INFO),
    ]


class InputManager:
    def __init__(self):
        self.use_pen_injection = False
        self.pointer_id        = 1
        self.frame_id          = 1
        self._pen_info         = None
        self._inject_fn        = None
        self._user32           = None

        if not hasattr(ctypes, "windll"):
            return

        self._user32 = ctypes.windll.user32

        # DPI awareness
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(1)
            except Exception:
                try:
                    self._user32.SetProcessDPIAware()
                except Exception:
                    pass

        # Declare SendInput signature explicitly
        self._user32.SendInput.argtypes = [
            wintypes.UINT,
            ctypes.POINTER(INPUT),
            ctypes.c_int,
        ]
        self._user32.SendInput.restype = wintypes.UINT

        self._setup_pen_injection()

    def _setup_pen_injection(self):
        try:
            init_fn = getattr(self._user32, "InitializePointerDeviceInjection", None)
            if init_fn is None:
                return

            init_fn.argtypes = [ctypes.c_uint32, ctypes.c_uint32, wintypes.DWORD]
            init_fn.restype  = wintypes.BOOL

            inject_fn = getattr(self._user32, "InjectPointerInput", None)
            if inject_fn is None:
                return

            inject_fn.argtypes = [ctypes.c_uint32, ctypes.POINTER(POINTER_TYPE_INFO)]
            inject_fn.restype  = wintypes.BOOL

            # nonzero = success; 0 = failure — never call WinError() here
            if not init_fn(self.pointer_id, 1, PT_PEN):
                return

            pti = POINTER_TYPE_INFO()
            pti.type = PT_PEN
            p = pti.penInfo
            p.pointerInfo.pointerType = PT_PEN
            p.pointerInfo.pointerId   = self.pointer_id
            p.penFlags                = PEN_FLAG_NONE
            p.penMask                 = PEN_MASK_PRESSURE

            self._pen_info         = pti
            self._inject_fn        = inject_fn
            self.use_pen_injection = True
        except Exception:
            self.use_pen_injection = False

    def _inject_pen(self, x: int, y: int, flags: int, pressure: int = 512) -> bool:
        try:
            p = self._pen_info.penInfo
            p.pointerInfo.frameId           = self.frame_id
            p.pointerInfo.ptPixelLocation.x = int(x)
            p.pointerInfo.ptPixelLocation.y = int(y)
            p.pointerInfo.pointerFlags      = flags
            p.pointerInfo.dwTime            = 0
            p.pressure                      = max(0, min(1024, int(pressure)))
            self.frame_id += 1
            # Returns nonzero = success; 0 = failure. NOT an exception.
            return bool(self._inject_fn(1, ctypes.byref(self._pen_info)))
        except Exception:
            return False

    def _send_mouse(self, x: int, y: int, extra_flags: int) -> bool:
        try:
            flags = MOUSEEVENTF_MOVE | MOUSEEVENTF_VIRTUALDESK | MOUSEEVENTF_ABSOLUTE | extra_flags
            extra = ctypes.c_ulong(0)
            mi    = MOUSEINPUT(int(x), int(y), 0, flags, 0, ctypes.pointer(extra))
            inp   = INPUT(INPUT_MOUSE, INPUT_UNION(mi=mi))
            # SendInput: returns events sent. 0 = failure; >0 = success.
            sent = self._user32.SendInput(
                wintypes.UINT(1),
                ctypes.byref(inp),
                ctypes.c_int(ctypes.sizeof(inp)),
            )
            return sent > 0
        except Exception:
            return False

    def move_to(self, x: int, y: int, is_absolute: bool = True, pressure: int = 512) -> bool:
        if self.use_pen_injection:
            return self._inject_pen(x, y,
                POINTER_FLAG_UPDATE | POINTER_FLAG_INRANGE |
                POINTER_FLAG_INCONTACT | POINTER_FLAG_CONFIDENCE | POINTER_FLAG_PRIMARY,
                pressure)
        return self._send_mouse(x, y, 0)

    def down(self, x: int, y: int, is_absolute: bool = True, pressure: int = 512) -> bool:
        if self.use_pen_injection:
            return self._inject_pen(x, y,
                POINTER_FLAG_DOWN | POINTER_FLAG_INRANGE |
                POINTER_FLAG_INCONTACT | POINTER_FLAG_CONFIDENCE | POINTER_FLAG_PRIMARY,
                pressure)
        return self._send_mouse(x, y, MOUSEEVENTF_LEFTDOWN)

    def up(self, x: int, y: int, is_absolute: bool = True) -> bool:
        if self.use_pen_injection:
            return self._inject_pen(x, y,
                POINTER_FLAG_UP | POINTER_FLAG_CONFIDENCE | POINTER_FLAG_PRIMARY, 0)
        return self._send_mouse(x, y, MOUSEEVENTF_LEFTUP)
