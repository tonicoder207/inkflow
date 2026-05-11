import numpy as np
import math

class StrokeProcessor:
    @staticmethod
    def smooth_stroke_v2(points: list[tuple[float, float]], density: float = 0.5) -> list[tuple[float, float]]:
        """
        High-quality stroke smoothing using Catmull-Rom splines with distance-based density.
        'density' controls how many points are generated per pixel of length.
        """
        if len(points) < 2:
            return points
        
        # 1. Pre-process: Remove duplicate points
        clean_pts = [points[0]]
        for i in range(1, len(points)):
            if points[i] != points[i-1]:
                clean_pts.append(points[i])
        
        if len(clean_pts) < 2:
            return clean_pts

        # 2. Add ghost points at start and end for Catmull-Rom to handle ends
        # p0 (ghost), p1, p2, ..., pn, pn+1 (ghost)
        p0 = (2 * clean_pts[0][0] - clean_pts[1][0], 2 * clean_pts[0][1] - clean_pts[1][1])
        pn_1 = (2 * clean_pts[-1][0] - clean_pts[-2][0], 2 * clean_pts[-1][1] - clean_pts[-2][1])
        
        pts = [p0] + clean_pts + [pn_1]
        
        smoothed = []
        for i in range(1, len(pts) - 2):
            p_prev = pts[i-1]
            p_curr = pts[i]
            p_next = pts[i+1]
            p_after = pts[i+2]
            
            # Calculate segment length to determine point count
            dist = math.sqrt((p_next[0] - p_curr[0])**2 + (p_next[1] - p_curr[1])**2)
            num_steps = max(2, int(dist * density))
            
            for t in np.linspace(0, 1, num_steps, endpoint=False):
                smoothed.append(StrokeProcessor._catmull_rom_point(
                    t, p_prev, p_curr, p_next, p_after
                ))
        
        smoothed.append(clean_pts[-1])
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

    @staticmethod
    def simplify_points(points: list[tuple[float, float]], tolerance: float = 0.5) -> list[tuple[float, float]]:
        """Optional: RDP simplification to remove noise before smoothing."""
        if len(points) < 3:
            return points
        
        def dsq(p1, p2):
            return (p1[0]-p2[0])**2 + (p1[1]-p2[1])**2
        
        def dist_to_segment_sq(p, p1, p2):
            l2 = dsq(p1, p2)
            if l2 == 0: return dsq(p, p1)
            t = ((p[0]-p1[0])*(p2[0]-p1[0]) + (p[1]-p1[1])*(p2[1]-p1[1])) / l2
            t = max(0, min(1, t))
            return dsq(p, (p1[0]+t*(p2[0]-p1[0]), p1[1]+t*(p2[1]-p1[1])))

        dmax, idx = 0, 0
        for i in range(1, len(points)-1):
            d = dist_to_segment_sq(points[i], points[0], points[-1])
            if d > dmax:
                dmax, idx = d, i
        
        if dmax > tolerance**2:
            left = StrokeProcessor.simplify_points(points[:idx+1], tolerance)
            right = StrokeProcessor.simplify_points(points[idx:], tolerance)
            return left[:-1] + right
        else:
            return [points[0], points[-1]]
