import matplotlib.pyplot as plt
import numpy as np
import pytest
from spatial_vtk.visualize.fit import scatter_fit_label
from spatial_vtk.spatial.plot.metrics import _scatter_fit_label
from spatial_vtk.visualize.figure_context import add_below_axes_table


@pytest.mark.parametrize('labeler', [scatter_fit_label, _scatter_fit_label])
@pytest.mark.parametrize('method', ['lowess', 'best:lowess'])
def test_lowess_legend_does_not_imply_a_single_slope(labeler, method):
    x = np.arange(5.)
    assert labeler(method, x, x*x, x, x*x, label='PGA') == 'PGA LOWESS trend'
    assert 'slope=' in labeler('linear', x, 2*x, x, 2*x, label='PGA')


def test_table_clears_rotated_labels_and_has_readable_row_height():
    fig, ax = plt.subplots(figsize=(8, 5), dpi=120)
    ax.set_xticks([0, 1], ['LA Basin', 'Santa Monica Mountains'], rotation=22)
    ax.set_xlabel('Station region')
    add_below_axes_table(ax, rows=[['PGA: Mountains - Basin', '+0.1']] * 6,
                         columns=['Comparison', 'Effect'], font_size=8)
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    table = list(ax.tables)[0]
    table_box = table.get_window_extent(renderer)
    labels = [*ax.get_xticklabels(), ax.xaxis.label]
    assert table_box.y1 < min(label.get_window_extent(renderer).y0 for label in labels) - 10
    assert all(cell.get_window_extent(renderer).height >= .27 * fig.dpi for cell in table.get_celld().values())
    assert table_box.y0 >= 0
    plt.close(fig)
