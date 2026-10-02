"""課題3の解答。Qhull自体の再実装ではありません。"""

from scipy.spatial import QhullError, Voronoi

from voronoi.common import run_demo, validate_points


def compute_voronoi(points):
    points = validate_points(points)
    if len(points) < 3:
        raise ValueError("SciPy教材では非共線の母点を3点以上指定してください。")
    try:
        return Voronoi(points)
    except QhullError as exc:
        raise ValueError("共線・数値的に退化した点配置です。半平面法も試してください。") from exc


if __name__ == "__main__":
    run_demo(compute_voronoi, "SciPy / Qhull (solution)", "scipy")
