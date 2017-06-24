

import xlwt
import xls.base


NR_ITEMS_ROW   = 40
NR_ITEMS_COL   = 25
NR_ITEMS_PER_PAGE = NR_ITEMS_ROW * NR_ITEMS_COL
NR_PAGE_ROWS   = 34 # Depends on cell heights!
NR_PAGE_COLS   = 43
NR_ROWS_HEADER = 4

WIDTH_NUMBER  = xls.base.convert_row_width(0.381)
WIDTH_KEY   = xls.base.convert_row_width(4)

HEIGHT_ROW  = xls.base.convert_row_height(0.79)

# Syntax: (<element>:(<attribute> <value>,)+;)+
style_number = xlwt.easyxf(
    'font: name Arial, height 180;'
    'alignment: horizontal center;'
)


class NumberTable(xls.base.RecallTable):

    def __init__(self, *, name, recall_key, title='Svenska Minnesförbundet',
                 recall_time='X', language='Decimal'):
        super().__init__(name, recall_key, title, recall_time, language,
                         NR_ITEMS_PER_PAGE, NR_PAGE_ROWS, NR_PAGE_COLS,
                         HEIGHT_ROW, 4)
        self.sheet.portrait = True

        self.sheet.col(0).width = WIDTH_NUMBER
        self.sheet.col(1).width = WIDTH_NUMBER
        for i in range(NR_ITEMS_ROW):
            self.sheet.col(i + 2).width = WIDTH_NUMBER
        self.sheet.col(NR_ITEMS_ROW + 3).width = HEIGHT_ROW

        self._update_page()

    def add_item(self, item):
        col = self.nr_items % NR_ITEMS_ROW
        row = (self.nr_items % NR_ITEMS_PER_PAGE) // NR_ITEMS_ROW + self.page_offset + NR_ROWS_HEADER

        self.sheet.write(row, col + 2, str(item), style_number)
        if col == 2:
            self.sheet.write(row, NR_ITEMS_ROW + 2, f'Row {self.nr_items//NR_ITEMS_ROW + 1}', style_number)

        self.nr_items += 1
        self._update_page()


if __name__ == '__main__':
    import random
    numbers = [random.randint(0,9) for _ in range(1234)]

    w = NumberTable(name='Numbers', recall_key='abc123')

    for n in numbers:
        w.add_item(n)

    w.save('numbers.xls')