import numpy as np

class StrokeProcessor:
    @staticmethod
    def smooth_bezier(points: list[tuple[float, float]], steps_per_segment: int = 5) -> list[tuple[float, float]]:
        """
        Applies basic smoothing. For simplicity and reliability,
        we use linear interpolation if points are sparse, or a simple
        moving average / spline if requested.

        Here we implement a simple linear subdivision to ensure density.
        """
        if len(points) < 2:
            return points

        new_points = []
        for i in range(len(points) - 1):
            p1 = points[i]
            p2 = points[i+1]

            for t in np.linspace(0, 1, steps_per_segment, endpoint=False):
                ix = p1[0] + (p2[0] - p1[0]) * t
                iy = p1[1] + (p2[1] - p1[1]) * t
                new_points.append((ix, iy))

        new_points.append(points[-1])
        return new_points

    @staticmethod
    def get_catmull_rom_spline(points: list[tuple[float, float]], num_points: int = 10) -> list[tuple[float, float]]:
        """
        Implementation of Catmull-Rom Spline for smoother curves.
        """
        if len(points) < 4:
            return points

        smoothed = []
        for i in range(len(points) - 3):
            for t in np.linspace(0, 1, num_points, endpoint=False):
                smoothed.append(StrokeProcessor._catmull_rom_point(
                    t, points[i], points[i+1], points[i+2], points[i+3]
                ))
        smoothed.append(points[-1])
        return smoothed

    @staticmethod
    def _catmull_rom_point(t, p0, p1, p2, p3):
        t2 = t * t
        t3 = t2 * t

        f0 = -0.5*t3 + t2 - 0.5*t
        f1 = 1.5*t3 - 2.5*t2 + 1.0
        f2 = -1.5*t3 + 2.0*t2 + 0.5*t
        f3 = 0.5*t3 - 0.5*t2

        x = p0[0]*f0 + p1[0]*f1 + p2[0]*f2 + p3[0]*f3
        y = p0[1]*f0 + p1[1]*f1 + p2[1]*f2 + p3[1]*f3
        return (x, y)
