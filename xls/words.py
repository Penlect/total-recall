

import xlwt
from xlwt import Workbook


def convert_row_width(cm):
    return round(1000*cm/0.77)


def convert_row_height(cm):
    return round(1000*cm/1.76)

NR_ROWS_WORDS = 20
NR_COLUMNS_WORDS = 5
NR_WORDS_PER_PAGE = NR_ROWS_WORDS*NR_COLUMNS_WORDS
NR_ROWS_PAGE = 28 # Depends on cell heights!
NR_COLUMNS_PAGE = NR_COLUMNS_WORDS
NR_ROWS_HEADER = 4

WIDTH_INDEX = convert_row_width(1)
WIDTH_GAP   = convert_row_width(0.36)
WIDTH_WORD  = convert_row_width(3.7)

HEIGHT_ROW = convert_row_height(0.65)

# Syntax: (<element>:(<attribute> <value>,)+;)+
style_title = xlwt.easyxf(
    'font: name Arial, height 220;'
    'alignment: horizontal center;'
)
style_header = xlwt.easyxf(
    'font: italic True;'
)
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

class WordTable:

    def __init__(self, *, name, recall_key, title='Svenska Minnesförbundet',
                 language='Unknown Language', recall_time='X'):
        self.recall_key = recall_key
        self.title = title
        self.language = language
        self.recall_time = recall_time
        self.book = Workbook(name)
        self.sheet = self.book.add_sheet(name)
        self.nr_words = 0
        self.page = None
        self.page_offset = None

        for i in range(NR_COLUMNS_WORDS):
            self.sheet.col(i*3).width = WIDTH_INDEX
            self.sheet.col(i*3 + 1).width = WIDTH_GAP
            self.sheet.col(i*3 + 2).width = WIDTH_WORD

        self._update_page()

    def add_word(self, word):
        row = self.nr_words%NR_ROWS_WORDS + self.page_offset + NR_ROWS_HEADER
        col = 3*((self.nr_words%NR_WORDS_PER_PAGE)//NR_ROWS_WORDS)

        self.sheet.write(row, col, str(self.nr_words + 1), style_index)
        self.sheet.write(row, col + 1, '', style_gap)
        self.sheet.write(row, col + 2, word, style_word)

        self.nr_words += 1
        self._update_page()

    def _update_page(self):
        prev_page = self.page
        self.page = self.nr_words//NR_WORDS_PER_PAGE
        self.page_offset = self.page*NR_ROWS_PAGE

        if prev_page != self.page:
            for i in range(self.page_offset, self.page_offset + NR_ROWS_PAGE):
                self.sheet.row(i).height_mismatch = True
                self.sheet.row(i).height = HEIGHT_ROW
            self._write_header()

    def _write_header(self):
        self.sheet.write_merge(
            self.page_offset,
            self.page_offset,
            0,
            3*NR_COLUMNS_PAGE - 1,
            self.title,
            style_title
        )
        self.sheet.write(
            self.page_offset + 1,
            0,
            f'{self.recall_time} Min Words Memorization, {self.language}',
            style_header
        )
        self.sheet.write(
            self.page_offset + 1,
            3 * NR_COLUMNS_PAGE - 1,
            f'Recall key: {self.recall_key}',
            style_header
        )

    def save(self, filename):
        self.book.save(filename)


if __name__ == '__main__':
    import random
    words = ['dator', 'kortlek', 'vattenfall', 'bacon', 'pizza']

    w = WordTable(name='Words', recall_key='abc123')

    for _ in range(20*5*5 + 23):
        w.add_word(random.choice(words))

    w.save('simple_class.xls')