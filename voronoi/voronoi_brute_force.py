"""課題1: 格子上の各点を最も近い母点に割り当てる。"""

from voronoi.common import run_demo, validate_points


def compute_voronoi(points, xx, yy):
    """(H,W)のxx,yyに対し、母点の番号を格納した(H,W)整数配列を返す。

    同距離なら小さい番号を優先する。
    ヒント: 平方距離なら平方根は不要。各母点との距離を比較する。
    """
    points = validate_points(points)
    for i in range(len(yy)):
        for j in range(len(xx)):
            
    # TODO: 各格子点で距離が最小になる母点の番号を求める。
    raise NotImplementedError("compute_voronoiのTODOを実装してください。")


if __name__ == "__main__":
    run_demo(compute_voronoi, "Brute force (exercise)", "grid")
