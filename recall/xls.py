"""Create memorization sheets in .xls format

This module is used to create the .xls files used as memorization
sheets in memory competitions. These disciplines are supported today:

* Numbers
* Binary
* Words
* Historical Dates

The .xls files are easily opened in OpenOffice Calc, which is a free
to use software.

This module depends on the xlwt package. Documentation of xlwt is
best studied here:
https://github.com/python-excel/tutorial/raw/master/python-excel.pdf
"""

import itertools
import re
import xlwt

MAX_LENGTH_PATTERN = 40

def convert_row_width(cm):
    return round(1000*cm/0.77)


def convert_row_height(cm):
    return round(1000*cm/1.76)


def verify_and_clean_pattern(pattern):
    # Pattern must be string
    if pattern.strip() == '':
        return ''
    if not re.fullmatch('(\d+)(,\s*\d+\s*)*', pattern):
        raise ValueError(f'The pattern "{pattern}" is not a comma-separated '
                         f'list of integers.')
    try:
        pattern_ints = [int(p) for p in pattern.split(',') if p.strip()]
    except Exception:
        raise ValueError(f'The pattern "{pattern}" could not be converted '
                         f'to a list of integers.')
    if any(p <= 0 for p in pattern_ints):
        raise ValueError(f'The pattern "{pattern}" contains non-positive '
                         f'integers.')
    if len(pattern_ints) > MAX_LENGTH_PATTERN:
        raise ValueError(f'The pattern is too long ({len(pattern_ints)}), '
                         f'maximum {MAX_LENGTH_PATTERN} integers are allowed.')

    return ','.join(str(p) for p in pattern_ints)


class Table:
    """Each discipline specific table should inherit this class"""

    style_item_normal = xlwt.easyxf()
    style_item_single = xlwt.easyxf()
    style_item_start = xlwt.easyxf()
    style_item_middle = xlwt.easyxf()
    style_item_stop = xlwt.easyxf()

    def __init__(
            self,
            nr_header_rows,
            nr_item_rows,
            nr_page_rows,

            left_padding,
            nr_item_cols,
            nr_page_cols,

            item_width,
            item_height,

            pattern,
            **kwargs
    ):
        assert nr_page_rows >= nr_item_rows + nr_header_rows
        self.nr_header_rows = nr_header_rows
        self.nr_item_rows = nr_item_rows
        self.nr_page_rows = nr_page_rows
        self.nr_empty_tail_rows = nr_page_rows - (nr_header_rows + nr_item_rows*item_height)

        assert nr_page_cols >= left_padding + nr_item_cols
        self.left_padding = left_padding
        self.nr_item_cols = nr_item_cols
        self.nr_page_cols = nr_page_cols

        # Item size in units of cells
        self.item_width = item_width
        self.item_height = item_height

        # The memo and recall sheets
        self.book = xlwt.Workbook(encoding='utf-8')
        self.sheet_memo = self.book.add_sheet('Memorization')
        self.sheet_recall = self.book.add_sheet('Recall')

        # Coordinates to current item
        self.x_item = 0
        self.y_item = 0

        # Current page, 0 mean first page
        self.page = 0

        # Boolean indicators that is triggered when new areas
        # are reached by an item
        self.new_page = True
        self.new_row = True
        self.new_col = True

        self.x_header = 0

        # Determine and create the style cycle for numbers
        if pattern is None:
            pattern = ''
        try:
            pattern = tuple(int(p) for p in pattern.split(',') if p.strip())
        except Exception as e:
            raise ValueError('The pattern could not be converted to a tuple '
                             'of integers.' + str(e))
        styles = list()
        if len(pattern) == 0:
            styles.append(self.style_item_normal)
        else:
            for p in pattern:
                if p < 1:
                    raise ValueError(f'Pattern invalid: {pattern}')
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
        """Index to first row of header in current page"""
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

        if self.new_page is True:
            # Set row heights of trailing empty rows
            # of last page
            for i in range(self.nr_empty_tail_rows):
                index = self.y_header - (i + 1)
                if index >= 0:
                    self._set_row_height(index, height=0.45)

    def write_header(self, header):
        # Write header

        for i in range(self.nr_header_rows):
            if i == 0:
                height = 0.50
            else:
                height = 0.45
            self._set_row_height(self.y_header + i, height)

        style_title = xlwt.easyxf(
            'font: name Arial, height 220;'
            'alignment: horizontal center;'
        )
        style_normal = xlwt.easyxf(
            'font: name Arial, height 180;'
            'alignment: horizontal left;'
        )
        for sheet in (self.sheet_memo, self.sheet_recall):
            # Write top Title row
            sheet.write_merge(
                # Y-range
                self.y_header,
                self.y_header,
                # X-range
                header.left_offset,
                header.left_offset + self.nr_page_cols - 1,
                # Content
                header.title,
                style_title
            )
            # Write second header row
            sheet.write(
                self.y_header + 1, header.left_offset,
                f'{header.description}',
                style_normal
            )
            sheet.write(
                self.y_header + 1,
                header.left_offset + self.nr_page_cols + header.right_offset,
                f'Memo id: {header.recall_key}',
                style_normal
            )
            # Write third header row
            sheet.write(
                self.y_header + 2, header.left_offset,
                f'Memo. time: {header.memo_time} Min',
                style_normal
            )
            sheet.write(
                self.y_header + 2,
                header.left_offset + self.nr_page_cols + header.right_offset,
                f'Recall time: {header.recall_time} Min',
                style_normal
            )

    def set_column_widths(self, widths):
        for i, width in enumerate(widths):
            self.sheet_memo.col(i).width = convert_row_width(width)
            self.sheet_recall.col(i).width = convert_row_width(width)

    def set_item_row_height(self, height):
        """Set height of row containing items (self.y_cell used)"""
        self._set_row_height(self.y_cell, height)

    def _set_row_height(self, row_index, height):
        self.sheet_memo.row(row_index).height_mismatch = True
        self.sheet_recall.row(row_index).height_mismatch = True
        self.sheet_memo.row(row_index).height = convert_row_height(height)
        self.sheet_recall.row(row_index).height = convert_row_height(height)


    def save(self, filename):
        self.book.save(filename)


class NumberTable(Table):

    normal = (
        'font: name Arial, height 180;'
        'alignment: horizontal center, vertical center;'
    )
    # Tuples of memorization sheet cell style, and recall sheet cell style
    style_item_normal = (
        xlwt.easyxf(normal),
        xlwt.easyxf(normal + 'borders: left hair, right hair, top hair, bottom hair;'))
    style_item_single = (
        xlwt.easyxf(normal + 'borders: left hair, right hair, top hair, bottom hair;'),
        xlwt.easyxf(normal + 'borders: left thin, right thin, top thin, bottom thin;'))
    style_item_start = (
        xlwt.easyxf(normal + 'borders: left hair, top hair, bottom hair;'),
        xlwt.easyxf(normal + 'borders: left thin, right hair, top thin, bottom thin;'))
    style_item_middle = (
        xlwt.easyxf(normal + 'borders: top hair, bottom hair;'),
        xlwt.easyxf(normal + 'borders: left hair, right hair, top thin, bottom thin;'))
    style_item_stop = (
        xlwt.easyxf(normal + 'borders: right hair, top hair, bottom hair;'),
        xlwt.easyxf(normal + 'borders: left hair, right thin, top thin, bottom thin;'))

    def __init__(self, header, **kwargs):
        self.header = header
        super().__init__(**kwargs)
        self.nr_items = 0
        # The last page_column need to be wider to fit "Row 23"
        self.set_column_widths([0.361]*(self.nr_page_cols - 1) + [2])

    def add_item(self, item):
        assert 0 <= int(item) <= 9
        item = str(item)

        # Check for newline action
        if self.new_row is True:
            self.set_item_row_height(height=0.79)

            # Write "Row Nr" on the rightmost side
            style_row_enumeration = xlwt.easyxf(
                'font: name Arial, height 180;'
                'alignment: horizontal left, vertical center;'
            )
            self.sheet_memo.write(self.y_cell, self.nr_page_cols - 1,
                                  f'Row {self.y_item + self.page*self.nr_item_rows + 1}',
                                  style_row_enumeration)
            self.sheet_recall.write(self.y_cell, self.nr_page_cols - 1,
                                    f'Row {self.y_item + self.page*self.nr_item_rows + 1}',
                                    style_row_enumeration)

        # Check for new page action
        if self.new_page is True:
            self.write_header(self.header)

        self.nr_items += 1
        style_memo, style_recall = next(self.item_styles)
        self.sheet_memo.write(self.y_cell, self.x_cell, item, style_memo)
        # Todo: recall sheet: hair -> thin, none -> hair
        self.sheet_recall.write(self.y_cell, self.x_cell, '', style_recall)
        self.next_pos(direction='horizontal')


class WordTable(Table):

    normal = (
        'font: name Arial, height 220;'
        'alignment: horizontal left, vertical center;'
    )
    style_item_normal = (
        xlwt.easyxf(normal.replace('left', 'right')),
        xlwt.easyxf(normal),
        xlwt.easyxf(normal)
    )
    style_item_single = (
        xlwt.easyxf(normal.replace('left', 'right') + 'borders: left hair, top hair, bottom hair;'),
        xlwt.easyxf(normal + 'borders: top hair, bottom hair;'),
        xlwt.easyxf(normal + 'borders: right hair, top hair, bottom hair;'),
    )
    style_item_start = (
        xlwt.easyxf(normal.replace('left', 'right') + 'borders: left hair, top hair;'),
        xlwt.easyxf(normal + 'borders: top hair;'),
        xlwt.easyxf(normal + 'borders: right hair, top hair;'),
    )
    style_item_middle = (
        xlwt.easyxf(normal.replace('left', 'right') + 'borders: left hair;'),
        xlwt.easyxf(normal),
        xlwt.easyxf(normal + 'borders: right hair;'),
    )
    style_item_stop = (
        xlwt.easyxf(normal.replace('left', 'right') + 'borders: left hair, bottom hair;'),
        xlwt.easyxf(normal + 'borders: bottom hair;'),
        xlwt.easyxf(normal + 'borders: right hair, bottom hair;'),
    )

    def __init__(self, header, **kwargs):
        self.header = header
        super().__init__(**kwargs)
        self.nr_items = 0
        self.set_column_widths([1, 0.36, 3.9]*self.nr_item_cols)

        self.sheet_memo.portrait = False
        self.sheet_recall.portrait = False

    def add_item(self, item):
        item = str(item)

        # Check for newline action
        if self.new_row is True:
            self.set_item_row_height(height=0.65)

        # Check for new page action
        if self.new_page is True:
            self.write_header(self.header)

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

    # Todo: recall sheet is wrong, should not have same order as memo sheet

    _style_item_normal = (
        'font: name Arial, height 220;'
    )
    _style_item_single = _style_item_normal + 'borders: top hair, bottom hair;'
    _style_item_start = _style_item_normal + 'borders: top hair;'
    _style_item_middle = _style_item_normal
    _style_item_stop = _style_item_normal + 'borders: bottom hair;'

    _recall_style_item_normal = (
        'font: name Arial, height 220;' + 'borders: top hair, bottom hair;'
    )
    _recall_style_item_single = _style_item_normal + 'borders: top thin, bottom thin;'
    _recall_style_item_start = _style_item_normal + 'borders: top thin, bottom hair;'
    _recall_style_item_middle = _style_item_normal + 'borders: top hair, bottom hair;'
    _recall_style_item_stop = _style_item_normal + 'borders: top hair, bottom thin;'

    _left = 'alignment: horizontal left, vertical center;'
    _right = 'alignment: horizontal right, vertical center;'
    style_item_normal = (
        (
            xlwt.easyxf(_style_item_normal + _left),
            xlwt.easyxf(_style_item_normal + _right)
        ),
        (
            xlwt.easyxf(_recall_style_item_normal + _left),
            xlwt.easyxf(_recall_style_item_normal + _right)
        )
    )
    style_item_single = (
        (
            xlwt.easyxf(_style_item_single + _left),
            xlwt.easyxf(_style_item_single + _right)
        ),
        (
            xlwt.easyxf(_recall_style_item_single + _left),
            xlwt.easyxf(_recall_style_item_single + _right)
        )
    )
    style_item_start = (
        (
            xlwt.easyxf(_style_item_start + _left),
            xlwt.easyxf(_style_item_start + _right)
        ),
        (
            xlwt.easyxf(_recall_style_item_start + _left),
            xlwt.easyxf(_recall_style_item_start + _right)
        )
    )
    style_item_middle = (
        (
            xlwt.easyxf(_style_item_middle + _left),
            xlwt.easyxf(_style_item_middle + _right)
        ),
        (
            xlwt.easyxf(_recall_style_item_middle + _left),
            xlwt.easyxf(_recall_style_item_middle + _right)
        )
    )
    style_item_stop = (
        (
            xlwt.easyxf(_style_item_stop + _left),
            xlwt.easyxf(_style_item_stop + _right)
        ),
        (
            xlwt.easyxf(_recall_style_item_stop + _left),
            xlwt.easyxf(_recall_style_item_stop + _right)
        )
    )

    def __init__(self, header, **kwargs):
        self.header = header
        super().__init__(**kwargs)
        self.nr_items = 0
        self.set_column_widths([1.5, 3, 0.4, 10, 4])

    def add_item(self, item):
        date, story, *_ = item

        # Check for newline action
        if self.new_row is True:
            self.set_item_row_height(height=0.55)

        # Check for new page action
        if self.new_page is True:
            self.write_header(self.header)

        self.nr_items += 1
        ((style_story, style_date),
         (recall_style_story, recall_style_date)) = next(self.item_styles)

        y, x = self.y_cell, self.x_cell
        self.sheet_memo.write(y, x + 0, self.nr_items, style_date)
        self.sheet_memo.write(y, x + 1, str(date), style_date)
        self.sheet_memo.write(y, x + 2, '', style_date)
        self.sheet_memo.write(y, x + 3, str(story), style_story)

        self.sheet_recall.write(y, x + 0, self.nr_items, recall_style_date)
        self.sheet_recall.write(y, x + 1, '', recall_style_date)
        self.sheet_recall.write(y, x + 2, '', recall_style_date)
        self.sheet_recall.write(y, x + 3, str(story), recall_style_story)
        self.next_pos(direction='vertical')


class StandardDeck:

    card_values = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10',
                   'J', 'Q', 'K']
    card_suites = ['\u2660', '\u2665', '\u2666', '\u2663']

    def get_card(self, card_id):
        card_id = int(card_id)
        value, suite = card_id%13, card_id//13
        return self.card_values[value], self.card_suites[suite]


def _card_styles(left, right):

    value = (
        'font: name Arial, height 260, bold true, color {color};'
        'alignment: horizontal center, vertical top;'
        'borders: left {left}, right {right}, top thin;'
    )
    suite = (
        'font: name Arial, height 360, color {color};'
        'alignment: horizontal center;'
        'borders: left {left}, right {right}, bottom thin;'
    )

    return (
        (
            # Value styles
            xlwt.easyxf(value.format(color='black', left=left, right=right)),
            xlwt.easyxf(value.format(color='red', left=left, right=right)),
            xlwt.easyxf(value.format(color='blue', left=left, right=right)),
            xlwt.easyxf(value.format(color='green', left=left, right=right)),
        ),
        (
            # Suite styles
            xlwt.easyxf(suite.format(color='black', left=left, right=right)),
            xlwt.easyxf(suite.format(color='red', left=left, right=right)),
            xlwt.easyxf(suite.format(color='blue', left=left, right=right)),
            xlwt.easyxf(suite.format(color='green', left=left, right=right)),
        )
    )


class CardTable(Table):

    style_item_single = _card_styles('thin', 'thin')
    style_item_normal = style_item_single
    style_item_start = _card_styles('thin', 'hair')
    style_item_middle = _card_styles('hair', 'hair')
    style_item_stop = _card_styles('hair', 'thin')

    def __init__(self, header, card_colors, **kwargs):
        self.header = header
        self.card_colors = card_colors
        super().__init__(**kwargs)
        self.nr_items = 0
        # The last page_column need to be wider to fit "Row 23"
        self.set_column_widths([0.65]*self.nr_page_cols)
        # "Reset" grid pattern for each deck of cards
        self.item_styles = itertools.cycle(itertools.islice(self.item_styles, 52))

    def add_item(self, item):
        assert 0 <= int(item) <= 51
        value, suite = StandardDeck().get_card(item)

        # Check for newline action
        if self.new_row is True:
            self._set_row_height(self.y_cell, 0.55)
            self._set_row_height(self.y_cell + 1, 0.6)
            if self.nr_items%52 == 48:
                height = 1
            else:
                height = 0.4
            self._set_row_height(self.y_cell + 2, height)

        # Check for new page action
        if self.new_page is True:
            self.write_header(self.header)

        self.nr_items += 1
        (value_styles, suite_styles) = next(self.item_styles)

        if self.card_colors is True:
            # Black, Red, Blue, Green
            value_style = value_styles[item//13]
            suite_style = suite_styles[item//13]
        else:
            # Black, Red, Red, Black
            value_style = value_styles[1 if 1 <= item//13 <= 2 else 0]
            suite_style = suite_styles[1 if 1 <= item//13 <= 2 else 0]

        self.sheet_memo.write(self.y_cell, self.x_cell, value, value_style)
        self.sheet_memo.write(self.y_cell + 1, self.x_cell, suite, suite_style)
        self.sheet_memo.write(self.y_cell + 2, self.x_cell, '')
        # Todo: recall sheet: hair -> thin, none -> hair
        self.sheet_recall.write(self.y_cell, self.x_cell, '', value_style)
        self.sheet_recall.write(self.y_cell + 1, self.x_cell, '', suite_style)
        self.sheet_recall.write(self.y_cell + 2, self.x_cell, '')
        if self.nr_items%52 == 0:
            self.x_item = self.nr_item_cols - 1
        self.next_pos(direction='horizontal')


def get_decimal_table(header, pattern):
    header.right_offset = -5
    return NumberTable(
                    header=header,
                    pattern=pattern,
                    nr_header_rows=7,
                    nr_item_rows=25,
                    nr_page_rows=40,
                    nr_item_cols=40,
                    nr_page_cols=43 + 2,
                    item_width=1,
                    item_height=1,
                    left_padding=2
                    )


def get_binary_table(header, pattern):
    header.right_offset = -5
    return NumberTable(
                    header=header,
                    pattern=pattern,
                    nr_header_rows=7,
                    nr_item_rows=25,
                    nr_page_rows=40,
                    nr_item_cols=30,
                    nr_page_cols=43 + 2,
                    item_width=1,
                    item_height=1,
                    left_padding=7
                    )


def get_words_table(header, pattern):
    header.right_offset = -1
    return WordTable(
                    header=header,
                    pattern=pattern,
                    nr_header_rows=7,
                    nr_item_rows=20,
                    nr_page_rows=31,
                    nr_item_cols=5,
                    nr_page_cols=15,
                    item_width=3,
                    item_height=1,
                    left_padding=0
                    )


def get_dates_table(header, pattern):
    header.right_offset = -1
    return DatesTable(
                    header=header,
                    pattern=pattern,
                    nr_header_rows=7,
                    nr_item_rows=40,
                    nr_page_rows=51,
                    nr_item_cols=1,
                    nr_page_cols=5,
                    item_width=4,
                    item_height=1,
                    left_padding=0
                    )


def get_card_table(header, pattern, card_colors=True):
    header.right_offset = -5
    return CardTable(
                    header=header,
                    card_colors=card_colors,
                    pattern=pattern,
                    nr_header_rows=7,
                    nr_item_rows=3*4,
                    nr_page_rows=49,
                    nr_item_cols=24,
                    nr_page_cols=30,
                    item_width=1,
                    item_height=3,
                    left_padding=3
                    )


class Header:
    def __init__(self, title, description, recall_key, memo_time, recall_time):
        self.title = title
        self.description = description
        self.recall_key = recall_key
        self.memo_time = memo_time
        self.recall_time = recall_time
        self.left_offset = 0
        self.right_offset = -1


if __name__ == '__main__':
    import random

    header_decimal = Header(
        title='Svenska Minnesförbundet',
        description='Decimal Numbers, 1234 st',
        recall_key='4211',
        memo_time='5',
        recall_time='15'
    )
    header_binary = Header(
        title='Svenska Minnesförbundet',
        description='Binary Numbers, 1234 st',
        recall_key='7452',
        memo_time='5',
        recall_time='15'
    )
    header_words = Header(
        title='Svenska Minnesförbundet',
        description='Words, 1234 st',
        recall_key='2344',
        memo_time='5',
        recall_time='15'
    )
    header_dates = Header(
        title='Svenska Minnesförbundet',
        description='Dates, 1234 st',
        recall_key='7812',
        memo_time='5',
        recall_time='15'
    )
    header_cards = Header(
        title='Svenska Minnesförbundet',
        description='Cards, 1234 st',
        recall_key='5632',
        memo_time='5',
        recall_time='15'
    )
    d = get_decimal_table(header_decimal, pattern='5, 3')
    b = get_binary_table(header_binary, pattern='4, 3, 3')
    w = get_words_table(header_words, pattern='2')
    h = get_dates_table(header_dates, pattern='10')
    c = get_card_table(header_cards, pattern='3')

    # Cards: Q\u2665 2\u2666 A\u2663
    words = itertools.cycle(['bacon', 'pizza', 'hej', 'vattenfall', 'åäö'])
    dates = itertools.cycle([('2017', 'Katter kan flyga'),
                             ('2008', 'Hunda vill bli katt'),
                             ('2008', 'Åäö tas bort från svenskan')])
    cards = (random.randint(0, 51) for _ in range(10**10))
    for _ in range(12340):
        d.add_item(random.randint(0, 9))
        b.add_item(random.randint(0, 1))
    for _ in range(1234):
        w.add_item(next(words))
    for _ in range(300):
        h.add_item(next(dates))
    for _ in range(52*5 + 17):
        c.add_item(next(cards))
    d.save('Decimal.xls')
    b.save('Binary.xls')
    w.save('Word.xls')
    h.save('Dates.xls')
    c.save('Cards.xls')
