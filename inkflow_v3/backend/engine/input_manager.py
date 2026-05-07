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

class InputManager:
    def __init__(self):
        try:
            # Set DPI Awareness: 1 = Process_System_DPI_Aware, 2 = Process_Per_Monitor_DPI_Aware
            # 1 is requested in the mission
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

    def _send_input(self, flags, x, y):
        extra = ctypes.c_ulong(0)
        mi = MOUSEINPUT(x, y, 0, flags, 0, ctypes.pointer(extra))
        input_obj = INPUT(INPUT_MOUSE, INPUT_UNION(mi=mi))
        # Note: In a real Windows environment, this would be:
        # ctypes.windll.user32.SendInput(1, ctypes.byref(input_obj), ctypes.sizeof(input_obj))
        # But we use a guarded call for portability during development if needed.
        if hasattr(ctypes, "windll"):
            ctypes.windll.user32.SendInput(1, ctypes.byref(input_obj), ctypes.sizeof(input_obj))

    def move_to(self, abs_x: int, abs_y: int):
        """Move cursor to absolute coordinates (0-65535)."""
        self._send_input(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK, abs_x, abs_y)

    def down(self, abs_x: int, abs_y: int):
        """Press left mouse button at absolute coordinates."""
        self._send_input(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK | MOUSEEVENTF_LEFTDOWN, abs_x, abs_y)

    def up(self, abs_x: int, abs_y: int):
        """Release left mouse button at absolute coordinates."""
        self._send_input(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK | MOUSEEVENTF_LEFTUP, abs_x, abs_y)
