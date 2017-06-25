
import os
import re
from flask import render_template, request, jsonify, url_for

import random
from pprint import pprint
import json
import hashlib

from recall import app


# Todo: fix imports
import recall.xls.numbers_
import recall.xls.binary
import recall.xls.words
import recall.xls.dates

def sha(string):
    h = hashlib.sha1(string.encode())
    h.update(str(random.random()).encode())
    return h.hexdigest()[0:6]


def load_words():
    with open(os.path.join(app.root_path, 'db_words.txt')) as db_file:
        words = list(sorted(w.strip().lower() for w in db_file.readlines()
                            if w.strip()))
        return words

def load_dates():
    with open(os.path.join(app.root_path, 'db_dates.txt')) as db_file:
        dates = list(sorted(w.strip() for w in db_file.readlines()
                            if w.strip()))
        return dates


@app.route('/database/words')
def db_words():
    return render_template('db_words.html', words=load_words())


@app.route('/generate')
def generate():
    return render_template('generate.html')


@app.route('/create')
def create():
    return render_template('create.html')


class Blob:

    VALID_DISCIPLINES = {'binary', 'decimal', 'words', 'dates'}
    VALID_CORRECTIONS = {'kind', 'harsh'}

    def __init__(self, *, discipline, recall_time, correction, data: str,
                 language=None, nr_items=None):
        # Assign values and check for errors in input
        self.discipline = discipline.lower()
        if self.discipline not in self.VALID_DISCIPLINES:
            raise ValueError(f'Invalid discipline: "{discipline}". '
                             'Choose from ' + str(self.VALID_DISCIPLINES))
        self.recall_time = int(recall_time)
        if self.recall_time < 0:
            raise ValueError(f'Recall time cannot be negative: {self.recall_time}')
        self.correction = correction.lower()
        if self.correction not in self.VALID_CORRECTIONS:
            raise ValueError(f'Invalid correction: "{correction}". '
                             'Choose from ' + str(self.VALID_CORRECTIONS))

        if data is None:
            # If data was not provided, we must generate it ourselves.
            # In order to do so we need to know how many items to
            # generate, + language if words or dates.
            assert nr_items is not None, 'Nr_items not provided to blob!'
            self.nr_items = int(nr_items)
            if self.discipline in {'words', 'dates'}:
                assert language is not None, 'Language not provided to blob!'
                self.language = language

            if self.discipline == 'binary':
                self.data = tuple(random.randint(0, 1) for _ in range(self.nr_items))
            elif self.discipline == 'decimal':
                self.data = tuple(random.randint(0, 9) for _ in range(self.nr_items))
            elif self.discipline == 'words':
                words = load_words()  # Language not yet supported
                random.shuffle(words)
                self.data = tuple(words[0:self.nr_items])
            elif self.discipline == 'dates':
                stories = load_dates()  # Language not yet supported
                random.shuffle(stories)
                stories = stories[0:self.nr_items]
                dates = [random.randint(1000,2099) for _ in stories]
                self.data = tuple(zip(dates, stories))
            else:
                raise Exception(f'Data generation for discipline "{self.discipline}" not implemented.')

        else:
            # If data is provided, it's just a matter of parsing the data
            # from the string
            if self.discipline == 'binary':
                self.data = tuple(int(digit) for digit in re.findall('[01]', data))
            elif self.discipline == 'decimal':
                self.data = tuple(int(digit) for digit in re.findall('\d', data))
            elif self.discipline == 'words':
                self.data = tuple(word.strip() for word in data.lower().split('\n') if word.strip())
            elif self.discipline == 'dates':
                historical_dates = list()
                for line in data.split('\n'):
                    if line.strip():
                        date, story = line.split(maxsplit=1)
                        historical_dates.append((date.strip(), story.strip()))
                self.data = tuple(historical_dates)
            else:
                raise Exception(f'Data creation for discipline "{self.discipline}" not implemented.')

    def add_to_database(self):

        blob = {
            'discipline': self.discipline,
            'recall_time': self.recall_time,
            'correction': self.correction,
            'data': self.data
        }

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
        with open(output_file, 'w') as file:
            json.dump(blob, file)
        return h



@app.route('/numbers', methods=['POST'])
def numbers():
    if request.method == 'POST':
        # The request form is a ImmutableMultiDict
        form = request.form
        blob = Blob(
            discipline=form['base'],
            recall_time=form['recall_time'],
            correction=form['correction'],
            data=form.get('data'),
            nr_items=form.get('nr_items')
        )
        h = blob.add_to_database()
        app.logger.info(f'Created blob for numbers: {h}')

        # CREATE XLS DOCUMENT
        description = (
            f"Memorization: {blob.discipline.title()} Numbers, "
            f"{len(blob.data)} digits. "
            f"Recall time: {blob.recall_time} Min"
        )

        if blob.discipline == 'binary':
            table = recall.xls.binary.BinaryTable
        elif blob.discipline == 'decimal':
            table = recall.xls.numbers_.NumberTable
        else:
            raise ValueError('Invalid discipline for Numbers: "{blob.discipline}"')

        w = table(name='Numbers', recall_key=h.upper(),
                  title='Svenska Minnesförbundet',
                  description=description)
        for n in blob.data:
            w.add_item(n)
        w.save(os.path.join(app.root_path, 'static/sheets/' + blob.discipline + '.xls'))
        return render_template('memorize.html',
                               xls_download_link=url_for('static', filename='sheets/' + blob.discipline + '.xls'))
        return str(blob)


@app.route('/words', methods=['POST'])
def words():
    if request.method == 'POST':
        # The request form is a ImmutableMultiDict
        form = request.form
        blob = Blob(
            discipline='words',
            recall_time=form['recall_time'],
            correction=form['correction'],
            data=form.get('data'),
            nr_items=form.get('nr_items'),
            language=form.get('language')
        )
        h = blob.add_to_database()
        app.logger.info(f'Created blob for words: {h}')

        # CREATE XLS DOCUMENT
        description = (
            f"Memorization: {blob.language.title()} Words, "
            f"{len(blob.data)} st. "
            f"Recall time: {blob.recall_time} Min"
        )

        w = recall.xls.words.WordTable(name='Numbers', recall_key=h.upper(),
                                       title='Svenska Minnesförbundet',
                                       description=description)
        for n in blob.data:
            w.add_item(n)
        w.save(os.path.join(app.root_path, 'static/sheets/' + blob.discipline + '.xls'))
        return render_template('memorize.html',
                               xls_download_link=url_for('static', filename='sheets/' + blob.discipline + '.xls'))
        return str(blob)


@app.route('/dates', methods=['POST'])
def dates():
    if request.method == 'POST':
        # The request form is a ImmutableMultiDict
        form = request.form
        blob = Blob(
            discipline='dates',
            recall_time=form['recall_time'],
            correction=form['correction'],
            data=form.get('data'),
            nr_items=form.get('nr_items'),
            language=form.get('language')
        )
        h = blob.add_to_database()
        app.logger.info(f'Created blob for dates: {h}')

        # CREATE XLS DOCUMENT
        description = (
            f"Memorization: {blob.language.title()} Historical Dates, "
            f"{len(blob.data)} st. "
            f"Recall time: {blob.recall_time} Min"
        )

        w = recall.xls.dates.DatesTable(name='Numbers', recall_key=h.upper(),
                                        title='Svenska Minnesförbundet',
                                        description=description)
        for n in blob.data:
            w.add_item(n)
        w.save(os.path.join(app.root_path, 'static/sheets/' + blob.discipline + '.xls'))
        return render_template('memorize.html',
                               xls_download_link=url_for('static', filename='sheets/' + blob.discipline + '.xls'))
        return str(blob)



@app.route('/recall/<string:key>')
def recall_(key):
    blob_file = os.path.join(app.root_path, f'database/{key[0:2]}/{key[2:6]}.json')
    if not os.path.isfile(blob_file):
        return f'No such key exsists: {key}'
    with open(blob_file, 'r') as file:
        blob = json.load(file)
    return render_template('numbers.html', key=key, blob=blob)


def _arbeiter(key, dictionary):
    pass


@app.route('/arbeiter', methods=['POST'])
def arbeiter():
    if request.method == 'POST':
        d = dict(request.form)
        resp = dict()
        key = 'abc123'
        with open(f'database/{key}.txt', 'r') as file:
            data = file.read().split(';')
            for key in d:
                id_ = int(key.split('_')[-1].strip())
                if d[key][0].strip():
                    resp[key] = data[id_] == d[key][0]
                else:
                    resp[key] = None
        app.logger.info(resp)
        return jsonify(resp)
    else:
        print('Wrong method!')

