
import xlwt


def convert_row_width(cm):
    return round(1000*cm/0.77)


def convert_row_height(cm):
    return round(1000*cm/1.76)


class RecallTable:

    style_title = xlwt.easyxf(
        'font: name Arial, height 220;'
        'alignment: horizontal center;'
    )
    style_description = xlwt.easyxf(
    )
    style_key = xlwt.easyxf(
    )

    def __init__(self, name, recall_key, title, description,
                 nr_items_per_page, nr_rows_page, nr_cols_page,
                 height_row, key_left_shift=1):
        self.recall_key = recall_key
        self.title = title
        self.description = description

        self.nr_items_per_page = nr_items_per_page
        self.nr_rows_page = nr_rows_page
        self.nr_cols_page = nr_cols_page
        self.height_row = height_row

        self.key_left_shift = key_left_shift

        self.book = xlwt.Workbook(name.replace(' ', '_'))
        self.sheet = self.book.add_sheet(name.replace(' ', '_'))

        self.nr_items = 0
        self.page = None
        self.page_offset = None

    def _update_page(self):
        prev_page = self.page
        self.page = self.nr_items//self.nr_items_per_page
        self.page_offset = self.page*self.nr_rows_page

        if prev_page != self.page:
            for i in range(self.page_offset, self.page_offset + self.nr_rows_page):
                self.sheet.row(i).height_mismatch = True
                self.sheet.row(i).height = self.height_row
            self._write_header()

    def _write_header(self):
        self.sheet.write_merge(
            self.page_offset,
            self.page_offset,
            0,
            self.nr_cols_page - 1,
            self.title,
            self.style_title
        )
        self.sheet.write(
            self.page_offset + 1,
            0,
            self.description,
            self.style_description
        )
        self.sheet.write(
            self.page_offset + 1,
            self.nr_cols_page - self.key_left_shift,
            f'Recall key: {self.recall_key}',
            self.style_key
        )

    def save(self, filename):
        self.book.save(filename)