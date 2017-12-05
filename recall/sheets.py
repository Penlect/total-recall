
import random
import itertools
import time
import math
from collections import namedtuple

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.font_manager import FontProperties
from matplotlib.collections import LineCollection
import numpy as np

A4 = (8.267, 11.692)
Margins = namedtuple('Margins', 'left right top bottom')
FONT = ['Arial']
c = ['C0', 'C1', 'C2', 'C3', 'C4', 'C5', 'C6', 'C7', 'C8', 'C9']


def pairs(seq, step=1):
    seq = list(seq)
    step = int(step)
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


# Remove?
def get_pattern_index(pattern, nr_cols, nr_rows, flip_horizontal,
                      flip_vertical):
    pattern_sum = sum(pattern)
    boundaries = [0] + [s - 1 for s in itertools.accumulate(pattern)]
    bs = list(enumerate((pairs(boundaries, step=1))))
    def index(row_i, col_i):
        if flip_horizontal:
            col_i = nr_cols - 1 - col_i
        if flip_vertical:
            row_i = nr_rows - 1 - row_i
        cell_i = nr_cols*row_i + col_i
        pos = cell_i%pattern_sum
        if pos == 0:
            return 0
        for i, (b0, b1) in bs:
            if b0 < pos <= b1:
                return i
    return index


def add_row_enumeration(ax, item_pos_y, pos_x, start=1, **kwargs):
    for i, y in enumerate(item_pos_y, start=start):
        ax.text(pos_x, y, f'Row {i}', **kwargs)


def add_items(ax, item_pos_x, item_pos_y, data, direction, item_colorer=None,
              **kwargs):
    if direction == 'horizontal':
        x, y = item_pos_x, item_pos_y
    elif direction == 'vertical':
        x, y = item_pos_y, item_pos_x
    else:
        raise ValueError(f'Invalid direction: {direction}')
    if item_colorer is None:
        item_colorer = lambda p, cell_i: 'black'
    nr_cols = len(x)
    for row_i, pos_y in enumerate(y):
        for col_i, pos_x in enumerate(x):
            cell_i = nr_cols * row_i + col_i
            try:
                item = data[cell_i]
            except IndexError:
                return
            else:
                ax.text(pos_x, pos_y, item,
                        color=item_colorer((row_i, col_i), item),
                        **kwargs)


def grid(ax, grid_pos_x, grid_pos_y, pattern, size, direction,
         flip_horizontal=False, flip_vertical=False, **kwargs):
    if flip_horizontal:
        grid_pos_x = list(reversed(grid_pos_x))
    if flip_vertical:
        grid_pos_y = list(reversed(grid_pos_y))
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
    nr_cols = len(x) - 1
    for row_i, (y0, y1) in enumerate(pairs(y, step=size), start=0):
        for col_i, (x0, x1) in enumerate(pairs(x, step=1), start=0):
            cell_i = nr_cols * row_i + col_i
            if col_i == 0 and boundary(cell_i - 1):
                lines.append(np.array([[x0, y0], [x0, y1]], dtype=np.float64))
            if boundary(cell_i):
                lines.append(np.array([[x1, y0], [x1, y1]], dtype=np.float64))
        lines.append(np.array([[min(x), y0], [max(x), y0]]))
    if (row_i + 1)*size == len(y) - 1:
        lines.append(np.array([[min(x), y1], [max(x), y1]]))
    for index in range(len(lines)):
        lines[index] = np.dot(lines[index], transform)
    ax.add_collection(LineCollection(lines, **kwargs))

    pattern_sum = sum(pattern)
    boundaries = [0] + [s - 1 for s in itertools.accumulate(pattern)]
    bs = list(enumerate((pairs(boundaries, step=1))))
    def index(row_i, col_i):
        if flip_horizontal:
            col_i = len(grid_pos_x) - 2 - col_i
        if flip_vertical:
            row_i = len(grid_pos_y) - 2 - row_i
        if direction == 'horizontal':
            row_i //= size
        elif direction == 'vertical':
            col_i //= size
        if direction == 'horizontal':
            cell_i = (len(grid_pos_x) - 1)*row_i + col_i
        elif direction == 'vertical':
            cell_i = (len(grid_pos_y) - 1)*col_i + row_i
        pos = cell_i%pattern_sum
        if pos == 0:
            return 0
        for i, (b0, b1) in bs:
            if b0 < pos <= b1:
                return i
    return index


def header(ax, a, b, title='title', a1='a1', a2='a2', b1='b1', b2='b2'):
    fp_title = FontProperties(family=FONT, size='large')
    fp_header = FontProperties(family=FONT, size='medium')
    ax.text(0.5, 1, title, fontproperties=fp_title, ha='center', va='top')
    ax.text(0, a, a1, fontproperties=fp_header, ha='left')
    ax.text(1, a, a2, fontproperties=fp_header, ha='right')
    ax.text(0, b, b1, fontproperties=fp_header, ha='left')
    ax.text(1, b, b2, fontproperties=fp_header, ha='right')


def digits(digits, pattern=None, size=0, direction='horizontal', nr_cols=40,
           nr_rows=25, wide=False, example=False, item_colors=None,
           bold=False, filename='digits.pdf',
           header_kwargs=None, grid_kwargs=None):
    digits = list(digits)
    if pattern is None:
        pattern = [0]
    if not len(digits) % nr_cols == 0:
        raise ValueError('Nr digits must be a multiple of nr_cols')
    max_nr_cols = 40
    if not 0 < nr_cols <= max_nr_cols:
        raise ValueError(f'Invalid nr_cols: 0 < {nr_cols} <= {max_nr_cols}')
    size = int(size)

    grid_x_start = 0
    grid_x_end = 0.89
    enumeration_offset = 0.03
    m = Margins(left=0.1, right=0.1, top=0.18, bottom=0.1)
    header_m = Margins(left=0.085, right=0.085, top=0.05, bottom=1 - m.top)
    # footer_m = Margins(left=0, right=0, top=0.9, bottom=0)

    grid_y_adjustment = 1 / 1.3
    _pos_y = np.linspace(0, 1, nr_rows + 2)
    if wide:
        _pos_x = np.linspace(grid_x_start, grid_x_end, nr_cols + 2)
    else:
        x = max_nr_cols - nr_cols
        nr_cols_slice = slice(x // 2 + x % 2, - x // 2 if x >= 2 else None)
        _pos_x = np.linspace(grid_x_start, grid_x_end,
                             max_nr_cols + 2)[nr_cols_slice]
    dy = abs(_pos_y[1] - _pos_y[0])
    dx = abs(_pos_x[1] - _pos_x[0])
    item_pos_y = _pos_y[1:-1]
    item_pos_x = _pos_x[1:-1]
    grid_pos_y = _pos_y[0:-1] + grid_y_adjustment * dy / 2
    grid_pos_x = _pos_x[0:-1] + dx / 2

    item_fp = FontProperties(family=FONT,
                             size='medium',
                             weight='bold' if bold else 'normal')
    row_enumeration_fp = FontProperties(family=FONT, size='small')

    pp = PdfPages(filename)
    fig = plt.figure(figsize=A4)

    multipage = len(digits) > nr_rows*nr_cols
    for page_i, i in enumerate(range(0, len(digits), nr_rows*nr_cols)):

        header_ax = fig.add_axes([
            header_m.left,                # Left
            header_m.bottom,              # Bottom
            1 - header_m.left - header_m.right,  # Width
            1 - header_m.top - header_m.bottom   # Height
        ])
        header(header_ax, a=0.7, b=0.55, **header_kwargs)
        header_ax.set_axis_off()

        ax = fig.add_axes([
            m.left,                # Left
            m.bottom,              # Bottom
            1 - m.left - m.right,  # Width
            1 - m.top - m.bottom   # Height
        ])
        ax.set_axis_off()
        ax.set_xlim(0, 1)
        ax.set_ylim(1, 0)

        end_row = math.ceil(len(digits)/nr_cols)
        if sum(pattern) > 0 and size > 0:
            index = grid(ax, grid_pos_x, grid_pos_y[:end_row + 1],
                 pattern, size, direction, **grid_kwargs)
            #index = get_pattern_index(pattern, len(item_pos_x), end_row,
            #                          grid_kwargs['flip_horizontal'],
            #                          grid_kwargs['flip_vertical'])
        def item_colorer(p, item):
            color = c[index(*p)]
            return color

        add_items(
            ax, item_pos_x, item_pos_y,
            data=digits[i:i + nr_rows*nr_cols],
            direction='horizontal',
            item_colorer=item_colorer,
            fontproperties=item_fp,
            horizontalalignment='center'
        )
        item_pos_y = item_pos_y[:end_row]
        add_row_enumeration(
            ax, item_pos_y, max(_pos_x) + enumeration_offset,
            start=1 + page_i*nr_rows,
            fontproperties=row_enumeration_fp,
            horizontalalignment='left'
        )

        if multipage:
            ax.text(0.5, 1.05, str(page_i + 1),
                    fontproperties=item_fp,
                    ha="center")

        if example:
            example_x_pos = (max(item_pos_x) + min(item_pos_x))/2
            example_y_pos = (max(item_pos_y) + min(item_pos_y))/2
            example_y_pos = max(example_y_pos, min(item_pos_y) + dy*6)
            ax.text(
                example_x_pos, example_y_pos, "Example",
                size=70, rotation=45,
                ha="center", va="center", alpha=0.3,
                bbox=dict(boxstyle="round", ec='black', fc='silver', alpha=0.2)
            )

        pp.savefig(fig, figsize=A4)
        fig.clear()

    pp.close()

if __name__ == '__main__':

    x = [random.randint(0, 9) for _ in range(30*12 + 40)]
    header_kwargs = dict(title='Svenska Minnesförbundet',
                         a1='Decimal Numbers; 2320',
                         a2='Memo id: 78',
                         b1='Memo. time: 30 Min',
                         b2='Recall time: 60 Min')
    grid_kwargs = dict(flip_horizontal=False,
                       flip_vertical=False,
                       linewidth=0.1,
                       color='black')
    item_colors = {0: 'black', 1: 'red', 2: 'blue', 3: 'brown', 4: 'green'}

    digits(x, [3, 5, 3], 2, 'horizontal', nr_cols=40, example=False,
           item_colors=item_colors,
           header_kwargs=header_kwargs, grid_kwargs=grid_kwargs)