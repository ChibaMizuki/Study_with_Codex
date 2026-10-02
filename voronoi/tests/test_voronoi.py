import numpy as np
import pytest

from voronoi.common import BOUNDS
from voronoi.voronoi_brute_force_solution import compute_voronoi as grid
from voronoi.voronoi_half_plane_solution import compute_voronoi as polygons
from voronoi.voronoi_scipy_solution import compute_voronoi as scipy_voronoi


def area(polygon):
    if len(polygon) < 3:
        return 0.0
    x, y = polygon.T
    return abs(np.dot(x, np.roll(y, 1)) - np.dot(y, np.roll(x, 1))) / 2


def test_grid_tie_and_nearest():
    xx = np.array([[0.0, 0.5, 1.0]])
    yy = np.zeros_like(xx)
    np.testing.assert_array_equal(grid([[0, 0], [1, 0]], xx, yy), [[0, 0, 1]])


@pytest.mark.parametrize("points", [
    [[0.5, 0.5]],
    [[0.25, 0.5], [0.75, 0.5]],
    [[0.1, 0.5], [0.5, 0.5], [0.9, 0.5]],
    np.random.default_rng(7).uniform(0, 1, (20, 2)),
])
def test_cells_cover_rectangle_and_are_nearest(points):
    points = np.asarray(points)
    cells = polygons(points, BOUNDS)
    assert sum(map(area, cells)) == pytest.approx(1.0, abs=1e-10)
    for i, cell in enumerate(cells):
        assert len(cell) >= 3
        assert np.all(cell >= -1e-12) and np.all(cell <= 1 + 1e-12)
        distances = ((cell[:, None, :] - points[None, :, :]) ** 2).sum(axis=2)
        assert np.all(distances[:, i, None] <= distances + 1e-10)


def test_two_equal_cells():
    cells = polygons([[0.25, 0.5], [0.75, 0.5]], BOUNDS)
    assert [area(cell) for cell in cells] == pytest.approx([0.5, 0.5])


def test_outside_site_can_have_empty_cell():
    cells = polygons([[0.5, 0.5], [10, 10]], BOUNDS)
    assert area(cells[0]) == pytest.approx(1)
    assert cells[1].shape == (0, 2)


def test_scipy_known_circumcenter():
    result = scipy_voronoi([[0, 0], [1, 0], [0, 1]])
    np.testing.assert_allclose(result.vertices, [[0.5, 0.5]])


def test_scipy_collinear_rejected():
    with pytest.raises(ValueError):
        scipy_voronoi([[0, 0], [1, 0], [2, 0]])


def test_duplicates_rejected():
    with pytest.raises(ValueError):
        polygons([[0, 0], [0, 0]], BOUNDS)
