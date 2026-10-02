"""課題1の解答: 母点を1つずつ比較し、メモリ消費を抑える。"""

import numpy as np

from voronoi.common import run_demo, validate_points


def compute_voronoi(points, xx, yy):
    points = validate_points(points)
    best = np.full(xx.shape, np.inf)
    labels = np.zeros(xx.shape, dtype=int)
    for index, (px, py) in enumerate(points):
        distance = (xx - px) ** 2 + (yy - py) ** 2
        closer = distance < best  # 等距離では先に調べた番号を維持
        best[closer] = distance[closer]
        labels[closer] = index
    return labels


if __name__ == "__main__":
    run_demo(compute_voronoi, "Brute force (solution)", "grid")
