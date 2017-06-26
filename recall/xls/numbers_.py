

import xlwt
import recall.xls.base


NR_ITEMS_ROW   = 40
NR_ITEMS_COL   = 25
NR_ITEMS_PER_PAGE = NR_ITEMS_ROW * NR_ITEMS_COL
NR_PAGE_ROWS   = 34 # Depends on cell heights!
NR_PAGE_COLS   = 43
NR_ROWS_HEADER = 4

WIDTH_NUMBER  = recall.xls.base.convert_row_width(0.381)
WIDTH_KEY   = recall.xls.base.convert_row_width(4)

HEIGHT_ROW  = recall.xls.base.convert_row_height(0.79)

LEFT_OFFSET = 2

# Syntax: (<element>:(<attribute> <value>,)+;)+
style_number = xlwt.easyxf(
    'font: name Arial, height 180;'
    'alignment: horizontal center;'
)


class NumberTable(recall.xls.base.RecallTable):

    def __init__(self, *, name, recall_key, title, description):
        super().__init__(name, recall_key, title, description,
                         NR_ITEMS_PER_PAGE, NR_PAGE_ROWS, NR_PAGE_COLS,
                         HEIGHT_ROW, 4)
        self.sheet.portrait = True

        for i in range(LEFT_OFFSET):
            self.sheet.col(i).width = WIDTH_NUMBER

        for i in range(NR_ITEMS_ROW):
            self.sheet.col(i + LEFT_OFFSET).width = WIDTH_NUMBER
        self.sheet.col(NR_ITEMS_ROW + LEFT_OFFSET + 1).width = HEIGHT_ROW

        self._update_page()

    def add_item(self, item):
        col = self.nr_items % NR_ITEMS_ROW
        row = (self.nr_items % NR_ITEMS_PER_PAGE) // NR_ITEMS_ROW + self.page_offset + NR_ROWS_HEADER

        self.sheet.write(row, col + LEFT_OFFSET, str(item), style_number)
        if col == LEFT_OFFSET:
            self.sheet.write(row, NR_ITEMS_ROW + LEFT_OFFSET, f'Row {self.nr_items//NR_ITEMS_ROW + 1}', style_number)

        self._update_page()
        self.nr_items += 1


if __name__ == '__main__':
    import random
    numbers = [random.randint(0,9) for _ in range(1234)]

    w = NumberTable(name='Numbers', recall_key='abc123',
                    title='Svenska Minnesförbundet',
                    description='Word description')

    for n in numbers:
        w.add_item(n)

    w.save('numbers.xls')