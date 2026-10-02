"""教材に共通する入力・描画処理。ここを編集する必要はありません。"""

import argparse
from pathlib import Path

import numpy as np

BOUNDS = (0.0, 1.0, 0.0, 1.0)  # xmin, xmax, ymin, ymax


def validate_points(points):
    points = np.asarray(points, dtype=float)
    if points.ndim != 2 or points.shape[1] != 2 or len(points) == 0:
        raise ValueError("pointsは1点以上の(N, 2)配列にしてください。")
    if not np.isfinite(points).all():
        raise ValueError("座標には有限の値を指定してください。")
    if len(np.unique(points, axis=0)) != len(points):
        raise ValueError("重複する母点は取り除いてください。")
    return points


def run_demo(compute, method, kind):
    parser = argparse.ArgumentParser(description=method)
    parser.add_argument("--points", type=int, default=12)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--resolution", type=int, default=250)
    parser.add_argument("--save", type=Path, help="表示の代わりに画像を保存")
    args = parser.parse_args()
    if args.points < 1 or args.resolution < 2:
        parser.error("pointsは1以上、resolutionは2以上にしてください。")

    import matplotlib

    if args.save:
        matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap

    points = np.random.default_rng(args.seed).uniform(0.05, 0.95, (args.points, 2))
    x = np.linspace(BOUNDS[0], BOUNDS[1], args.resolution)
    y = np.linspace(BOUNDS[2], BOUNDS[3], args.resolution)
    xx, yy = np.meshgrid(x, y)
    try:
        if kind == "grid":
            result = compute(points, xx, yy)
        elif kind == "polygons":
            result = compute(points, BOUNDS)
        else:
            result = compute(points)
    except (NotImplementedError, ValueError) as exc:
        parser.exit(1, f"{exc}\n")

    fig, ax = plt.subplots(figsize=(7, 7))
    colors = plt.get_cmap("tab20")(np.arange(len(points)) % 20)
    if kind == "grid":
        ax.pcolormesh(xx, yy, result, cmap=ListedColormap(colors),
                      vmin=-0.5, vmax=len(points) - 0.5, shading="nearest", alpha=0.5)
    elif kind == "polygons":
        for index, polygon in enumerate(result):
            if len(polygon) >= 3:
                ax.fill(polygon[:, 0], polygon[:, 1], color=colors[index], alpha=0.5,
                        edgecolor="black")
    else:
        from scipy.spatial import voronoi_plot_2d

        voronoi_plot_2d(result, ax=ax, show_points=False, show_vertices=True)
    ax.scatter(points[:, 0], points[:, 1], color="black", s=20, zorder=3)
    for index, point in enumerate(points):
        ax.annotate(str(index), point, xytext=(4, 4), textcoords="offset points")
    ax.set(xlim=BOUNDS[:2], ylim=BOUNDS[2:], aspect="equal", title=method,
           xlabel="x", ylabel="y")
    fig.tight_layout()
    if args.save:
        args.save.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(args.save, dpi=150)
        print(f"保存しました: {args.save.resolve()}")
    else:
        plt.show()
    plt.close(fig)
