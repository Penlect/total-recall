
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

class InvalidPattern(Exception):
    pass


class Pattern:
    def __init__(self, pattern, size=1, color=''):
        if isinstance(pattern, str):
            try:
                self.pattern = [int(pattern)]
            except ValueError:
                raise InvalidPattern(f'Invalid Pattern: "{pattern}"')
        elif isinstance(pattern, int):
            self.pattern = [pattern]
        else:
            self.pattern = pattern
        self.size = int(size)
        if isinstance(color, str):
            self.color = [color]*len(pattern)
        else:
            self.color = color
        if sum(self.pattern) > 0 and len(self.pattern) != len(self.color):
            raise InvalidPattern(f'Pattern and color length does not match')

        self._sum = sum(self.pattern)
        acc = list(itertools.accumulate(self.pattern))
        self._endpoints = {s - 1 for s in acc}
        self._boundaries = [0] + [s - 1 for s in acc]
        self._boundary_pairs = list(enumerate((pairs(self._boundaries, step=1))))

    def __repr__(self):
        return f'Pattern({self.pattern!r}, {self.size!r}, {self.color!r})'

    def __str__(self):
        pc = ', '.join(f'{p}:{c}' if c else str(p)
                       for p, c in zip(self.pattern, self.color))
        return f'Pattern([{pc}]; size={self.size})'

    @classmethod
    def from_string(cls, pattern_with_colors, size=1):
        pattern = list()
        color = list()
        for n, c in pattern_with_colors.split(':'):
            pattern.append(int(n))
            color.append(c.lower().strip())
        return cls(pattern, size, color)

    def is_at_boundary(self, cell_i):
        if self._sum == 0 or self.size == 0:
            return False
        return cell_i < 0 or cell_i%self._sum in self._endpoints

    def get_index_color(self, nr_cols, nr_rows, direction, flip_horizontal,
                        flip_vertical):
        def index_color(row_i, col_i):
            if flip_horizontal:
                col_i = nr_cols - 1 - col_i
            if flip_vertical:
                row_i = nr_rows - 1 - row_i
            if direction == 'horizontal':
                row_i //= max(abs(self.size), 1)
            elif direction == 'vertical':
                col_i //= max(abs(self.size), 1)
            else:
                raise ValueError(f'Invalid direction: {direction}')
            if direction == 'horizontal':
                cell_i = nr_cols*row_i + col_i
            elif direction == 'vertical':
                cell_i = nr_rows*col_i + row_i
            else:
                raise ValueError(f'Invalid direction: {direction}')
            pos = cell_i%self._sum
            if pos == 0:
                return self.color[0]
            for i, (b0, b1) in self._boundary_pairs:
                if b0 < pos <= b1:
                    return self.color[i]
        return index_color


def pairs(seq, step=1):
    seq = list(seq)
    step = int(step)
    if step >= len(seq):
        return (seq[0], seq[-1])
    for i in range(0, len(seq) - step, step):
        yield (seq[i], seq[i + step])
    if seq and seq[i + step] != seq[-1]:
        yield (seq[i + step], seq[-1])


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


def add_grid(ax, grid_pos_x, grid_pos_y, direction, pattern=None,
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
    lines = list()
    nr_cols = len(x) - 1
    step_size = max(abs(pattern.size), 1)
    for row_i, (y0, y1) in enumerate(pairs(y, step=step_size), start=0):
        for col_i, (x0, x1) in enumerate(pairs(x, step=1), start=0):
            cell_i = nr_cols * row_i + col_i
            if col_i == 0 and pattern.is_at_boundary(cell_i - 1):
                lines.append(np.array([[x0, y0], [x0, y1]], dtype=np.float64))
            if pattern.is_at_boundary(cell_i):
                lines.append(np.array([[x1, y0], [x1, y1]], dtype=np.float64))
        if pattern.size > 0:
            lines.append(np.array([[min(x), y0], [max(x), y0]]))
    if pattern.size > 0 and (row_i + 1)*pattern.size == len(y) - 1:
        lines.append(np.array([[min(x), y1], [max(x), y1]]))
    for index in range(len(lines)):
        lines[index] = np.dot(lines[index], transform)
    ax.add_collection(LineCollection(lines, **kwargs))
    return pattern.get_index_color(len(grid_pos_x) - 1, len(grid_pos_y) - 1,
                                   direction, flip_horizontal, flip_vertical)


def header(ax, a, b, title='title', a1='a1', a2='a2', b1='b1', b2='b2'):
    fp_title = FontProperties(family=FONT, size='large')
    fp_header = FontProperties(family=FONT, size='medium')
    ax.text(0.5, 1, title, fontproperties=fp_title, ha='center', va='top')
    ax.text(0, a, a1, fontproperties=fp_header, ha='left')
    ax.text(1, a, a2, fontproperties=fp_header, ha='right')
    ax.text(0, b, b1, fontproperties=fp_header, ha='left')
    ax.text(1, b, b2, fontproperties=fp_header, ha='right')


def digits(digits, direction='horizontal', nr_cols=40, nr_rows=25, wide=False,
           example=False, item_colors=None, bold=False, filename='digits',
           header_kwargs=None, grid_kwargs=None, print_parameters=False,
           target='pdf'):
    digits = list(digits)
    if not len(digits) % nr_cols == 0:
        raise ValueError('Nr digits must be a multiple of nr_cols')
    max_nr_cols = 40
    if not 0 < nr_cols <= max_nr_cols:
        raise ValueError(f'Invalid nr_cols: 0 < {nr_cols} <= {max_nr_cols}')
    if target not in {'pdf', 'png'}:
        raise ValueError(f'Invalid target: "{target}"')

    grid_x_start = 0
    grid_x_end = 0.89
    enumeration_offset = 0.03
    m = Margins(left=0.1, right=0.1, top=0.18, bottom=0.1)
    header_m = Margins(left=0.085, right=0.085, top=0.05, bottom=1 - m.top)

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

    item_fp = FontProperties(family=FONT, size='medium',
                             weight='bold' if bold else 'normal')
    row_enumeration_fp = FontProperties(family=FONT, size='small')

    if target == 'pdf':
        pp = PdfPages(f'{filename}.pdf')
    fig = plt.figure(figsize=A4)

    multipage = len(digits) > nr_rows*nr_cols
    for page_i, i in enumerate(range(0, len(digits), nr_rows*nr_cols)):

        header_ax = fig.add_axes([
            header_m.left,                       # Left
            header_m.bottom,                     # Bottom
            1 - header_m.left - header_m.right,  # Width
            1 - header_m.top - header_m.bottom   # Height
        ])
        header(header_ax, a=0.7, b=0.55, **header_kwargs)

        if print_parameters:
            x = min(item_pos_x)
            header_ax.text(x, 0.35,
            f'direction={direction}, nr_cols={nr_cols}, nr_rows={nr_rows}, '
            f'wide={wide}, example={example}, bold={bold}', size='small')
            header_ax.text(x, 0.25, str(item_colors), size='small')
            header_ax.text(x, 0.15, str(grid_kwargs['pattern']), size='small')
            header_ax.text(x, 0.05,
            'flip_h={flip_horizontal}, flip_v={flip_vertical}, '
            'linewidth={linewidth}, color={color}'.format(**grid_kwargs),
            size='small')

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

        nr_digits_on_this_page = min(nr_rows*nr_cols,
                                     len(digits) - page_i*nr_rows*nr_cols)
        end_row = math.ceil(nr_digits_on_this_page/nr_cols)
        index_color = add_grid(ax, grid_pos_x, grid_pos_y[:end_row + 1],
                               direction, **grid_kwargs)


        def item_colorer(p, item):
            color = index_color(*p)
            if color:
                return color
            else:
                return item_colors.get(item, 'black')

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

        if target == 'pdf':
            pp.savefig(fig, figsize=A4)
        elif target == 'png':
            fig.savefig(f'{filename}_{page_i}.png', dpi=200)
        fig.clear()

    if target == 'pdf':
        pp.close()

if __name__ == '__main__':

    x = [random.randint(0, 9) for _ in range(1600)]

    p = Pattern([11, 3], 2, ['blue', 'yellow'])

    header_kwargs = dict(title='Svenska Minnesförbundet',
                         a1='Decimal Numbers; 2320',
                         a2='Memo id: 78',
                         b1='Memo. time: 30 Min',
                         b2='Recall time: 60 Min')
    grid_kwargs = dict(pattern=p,
                       flip_horizontal=True,
                       flip_vertical=True,
                       linewidth=0.1,
                       color='black')
    item_colors = {0: 'black', 1: 'red', 2: 'blue', 3: 'brown', 4: 'green'}


    digits(x, direction='horizontal', nr_cols=40, example=False,
           item_colors=item_colors, print_parameters=False,
           header_kwargs=header_kwargs, grid_kwargs=grid_kwargs,
           target='pdf')