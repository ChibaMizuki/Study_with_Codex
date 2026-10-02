"""課題3: SciPyのAPIで計算し、返される構造を観察する。"""

from voronoi.common import run_demo, validate_points


def compute_voronoi(points):
    """scipy.spatial.Voronoiオブジェクトを返す。

    ヒント: vertices / regions / point_region / ridge_verticesを調べる。
    無限遠の頂点を示す-1を配列の添字として使わないこと。
    """
    points = validate_points(points)
    # TODO: scipy.spatial.Voronoiにpointsを渡し、結果を返す。
    raise NotImplementedError("compute_voronoiのTODOを実装してください。")


if __name__ == "__main__":
    run_demo(compute_voronoi, "SciPy / Qhull (exercise)", "scipy")
