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
        except:
            try: ctypes.windll.user32.SetProcessDPIAware()
            except: pass

        if hasattr(ctypes, "windll"):
            try:
                if ctypes.windll.user32.InitializePointerDeviceInjection(10, 1, PT_PEN):
                    self.use_pen_injection = True
                    self.pointer_id = 1
                    self.frame_id = 1
                    self._pen_info = POINTER_TYPE_INFO()
                    self._pen_info.type = PT_PEN
                    p = self._pen_info.penInfo
                    p.pointerInfo.pointerType = PT_PEN
                    p.pointerInfo.pointerId = self.pointer_id
                    p.penFlags = PEN_FLAG_NONE
                    p.penMask = PEN_MASK_PRESSURE
            except: pass

    def _inject_pen(self, x, y, flags, pressure=512):
        p = self._pen_info.penInfo
        p.pointerInfo.frameId = self.frame_id
        p.pointerInfo.ptPixelLocation.x = int(x)
        p.pointerInfo.ptPixelLocation.y = int(y)
        p.pointerInfo.pointerFlags = flags
        p.pointerInfo.dwTime = 0
        p.pressure = int(pressure)
        self.frame_id += 1
        return ctypes.windll.user32.InjectPointerInput(1, ctypes.byref(self._pen_info))

    def move_to(self, x, y, is_absolute=True, pressure=512):
        if self.use_pen_injection:
            return self._inject_pen(x, y, POINTER_FLAG_UPDATE | POINTER_FLAG_INRANGE | POINTER_FLAG_INCONTACT | POINTER_FLAG_CONFIDENCE | POINTER_FLAG_PRIMARY, pressure)

        extra = ctypes.c_ulong(0)
        flags = MOUSEEVENTF_MOVE | MOUSEEVENTF_VIRTUALDESK
        if is_absolute: flags |= MOUSEEVENTF_ABSOLUTE
        mi = MOUSEINPUT(int(x), int(y), 0, flags, 0, ctypes.pointer(extra))
        input_obj = INPUT(0, INPUT_UNION(mi=mi))
        return ctypes.windll.user32.SendInput(1, ctypes.byref(input_obj), ctypes.sizeof(input_obj))

    def down(self, x, y, is_absolute=True, pressure=512):
        if self.use_pen_injection:
            return self._inject_pen(x, y, POINTER_FLAG_DOWN | POINTER_FLAG_INRANGE | POINTER_FLAG_INCONTACT | POINTER_FLAG_CONFIDENCE | POINTER_FLAG_PRIMARY, pressure)

        extra = ctypes.c_ulong(0)
        flags = MOUSEEVENTF_MOVE | MOUSEEVENTF_VIRTUALDESK | MOUSEEVENTF_LEFTDOWN
        if is_absolute: flags |= MOUSEEVENTF_ABSOLUTE
        mi = MOUSEINPUT(int(x), int(y), 0, flags, 0, ctypes.pointer(extra))
        input_obj = INPUT(0, INPUT_UNION(mi=mi))
        return ctypes.windll.user32.SendInput(1, ctypes.byref(input_obj), ctypes.sizeof(input_obj))

    def up(self, x, y, is_absolute=True):
        if self.use_pen_injection:
            return self._inject_pen(x, y, POINTER_FLAG_UP | POINTER_FLAG_CONFIDENCE | POINTER_FLAG_PRIMARY, 0)

        extra = ctypes.c_ulong(0)
        flags = MOUSEEVENTF_MOVE | MOUSEEVENTF_VIRTUALDESK | MOUSEEVENTF_LEFTUP
        if is_absolute: flags |= MOUSEEVENTF_ABSOLUTE
        mi = MOUSEINPUT(int(x), int(y), 0, flags, 0, ctypes.pointer(extra))
        input_obj = INPUT(0, INPUT_UNION(mi=mi))
        return ctypes.windll.user32.SendInput(1, ctypes.byref(input_obj), ctypes.sizeof(input_obj))
