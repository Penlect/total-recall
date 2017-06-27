

import itertools
import xlwt


def convert_row_width(cm):
    return round(1000*cm/0.77)


def convert_row_height(cm):
    return round(1000*cm/1.76)


class Table:

    style_item_normal = xlwt.easyxf()
    style_item_single = xlwt.easyxf()
    style_item_start = xlwt.easyxf()
    style_item_middle = xlwt.easyxf()
    style_item_stop = xlwt.easyxf()

    def __init__(
            self,
            name,

            nr_header_rows,
            nr_item_rows,
            nr_page_rows,

            left_padding,
            nr_item_cols,
            nr_page_cols,

            item_width,
            item_height,

            pattern
    ):
        assert nr_page_rows >= nr_item_rows + nr_header_rows
        self.nr_header_rows = nr_header_rows
        self.nr_item_rows = nr_item_rows
        self.nr_page_rows = nr_page_rows

        assert nr_page_cols >= left_padding + nr_item_cols
        self.left_padding = left_padding
        self.nr_item_cols = nr_item_cols
        self.nr_page_cols = nr_page_cols

        self.item_width = item_width
        self.item_height = item_height

        self.book = xlwt.Workbook(name)
        self.sheet_memo = self.book.add_sheet('Memorization')
        self.sheet_recall = self.book.add_sheet('Recall')

        self.x_item = 0
        self.y_item = 0
        self.page = 0
        self.new_page = True
        self.new_row = True
        self.new_col = True

        self.x_header = 0

        # Determine and create the style cycle for numbers
        styles = list()
        if pattern is None or not pattern.strip():
            styles.append(self.style_item_normal)
        else:
            for p in (int(p) for p in pattern.split(',')):
                if p < 1:
                    raise ValueError(f'Pattern invalid: {self.pattern}')
                elif p == 1:
                    styles.append(self.style_item_single)
                elif p == 2:
                    styles.append(self.style_item_start)
                    styles.append(self.style_item_stop)
                elif p > 2:
                    styles.append(self.style_item_start)
                    for _ in range(p - 2):
                        styles.append(self.style_item_middle)
                    styles.append(self.style_item_stop)
        self.item_styles = itertools.cycle(styles)

    @property
    def x_cell(self):
        return self.x_item*self.item_width + self.left_padding

    @property
    def y_cell(self):
        return self.y_item*self.item_height + self.nr_header_rows + self.page*self.nr_page_rows

    @property
    def y_header(self):
        return self.page*self.nr_page_rows

    def next_pos(self, direction='horizontal'):
        # Called last

        # Assume
        self.new_page = False
        self.new_row = False
        self.new_col = False

        if direction == 'horizontal':
            self.x_item += 1
            self.new_col = True
            if self.x_item == self.nr_item_cols:
                # Hit new row
                self.x_item = 0
                self.y_item += 1
                self.new_row = True
                if self.y_item == self.nr_item_rows:
                    # Hit new page
                    self.y_item = 0
                    self.page += 1
                    self.new_page = True
        elif direction == 'vertical':
            self.y_item += 1
            self.new_row = True
            if self.y_item == self.nr_item_rows:
                self.y_item = 0
                self.x_item += 1
                self.new_col = True
                if self.x_item == self.nr_item_cols:
                    self.x_item = 0
                    self.page += 1
                    self.new_page = True
        else:
            raise ValueError(f'Invalid direction: {direction}')

    def write_header(self, sheets,
                     left_column, right_column,
                     title, discipline, recall_key,
                     memo_time, recall_time):
            for sheet in sheets:
                sheet.write_merge(
                    self.y_header,
                    self.y_header,
                    self.x_header,
                    self.x_header + self.nr_page_cols - 1,
                    *title
                )
                sheet.write(
                    self.y_header + 1,
                    left_column,
                    *discipline
                )
                sheet.write(
                    self.y_header + 1,
                    right_column,
                    *recall_key
                )
                sheet.write(
                    self.y_header + 2,
                    left_column,
                    *memo_time
                )
                sheet.write(
                    self.y_header + 2,
                    right_column,
                    *recall_time
                )

    def save(self, filename):
        self.book.save(filename)



class NumberTable(Table):

    normal = (
        'font: name Arial, height 180;'
        'alignment: horizontal center, vertical center;'
    )
    style_item_normal = xlwt.easyxf(normal)
    style_item_single = xlwt.easyxf(
        normal + 'borders: left hair, right hair, top hair, bottom hair;'
    )
    style_item_start = xlwt.easyxf(
        normal + 'borders: left hair, top hair, bottom hair;'
    )
    style_item_middle = xlwt.easyxf(
        normal + 'borders: top hair, bottom hair;'
    )
    style_item_stop = xlwt.easyxf(
        normal + 'borders: right hair, top hair, bottom hair;'
    )

    def __init__(self, title, discipline, recall_key, memo_time, recall_time,
                 **kwargs):

        self.title = title
        self.discipline = discipline
        self.recall_key = recall_key
        self.memo_time = memo_time
        self.recall_time = recall_time

        super().__init__(**kwargs)
        self.nr_items = 0

        for i in range(self.nr_page_cols):
            self.sheet_memo.col(i).width = convert_row_width(0.361)
            self.sheet_recall.col(i).width = convert_row_width(0.361)

        # Set width of "Row Nr" column
        self.sheet_memo.col(self.nr_page_cols - 1).width = convert_row_width(2)
        self.sheet_recall.col(self.nr_page_cols - 1).width = convert_row_width(2)


    def add_item(self, item):

        assert 0 <= int(item) <= 9
        item = str(item)

        # Check for newline action
        if self.new_row is True:
            # Set the height for this new row
            self.sheet_memo.row(self.y_cell).height_mismatch = True
            self.sheet_recall.row(self.y_cell).height_mismatch = True
            self.sheet_memo.row(self.y_cell).height = convert_row_height(0.79)
            self.sheet_recall.row(self.y_cell).height = convert_row_height(0.79)
            # Write "Row Nr" on the rightmost side
            style_row_enumeration = xlwt.easyxf(
                'font: name Arial, height 180;'
                'alignment: horizontal left, vertical center;'
            )
            self.sheet_memo.write(self.y_cell, self.nr_page_cols - 1, f'Row {self.y_item + self.page*self.nr_item_rows + 1}', style_row_enumeration)
            self.sheet_recall.write(self.y_cell, self.nr_page_cols - 1, f'Row {self.y_item + self.page*self.nr_item_rows + 1}', style_row_enumeration)

        # Check for new page action
        if self.new_page is True:
            # Write header
            style_title = xlwt.easyxf(
                'font: name Arial, height 220;'
                'alignment: horizontal center;'
            )
            style_normal = xlwt.easyxf(
                'font: name Arial, height 180;'
                'alignment: horizontal left;'
            )
            self.write_header(
                sheets=(self.sheet_memo, self.sheet_recall),
                left_column=self.x_header,
                right_column=self.x_header + self.nr_page_cols - 5,
                title=(self.title, style_title),
                discipline=(f'Discip. {self.discipline}', style_normal),
                recall_key=(f'Recall key: {self.recall_key}', style_normal),
                memo_time=(f'Memo. time: {self.memo_time} Min', style_normal),
                recall_time=(f'Recall time: {self.recall_time} Min', style_normal)
            )

            # Write footer - Not implemented

        self.nr_items += 1
        style = next(self.item_styles)
        self.sheet_memo.write(self.y_cell, self.x_cell, item, style)
        # Todo: recall sheet: hair -> thin, none -> hair
        self.sheet_recall.write(self.y_cell, self.x_cell, '', style)
        self.next_pos(direction='horizontal')


class WordTable(Table):

    normal = (
        'font: name Arial, height 220;'
        'alignment: horizontal left, vertical center;'
    )
    style_item_normal = (
        xlwt.easyxf(normal),
        xlwt.easyxf(normal),
        xlwt.easyxf(normal)
    )
    style_item_single = (
        xlwt.easyxf(normal + 'borders: left hair, top hair, bottom hair;'),
        xlwt.easyxf(normal + 'borders: top hair, bottom hair;'),
        xlwt.easyxf(normal + 'borders: right hair, top hair, bottom hair;'),
    )
    style_item_start = (
        xlwt.easyxf(normal + 'borders: left hair, top hair;'),
        xlwt.easyxf(normal + 'borders: top hair;'),
        xlwt.easyxf(normal + 'borders: right hair, top hair;'),
    )
    style_item_middle = (
        xlwt.easyxf(normal + 'borders: left hair;'),
        xlwt.easyxf(normal),
        xlwt.easyxf(normal + 'borders: right hair;'),
    )
    style_item_stop = (
        xlwt.easyxf(normal + 'borders: left hair, bottom hair;'),
        xlwt.easyxf(normal + 'borders: bottom hair;'),
        xlwt.easyxf(normal + 'borders: right hair, bottom hair;'),
    )

    def __init__(self, title, discipline, recall_key, memo_time, recall_time,
                 **kwargs):

        self.title = title
        self.discipline = discipline
        self.recall_key = recall_key
        self.memo_time = memo_time
        self.recall_time = recall_time

        super().__init__(**kwargs)
        self.nr_items = 0

        self.sheet_memo.portrait = False
        self.sheet_recall.portrait = False

        for i in range(self.nr_item_cols):

            self.sheet_memo.col(i*self.item_width + 0).width = convert_row_width(1)
            self.sheet_memo.col(i*self.item_width + 1).width = convert_row_width(0.36)
            self.sheet_memo.col(i*self.item_width + 2).width = convert_row_width(3.9)

            self.sheet_recall.col(i*self.item_width + 0).width = convert_row_width(1)
            self.sheet_recall.col(i*self.item_width + 1).width = convert_row_width(0.36)
            self.sheet_recall.col(i*self.item_width + 2).width = convert_row_width(3.9)


    def add_item(self, item):

        item = str(item)

        # Check for newline action
        if self.new_row is True:
            # Set the height for this new row
            self.sheet_memo.row(self.y_cell).height_mismatch = True
            self.sheet_recall.row(self.y_cell).height_mismatch = True
            self.sheet_memo.row(self.y_cell).height = convert_row_height(0.65)
            self.sheet_recall.row(self.y_cell).height = convert_row_height(0.65)

        # Check for new page action
        if self.new_page is True:
            # Write header
            style_title = xlwt.easyxf(
                'font: name Arial, height 220;'
                'alignment: horizontal center;'
            )
            style_normal = xlwt.easyxf(
                'font: name Arial, height 180;'
                'alignment: horizontal left;'
            )
            self.write_header(
                sheets=(self.sheet_memo, self.sheet_recall),
                left_column=self.x_header,
                right_column=self.x_header + self.nr_page_cols - 1,
                title=(self.title, style_title),
                discipline=(f'Discip. {self.discipline}', style_normal),
                recall_key=(f'Recall key: {self.recall_key}', style_normal),
                memo_time=(f'Memo. time: {self.memo_time} Min', style_normal),
                recall_time=(f'Recall time: {self.recall_time} Min', style_normal)
            )

            # Write footer - Not implemented

        self.nr_items += 1
        style_A, style_B, style_C = next(self.item_styles)
        self.sheet_memo.write(self.y_cell, self.x_cell + 0, self.nr_items, style_A)
        self.sheet_memo.write(self.y_cell, self.x_cell + 1, '', style_B)
        self.sheet_memo.write(self.y_cell, self.x_cell + 2, item, style_C)
        # Todo: recall sheet: hair -> thin, none -> hair
        self.sheet_recall.write(self.y_cell, self.x_cell + 0, self.nr_items, style_A)
        self.sheet_recall.write(self.y_cell, self.x_cell + 1, '', style_B)
        self.sheet_recall.write(self.y_cell, self.x_cell + 2, '', style_C)
        self.next_pos(direction='vertical')




class DatesTable(Table):

    style_item_normal = (
        'font: name Arial, height 220;'
    )
    style_item_single = style_item_normal + 'borders: top hair, bottom hair;'
    style_item_start = style_item_normal + 'borders: top hair;'
    style_item_middle = style_item_normal
    style_item_stop = style_item_normal + 'borders: bottom hair;'

    def __init__(self, title, discipline, recall_key, memo_time, recall_time,
                 **kwargs):

        self.title = title
        self.discipline = discipline
        self.recall_key = recall_key
        self.memo_time = memo_time
        self.recall_time = recall_time

        super().__init__(**kwargs)
        self.nr_items = 0

        self.sheet_memo.col(0).width = convert_row_width(1.5)
        self.sheet_memo.col(1).width = convert_row_width(3)
        self.sheet_memo.col(2).width = convert_row_width(0.4)
        self.sheet_memo.col(3).width = convert_row_width(10)
        self.sheet_memo.col(4).width = convert_row_width(4)

        self.sheet_recall.col(0).width = convert_row_width(1.5)
        self.sheet_recall.col(1).width = convert_row_width(3)
        self.sheet_recall.col(2).width = convert_row_width(0.4)
        self.sheet_recall.col(3).width = convert_row_width(10)
        self.sheet_recall.col(4).width = convert_row_width(4)


    def add_item(self, item):

        date, story = item

        # Check for newline action
        if self.new_row is True:
            # Set the height for this new row
            self.sheet_memo.row(self.y_cell).height_mismatch = True
            self.sheet_recall.row(self.y_cell).height_mismatch = True
            self.sheet_memo.row(self.y_cell).height = convert_row_height(0.55)
            self.sheet_recall.row(self.y_cell).height = convert_row_height(0.55)

        # Check for new page action
        if self.new_page is True:
            # Write header
            style_title = xlwt.easyxf(
                'font: name Arial, height 220;'
                'alignment: horizontal center;'
            )
            style_normal = xlwt.easyxf(
                'font: name Arial, height 180;'
                'alignment: horizontal left;'
            )
            self.write_header(
                sheets=(self.sheet_memo, self.sheet_recall),
                left_column=self.x_header,
                right_column=self.x_header + self.nr_page_cols - 1,
                title=(self.title, style_title),
                discipline=(f'Discip. {self.discipline}', style_normal),
                recall_key=(f'Recall key: {self.recall_key}', style_normal),
                memo_time=(f'Memo. time: {self.memo_time} Min', style_normal),
                recall_time=(f'Recall time: {self.recall_time} Min', style_normal)
            )

            # Write footer - Not implemented

        self.nr_items += 1
        style = next(self.item_styles)
        style_story = xlwt.easyxf(style + 'alignment: horizontal left, vertical center;')
        style_date = xlwt.easyxf(style + 'alignment: horizontal right, vertical center;')

        self.sheet_memo.write(self.y_cell, self.x_cell + 0, self.nr_items, style_date)
        self.sheet_memo.write(self.y_cell, self.x_cell + 1, str(date), style_date)
        self.sheet_memo.write(self.y_cell, self.x_cell + 2, '', style_date)
        self.sheet_memo.write(self.y_cell, self.x_cell + 3, str(story), style_story)
        # Todo: recall sheet: hair -> thin, none -> hair
        self.sheet_recall.write(self.y_cell, self.x_cell + 0, self.nr_items, style_date)
        self.sheet_recall.write(self.y_cell, self.x_cell + 1, '', style_date)
        self.sheet_recall.write(self.y_cell, self.x_cell + 2, '', style_date)
        self.sheet_recall.write(self.y_cell, self.x_cell + 3, str(story), style_story)
        self.next_pos(direction='vertical')



def get_decimal_table(**kwargs):
    return NumberTable(
                    name='Decimal',
                    nr_header_rows=7,
                    nr_item_rows=25,
                    nr_page_rows=40,
                    nr_item_cols=40,
                    nr_page_cols=43 + 2,
                    item_width=1,
                    item_height=1,
                    left_padding=2,
                    **kwargs
                    )

def get_binary_table(**kwargs):
    return NumberTable(
                    name='Binary',
                    nr_header_rows=7,
                    nr_item_rows=25,
                    nr_page_rows=40,
                    nr_item_cols=30,
                    nr_page_cols=43 + 2,
                    item_width=1,
                    item_height=1,
                    left_padding=7,
                    **kwargs
                    )

def get_words_table(**kwargs):
    return WordTable(
                    name='Word',
                    nr_header_rows=7,
                    nr_item_rows=20,
                    nr_page_rows=31,
                    nr_item_cols=5,
                    nr_page_cols=15,
                    item_width=3,
                    item_height=1,
                    left_padding=0,
                    **kwargs
                    )

def get_dates_table(**kwargs):
    return DatesTable(
                    name='Dates',
                    nr_header_rows=7,
                    nr_item_rows=40,
                    nr_page_rows=51,
                    nr_item_cols=1,
                    nr_page_cols=5,
                    item_width=4,
                    item_height=1,
                    left_padding=0,
                    **kwargs
                    )

if __name__ == '__main__':
    import random

    d = get_decimal_table(title='Svenska Minnesförbundet',
                    discipline='Decimal Numbers, 1234 st',
                    recall_key='A4B2C9',
                    memo_time='5',
                    recall_time='15',
                    pattern=[5])

    b = get_binary_table(title='Svenska Minnesförbundet',
                    discipline='Binary Numbers, 1234 st',
                    recall_key='ABC123',
                    memo_time='5',
                    recall_time='15',
                    pattern=[4])

    w = get_words_table(title='Svenska Minnesförbundet',
                    discipline='Words, 1234 st',
                    recall_key='ABC123',
                    memo_time='5',
                    recall_time='15',
                    pattern=[2])

    h = get_dates_table(title='Svenska Minnesförbundet',
                    discipline='Historical Dates, 1234 st',
                    recall_key='ABC123',
                    memo_time='5',
                    recall_time='15',
                    pattern=[10])

    words = itertools.cycle(['bacon', 'pizza', 'hej', 'vattenfall'])
    dates = itertools.cycle([('2017', 'Katter kan flyga'),
                             ('2008', 'Hunda vill bli katt')])
    for _ in range(1234):
        d.add_item(random.randint(0, 9))
        b.add_item(random.randint(0, 1))
        w.add_item(next(words))
        h.add_item(next(dates))
    d.save('Decimal.xls')
    b.save('Binary.xls')
    w.save('Word.xls')
    h.save('Dates.xls')
