

import xlwt
import xls.base


NR_ITEMS_ROW   = 20
NR_ITEMS_COL   = 5
NR_ITEMS_PER_PAGE = NR_ITEMS_ROW * NR_ITEMS_COL
NR_PAGE_ROWS   = 28 # Depends on cell heights!
NR_PAGE_COLS   = 3 * NR_ITEMS_COL
NR_ROWS_HEADER = 4

WIDTH_INDEX = xls.base.convert_row_width(1)
WIDTH_GAP   = xls.base.convert_row_width(0.36)
WIDTH_WORD  = xls.base.convert_row_width(3.7)

HEIGHT_ROW  = xls.base.convert_row_height(0.65)

# Syntax: (<element>:(<attribute> <value>,)+;)+
style_index = xlwt.easyxf(
    'font: name Arial, height 220;'
    'alignment: horizontal right;'
    'borders: left hair, top hair, bottom hair'
)
style_gap = xlwt.easyxf(
    'font: name Arial, height 220;'
    'alignment: horizontal left;'
    'borders: top hair, bottom hair'
)
style_word = xlwt.easyxf(
    'font: name Arial, height 220;'
    'alignment: horizontal left;'
    'borders: right hair, top hair, bottom hair'
)


class WordTable(xls.base.RecallTable):

    def __init__(self, *, name, recall_key, title, description):
        super().__init__(name, recall_key, title, description,
                         NR_ITEMS_PER_PAGE, NR_PAGE_ROWS, NR_PAGE_COLS,
                         HEIGHT_ROW)
        self.sheet.portrait = False

        for i in range(NR_ITEMS_COL):
            self.sheet.col(i*3).width = WIDTH_INDEX
            self.sheet.col(i*3 + 1).width = WIDTH_GAP
            self.sheet.col(i*3 + 2).width = WIDTH_WORD

        self._update_page()

    def add_item(self, item):
        row = self.nr_items % NR_ITEMS_ROW + self.page_offset + NR_ROWS_HEADER
        col = 3*((self.nr_items % NR_ITEMS_PER_PAGE) // NR_ITEMS_ROW)

        self.sheet.write(row, col, str(self.nr_items + 1), style_index)
        self.sheet.write(row, col + 1, '', style_gap)
        self.sheet.write(row, col + 2, item, style_word)

        self.nr_items += 1
        self._update_page()


if __name__ == '__main__':
    import random
    words = ['dator', 'kortlek', 'vattenfall', 'bacon', 'pizza']

    w = WordTable(name='Words', recall_key='abc123',
                  title='Svenska Minnesförbundet',
                  description='Word description')

    for _ in range(20*5*5 + 23):
        w.add_item(random.choice(words))

    w.save('words.xls')