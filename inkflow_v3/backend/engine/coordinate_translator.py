import numpy as np

class CoordinateTranslator:
    def __init__(self, calibration_profile=None):
        self.matrix = None
        if calibration_profile and calibration_profile.transform_matrix:
            self.matrix = np.array(calibration_profile.transform_matrix, dtype=np.float32)

        self.write_area_x = calibration_profile.write_area_x if calibration_profile else 0
        self.write_area_y = calibration_profile.write_area_y if calibration_profile else 0

    def to_windows_coordinates(self, x: float, y: float) -> tuple[int, int]:
        """
        Maps normalized (0.0 - 1.0) or local pixels to Screen Pixels.
        If a matrix is present, it uses perspective transform.
        """
        if self.matrix is not None:
            # Perspective transform
            vec = np.array([x, y, 1.0], dtype=np.float32)
            res = self.matrix @ vec
            if abs(res[2]) > 1e-9:
                target_x, target_y = res[0] / res[2], res[1] / res[2]
            else:
                target_x, target_y = self.write_area_x + x, self.write_area_y + y
        else:
            # Simple offset
            target_x, target_y = self.write_area_x + x, self.write_area_y + y

        return target_x, target_y

    @staticmethod
    def normalize_to_win_abs(px, py, vx, vy, vw, vh) -> tuple[int, int]:
        """
        Convert pixel coordinates to 0-65535 range, relative to the virtual screen.
        vx, vy: origin of virtual screen
        vw, vh: width and height of virtual screen
        """
        # When using MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK,
        # (0, 0) maps to the top-left of the virtual screen and (65535, 65535) maps to bottom-right.
        ax = int((px - vx) * 65535 / (vw - 1)) if vw > 1 else 0
        ay = int((py - vy) * 65535 / (vh - 1)) if vh > 1 else 0
        return max(0, min(65535, ax)), max(0, min(65535, ay))
