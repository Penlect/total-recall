
import os
import re
from flask import render_template, request, jsonify, url_for

import random
import time
import math
from pprint import pprint
import json
import hashlib
from collections import namedtuple
import pickle
import functools
import collections

from recall import app

import recall.xls


def sha(string):
    h = hashlib.sha1(string.encode())
    h.update(str(random.random()).encode())
    return h.hexdigest()[0:6]

DATABASE_WORDS = os.path.join(app.root_path, 'db_words.txt')
DATABASE_STORIES = os.path.join(app.root_path, 'db_stories.txt')
WordEntry = namedtuple('WordEntry', 'language value name date word_class')
StoryEntry = namedtuple('StoryEntry', 'language value name date')


def load_database(db_file, entry):
    """Load database entries"""
    with open(db_file, 'r', encoding='utf-8') as db_file:
        entries = set()
        for line in db_file:
            if line.strip():
                row_data = [x.strip() for x in line.split(';')]
                entries.add(entry(*row_data))
        return list(sorted(entries))


def save_database(db_file, entries):
    """Save database entries"""
    with open(db_file, 'w', encoding='utf-8') as db_file:
        lines = (';'.join(entry) for entry in sorted(entries))
        db_file.write('\n'.join(lines))


def unique_lines_in_textarea(data: str, lower=False):
    """Get unique nonempty lines in textarea"""
    if lower:
        data = data.lower()
    return {line.strip() for line in data.split('\n') if line.strip()}


@functools.lru_cache(maxsize=8)
def load_blob(recall_key):
    blob_file = os.path.join(
        app.root_path, f'database/{recall_key[0:2]}/{recall_key[2:6]}.json')
    with open(blob_file, 'r', encoding='utf-8') as file:
        return json.load(file)


class Blob:

    VALID_DISCIPLINES = {'binary', 'decimal', 'words', 'dates'}
    VALID_CORRECTIONS = {'kind', 'standard'}

    def __init__(self, *,
                 discipline: str,
                 memo_time: int, recall_time: int,
                 correction,
                 data: str,  # Mandatory for 'create' but not 'generate'

                 language=None,  # Mandatory for 'dates' and 'words'
                 nr_items=None,  # Mandatory for 'generate' but not 'create'
                 pattern=''
                 ):

        self._recall_data = None # Only used for historical dates
        self.recall_key = None  # Final hash for this blob

        # Assign values and check for errors in input
        self.discipline = discipline.strip().lower()
        if self.discipline not in self.VALID_DISCIPLINES:
            raise ValueError(f'Invalid discipline: "{discipline}". '
                             'Choose from ' + str(self.VALID_DISCIPLINES))

        self.memo_time = int(memo_time)
        if self.memo_time < 0:
            raise ValueError('Memo. time cannot be negative: '
                             f'{self.memo_time}')

        self.recall_time = int(recall_time)
        if self.recall_time < 0:
            raise ValueError('Recall time cannot be negative: '
                             f'{self.recall_time}')

        self.correction = correction.strip().lower()
        if self.correction not in self.VALID_CORRECTIONS:
            raise ValueError(f'Invalid correction: "{correction}". '
                             'Choose from ' + str(self.VALID_CORRECTIONS))

        if language is None and self.discipline in {'words', 'dates'}:
            raise ValueError('Language must be provided when discipline = ' +
                             self.discipline)
        elif language:
            self.language = language.lower()
        else:
            self.language = ''

        if pattern.strip():
            if not re.fullmatch('(\d+)(,\s*\d+\s*)*', pattern):
                raise ValueError('The pattern provided doesn\'t match a '
                                 'comma separated list of numbers.')
        try:
            self.pattern = tuple(int(p) for p in pattern.split(',')
                                 if p.strip())
        except Exception as e:
            raise ValueError('The pattern could not be converted to a tuple '
                             'of integers.' + str(e))

        if data is None:
            # If data was not provided, we must generate it ourselves.
            # In order to do so we need to know how many items to
            # generate, + language if words or dates.
            assert nr_items is not None, 'Nr_items not provided to blob!'
            self.nr_items = int(nr_items)

            if self.discipline == 'binary':
                self.data = tuple(random.randint(0, 1)
                                  for _ in range(self.nr_items))
            elif self.discipline == 'decimal':
                self.data = tuple(random.randint(0, 9)
                                  for _ in range(self.nr_items))
            elif self.discipline == 'words':
                words = [word.value for word in
                         load_database(DATABASE_WORDS, WordEntry)
                         if word.language == self.language]
                random.shuffle(words)
                self.data = tuple(words[0:self.nr_items])
            elif self.discipline == 'dates':
                stories = [story.value for story in
                           load_database(DATABASE_STORIES, StoryEntry)
                           if story.language == self.language]
                random.shuffle(stories)
                stories = stories[0:self.nr_items]
                dates = [random.randint(1000, 2099) for _ in stories]
                self.data = tuple(zip(dates, stories))
                recall_data = list(self.data)
                random.shuffle(recall_data)
                self._recall_data = tuple(recall_data)
            else:
                raise Exception('Data generation for discipline '
                                f'"{self.discipline}" not implemented.')
        else:
            # If data is provided, it's just a matter of parsing the data
            # from the string
            if self.discipline == 'binary':
                self.data = tuple(int(digit) for digit in
                                  re.findall('[01]', data))
            elif self.discipline == 'decimal':
                self.data = tuple(int(digit) for digit in
                                  re.findall('\d', data))
            elif self.discipline == 'words':
                self.data = tuple(unique_lines_in_textarea(data, lower=True))
            elif self.discipline == 'dates':
                lines = unique_lines_in_textarea(data, lower=False)
                historical_dates = []
                for line in lines:
                    date, story = line.split(maxsplit=1)
                    if not (1000 <= int(date) <= 2099):
                        raise ValueError(f'Date out of range: 1000 <= {date} <= 2099')
                    historical_dates.append((date.strip(), story.strip()))
                self.data = tuple(historical_dates)
                recall_data = list(self.data)
                random.shuffle(recall_data)
                self._recall_data = tuple(recall_data)
            else:
                raise Exception('Data creation for discipline '
                                f'"{self.discipline}" not implemented.')

    def __iter__(self):
        yield from (
            ('discipline', self.discipline),
            ('memo_time', self.memo_time),
            ('recall_time', self.recall_time),
            ('correction', self.correction),
            ('data', self.data),
            ('language', self.language),
            ('pattern', self.pattern),
            ('recall_key', self.recall_key),
            ('date_created', time.time()),
            ('_recall_data', self._recall_data)
        )

    def add_to_database(self):
        """Write blob as json file to database"""
        blob = dict(self)

        hash_candidate = str(blob)
        while True:
            h = sha(hash_candidate)
            output_file = os.path.join(app.root_path,
                                       f'database/{h[0:2]}/{h[2:6]}.json')
            if os.path.isfile(output_file):
                hash_candidate = h
            else:
                break
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as file:
            json.dump(blob, file)
        self.recall_key = h
        return h


def alert(message):
    return f'<div class="alert alert-danger">{message}</div>'


@app.route('/database/words', methods=['GET', 'POST'])
def manage_words_database():
    """Words database dashboard"""
    if request.method == 'GET':
        return render_template('db_words.html')


@app.route('/database/words/content', methods=['GET'])
def database_words_content():
    """View whole word database in one big table"""
    db_words = load_database(DATABASE_WORDS, WordEntry)
    return render_template('db_words_content.html', words=db_words)


@app.route('/database/words/modify', methods=['POST'])
def database_words_modify():
    """ Update word database and respond modifications table summary """
    modification_time = time.strftime('%Y-%m-%d %H:%M:%S')
    db_words = load_database(DATABASE_WORDS, WordEntry)
    if request.method == 'POST':
        form = request.form

        if form['pwd'].lower().strip() != 'minnsej':
            return 'Wrong password!'

        if not form['added_by'].strip():
            return 'Your name is mandatory!'

        if not form['data'].strip():
            return 'No words were added since Words input was empty!'

        # We can't check words in database only on the word value,
        # the language is needed as well. Two words might exists
        # with the same word value but different meaning in two
        # languages.
        db_lang_word = {f'{w.language};{w.value}':w for w in db_words}

        status = dict()
        data = unique_lines_in_textarea(form['data'], lower=True)
        for word in data:
            delete_me = word.startswith('delete:')
            w = WordEntry(
                language=form['language'].lower(),
                value=word.replace('delete:', ''),
                name=form['added_by'],
                date=modification_time,
                word_class=form['word_class'].lower()
            )
            lw = f'{w.language};{w.value}'
            if delete_me:
                if lw in db_lang_word:
                    status[db_lang_word[lw]] = 'deleted'
                    del db_lang_word[lw]
                else:
                    status[w] = 'failed_delete'
            elif lw in db_lang_word:
                if db_lang_word[lw].word_class != w.word_class:
                    db_lang_word[lw] = w
                    status[w] = 'updated'
                else:
                    status[db_lang_word[lw]] = 'already_exists'
            else:
                db_lang_word[lw] = w
                status[w] = 'added'

        new_words = list(sorted(set(db_lang_word.values())))
        save_database(DATABASE_WORDS, new_words)
        return render_template(
            'db_words_modification.html', words=new_words, status=status,
            modification_time=modification_time
        )


@app.route('/generate')
def generate():
    return render_template('make_generate.html')


@app.route('/create')
def create():
    return render_template('make_create.html')


def form_to_blob(form, discipline:str):
    # The request form is a ImmutableMultiDict
    blob = Blob(
        discipline=discipline,
        memo_time=form['memo_time'],
        recall_time=form['recall_time'],
        correction=form['correction'],
        data=form.get('data'),
        nr_items=form.get('nr_items'),
        language=form.get('language'),
        pattern=form['pattern']
    )
    h = blob.add_to_database()
    app.logger.info(f'Created blob for {discipline}: {h}')
    return blob


def blob_to_xls_filename(blob):
    """Create xls filename containing blob data"""
    XLS_FILENAME_FMT = '{discipline}_{nr}st_{language}_{memo_time}-{recall_time}min_p{pattern_str}_{correction}_{recall_key}'
    b = dict(blob)  # So we can unpack below
    xls_filename = XLS_FILENAME_FMT.format(
        nr=len(blob.data),
        pattern_str=','.join(str(p) for p in blob.pattern),
        **b
    ) + '.xls'
    return xls_filename


def blob_to_table(blob):
    """Take relevant data of blob and create table

    The table can later be saved to disk as .xls file.
    """

    # Depending on which discipline we have, we'll need discipline
    # specific table and description
    if blob.discipline == 'binary':
        table = recall.xls.get_binary_table
        description=f'{blob.discipline.title()} Numbers, {len(blob.data)} st.'
    elif blob.discipline == 'decimal':
        table = recall.xls.get_decimal_table
        description=f'{blob.discipline.title()} Numbers, {len(blob.data)} st.'
    elif blob.discipline == 'words':
        table = recall.xls.get_words_table
        description=f'Words, {blob.language.title()}, {len(blob.data)} st.'
    elif blob.discipline == 'dates':
        table = recall.xls.get_dates_table
        description=f'Historical Dates, {blob.language.title()}, {len(blob.data)} st.'
    else:
        raise ValueError(
            f'Invalid discipline in blob: "{blob.discipline}"'
        )
    # Create header
    header = recall.xls.Header(
        title='Svenska Minnesförbundet',
        description=description,
        recall_key=blob.recall_key,
        memo_time=blob.memo_time,
        recall_time=blob.recall_time
    )
    # Create table
    t = table(header=header, pattern=blob.pattern)
    # Update the table with data
    for n in blob.data:
        t.add_item(n)
    return t


@app.route('/make', methods=['POST'])
def make_blob_and_sheets():
    """Convert request form to blob, create xls file, return links"""
    if request.method == 'POST':
        try:
            blob = form_to_blob(request.form, discipline=request.form['base'])
        except Exception as e:
            return alert(f'Failed to create blob of form data: {e}')
        xls_filename = blob_to_xls_filename(blob)
        try:
            t = blob_to_table(blob)
        except Exception as e:
            return alert(f'Failed to create table object of blob: {e}')
        try:
            t.save(os.path.join(app.root_path, 'static/sheets/' + xls_filename))
        except Exception as e:
            return alert(f'Failed to save xls file on server: {e}')
        return render_template(
            'make_links_memo_and_recall.html',
            xls_filename=xls_filename,
            recall_key=blob.recall_key
        )


@app.route('/recall/<string:key>')
def recall_(key):
    try:
        blob = load_blob(key)
    except FileNotFoundError:
        return f'No blob for key "{key}" exists'

    if blob['discipline'] == 'binary':
        nr_rows = math.ceil(len(blob['data'])/30)
        return render_template('recall_numbers.html', key=key, blob=blob,
                               nr_cols=30, nr_rows=nr_rows)
    elif blob['discipline'] == 'decimal':
        nr_rows = math.ceil(len(blob['data'])/40)
        return render_template('recall_numbers.html', key=key, blob=blob,
                               nr_cols=40, nr_rows=nr_rows)
    elif blob['discipline'] == 'words':
        nr_cols = math.ceil(len(blob['data'])/20)
        if nr_cols%5 == 0:
            nr_cols_iter = [5]*(nr_cols//5)
        else:
            nr_cols_iter = [5]*(nr_cols//5) + [nr_cols%5]
        return render_template('recall_words.html', key=key, blob=blob,
                               nr_cols_iter=nr_cols_iter)
    elif blob['discipline'] == 'dates':
        return render_template('recall_dates.html', key=key, blob=blob)
    else:
        return 'Not implemented yet: ' + blob['discipline']


def _arbeiter(key, dictionary):
    pass


class ClientRecallData:
    """Collect and hold submitted recall data

    The user will after recall press the submit button
    or wait until the time runs out and the submit is
    triggered automatically.

    The server will receive a form from the client
    that this class will take care of.

    The important fields in the form that must exist
    are:
        * username
        * recall_key
        * recall_cell_X values

    The username is used to identify the user, the
    recall_key is used to identify the blob, the
    cells are the data that will be corrected.

    Remember that all values will be strings, even
    numbers in cells from number disciplines.
    """
    # Todo: add seconds_remaining, ip address(?)
    def __init__(self, request_form):

        # Clean and set username
        _username = request_form['username']
        if not _username.strip():
            _username = 'Unknown'
        # Replace whitespace with '_'
        _username = re.sub(r'\s', '_', _username)
        # Remove non-word characters
        _username = re.sub(r'[^\w-]', '', _username)
        self.username = _username

        self.recall_key = request_form['recall_key']

        self._data = dict()
        for key in request_form:
            if key.startswith('recall_cell_'):
                self._data[key] = request_form[key]
        self._nr_recall_cells = len(self._data)

        # Make sure the cells make a consecutive set
        # of cells.
        _temp_data = [None]*self._nr_recall_cells
        for i in range(self._nr_recall_cells):
            try:
                user_value = self._data[f'recall_cell_{i}']
            except KeyError:
                raise Exception('Failed to get consecutive set of cells')
            else:
                _temp_data[i] = user_value
        self._data = _temp_data

    def __repr__(self):
        return f'<ClientRecallData {self.recall_key}:{self.username}>'

    def start_of_emptiness_before(self, index):
        index_of_empty_cell = index
        for i in reversed(range(index)):
            if self[i].strip():
                break
            else:
                index_of_empty_cell = i
        return index_of_empty_cell

    def __getitem__(self, item):
            return self._data[item]

    def __iter__(self):
        yield from self._data

    def __len__(self):
        return self._nr_recall_cells


class Arbeiter:
    """Correct user's recall data

    The Arbeiter is used to correct the user's recall.
    The user's recall is compared to the blob answer.
    """
    def __init__(self):
        pass

    def correct(self, client_data):
        """Correct client_data (user's recall data)"""
        self._client_data = client_data
        self._blob = load_blob(client_data.recall_key)

        cell_by_cell_result = self._correct_cells()
        count = dict(collections.Counter(cell_by_cell_result))
        raw_score = self._raw_score(cell_by_cell_result)
        points = self._points(raw_score)

        return {
            'cell_by_cell_result': tuple(cell_by_cell_result),
            'count': count,
            'raw_score': raw_score,
            'points': points
        }

    def _correct_cells(self):
        d = self._blob['discipline']
        if d == 'binary':
            correcter = self._correct_binary
        elif d == 'decimal':
            correcter = self._correct_decimals
        elif d == 'words':
            correcter = self._correct_words
        elif d == 'dates':
            correcter = self._correct_dates
        else:
            raise Exception(f'Blob contain invalid discipline: {d}')

        result = [None]*len(self._client_data)
        for i, user_value in enumerate(self._client_data, start=0):
            try:
                correct_value = self._blob['data'][i]
            except IndexError:
                result[i] = 'off_limits'
            else:
                if not user_value.strip():
                    # Empty cell
                    if i < self._client_data.start_of_emptiness_before(
                            len(self._blob['data'])):
                        result[i] = 'gap'
                    else:
                        result[i] = 'not_reached'
                else:
                    result[i] = correcter(user_value, correct_value)
        return result

    @staticmethod
    def _correct_binary(user_value: str, correct_value: int):
        if user_value == str(correct_value):
            return 'correct'
        else:
            return 'wrong'

    @staticmethod
    def _correct_decimals(user_value: str, correct_value: int):
        if user_value == str(correct_value):
            return 'correct'
        else:
            return 'wrong'

    def _correct_words(self, user_value: str, correct_value: str):
        if user_value.strip().lower() == correct_value.strip().lower():
            return 'correct'
        elif self._word_almost_correct(user_value, correct_value):
            return 'almost_correct'
        else:
            return 'wrong'

    @staticmethod
    def _correct_dates(user_value: str, correct_value: int):
        if user_value == str(correct_value):
            return 'correct'
        else:
            return 'wrong'

    @staticmethod
    def _word_almost_correct(user_value, correct_value):
        return False

    def _raw_score(self, cell_by_cell_result):
        # Will depend on correction method
        return 123

    def _points(self, raw_score):
        return 3.14


@app.route('/arbeiter', methods=['POST'])
def arbeiter():
    if request.method == 'POST':
        client = ClientRecallData(request.form)
        # Todo: save client data to disk for backup
        blob = load_blob(client.recall_key)
        result = Arbeiter(client, blob).correct()
        return jsonify(result)
    else:
        print('Wrong method!')

