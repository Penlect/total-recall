
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


class Blob:

    VALID_DISCIPLINES = {'binary', 'decimal', 'words', 'dates'}
    VALID_CORRECTIONS = {'kind', 'standard'}

    def __init__(self, *,
                 discipline: str,
                 memo_time: int, recall_time: int,
                 correction,
                 data: str,  # Mandatory for 'create' but not 'generate'

                 language=None,  # Mandatory for 'dates' and 'wrods'
                 nr_items=None,  # Mandatory for 'generate' but not 'create'
                 pattern=''
                 ):
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

        try:
            self.pattern = tuple(int(p) for p in pattern.split(',')
                                 if p.strip())
        except ValueError:
            self.pattern = ()  # Empty tuple

        if data is None:
            # If data was not provided, we must generate it ourselves.
            # In order to do so we need to know how many items to
            # generate, + language if words or dates.
            assert nr_items is not None, 'Nr_items not provided to blob!'
            self.nr_items = int(nr_items)
            if self.discipline in {'words', 'dates'}:
                assert language is not None, 'Language not provided to blob!'

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
                dates = [random.randint(1000,2099) for _ in stories]
                self.data = tuple(zip(dates, stories))
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
                    assert 1000 <= int(date) <= 2099
                    historical_dates.append((date.strip(), story.strip()))
                self.data = tuple(historical_dates)
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
            ('date_created', time.time())
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


def load_blob(recall_key):
    blob_file = os.path.join(
        app.root_path, f'database/{recall_key[0:2]}/{recall_key[2:6]}.json')
    with open(blob_file, 'r', encoding='utf-8') as file:
        return json.load(file)


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
    return render_template('generate.html')


@app.route('/create')
def create():
    return render_template('create.html')


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

XLS_FILENAME_FMT = '{discipline}_{language}_{nr}st_{memo_time}min_{recall_time}min_{pattern_str}_{correction}'

@app.route('/numbers', methods=['POST'])
def numbers():
    if request.method == 'POST':
        blob = form_to_blob(request.form, discipline=request.form['base'])

        # CREATE XLS DOCUMENT
        if blob.discipline == 'binary':
            table = recall.xls.get_binary_table
        elif blob.discipline == 'decimal':
            table = recall.xls.get_decimal_table
        else:
            raise ValueError(
                'Invalid discipline for Numbers: "{blob.discipline}"'
            )

        b = dict(blob)
        xls_filename = XLS_FILENAME_FMT.format(
            nr=len(blob.data),
            pattern_str=','.join(str(p) for p in blob.pattern),
            **b
        ).title() + '.xls'

        b.pop('discipline')
        t = table(
            title='Svenska Minnesförbundet',
            discipline=f'{blob.discipline.title()} Numbers, {len(blob.data)} st.',
            **b
        )
        for n in blob.data:
            t.add_item(n)
        t.save(os.path.join(app.root_path, 'static/sheets/' + xls_filename))
        return render_template('memorize.html',
                               xls_download_link=url_for('static', filename='sheets/' + xls_filename),
                               xls_filename=xls_filename)


@app.route('/words', methods=['POST'])
def words():
    if request.method == 'POST':
        blob = form_to_blob(request.form, discipline='words')

        # CREATE XLS DOCUMENT
        b = dict(blob)
        xls_filename = XLS_FILENAME_FMT.format(
            nr=len(blob.data),
            pattern_str=','.join(str(p) for p in blob.pattern),
            **b
        ).title() + '.xls'

        b.pop('discipline')
        t = recall.xls.get_words_table(
            title='Svenska Minnesförbundet',
            discipline=f'Words, {blob.language.title()}, {len(blob.data)} st.',
            **b
        )

        for n in blob.data:
            t.add_item(n)
        t.save(os.path.join(app.root_path, 'static/sheets/' + xls_filename))
        return render_template('memorize.html',
                               xls_download_link=url_for('static', filename='sheets/' + xls_filename),
                               xls_filename=xls_filename)


@app.route('/dates', methods=['POST'])
def dates():
    if request.method == 'POST':
        blob = form_to_blob(request.form, discipline='dates')

        # CREATE XLS DOCUMENT
        b = dict(blob)
        xls_filename = XLS_FILENAME_FMT.format(
            nr=len(blob.data),
            pattern_str=','.join(str(p) for p in blob.pattern),
            **b
        ).title() + '.xls'

        b.pop('discipline')
        t = recall.xls.get_words_table(
            title='Svenska Minnesförbundet',
            discipline=f'Historical Dates, {blob.language.title()}, {len(blob.data)} st.',
            **b
        )

        for n in blob.data:
            t.add_item(n)
        t.save(os.path.join(app.root_path, 'static/sheets/' + xls_filename))
        return render_template('memorize.html',
                               xls_download_link=url_for('static', filename='sheets/' + xls_filename),
                               xls_filename=xls_filename)



@app.route('/recall/<string:key>')
def recall_(key):
    blob_file = os.path.join(app.root_path, f'database/{key[0:2]}/{key[2:6]}.json')
    if not os.path.isfile(blob_file):
        return f'No such key exsists: {key}, {blob_file}'
    with open(blob_file, 'r', encoding='utf-8') as file:
        blob = json.load(file)
    return render_template('numbers.html', key=key, blob=blob,
                           nr_cols=40, nr_rows=math.ceil(len(blob['data'])/40))


def _arbeiter(key, dictionary):
    pass


class ClientRecallData:
    def __init__(self, request_form):
        self.recall_key = request_form['recall_key']
        self._data = dict()
        for key in request_form:
            if key.startswith('recall_cell_'):
                self._data[key] = request_form[key]
        self.nr_recall_cells = len(self._data)

        for i in range(self.nr_recall_cells):
            assert f'recall_cell_{i}' in self._data

        self.empty_from_this_and_after = self.nr_recall_cells
        for i in reversed(range(self.nr_recall_cells)):
            if self[i].strip():
                break
            else:
                self.empty_from_this_and_after = i

    def __getitem__(self, item):
        try:
            return self._data[str(item)]
        except KeyError:
            return self._data['recall_cell_' + str(item)]

    def __setitem__(self, key, value):
        if key in self._data:
            self._data[key] = value
        elif 'recall_cell_' + str(value) in self._data:
            self._data['recall_cell_' + str(value)] = value
        else:
            raise ValueError(f'Can\'t set item: {key}')

    def __iter__(self):
        for i in range(self.nr_recall_cells):
            yield self[i]


class Arbeiter:
    def __init__(self, client_data, blob: dict):
        self.client_data = client_data
        self.blob = blob

    def correct(self):
        d = self.blob['discipline']
        if d == 'binary':
            return self._correct_binary()
        elif d == 'decimal':
            return self._correct_decimals()
        elif d == 'words':
            return self._correct_words()
        elif d == 'dates':
            return self._correct_dates()
        else:
            raise Exception(f'Blob contain invalid discipline: {d}')

    def _correct_binary(self):
        result = {
            'cells': dict()
        }
        for i, cell_value in enumerate(self.client_data, start=0):
            try:
                correct_value = self.blob['data'][i]
            except IndexError:
                result['cells'][f'recall_cell_{i}'] = 'off_limits'
            else:
                if not cell_value.strip():
                    # Empty cell
                    if i < self.client_data.empty_from_this_and_after:
                        result['cells'][f'recall_cell_{i}'] = 'gap'
                    else:
                        result['cells'][f'recall_cell_{i}'] = 'not_reached'
                else:
                    if int(cell_value) == correct_value:
                        result['cells'][f'recall_cell_{i}'] = 'correct'
                    else:
                        result['cells'][f'recall_cell_{i}'] = 'wrong'
        return result

    def _correct_decimals(self):
        return self._correct_binary()

    def _correct_words(self):
        pass

    def _correct_dates(self):
        pass


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

