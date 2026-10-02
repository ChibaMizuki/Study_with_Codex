# アルゴリズム学習環境

Pythonでアルゴリズムを実装し、描画して理解するための環境です。
Python 3.12と依存ライブラリは **uv** で管理します。

## 準備と実行

リポジトリのルートで実行してください。仮想環境を手動で有効化する必要はありません。

```powershell
uv sync
uv run python -m voronoi.voronoi_brute_force_solution
```

`uv sync` は `.venv/` を作成します。NumPy（数値計算）、SciPy（計算幾何）、
Matplotlib（描画）、pytest（検証）、Ruff（コードチェック）を導入します。
`uv.lock` を共有することで依存バージョンを再現できます。
詳細: [uv公式のプロジェクトガイド](https://docs.astral.sh/uv/guides/projects/)。

## 学習の進め方

1. [ボロノイ分割の解説](voronoi/README.md)を読む。
   配列や引数の読み方は [コード面の実装ガイド](voronoi/IMPLEMENTATION.md) を参照してください。
2. `voronoi/voronoi_brute_force.py` のTODOを実装する。
3. `uv run python -m voronoi.voronoi_brute_force` で描画する。
4. `_solution.py` と比較し、半平面法、SciPyへ進む。

学習用ファイルは未実装のまま実行すると、実装箇所を案内して終了します。
初期値・乱数生成・描画・画像保存は準備済みです。

```powershell
# 同じseedで同じ母点を使う
uv run python -m voronoi.voronoi_half_plane_solution --points 20 --seed 7
# 画面を開かず保存
uv run python -m voronoi.voronoi_scipy_solution --save outputs/voronoi_scipy.png
# 解答の検証とコードチェック
uv run pytest
uv run ruff check .
```

## 教材とファイルのルール

- アルゴリズムごとに `voronoi/`、`quickhull/` のようにフォルダを分けます。
- 各フォルダの `README.md` にアルゴリズムの原理・計算量・実行方法を記述します。
- 学習用ファイルには、初期値や描画設定など学習と直接関係のない部分を最初から用意します。
- 学習用は `<アルゴリズム>_<手法>.py`、答え合わせ用は末尾に `_solution` を付けます。
- 共通の補助処理は `common.py`、検証は各フォルダの `tests/` にまとめます。
- 現在の教材は [voronoi](voronoi/README.md) です。発展手法は解説のみです。
- 作業方針は [AGENTS.md](AGENTS.md) に記載しています。

## 今後追加する場合

新しいフォルダ、解説、学習用、解答、テストを作成し、上の教材一覧に追加してください。
新しいテストフォルダは `pyproject.toml` の `testpaths` に追加します。
依存の追加は `uv add ライブラリ名`、開発用は `uv add --dev ライブラリ名`。
`.venv/` や生成画像はGit管理せず、`pyproject.toml` と `uv.lock` を管理します。
