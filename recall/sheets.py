
import random
import itertools

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.font_manager import FontProperties
from matplotlib.collections import LineCollection
import numpy as np

pp = PdfPages('multipage.pdf')

A4 = (8.267, 11.692)
fig = plt.figure(figsize=A4)

LEFT_MARGIN, RIGHT_MARGIN = 0.1, 0.1
TOP_MARGIN, BOTTOM_MARGIN = 0.1, 0.15
H_LINES_ADJUSTMENT = 1/1.3

left = LEFT_MARGIN
right = RIGHT_MARGIN
width = 1 - left - right
height = 1 - TOP_MARGIN - BOTTOM_MARGIN

ax = fig.add_axes([left, right, width, height])

ax.set_axis_off()
# ax.plot([0, 1], [0, 1])
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)

nr_rows = 25
nr_cols = 40
_pos_y = np.linspace(1, 0, nr_rows + 2)
_pos_x = np.linspace(0, 0.9, nr_cols + 2)
dy = abs(_pos_y[1] - _pos_y[0])
dx = abs(_pos_x[1] - _pos_x[0])
item_pos_y = _pos_y[1:-1]
item_pos_x = _pos_x[1:-1]
border_pos_y = _pos_y[0:-1] - H_LINES_ADJUSTMENT*dy/2
border_pos_x = _pos_x[0:-1] + dx/2

fp = FontProperties(family=['Arial'])
row_count_font = FontProperties(family=['Arial'], size='small')

# ROW ENUMERATION
for i, y in enumerate(item_pos_y, start=1):
    ax.text(0.915, y, f'Row {i}', fontproperties=row_count_font, ha='left')

# ITEM DATA GRID
for y in item_pos_y:
    for x in item_pos_x:
        ax.text(x, y, str(random.randint(0, 9)), fontproperties=fp, ha='center')


def pairs(seq, step=1):
    for i in range(0, len(seq) - step, step):
        yield (seq[i], seq[i + step])
    if seq[i + step] != seq[-1]:
        yield (seq[i + step], seq[-1])

pattern = [3]
width = 3
height = 1

# H LINES


def get_boundary_finder(pattern):
    pattern_sum = sum(pattern)
    boundaries = {s - 1 for s in itertools.accumulate(pattern)}
    def boundary(cell_i):
        return cell_i%pattern_sum in boundaries
    return boundary

boundary = get_boundary_finder(pattern)

for i, x in enumerate(border_pos_x):
    if i%width == 0:
        ax.plot([x, x], [min(border_pos_y), max(border_pos_y)], lw=0.1, color='black')

lines = list()
for row_i, (y0, y1) in enumerate(pairs(border_pos_y, step=height), start=0):
    for col_i, (x0, x1) in enumerate(pairs(border_pos_x, step=width), start=0):
        cell_i = nr_rows * col_i + row_i
        print(cell_i, boundary(cell_i))
        if cell_i == 0:
            lines.append(([x0, y0], [x1, y0]))
        elif row_i == 0 and boundary(cell_i - 1):
            lines.append(([x0, y0], [x1, y0]))
        elif boundary(cell_i):
            lines.append(([x0, y1], [x1, y1]))
ax.add_collection(LineCollection(lines, lw=0.1, color='black'))

# V LINES
def lol():
    for i, y in enumerate(border_pos_y):
        if i%height == 0:
            ax.plot([min(border_pos_x), max(border_pos_x)], [y, y], lw=0.1, color='black')

    lines = list()
    for col_i, (x0, x1) in enumerate(pairs(border_pos_x, step=width), start=0):
        for row_i, (y0, y1) in enumerate(pairs(border_pos_y, step=height), start=0):
            cell_i = nr_cols*row_i + col_i
            if cell_i == 0:
                lines.append(([x0, y0], [x0, y1]))
            elif col_i == 0 and boundary(cell_i - 1):
                lines.append(([x0, y0], [x0, y1]))
            elif boundary(cell_i):
                lines.append(([x1, y0], [x1, y1]))
    ax.add_collection(LineCollection(lines, lw=0.1, color='black'))

pp.savefig(fig, figsize=(8.27, 11.69))
fig.clear()


pp.savefig(fig, figsize=(8.27, 11.69))

pp.close()