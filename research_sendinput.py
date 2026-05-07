import ctypes
from ctypes import wintypes

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

def send_mouse_input(flags, x, y):
    extra = ctypes.c_ulong(0)
    mi = MOUSEINPUT(x, y, 0, flags, 0, ctypes.pointer(extra))
    input_obj = INPUT(INPUT_MOUSE, INPUT_UNION(mi=mi))
    ctypes.windll.user32.SendInput(1, ctypes.byref(input_obj), ctypes.sizeof(input_obj))

if __name__ == "__main__":
    # Set DPI Awareness
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
        print("DPI Awareness set.")
    except Exception as e:
        print(f"Failed to set DPI Awareness: {e}")

    # Move to center of screen (absolute coordinates 0-65535)
    print("Moving to 32768, 32768")
    send_mouse_input(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK, 32768, 32768)
