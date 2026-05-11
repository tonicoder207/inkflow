import numpy as np

class CoordinateTranslator:
    def __init__(self, calibration_profile=None):
        self.matrix = None
        self.scaling_factor = 1.0 # Default 100%
        
        if calibration_profile:
            if calibration_profile.transform_matrix:
                self.matrix = np.array(calibration_profile.transform_matrix, dtype=np.float32)
            if hasattr(calibration_profile, 'scaling_factor'):
                self.scaling_factor = calibration_profile.scaling_factor

        self.write_area_x = calibration_profile.write_area_x if calibration_profile else 0
        self.write_area_y = calibration_profile.write_area_y if calibration_profile else 0

    def to_windows_coordinates(self, x: float, y: float) -> tuple[float, float]:
        """
        Maps local pixels to Screen Pixels using perspective transformation.
        Applies scaling_factor to adjust for Windows Display Scaling (DPI).
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
            # Simple offset fallback
            target_x, target_y = self.write_area_x + x, self.write_area_y + y

        # APPLY SCALING FACTOR
        # If user has 150% scaling, the coordinates need to be multiplied by 1.5 
        # to match the system's virtual coordinate space.
        return target_x * self.scaling_factor, target_y * self.scaling_factor

    @staticmethod
    def normalize_to_win_abs(px, py, vx, vy, vw, vh) -> tuple[int, int]:
        """
        Convert pixel coordinates to 0-65535 range, relative to the virtual screen.
        """
        ax = int((px - vx) * 65535 / (vw - 1)) if vw > 1 else 0
        ay = int((py - vy) * 65535 / (vh - 1)) if vh > 1 else 0
        return max(0, min(65535, ax)), max(0, min(65535, ay))
