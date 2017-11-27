
import matplotlib

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.font_manager import FontProperties
import matplotlib.ticker as mticker
import matplotlib.font_manager as font_manager
import random
import numpy as np

pp = PdfPages('multipage.pdf')

A4 = (8.27, 11.69)
fig = plt.figure(figsize=A4)

ax = fig.add_axes([0.1, 0.1, 0.80, 0.75])

ax.set_axis_off()

ax.plot([0, 1], [0, 1])
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)

nr_rows = 25
nr_cols = 40
_pos_y = np.linspace(0, 1, nr_rows + 2)
_pos_x = np.linspace(0, 0.9, nr_cols + 2)
dy = _pos_y[1] - _pos_y[0]
dx = _pos_x[1] - _pos_x[0]
item_pos_y = _pos_y[1:-1]
item_pos_x = _pos_x[1:-1]
border_pos_y = _pos_y[0:-1] + 1.3*dy/2
print(border_pos_y)
border_pos_x = _pos_x[0:-1] + dx/2

fp = FontProperties(family=['Arial'])
row_count_font = FontProperties(family=['Arial'], size='small')

for i, y in enumerate(reversed(item_pos_y), start=1):
    ax.text(0.92, y, f'Row {i}', fontproperties=row_count_font, ha='left')

for y in reversed(item_pos_y):
    for x in item_pos_x:
        ax.text(x, y, str(random.randint(0, 9)), fontproperties=fp, ha='center')

for y in border_pos_y:
    ax.plot([min(border_pos_x), max(border_pos_x)], [y, y], lw=0.1, color='black')

for x in border_pos_x:
    ax.plot([x, x], [min(border_pos_y), max(border_pos_y)], lw=0.1, color='black')

pp.savefig(fig, figsize=(8.27, 11.69))

fig.clear()

ax = fig.add_axes([0.1, 0.1, 0.80, 0.75])

ax.set_axis_off()

ax.plot([0, 1], [0, 1])
ax.set_xlim(0, 1)
ax.set_ylim(0, 1)

nr_rows = 25
nr_cols = 40
_pos_y = np.linspace(0, 1, nr_rows + 2)
_pos_x = np.linspace(0, 0.9, nr_cols + 2)
dy = _pos_y[1] - _pos_y[0]
dx = _pos_x[1] - _pos_x[0]
item_pos_y = _pos_y[1:-1]
item_pos_x = _pos_x[1:-1]
border_pos_y = _pos_y[0:-1] + 1.3*dy/2
print(border_pos_y)
border_pos_x = _pos_x[0:-1] + dx/2

fp = FontProperties(family=['Arial'])
row_count_font = FontProperties(family=['Arial'], size='small')

for i, y in enumerate(reversed(item_pos_y), start=1):
    ax.text(0.92, y, f'Row {i}', fontproperties=row_count_font, ha='left')

for y in reversed(item_pos_y):
    for x in item_pos_x:
        ax.text(x, y, str(random.randint(0, 9)), fontproperties=fp, ha='center')

pp.savefig(fig, figsize=(8.27, 11.69))

pp.close()