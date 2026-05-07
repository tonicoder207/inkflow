import sys
import os
import time

# Add backend to path
sys.path.insert(0, os.path.join(os.getcwd(), "inkflow_v3", "backend"))

from engine.input_manager import InputManager
from engine.coordinate_translator import CoordinateTranslator

def debug_draw_square():
    print("Initializing debug square test...")
    input_mgr = InputManager()

    # Fake calibration for 1:1 mapping on a standard 1080p screen for testing
    # In reality, this would come from a CalibrationProfile
    class FakeCal:
        write_area_x = 500
        write_area_y = 500
        transform_matrix = None

    translator = CoordinateTranslator(FakeCal())

    # Assume 1920x1080 for normalization if we can't get it
    screen_w = 1920
    screen_h = 1080

    size = 200

    def move_to_pixel(px, py, action="move"):
        tx, ty = translator.to_windows_coordinates(px, py)
        ax, ay = translator.normalize_to_win_abs(tx, ty, 0, 0, screen_w, screen_h)
        if action == "move":
            input_mgr.move_to(ax, ay)
        elif action == "down":
            input_mgr.down(ax, ay)
        elif action == "up":
            input_mgr.up(ax, ay)

    print("Wait 2 seconds to focus OneNote manually if desired...")
    time.sleep(2)

    print(f"Drawing {size}x{size} square at (500, 500)...")

    # Start top-left
    move_to_pixel(0, 0, "down")
    time.sleep(0.1)

    # Top
    for i in range(11):
        move_to_pixel(size * i / 10, 0)
        time.sleep(0.02)

    # Right
    for i in range(11):
        move_to_pixel(size, size * i / 10)
        time.sleep(0.02)

    # Bottom
    for i in range(11):
        move_to_pixel(size - (size * i / 10), size)
        time.sleep(0.02)

    # Left
    for i in range(11):
        move_to_pixel(0, size - (size * i / 10))
        time.sleep(0.02)

    move_to_pixel(0, 0, "up")
    print("Test complete.")

if __name__ == "__main__":
    debug_draw_square()
