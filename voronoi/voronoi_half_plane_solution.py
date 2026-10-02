"""課題2の解答: 凸多角形を半平面で逐次クリッピングする。"""

import numpy as np

from voronoi.common import run_demo, validate_points


def clip_polygon(polygon, normal, offset):
    if len(polygon) == 0:
        return np.empty((0, 2))
    result = []
    start = polygon[-1]
    ds = np.dot(normal, start) - offset
    for end in polygon:
        de = np.dot(normal, end) - offset
        if (ds <= 0) != (de <= 0):
            # 符号が異なるので分母は0にならない。
            t = ds / (ds - de)
            result.append(start + t * (end - start))
        if de <= 0:
            result.append(end)
        start, ds = end, de
    return np.asarray(result, dtype=float).reshape(-1, 2)


def compute_voronoi(points, bounds):
    points = validate_points(points)
    xmin, xmax, ymin, ymax = bounds
    if not np.isfinite(bounds).all() or xmin >= xmax or ymin >= ymax:
        raise ValueError("boundsは有限で正の幅・高さを持つ矩形にしてください。")
    cells = []
    for i, p in enumerate(points):
        polygon = np.array([[xmin, ymin], [xmax, ymin], [xmax, ymax], [xmin, ymax]])
        for j, q in enumerate(points):
            if i == j:
                continue
            normal = q - p
            offset = np.dot(normal, (p + q) / 2)
            polygon = clip_polygon(polygon, normal, offset)
        cells.append(polygon)
    return cells


if __name__ == "__main__":
    run_demo(compute_voronoi, "Half-plane intersection (solution)", "polygons")
