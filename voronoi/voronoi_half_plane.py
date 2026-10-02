"""課題2: 垂直二等分線の半平面で矩形を順に切り取る。"""

from voronoi.common import run_demo, validate_points


def clip_polygon(polygon, normal, offset):
    """凸多角形を normal @ x <= offset で切り取り、(M,2)配列を返す。

    ヒント: 辺の始点・終点の内外を判定。境界を横切る場合は交点を追加。
    """
    # TODO: Sutherland–Hodgman型のクリッピングを実装する。
    raise NotImplementedError("clip_polygonのTODOを実装してください。")


def compute_voronoi(points, bounds):
    """母点の順に、bounds内に切り取った凸多角形の配列をリストで返す。

    bounds = (xmin, xmax, ymin, ymax)。空の領域はshape (0,2)。
    ヒント: 母点pの領域は全てのqについて |x-p|² <= |x-q|² を満たす。
    """
    points = validate_points(points)
    # TODO: 母点ごとに矩形から始め、他の母点との半平面で切り取る。
    raise NotImplementedError("compute_voronoiのTODOを実装してください。")


if __name__ == "__main__":
    run_demo(compute_voronoi, "Half-plane intersection (exercise)", "polygons")
