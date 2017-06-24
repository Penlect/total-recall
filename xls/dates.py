

import xlwt
import xls.base


NR_ITEMS_ROW   = 40
NR_ITEMS_COL   = 1
NR_ITEMS_PER_PAGE = NR_ITEMS_ROW * NR_ITEMS_COL
NR_PAGE_ROWS   = 49 # Depends on cell heights!
NR_PAGE_COLS   = 5
NR_ROWS_HEADER = 4

WIDTH_INDEX = xls.base.convert_row_width(1.5)
WIDTH_DATE  = xls.base.convert_row_width(3)
WIDTH_GAP   = xls.base.convert_row_width(0.4)
WIDTH_STORY = xls.base.convert_row_width(10)
WIDTH_KEY   = xls.base.convert_row_width(4)

HEIGHT_ROW  = xls.base.convert_row_height(0.55)

# Syntax: (<element>:(<attribute> <value>,)+;)+
style_index = xlwt.easyxf(
    'font: name Arial, height 220;'
    'alignment: horizontal right;'
)
style_date = xlwt.easyxf(
    'font: name Arial, height 220;'
    'alignment: horizontal right;'
)
style_gap = xlwt.easyxf(
    'font: name Arial, height 220;'
)
style_story = xlwt.easyxf(
    'font: name Arial, height 220;'
    'alignment: horizontal left;'
)

class DatesTable(xls.base.RecallTable):

    def __init__(self, *, name, recall_key, title='Svenska Minnesförbundet',
                 recall_time='X', language='Unknown Language'):
        super().__init__(name, recall_key, title, recall_time, language,
                         NR_ITEMS_PER_PAGE, NR_PAGE_ROWS, NR_PAGE_COLS,
                         HEIGHT_ROW)
        self.sheet.portrait = True

        self.sheet.col(0).width = WIDTH_INDEX
        self.sheet.col(1).width = WIDTH_DATE
        self.sheet.col(2).width = WIDTH_GAP
        self.sheet.col(3).width = WIDTH_STORY
        self.sheet.col(4).width = WIDTH_KEY

        self._update_page()

    def add_item(self, item):
        row = self.nr_items % NR_ITEMS_ROW + self.page_offset + NR_ROWS_HEADER

        date, story = item
        self.sheet.write(row, 0, str(self.nr_items + 1), style_index)
        self.sheet.write(row, 1, str(date), style_date)
        self.sheet.write(row, 3, story, style_story)

        self.nr_items += 1
        self._update_page()


if __name__ == '__main__':
    import random
    dates = [
        (random.randint(1000,2099), 'Drottning gifter om sig'),
        (random.randint(1000,2099), 'Politiker slåss i parlament'),
        (random.randint(1000,2099), 'Wimbledon ställs in'),
        (random.randint(1000,2099), 'Hangarfartyg sjunker'),
        (random.randint(1000,2099), 'Fotbolls VM ställs in'),
        (random.randint(1000,2099), 'Jorden får nytt ekosystem'),
        (random.randint(1000,2099), 'Nyheter på TV upphör'),
    ]

    w = DatesTable(name='Dates', recall_key='abc123')

    for _ in range(20*5*5 + 23):
        w.add_item(random.choice(dates))

    w.save('historical_dates.xls')