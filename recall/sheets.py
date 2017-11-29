
import random
import itertools
import time
from collections import namedtuple

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.font_manager import FontProperties
from matplotlib.collections import LineCollection
import numpy as np

A4 = (8.267, 11.692)
Margins = namedtuple('Margins', 'left right top bottom')


def add_row_enumeration(ax, item_pos_y, pos_x, start=1, **kwargs):
    for i, y in enumerate(item_pos_y, start=start):
        ax.text(pos_x, y, f'Row {i}', **kwargs)


def add_items(ax, item_pos_x, item_pos_y, data, direction, **kwargs):
    if direction == 'horizontal':
        x, y = item_pos_x, item_pos_y
    elif direction == 'vertical':
        x, y = item_pos_y, item_pos_x
    else:
        raise ValueError(f'Invalid direction: {direction}')

    nr_rows = len(y)
    nr_cols = len(x)
    last_nonempty_pos = (0, 0)
    for row_i, pos_y in enumerate(y):
        for col_i, pos_x in enumerate(x):
            cell_i = nr_cols * row_i + col_i
            item = data(cell_i)
            if item is None:
                return last_nonempty_pos
            else:
                ax.text(pos_x, pos_y, item, **kwargs)
                last_nonempty_pos = (row_i, col_i)
    return nr_rows - 1, nr_cols - 1


def pairs(seq, step=1):
    seq = list(seq)
    for i in range(0, len(seq) - step, step):
        yield (seq[i], seq[i + step])
    if seq and seq[i + step] != seq[-1]:
        yield (seq[i + step], seq[-1])


def get_boundary_finder(pattern):
    pattern_sum = sum(pattern)
    boundaries = {s - 1 for s in itertools.accumulate(pattern)}
    def boundary(cell_i):
        return cell_i < 0 or cell_i%pattern_sum in boundaries
    return boundary


def grid(ax, grid_pos_x, grid_pos_y, pattern, size, direction, max_row, max_col):
    if direction == 'horizontal':
        x, y = grid_pos_x, grid_pos_y
        transform = np.array([[1, 0],
                              [0, 1]], dtype=np.float64)
    elif direction == 'vertical':
        x, y = grid_pos_y, grid_pos_x
        transform = np.array([[0, 1],
                              [1, 0]], dtype=np.float64)
    else:
        raise ValueError(f'Invalid direction: {direction}')
    boundary = get_boundary_finder(pattern)
    lines = list()
    nr_cols = len(x)
    for row_i, (y0, y1) in enumerate(pairs(y, step=size), start=0):
        for col_i, (x0, x1) in enumerate(pairs(x, step=1), start=0):
            cell_i = (nr_cols - 1) * row_i + col_i
            if col_i == 0 and boundary(cell_i - 1):
                lines.append(np.array([[x0, y0], [x0, y1]], dtype=np.float64))
            if boundary(cell_i):
                lines.append(np.array([[x1, y0], [x1, y1]], dtype=np.float64))
        lines.append(np.array([[min(x), y0], [max(x), y0]]))
    if (row_i + 1)*size == len(y) - 1:
        lines.append(np.array([[min(x), y1], [max(x), y1]]))



    for index in range(len(lines)):
        lines[index] = np.dot(lines[index], transform)
    ax.add_collection(LineCollection(lines, lw=0.1, color='black'))


def digits(digits, pattern, size, direction='horizontal'):
    grid_y_adjustment = 1 / 1.3
    nr_rows = 25
    nr_cols = 40
    _pos_y = np.linspace(0, 1, nr_rows + 2)
    _pos_x = np.linspace(0, 0.9, nr_cols + 2)
    dy = abs(_pos_y[1] - _pos_y[0])
    dx = abs(_pos_x[1] - _pos_x[0])
    item_pos_y = _pos_y[1:-1]
    item_pos_x = _pos_x[1:-1]
    grid_pos_y = _pos_y[0:-1] + grid_y_adjustment * dy / 2
    grid_pos_x = _pos_x[0:-1] + dx / 2

    pp = PdfPages('multipage.pdf')
    fig = plt.figure(figsize=A4)
    m = Margins(left=0.1, right=0.1, top=0.15, bottom=0.1)
    ax = fig.add_axes([
        m.left,  # Left
        m.right,  # Right
        1 - m.left - m.right,  # Width
        1 - m.top - m.bottom  # Height
    ])
    ax.set_axis_off()
    ax.set_xlim(0, 1)
    ax.set_ylim(1, 0)

    BINARY = slice(5, -5)
    def data(cell_i):
        try:
            return digits[cell_i]
        except IndexError:
            return None

    item_fp = FontProperties(family=['Arial'])
    row_enumeration_fp = FontProperties(family=['Arial'], size='small')

    row_i, col_i = add_items(ax, item_pos_x, item_pos_y,
              data=data, direction='horizontal',
              fontproperties=item_fp, ha='center')
    add_row_enumeration(ax, item_pos_y[:row_i + 1], max(_pos_x) + 0.015, start=1,
                        fontproperties=row_enumeration_fp, ha='left')
    grid(ax, grid_pos_x, grid_pos_y[:row_i + 2], pattern, size, direction, row_i, col_i)

    pp.savefig(fig, figsize=(8.27, 11.69))
    fig.clear()

    pp.savefig(fig, figsize=(8.27, 11.69))
    pp.close()


if __name__ == '__main__':
    digits([0,1,2,3,4,5,6,7,8,9]*68, [3], 6, 'vertical')